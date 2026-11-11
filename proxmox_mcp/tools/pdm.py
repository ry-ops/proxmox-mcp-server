"""Proxmox Datacenter Manager tools: many clusters and Backup Servers through one PDM.

The tools come from pdm_spec.json, generated from PDM's API schema by scripts/pdm/gen.py:
every input, pattern and endpoint is PDM's own. A tool that covers both VMs and containers
takes `type` (qemu or lxc); one that reads several parts of a resource takes `section`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .. import tasks

_SPEC = json.loads(Path(__file__).with_name("pdm_spec.json").read_text())
_TOOLS: dict[str, dict[str, Any]] = {t["name"]: t for t in _SPEC["tools"]}

TOOLS = [
    {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
    for t in _SPEC["tools"]
]
NAMES = frozenset(_TOOLS)
READS = frozenset(n for n, t in _TOOLS.items() if t["kind"] == "read")
DESTRUCTIVE = frozenset(n for n, t in _TOOLS.items() if t["kind"] == "destructive")
WAITABLE = frozenset(n for n, t in _TOOLS.items() if t["waitable"])
_PATTERNS = {n: {k: re.compile(p) for k, p in t["patterns"].items()} for n, t in _TOOLS.items()}
_PLACEHOLDER = re.compile(r"\{([^}]+)\}")


def _endpoint(tool: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    endpoints: list[dict[str, Any]] = tool["endpoints"]
    for ep in endpoints:
        if all(args.get(k) == v for k, v in ep.get("when", {}).items()):
            return ep
    choices = {
        k: sorted({e["when"][k] for e in tool["endpoints"]})
        for k in tool["endpoints"][0].get("when", {})
    }
    raise ValueError(
        f"{tool['name']}: choose " + "; ".join(f"{k}: {', '.join(v)}" for k, v in choices.items())
    )


def _check(name: str, tool: dict[str, Any], args: dict[str, Any]) -> None:
    missing = [k for k in tool["inputSchema"]["required"] if args.get(k) is None]
    if missing:
        raise ValueError(f"{name}: missing {', '.join(missing)}")
    known = set(tool["inputSchema"]["properties"])
    unknown = sorted(set(args) - known)
    if unknown:
        raise ValueError(f"{name}: unknown input(s) {', '.join(unknown)}")
    for key, pattern in _PATTERNS[name].items():
        value = args.get(key)
        if value is not None and not pattern.fullmatch(str(value)):
            raise ValueError(f"{name}: {key} {value!r} isn't a valid PDM {key}")
    for key, prop in tool["inputSchema"]["properties"].items():
        value = args.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not (
            prop.get("minLength", 0) <= len(value) <= prop.get("maxLength", len(value))
        ):
            raise ValueError(f"{name}: {key} {value!r} isn't a valid PDM {key} (length)")
        if (
            isinstance(value, int)
            and not isinstance(value, bool)
            and not (prop.get("minimum", value) <= value <= prop.get("maximum", value))
        ):
            raise ValueError(f"{name}: {key} {value} is out of range")


def _path(ep: dict[str, Any], args: dict[str, Any]) -> str:
    # Each value fills exactly one path segment: "/" is encoded, so it can't add segments.
    return _PLACEHOLDER.sub(lambda m: quote(str(args[m[1]]), safe=":!@"), ep["path"])


# Tools that take a remote task ID. PDM wants "remote!UPID:...", but its own lists hand out
# plain "UPID:..." (pdm_pve_list_tasks) and "pve:remote!UPID:..." (pdm_list_remote_tasks).
_REMOTE_TASK_TOOLS = {
    "pdm_pve_task_status", "pdm_pve_task_log", "pdm_pve_stop_task",
    "pdm_pbs_task_status", "pdm_pbs_task_log", "pdm_pbs_stop_task",
}


def remote_task_id(remote: str, upid: str) -> str:
    """Any of the three forms PDM uses, as the "remote!UPID:..." its task endpoints take."""
    upid = str(upid)
    if "!" in upid.split("UPID:", 1)[0]:
        prefix, _, rest = upid.partition("!")
        return f"{prefix.split(':')[-1]}!{rest}"  # drop a "pve:" or "pbs:" product prefix
    return f"{remote}!{upid}"


def request_of(name: str, args: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """The method, path and remaining inputs (query or body) for a tool call."""
    tool = _TOOLS[name]
    if name in _REMOTE_TASK_TOOLS and args.get("upid") and args.get("remote"):
        args = {**args, "upid": remote_task_id(str(args["remote"]), str(args["upid"]))}
    _check(name, tool, args)
    ep = _endpoint(tool, args)
    in_path = set(_PLACEHOLDER.findall(ep["path"]))
    rest = {k: v for k, v in args.items() if k in ep["params"] and k not in in_path}
    for key, value in tool["defaults"].items():
        if key in ep["params"] and key not in in_path:
            rest.setdefault(key, value)
    return ep["method"], _path(ep, args), rest


# Task-status tools whose PDM endpoint takes `wait`. PDM would hold the request open until the
# task ends; this server follows the task instead, with its usual timeout (PROXMOX_WAIT_TIMEOUT).
_STATUS_WAIT = {"pdm_pve_task_status", "pdm_pbs_task_status"}


async def handle(name: str, args: dict[str, Any], client: Any) -> Any:
    if name in _STATUS_WAIT and args.get("wait"):
        args = {k: v for k, v in args.items() if k != "wait"}
        request_of(name, args)  # validate the inputs
        path, node = task_path(name, args, str(args["upid"]))
        return {"data": await tasks.wait(client, str(args["upid"]), task_path=path, node=node)}
    method, path, rest = request_of(name, args)
    if method in ("GET", "DELETE"):
        return await client.request(method, path, params=rest)
    return await client.request(method, path, body=rest)


def task_path(name: str, args: dict[str, Any], upid: str) -> tuple[str, str]:
    """Where to follow a task this tool started, and a label for its node."""
    tool = _TOOLS[name]
    first = tool["endpoints"][0]["path"]
    quoted = quote(upid, safe=":!@")
    if first.startswith("/pve/") or first.startswith("/pbs/"):
        product = first.split("/")[1]
        remote = str(args["remote"])
        quoted = quote(remote_task_id(remote, upid), safe=":!@")
        return f"/{product}/remotes/{quote(remote, safe='')}/tasks/{quoted}", remote
    return f"/nodes/localhost/tasks/{quoted}", "localhost"


def is_task_id(value: Any) -> bool:
    """A Proxmox UPID, or a PDM remote task ID (the remote, then the remote's UPID)."""
    return isinstance(value, str) and "UPID:" in value
