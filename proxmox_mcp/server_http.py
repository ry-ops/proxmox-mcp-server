#!/usr/bin/env python3
"""Streamable-HTTP entrypoint: run the Proxmox MCP server as a network service.

It serves the same tools, MCP `Server` and `ProxmoxClient` as the stdio entrypoint in
server.py, so PROXMOX_TOOLSETS and PROXMOX_READ_ONLY apply unchanged. Only the transport
differs: MCP streamable HTTP at /mcp, served by uvicorn.

Configuration (environment variables), on top of server.py's PROXMOX_* variables:
    MCP_HTTP_HOST           Bind address (default: 127.0.0.1)
    MCP_HTTP_PORT           Bind port (default: 8811)
    MCP_AUTH_TOKEN          Bearer token clients must send. Required on any address other
                            than loopback, unless MCP_HTTP_ALLOW_NO_AUTH=true.
    MCP_HTTP_ALLOW_NO_AUTH  Set to true to serve a non-loopback address with no token,
                            e.g. behind a proxy that authenticates (default: false)

Anyone who can call this endpoint can use every loaded tool with the configured Proxmox
credentials, including deleting VMs and running commands in guests.
"""

from __future__ import annotations

import contextlib
import hmac
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

from .client import PROXMOX_READ_ONLY, _validate_config
from .registry import TOOLSETS as ALL_TOOLSETS
from .server import ALL_TOOLS, TOOLSETS, app, proxmox

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


def check_http_config(host: str, token: str, allow_no_auth: bool) -> None:
    """Refuse to expose the tools on the network without a token, unless explicitly allowed."""
    if token or is_loopback(host) or allow_no_auth:
        return
    raise ValueError(
        f"Refusing to serve on {host} without authentication. Set MCP_AUTH_TOKEN, bind to "
        "127.0.0.1 (MCP_HTTP_HOST), or set MCP_HTTP_ALLOW_NO_AUTH=true if something in front "
        "of this server authenticates clients."
    )


class BearerAuth:
    """ASGI middleware that requires `Authorization: Bearer <token>`."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.expected = f"Bearer {token}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            supplied = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(supplied, self.expected):
                response = JSONResponse(
                    {"error": "unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": 'Bearer realm="proxmox-mcp-server"'},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


class _McpEndpoint:
    """Hands each /mcp request to the session manager (an ASGI app, so Starlette calls it raw)."""

    def __init__(self, manager: StreamableHTTPSessionManager) -> None:
        self.manager = manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.manager.handle_request(scope, receive, send)


async def healthz(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def build_asgi_app(host: str = "127.0.0.1", token: str = "") -> Starlette:
    """The HTTP app. Each call gets its own session manager, which can only run once."""
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
    if token:
        endpoint = BearerAuth(endpoint, token)

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
    token = os.getenv("MCP_AUTH_TOKEN", "")
    allow_no_auth = os.getenv("MCP_HTTP_ALLOW_NO_AUTH", "false").lower() == "true"
    try:
        check_http_config(host, token, allow_no_auth)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    scope = "all toolsets" if len(TOOLSETS) == len(ALL_TOOLSETS) else ", ".join(TOOLSETS)
    mode = ", read-only" if PROXMOX_READ_ONLY else ""
    auth = "bearer token" if token else "NO AUTH"
    print("=" * 60, file=sys.stderr)
    print("Proxmox VE MCP Server (streamable HTTP)", file=sys.stderr)
    print(f"Tools: {len(ALL_TOOLS)} ({scope}{mode})", file=sys.stderr)
    print(f"Listening on http://{host}:{port}/mcp ({auth})", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    uvicorn.run(build_asgi_app(host, token), host=host, port=port)


if __name__ == "__main__":
    run()
