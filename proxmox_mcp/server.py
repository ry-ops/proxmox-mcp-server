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
    PROXMOX_NO_DESTRUCTIVE   Hide tools that delete, stop, wipe or roll back (default: false)
    PROXMOX_PROTECTED_VMIDS  Guest IDs/ranges no tool may change, e.g. 100,9000-9010
    PROXMOX_WAIT_TIMEOUT     Seconds a `wait` lasts before returning (default: 900)
    PROXMOX_AUDIT_LOG        File (or "stderr") for a JSON-lines log of every write call
    PROXMOX_AUDIT_READS      Log read calls too (default: false)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any

import mcp.server.stdio
from mcp.server import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.types import GetPromptResult, Prompt, Resource, ResourceTemplate, TextContent, Tool
from pydantic import AnyUrl

from . import audit, auth, guards, prompts, registry, resources, tasks
from .client import PROXMOX_READ_ONLY, ProxmoxClient, _validate_config

# --- Build the tool registry ---

NO_DESTRUCTIVE = os.getenv("PROXMOX_NO_DESTRUCTIVE", "false").lower() == "true"

try:
    TOOLSETS = registry.parse_toolsets(os.getenv("PROXMOX_TOOLSETS"))
    PROTECTED = guards.parse_protected(os.getenv("PROXMOX_PROTECTED_VMIDS"))
except ValueError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

ALL_TOOLS, TOOL_MODULE = registry.build(
    TOOLSETS, read_only=PROXMOX_READ_ONLY, no_destructive=NO_DESTRUCTIVE
)


def startup_summary() -> str:
    """One line on what this server exposes, for the startup banner."""
    scope = "all toolsets" if len(TOOLSETS) == len(registry.TOOLSETS) else ", ".join(TOOLSETS)
    if PROXMOX_READ_ONLY:
        scope += ", read-only"
    elif NO_DESTRUCTIVE:
        scope += ", no destructive tools"
    if PROTECTED:
        scope += f", {len(PROTECTED)} protected guests"
    if audit.enabled():
        scope += f", audit log: {audit.AUDIT_LOG}"
    return f"Tools: {len(ALL_TOOLS)} ({scope})"


def current_principal() -> auth.Principal:
    """Who sent the request being handled: stdio, or the HTTP token's principal."""
    try:
        request = app.request_context.request
    except LookupError:
        return auth.STDIO
    if request is None:
        return auth.STDIO
    state = getattr(request, "scope", {}).get("state") or {}
    return state.get("principal") or auth.ANONYMOUS


def _dump(value: Any) -> str:
    # Compact JSON: indentation costs the client tokens on every large result.
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, default=str)

# --- MCP server setup ---

proxmox = ProxmoxClient()
app = Server("proxmox-mcp-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    role = current_principal().role
    if role == "admin":
        return ALL_TOOLS
    return [t for t in ALL_TOOLS if auth.allows(role, t.name)]


@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    return prompts.list_prompts()


@app.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    return prompts.get_prompt(name, arguments)


@app.list_resources()
async def list_resources() -> list[Resource]:
    return resources.list_resources()


@app.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    return resources.list_templates()


@app.read_resource()
async def read_resource(uri: AnyUrl) -> list[ReadResourceContents]:
    who = current_principal()
    started = time.monotonic()
    entry: dict[str, Any] = {
        "who": who.name,
        "via": "stdio" if who is auth.STDIO else "http",
        "resource": str(uri),
    }
    try:
        text = await resources.read(proxmox, str(uri))
        entry["outcome"] = "ok"
    except Exception as e:
        entry.update(outcome="error", error=str(e))
        raise
    finally:
        if audit.enabled() and audit.AUDIT_READS:
            entry["ms"] = round((time.monotonic() - started) * 1000)
            audit.record(entry)
    return [ReadResourceContents(content=text, mime_type=resources.MIME)]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    who = current_principal()
    started = time.monotonic()
    args = dict(arguments or {})
    entry: dict[str, Any] = {
        "who": who.name,
        "via": "stdio" if who is auth.STDIO else "http",
        "tool": name,
        "args": audit.redact(args),
    }
    try:
        mod = TOOL_MODULE.get(name)
        if mod is None:
            raise ValueError(
                f"Unknown or disabled tool: {name} (check PROXMOX_TOOLSETS; "
                "PROXMOX_READ_ONLY and PROXMOX_NO_DESTRUCTIVE hide tools)"
            )
        if not auth.allows(who.role, name):
            raise PermissionError(f"{name} is not allowed for {who.name} (role: {who.role})")
        wait = bool(args.pop("wait", False)) and name in registry.WAITABLE
        if not registry.is_read_only(name):
            guards.check(name, args, PROTECTED)
        result = await mod.handle(name, args, proxmox)
        if wait:
            upid = result.get("data") if isinstance(result, dict) else None
            if tasks.is_upid(upid):
                result = {**result, "task": await tasks.wait(proxmox, upid)}
        entry["outcome"] = "ok"
        if isinstance(result, dict):
            if tasks.is_upid(result.get("data")):
                entry["upid"] = result["data"]
            if isinstance(result.get("task"), dict):
                entry["task_ok"] = result["task"].get("ok")
        text = _dump(result)
    except Exception as e:
        entry["outcome"] = "refused" if isinstance(e, PermissionError) else "error"
        entry["error"] = str(e)
        text = _dump({"error": str(e), "tool": name})
    if audit.enabled() and (audit.AUDIT_READS or not registry.is_read_only(name)):
        entry["ms"] = round((time.monotonic() - started) * 1000)
        audit.record(entry)
    return [TextContent(type="text", text=text)]


async def main() -> None:
    _validate_config()

    print("=" * 60, file=sys.stderr)
    print("Proxmox VE MCP Server", file=sys.stderr)
    print(startup_summary(), file=sys.stderr)
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
