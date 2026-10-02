#!/usr/bin/env python3
"""
Proxmox VE MCP Server — full API coverage

Configuration (environment variables):
    PROXMOX_HOST        Proxmox hostname or IP (required)
    PROXMOX_PORT        API port (default: 8006)
    PROXMOX_USER        Username (e.g. root@pam) (required)
    PROXMOX_TOKEN_NAME  API token name (required if no password)
    PROXMOX_TOKEN_VALUE API token value (required if no password)
    PROXMOX_PASSWORD    Password (alternative to token auth)
    PROXMOX_VERIFY_SSL  Verify SSL certs (default: false)
    PROXMOX_READ_ONLY   Block all writes (POST/PUT/DELETE); GET only (default: false)

Transport (environment variables):
    MCP_TRANSPORT       "stdio" (default) or "http" (streamable-HTTP for remote clients)
    MCP_HOST            HTTP bind host (default: 0.0.0.0)  [http only]
    MCP_PORT            HTTP bind port (default: 8080)     [http only]
    MCP_AUTH_TOKEN      If set, require "Authorization: Bearer <token>" [http only]
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import TextContent, Tool
import mcp.server.stdio

from .client import ProxmoxClient, _validate_config
from .tools import (
    acme,
    access,
    ceph,
    cluster,
    disks,
    firewall,
    lxc,
    nodes,
    notifications,
    pools,
    qemu,
    sdn,
    storage,
)

load_dotenv()

MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").lower()
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8080"))
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

# --- Build unified tool registry ---

MODULES = [
    nodes,
    qemu,
    lxc,
    storage,
    cluster,
    access,
    firewall,
    disks,
    ceph,
    acme,
    sdn,
    notifications,
    pools,
]

ALL_TOOLS: list[Tool] = []
TOOL_MODULE: dict[str, Any] = {}

for mod in MODULES:
    for tool_def in mod.TOOLS:
        t = Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            inputSchema=tool_def["inputSchema"],
        )
        ALL_TOOLS.append(t)
        TOOL_MODULE[tool_def["name"]] = mod

# --- MCP server setup ---

proxmox = ProxmoxClient()
app = Server("proxmox-mcp-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return ALL_TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    try:
        mod = TOOL_MODULE.get(name)
        if mod is None:
            raise ValueError(f"Unknown tool: {name}")
        result = await mod.handle(name, arguments or {}, proxmox)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        error = {"error": str(e), "tool": name}
        return [TextContent(type="text", text=json.dumps(error, indent=2))]


def _authorized(headers: list[tuple[bytes, bytes]]) -> bool:
    # ponytail: single static token; swap for OAuth only if per-identity is needed.
    if not MCP_AUTH_TOKEN:
        return True
    auth = dict(headers).get(b"authorization", b"").decode()
    return auth == f"Bearer {MCP_AUTH_TOKEN}"


def _banner() -> None:
    print("=" * 60, file=sys.stderr)
    print("Proxmox VE MCP Server", file=sys.stderr)
    print(f"Transport: {MCP_TRANSPORT}", file=sys.stderr)
    print(f"Tools: {len(ALL_TOOLS)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


async def _serve_stdio() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


async def _serve_http() -> None:
    # Imported lazily so stdio deployments don't need starlette/uvicorn.
    import contextlib

    import uvicorn
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Mount, Route

    session_manager = StreamableHTTPSessionManager(app=app, stateless=True)

    async def handle_mcp(scope: Any, receive: Any, send: Any) -> None:
        if not _authorized(scope.get("headers") or []):
            await PlainTextResponse("Unauthorized", status_code=401)(scope, receive, send)
            return
        await session_manager.handle_request(scope, receive, send)

    async def health(_request):
        return PlainTextResponse("ok")

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette):
        async with session_manager.run():
            yield

    # /health is unauthenticated for infra probes. Mount MCP at root (like the
    # vita relay) so the endpoint is the host URL itself and there's no
    # trailing-slash redirect that would sidestep the auth check.
    star = Starlette(
        routes=[Route("/health", health), Mount("/", app=handle_mcp)],
        lifespan=lifespan,
    )
    auth_state = "on" if MCP_AUTH_TOKEN else "off"
    print(f"✓ HTTP on {MCP_HOST}:{MCP_PORT}/ — auth: {auth_state}", file=sys.stderr)
    config = uvicorn.Config(star, host=MCP_HOST, port=MCP_PORT, log_level="info")
    await uvicorn.Server(config).serve()


async def main() -> None:
    _validate_config()
    _banner()
    await proxmox.authenticate()
    print(f"✓ Ready — {len(ALL_TOOLS)} tools available", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    if MCP_TRANSPORT == "http":
        await _serve_http()
    else:
        await _serve_stdio()


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Server stopped", file=sys.stderr)
    except Exception as e:
        print(f"\n✗ Fatal: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        asyncio.run(proxmox.close())


if __name__ == "__main__":
    run()
