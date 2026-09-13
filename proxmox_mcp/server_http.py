#!/usr/bin/env python3
"""Streamable-HTTP entrypoint for the Proxmox MCP server.

Upstream ships only a stdio transport (a client-spawned subprocess),
which doesn't work for a server meant to run as a standalone network
service. This reuses the exact same tool registry, `Server` app, and
`ProxmoxClient` built in `server.py` and swaps only the transport:
streamable HTTP (via `StreamableHTTPSessionManager`, mounted at `/mcp`)
over uvicorn instead of stdio pipes.

Configuration (environment variables):
    All of server.py's PROXMOX_* variables, plus:
    MCP_HTTP_HOST   Bind address (default: 0.0.0.0)
    MCP_HTTP_PORT   Bind port (default: 8811)
"""

from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import AsyncIterator

import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

from .client import _validate_config
from .server import app, proxmox

HTTP_HOST = os.getenv("MCP_HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("MCP_HTTP_PORT", "8811"))

# Only one StreamableHTTPSessionManager may exist per process (see its
# docstring), so it's built once at module scope alongside the `app`
# and `proxmox` instances imported from server.py.
session_manager = StreamableHTTPSessionManager(app=app)


async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
    await session_manager.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(_: Starlette) -> AsyncIterator[None]:
    await proxmox.authenticate()
    async with session_manager.run():
        try:
            yield
        finally:
            await proxmox.close()


def build_asgi_app() -> Starlette:
    return Starlette(
        routes=[Mount("/mcp", app=handle_streamable_http)],
        lifespan=lifespan,
    )


def run() -> None:
    _validate_config()
    print(f"Proxmox MCP Server (HTTP) listening on {HTTP_HOST}:{HTTP_PORT}, path /mcp", file=sys.stderr)
    uvicorn.run(build_asgi_app(), host=HTTP_HOST, port=HTTP_PORT)


if __name__ == "__main__":
    run()
