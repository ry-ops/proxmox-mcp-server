"""Task tools that every toolset needs: waiting for a task (UPID) to finish."""

from __future__ import annotations

from typing import Any

from .. import tasks
from ..client import ProxmoxClient

TOOLS = [
    {
        "name": "wait_for_task",
        "description": (
            "Wait for a Proxmox task to finish, given the UPID that clone, migrate, backup, "
            "restore, disk-move or power actions return. Returns status, exitstatus and ok; a "
            "failed task includes the end of its log. If the task is still running when the "
            "timeout ends, it returns status 'running' so you can call this again."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "upid": {"type": "string", "description": "Task ID, starting with UPID:"},
                "timeout": {
                    "type": "integer",
                    "description": "Seconds to wait before returning (default 900, max 3600)",
                },
            },
            "required": ["upid"],
        },
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    if name == "wait_for_task":
        return await tasks.wait(client, args["upid"], args.get("timeout"))
    raise ValueError(f"Unknown tool: {name}")
