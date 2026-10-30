"""Wait for Proxmox tasks (UPIDs) to finish.

Most long operations (clone, migrate, backup, restore, disk moves, power actions) return a
task ID, a UPID such as "UPID:pve1:0003A1B2:01C9D3E4:6720F0A1:qmclone:100:root@pam:". The node
that runs the task is its second field, so waiting needs nothing but the UPID.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from .client import ProxmoxClient

# How long a wait lasts before it returns with the task still running (seconds).
DEFAULT_TIMEOUT = float(os.getenv("PROXMOX_WAIT_TIMEOUT", "900"))
MAX_TIMEOUT = 3600.0
LOG_TAIL = 20


def upid_node(upid: Any) -> str:
    """The node a task runs on, from its UPID."""
    parts = str(upid).split(":")
    if len(parts) < 3 or parts[0] != "UPID" or not parts[1]:
        raise ValueError(f"Not a Proxmox task ID (UPID): {upid!r}")
    return parts[1]


def is_upid(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("UPID:")


async def wait(
    client: ProxmoxClient, upid: str, timeout: float | None = None, poll: float = 1.0
) -> dict[str, Any]:
    """Wait for a task to stop, up to `timeout` seconds.

    Never raises for a slow or failed task: it reports the outcome, so the caller can decide.
    The result has `upid`, `node`, `status` ("stopped" or "running"), `exitstatus` and
    `ok` (true only for exitstatus "OK"). A failed task also carries the end of its log.
    """
    node = upid_node(upid)
    limit = min(max(float(timeout if timeout is not None else DEFAULT_TIMEOUT), 0.0), MAX_TIMEOUT)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + limit
    path = f"/nodes/{node}/tasks/{upid}"
    while True:
        status = (await client.get(f"{path}/status")).get("data") or {}
        if status.get("status") == "stopped":
            exitstatus = status.get("exitstatus")
            result: dict[str, Any] = {
                "upid": upid,
                "node": node,
                "status": "stopped",
                "exitstatus": exitstatus,
                "ok": exitstatus == "OK",
            }
            if exitstatus != "OK":
                log = (await client.get(f"{path}/log", {"start": 0, "limit": 5000})).get("data") or []
                result["log_tail"] = [line.get("t", "") for line in log[-LOG_TAIL:]]
            return result
        remaining = deadline - loop.time()
        if remaining <= 0:
            return {
                "upid": upid,
                "node": node,
                "status": "running",
                "ok": None,
                "note": f"Still running after {limit:.0f}s. Call wait_for_task with this upid to keep waiting.",
            }
        await asyncio.sleep(min(poll, remaining))
        poll = min(poll * 1.5, 5.0)
