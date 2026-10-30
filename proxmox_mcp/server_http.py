#!/usr/bin/env python3
"""Streamable-HTTP entrypoint: run the Proxmox MCP server as a network service.

It serves the same tools, MCP `Server` and `ProxmoxClient` as the stdio entrypoint in
server.py, so PROXMOX_TOOLSETS and PROXMOX_READ_ONLY apply unchanged. Only the transport
differs: MCP streamable HTTP at /mcp, served by uvicorn.

Configuration (environment variables), on top of server.py's PROXMOX_* variables:
    MCP_HTTP_HOST           Bind address (default: 127.0.0.1)
    MCP_HTTP_PORT           Bind port (default: 8811)
    MCP_AUTH_TOKEN          Bearer token clients must send (an admin token named "default").
    MCP_AUTH_TOKENS         Several tokens with roles: name:role:token,... (see auth.py)
    MCP_AUTH_TOKENS_FILE    The same, one "name role token" per line
                            A token is required on any address other than loopback,
                            unless MCP_HTTP_ALLOW_NO_AUTH=true.
    MCP_HTTP_ALLOW_NO_AUTH  Set to true to serve a non-loopback address with no token,
                            e.g. behind a proxy that authenticates (default: false)

Anyone who can call this endpoint can use every loaded tool with the configured Proxmox
credentials, including deleting VMs and running commands in guests.
"""

from __future__ import annotations

import contextlib
import ipaddress
import os
import sys
from collections.abc import AsyncIterator

import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from . import auth
from .client import _validate_config
from .server import app, proxmox, startup_summary

# Clients reach a loopback-bound server under these Host/Origin values.
_LOOPBACK_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
_LOOPBACK_ORIGINS = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]


def is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def check_http_config(host: str, token: object, allow_no_auth: bool) -> None:
    """Refuse to expose the tools on the network without a token, unless explicitly allowed."""
    if token or is_loopback(host) or allow_no_auth:
        return
    raise ValueError(
        f"Refusing to serve on {host} without authentication. Set MCP_AUTH_TOKEN(S), bind to "
        "127.0.0.1 (MCP_HTTP_HOST), or set MCP_HTTP_ALLOW_NO_AUTH=true if something in front "
        "of this server authenticates clients."
    )


class BearerAuth:
    """ASGI middleware that requires `Authorization: Bearer <token>` from a known principal,
    and records who it is in the request scope for the tool handlers."""

    def __init__(self, app: ASGIApp, principals: list[auth.Principal]) -> None:
        self.app = app
        self.principals = principals

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            supplied = dict(scope["headers"]).get(b"authorization", b"")
            principal = auth.authenticate(supplied, self.principals)
            if principal is None:
                response = JSONResponse(
                    {"error": "unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": 'Bearer realm="proxmox-mcp-server"'},
                )
                await response(scope, receive, send)
                return
            scope.setdefault("state", {})["principal"] = principal
        await self.app(scope, receive, send)


class _McpEndpoint:
    """Hands each /mcp request to the session manager (an ASGI app, so Starlette calls it raw)."""

    def __init__(self, manager: StreamableHTTPSessionManager) -> None:
        self.manager = manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.manager.handle_request(scope, receive, send)


async def healthz(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def build_asgi_app(
    host: str = "127.0.0.1", token: str = "", principals: list[auth.Principal] | None = None
) -> Starlette:
    """The HTTP app. Each call gets its own session manager, which can only run once.

    `token` is a single admin token; `principals` are named tokens with roles.
    """
    principals = list(principals or [])
    if token:
        principals.insert(0, auth.Principal("default", "admin", token))
    security = None
    if is_loopback(host):
        # Stop web pages from reaching a local server through DNS rebinding.
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=_LOOPBACK_HOSTS,
            allowed_origins=_LOOPBACK_ORIGINS,
        )
    manager = StreamableHTTPSessionManager(app=app, security_settings=security)
    endpoint: ASGIApp = _McpEndpoint(manager)
    if principals:
        endpoint = BearerAuth(endpoint, principals)

    @contextlib.asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        await proxmox.authenticate()
        try:
            async with manager.run():
                yield
        finally:
            await proxmox.close()

    return Starlette(
        routes=[
            Route("/healthz", healthz, methods=["GET"]),
            Route("/mcp", endpoint),
            Route("/mcp/", endpoint),
        ],
        lifespan=lifespan,
    )


def run() -> None:
    _validate_config()
    host = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_HTTP_PORT", "8811"))
    allow_no_auth = os.getenv("MCP_HTTP_ALLOW_NO_AUTH", "false").lower() == "true"
    try:
        principals = auth.load_principals(
            os.getenv("MCP_AUTH_TOKENS"),
            os.getenv("MCP_AUTH_TOKENS_FILE"),
            os.getenv("MCP_AUTH_TOKEN"),
        )
        check_http_config(host, principals, allow_no_auth)
    except (ValueError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if principals:
        who = ", ".join(f"{p.name} ({p.role})" for p in principals)
        mode = f"{len(principals)} token(s): {who}"
    else:
        mode = "NO AUTH"
    print("=" * 60, file=sys.stderr)
    print("Proxmox VE MCP Server (streamable HTTP)", file=sys.stderr)
    print(startup_summary(), file=sys.stderr)
    print(f"Listening on http://{host}:{port}/mcp ({mode})", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    uvicorn.run(build_asgi_app(host, principals=principals), host=host, port=port)


if __name__ == "__main__":
    run()
