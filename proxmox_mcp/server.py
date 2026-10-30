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
    PROXMOX_TOOLSETS    Comma-separated API areas to load, e.g. nodes,qemu,lxc (default: all)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

import mcp.server.stdio
from mcp.server import Server
from mcp.types import TextContent, Tool

from . import registry
from .client import PROXMOX_READ_ONLY, ProxmoxClient, _validate_config

# --- Build the tool registry ---

try:
    TOOLSETS = registry.parse_toolsets(os.getenv("PROXMOX_TOOLSETS"))
except ValueError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

ALL_TOOLS, TOOL_MODULE = registry.build(TOOLSETS, read_only=PROXMOX_READ_ONLY)

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
            raise ValueError(
                f"Unknown or disabled tool: {name} "
                "(check PROXMOX_TOOLSETS, and PROXMOX_READ_ONLY hides write tools)"
            )
        result = await mod.handle(name, arguments or {}, proxmox)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        error = {"error": str(e), "tool": name}
        return [TextContent(type="text", text=json.dumps(error, indent=2))]


async def main() -> None:
    _validate_config()

    print("=" * 60, file=sys.stderr)
    print("Proxmox VE MCP Server", file=sys.stderr)
    scope = "all toolsets" if len(TOOLSETS) == len(registry.TOOLSETS) else ", ".join(TOOLSETS)
    mode = ", read-only" if PROXMOX_READ_ONLY else ""
    print(f"Tools: {len(ALL_TOOLS)} ({scope}{mode})", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Close the HTTP client in this event loop: its connections are bound to it.
    try:
        await proxmox.authenticate()

        print(f"✓ Ready — {len(ALL_TOOLS)} tools available", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
    finally:
        await proxmox.close()


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Server stopped", file=sys.stderr)
    except Exception as e:
        print(f"\n✗ Fatal: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
