"""Tool registry: which tools load, and how each one is labelled for MCP clients.

Two levers keep the tool list small, because every advertised tool's schema sits in the
client's context on every turn (all 341 cost about 44k tokens):

* PROXMOX_TOOLSETS picks the API areas to load, e.g. "nodes,qemu,lxc,storage".
* Read-only mode advertises only the tools that read; the others would be refused anyway.

Every tool also carries MCP annotations (readOnlyHint, destructiveHint) so clients can
auto-approve reads and ask before anything that deletes, stops or overwrites.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

from mcp.types import Tool, ToolAnnotations

from .tools import (
    access,
    acme,
    appliances,
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
    tasks,
)

# Toolset name -> module. The order here is the order tools are advertised in.
TOOLSETS: dict[str, ModuleType] = {
    "nodes": nodes,
    "qemu": qemu,
    "lxc": lxc,
    "storage": storage,
    "cluster": cluster,
    "access": access,
    "firewall": firewall,
    "disks": disks,
    "ceph": ceph,
    "acme": acme,
    "sdn": sdn,
    "notifications": notifications,
    "pools": pools,
    "appliances": appliances,
}

# Loaded with every toolset selection: tools any of them may need.
CORE = [tasks]

# Long-running tools that return a task ID (UPID). They accept `wait: true` to return only
# once the task has finished.
WAITABLE = {
    "start_vm", "stop_vm", "shutdown_vm", "reboot_vm",
    "start_container", "stop_container", "shutdown_container", "reboot_container",
    "create_vm", "clone_vm", "delete_vm", "migrate_vm", "move_vm_disk",
    "create_container", "clone_container", "delete_container", "migrate_container",
    "move_container_disk",
    "create_vm_snapshot", "rollback_vm_snapshot", "delete_vm_snapshot",
    "create_container_snapshot", "rollback_container_snapshot", "delete_container_snapshot",
    "backup_vm", "restore_vm_backup", "restore_container_backup",
    "download_url_to_storage",
}
WAIT_PROPERTY = {
    "type": "boolean",
    "description": "Wait for the task to finish and return its outcome (default false)",
}

# Friendlier names people reach for first.
ALIASES = {"vms": "qemu", "vm": "qemu", "containers": "lxc", "ct": "lxc"}

# Tools whose name does not say what they do to the cluster.
# These only GET, though their names do not start with get_/list_:
_READS = {"vm_agent_exec_status", "wait_for_task"}
# These POST (they open a console ticket), though their names start with get_:
_WRITES = {"get_vm_vnc_proxy", "get_vm_spice_proxy"}

# Writes that remove, stop, overwrite or irreversibly change something.
_DESTRUCTIVE_PREFIXES = (
    "delete_",
    "wipe_",
    "rollback_",
    "revert_",
    "reset_",
    "stop_",
    "shutdown_",
    "reboot_",
    "restore_",
    "deregister_",
    "revoke_",
    "unlink_",
    "convert_",
)
_DESTRUCTIVE = {
    "node_shutdown",
    "node_stopall",
    "bulk_shutdown_guests",
    "init_disk_gpt",
    "vm_agent_exec",
    "vm_agent_set_user_password",
    "change_user_password",
}


def is_read_only(name: str) -> bool:
    """True when the tool only issues GET requests."""
    if name in _READS:
        return True
    if name in _WRITES:
        return False
    return name.startswith(("get_", "list_", "vm_agent_get_"))


def is_destructive(name: str) -> bool:
    """True when the tool can remove, stop, overwrite or irreversibly change something."""
    return name.startswith(_DESTRUCTIVE_PREFIXES) or name in _DESTRUCTIVE


def parse_toolsets(value: str | None) -> list[str]:
    """Turn a PROXMOX_TOOLSETS value into toolset names. Empty or "all" means every toolset."""
    names = [n.strip().lower() for n in (value or "").split(",") if n.strip()]
    if not names or "all" in names:
        return list(TOOLSETS)
    chosen: list[str] = []
    unknown: list[str] = []
    for n in names:
        n = ALIASES.get(n, n)
        if n not in TOOLSETS:
            unknown.append(n)
        elif n not in chosen:
            chosen.append(n)
    if unknown:
        raise ValueError(
            f"Unknown PROXMOX_TOOLSETS value(s): {', '.join(unknown)}. "
            f"Choose from: {', '.join(TOOLSETS)} (or all)"
        )
    return [n for n in TOOLSETS if n in chosen]


def build(
    toolsets: list[str], read_only: bool, no_destructive: bool = False
) -> tuple[list[Tool], dict[str, ModuleType]]:
    """The tools to advertise, and the module that handles each one.

    read_only drops every write tool; no_destructive drops only the destructive ones.
    """
    tools: list[Tool] = []
    handlers: dict[str, Any] = {}
    for mod in [TOOLSETS[ts] for ts in toolsets] + CORE:
        for d in mod.TOOLS:
            name = d["name"]
            ro = is_read_only(name)
            if read_only and not ro:
                continue
            if no_destructive and is_destructive(name):
                continue
            schema = d["inputSchema"]
            if name in WAITABLE:
                schema = {**schema, "properties": {**schema.get("properties", {}), "wait": WAIT_PROPERTY}}
            tools.append(
                Tool(
                    name=name,
                    description=d["description"],
                    input_schema=schema,
                    annotations=ToolAnnotations(
                        read_only_hint=ro,
                        destructive_hint=False if ro else is_destructive(name),
                    ),
                )
            )
            handlers[name] = mod
    return tools, handlers
