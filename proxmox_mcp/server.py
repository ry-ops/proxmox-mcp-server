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
"""

from __future__ import annotations

import asyncio
import json
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


async def main() -> None:
    _validate_config()

    print("=" * 60, file=sys.stderr)
    print("Proxmox VE MCP Server", file=sys.stderr)
    print(f"Tools: {len(ALL_TOOLS)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    await proxmox.authenticate()

    print(f"✓ Ready — {len(ALL_TOOLS)} tools available", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


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
