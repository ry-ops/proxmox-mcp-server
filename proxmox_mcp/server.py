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
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import mcp.server.stdio
from mcp.server import Server, ServerRequestContext
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    GetPromptRequestParams,
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    PaginatedRequestParams,
    ReadResourceRequestParams,
    ReadResourceResult,
    TextContent,
    TextResourceContents,
    Tool,
)

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


def principal_of(request: Any) -> auth.Principal:
    """Who sent a request: stdio (no HTTP request), or the principal the HTTP auth set."""
    if request is None:
        return auth.STDIO
    state = getattr(request, "scope", {}).get("state") or {}
    return state.get("principal") or auth.ANONYMOUS


def _dump(value: Any) -> str:
    # Compact JSON: indentation costs the client tokens on every large result.
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, default=str)


def _via(who: auth.Principal) -> str:
    return "stdio" if who is auth.STDIO else "http"


try:
    VERSION = version("proxmox-mcp-server")
except PackageNotFoundError:  # running from a source tree that isn't installed
    VERSION = "0"

proxmox = ProxmoxClient()


# --- What each handler does, with the caller passed in ---


def list_tools(who: auth.Principal = auth.STDIO) -> list[Tool]:
    if who.role == "admin":
        return ALL_TOOLS
    return [t for t in ALL_TOOLS if auth.allows(who.role, t.name)]


async def call_tool(name: str, arguments: Any, who: auth.Principal = auth.STDIO) -> CallToolResult:
    started = time.monotonic()
    args = dict(arguments or {})
    entry: dict[str, Any] = {
        "who": who.name,
        "via": _via(who),
        "tool": name,
        "args": audit.redact(args),
    }
    failed = False
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
        failed = True
        entry["outcome"] = "refused" if isinstance(e, PermissionError) else "error"
        entry["error"] = str(e)
        text = _dump({"error": str(e), "tool": name})
    if audit.enabled() and (audit.AUDIT_READS or not registry.is_read_only(name)):
        entry["ms"] = round((time.monotonic() - started) * 1000)
        audit.record(entry)
    return CallToolResult(content=[TextContent(type="text", text=text)], isError=failed)


async def read_resource(uri: str, who: auth.Principal = auth.STDIO) -> ReadResourceResult:
    started = time.monotonic()
    entry: dict[str, Any] = {"who": who.name, "via": _via(who), "resource": uri}
    try:
        text = await resources.read(proxmox, uri)
        entry["outcome"] = "ok"
    except Exception as e:
        entry.update(outcome="error", error=str(e))
        raise
    finally:
        if audit.enabled() and audit.AUDIT_READS:
            entry["ms"] = round((time.monotonic() - started) * 1000)
            audit.record(entry)
    return ReadResourceResult(
        contents=[TextResourceContents(uri=uri, mimeType=resources.MIME, text=text)]
    )


# --- MCP protocol handlers ---


async def _on_list_tools(
    ctx: ServerRequestContext, _: PaginatedRequestParams | None
) -> ListToolsResult:
    return ListToolsResult(tools=list_tools(principal_of(ctx.request)))


async def _on_call_tool(ctx: ServerRequestContext, params: CallToolRequestParams) -> CallToolResult:
    return await call_tool(params.name, params.arguments, principal_of(ctx.request))


async def _on_list_prompts(
    _: ServerRequestContext, __: PaginatedRequestParams | None
) -> ListPromptsResult:
    return ListPromptsResult(prompts=prompts.list_prompts())


async def _on_get_prompt(
    _: ServerRequestContext, params: GetPromptRequestParams
) -> GetPromptResult:
    return prompts.get_prompt(params.name, params.arguments)


async def _on_list_resources(
    _: ServerRequestContext, __: PaginatedRequestParams | None
) -> ListResourcesResult:
    return ListResourcesResult(resources=resources.list_resources())


async def _on_list_resource_templates(
    _: ServerRequestContext, __: PaginatedRequestParams | None
) -> ListResourceTemplatesResult:
    return ListResourceTemplatesResult(resourceTemplates=resources.list_templates())


async def _on_read_resource(
    ctx: ServerRequestContext, params: ReadResourceRequestParams
) -> ReadResourceResult:
    return await read_resource(str(params.uri), principal_of(ctx.request))


app = Server(
    "proxmox-mcp-server",
    version=VERSION,
    on_list_tools=_on_list_tools,
    on_call_tool=_on_call_tool,
    on_list_prompts=_on_list_prompts,
    on_get_prompt=_on_get_prompt,
    on_list_resources=_on_list_resources,
    on_list_resource_templates=_on_list_resource_templates,
    on_read_resource=_on_read_resource,
)


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
