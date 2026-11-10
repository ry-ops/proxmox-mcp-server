#!/usr/bin/env python3
"""
Proxmox VE MCP Server — full API coverage, plus Proxmox Datacenter Manager

Configuration (environment variables). Set PROXMOX_HOST, PDM_HOST, or both:
    PROXMOX_HOST        Proxmox VE hostname or IP
    PROXMOX_PORT        API port (default: 8006)
    PROXMOX_USER        Username (e.g. root@pam) (required)
    PROXMOX_TOKEN_NAME  API token name (required if no password)
    PROXMOX_TOKEN_VALUE API token value (required if no password)
    PROXMOX_PASSWORD    Password (alternative to token auth)
    PROXMOX_VERIFY_SSL  Verify SSL certs (default: false)
    PROXMOX_CA_BUNDLE   CA file to verify the Proxmox certificate against, e.g. pve-root-ca.pem
    PROXMOX_READ_ONLY   Block all writes (POST/PUT/DELETE); GET only (default: false)
    PROXMOX_TOOLSETS    Comma-separated API areas to load, e.g. nodes,qemu,lxc (default: all)
    PROXMOX_NO_DESTRUCTIVE   Hide tools that delete, stop, wipe or roll back (default: false)
    PROXMOX_PROTECTED_VMIDS  Guest IDs/ranges no tool may change, e.g. 100,9000-9010
    PROXMOX_WAIT_TIMEOUT     Seconds a `wait` lasts before returning (default: 900)
    PROXMOX_AUDIT_LOG        File (or "stderr") for a JSON-lines log of every write call
    PROXMOX_AUDIT_READS      Log read calls too (default: false)
    PDM_HOST, PDM_PORT, PDM_TOKEN_ID, PDM_TOKEN_SECRET, PDM_CA_BUNDLE, PDM_TLS_NAME, PDM_VERIFY_SSL
                             Proxmox Datacenter Manager; loads the `pdm` toolset (see pdm_client.py)
    PDM_PROTECTED_GUESTS     remote:ID entries PDM tools may not change, e.g. pve01:104,*:9000-9010
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

from . import audit, auth, guards, pdm_client, prompts, registry, resources, tasks
from .client import PROXMOX_HOST, PROXMOX_READ_ONLY, ProxmoxClient, tls_warning
from .client import _validate_config as _validate_pve_config
from .tools import pdm as pdm_tools

# --- Build the tool registry ---

NO_DESTRUCTIVE = os.getenv("PROXMOX_NO_DESTRUCTIVE", "false").lower() == "true"



def select_toolsets(requested: str | None, pve: bool, pdm: bool) -> tuple[list[str], bool]:
    """The toolsets to load and whether to add the Proxmox VE core tools.

    The `pdm` toolset needs PDM_HOST. With PDM_HOST but no PROXMOX_HOST, only `pdm` loads.
    """
    chosen = registry.parse_toolsets(requested)
    explicit = bool(requested and requested.strip().lower() not in ("", "all"))
    if not pdm and "pdm" in chosen:
        if explicit:
            raise ValueError("The pdm toolset needs PDM_HOST (Proxmox Datacenter Manager)")
        chosen.remove("pdm")
    if pdm and not pve:
        pve_sets = [t for t in chosen if t != "pdm"]
        if explicit and pve_sets:
            raise ValueError(f"Toolsets {', '.join(pve_sets)} need PROXMOX_HOST (Proxmox VE)")
        return [t for t in chosen if t == "pdm"], False
    return chosen, True


try:
    TOOLSETS, WITH_CORE = select_toolsets(
        os.getenv("PROXMOX_TOOLSETS"), bool(PROXMOX_HOST), pdm_client.configured()
    )
    PROTECTED = guards.parse_protected(os.getenv("PROXMOX_PROTECTED_VMIDS"))
    PDM_PROTECTED = guards.parse_pdm_protected(os.getenv("PDM_PROTECTED_GUESTS"))
except ValueError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

ALL_TOOLS, TOOL_MODULE = registry.build(
    TOOLSETS, read_only=PROXMOX_READ_ONLY, no_destructive=NO_DESTRUCTIVE, core=WITH_CORE
)
SCHEMAS = {t.name: t.input_schema for t in ALL_TOOLS}


def startup_summary() -> str:
    """One line on what this server exposes, for the startup banner."""
    available = (registry.PVE_TOOLSETS if PROXMOX_HOST else []) + (
        ["pdm"] if pdm_client.configured() else []
    )
    scope = "all toolsets" if set(TOOLSETS) >= set(available) else ", ".join(TOOLSETS)
    if PROXMOX_READ_ONLY:
        scope += ", read-only"
    elif NO_DESTRUCTIVE:
        scope += ", no destructive tools"
    if PROTECTED:
        scope += f", {len(PROTECTED)} protected guests"
    if PDM_PROTECTED:
        scope += f", {sum(len(v) for v in PDM_PROTECTED.values())} protected PDM guests"
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
pdm = pdm_client.PdmClient()


def _validate_config() -> None:
    """Check the settings before serving: Proxmox VE, Datacenter Manager, or both."""
    if not PROXMOX_HOST and not pdm_client.configured():
        print(
            "Error: set PROXMOX_HOST (Proxmox VE), PDM_HOST (Proxmox Datacenter Manager), or both",
            file=sys.stderr,
        )
        sys.exit(1)
    _validate_pve_config()
    pdm_client.startup_errors()


def tls_warnings() -> list[str]:
    return [w for w in (tls_warning(), pdm_client.tls_warning()) if w]


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
        "args": audit.redact(args, name),
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
        # Only tools that wait take `wait` away: some PDM endpoints have a `wait` of their own.
        wait = name in registry.WAITABLE and bool(args.pop("wait", False))
        guards.check_args(name, args, SCHEMAS.get(name))
        is_pdm = mod is pdm_tools
        if not registry.is_read_only(name):
            if is_pdm:
                guards.check_pdm(name, args, PDM_PROTECTED)
            else:
                guards.check(name, args, PROTECTED)
        result = await mod.handle(name, args, pdm if is_pdm else proxmox)
        upid = result.get("data") if isinstance(result, dict) else None
        if wait and isinstance(upid, str):
            if is_pdm and pdm_tools.is_task_id(upid):
                path, node = pdm_tools.task_path(name, args, upid)
                task = await tasks.wait(pdm, upid, task_path=path, node=node)
                result = {**result, "task": task}
            elif tasks.is_upid(upid):
                result = {**result, "task": await tasks.wait(proxmox, upid)}
        entry["outcome"] = "ok"
        if isinstance(result, dict):
            if tasks.is_upid(upid) or (is_pdm and pdm_tools.is_task_id(upid)):
                entry["upid"] = upid
            if isinstance(result.get("task"), dict):
                entry["task_ok"] = result["task"].get("ok")
        text = _dump(result)
    except Exception as e:
        failed = True
        entry["outcome"] = "refused" if isinstance(e, PermissionError) else "error"
        # Some exceptions have no message; an empty error string tells the client nothing.
        entry["error"] = str(e) or type(e).__name__
        text = _dump({"error": entry["error"], "tool": name})
    if audit.enabled() and (audit.AUDIT_READS or not registry.is_read_only(name)):
        entry["ms"] = round((time.monotonic() - started) * 1000)
        audit.record(entry)
    return CallToolResult(content=[TextContent(type="text", text=text)], is_error=failed)


async def read_resource(uri: str, who: auth.Principal = auth.STDIO) -> ReadResourceResult:
    started = time.monotonic()
    entry: dict[str, Any] = {"who": who.name, "via": _via(who), "resource": uri}
    try:
        text = await resources.read(proxmox, uri)
        entry["outcome"] = "ok"
    except Exception as e:
        entry.update(outcome="error", error=str(e) or type(e).__name__)
        raise
    finally:
        if audit.enabled() and audit.AUDIT_READS:
            entry["ms"] = round((time.monotonic() - started) * 1000)
            audit.record(entry)
    return ReadResourceResult(
        contents=[TextResourceContents(uri=uri, mime_type=resources.MIME, text=text)]
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
    return ListResourceTemplatesResult(resource_templates=resources.list_templates())


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
    for warning in tls_warnings():
        print(warning, file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Close the HTTP clients in this event loop: their connections are bound to it.
    try:
        if PROXMOX_HOST or not pdm_client.configured():  # not PDM-only
            await proxmox.authenticate()
        if pdm_client.configured():
            print(f"✓ Datacenter Manager: {pdm_client.PDM_HOST} ({pdm_client.PDM_TOKEN_ID})", file=sys.stderr)

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
        await pdm.close()


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
