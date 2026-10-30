"""MCP prompts: ready-made Proxmox workflows a client can offer by name.

Each prompt expands into instructions that name real tools in `backticks`; a test checks every
name against the registry. Prompts never act on their own: the model still calls the tools, and
the server's roles, read-only mode and protected guests still apply.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from mcp.types import GetPromptResult, Prompt, PromptArgument, PromptMessage, TextContent


@dataclass(frozen=True)
class Spec:
    name: str
    title: str
    description: str
    render: Callable[[dict[str, str]], str]
    arguments: list[PromptArgument] = field(default_factory=list)


def _health(_: dict[str, str]) -> str:
    return """Check the health of my Proxmox cluster. Only read; change nothing.

1. `get_cluster_status`: quorum, and which nodes are online.
2. `get_cluster_resources`: every node, guest and storage, with CPU, memory and disk use.
3. `list_cluster_tasks`: tasks that ended in an error recently. For the worst few, read why with `get_task_log`.
4. `get_ha_status`: any HA resource that isn't in its requested state.
5. If the cluster runs Ceph, `get_ceph_status` on one node.

Report findings grouped as Critical, Warning and OK. For each problem, name the node or guest, \
what you saw, and the tool or step that would fix it. End with a one-line verdict."""


def _capacity(args: dict[str, str]) -> str:
    threshold = args.get("threshold_percent") or "80"
    return f"""Write a capacity report for my Proxmox cluster. Only read; change nothing.

1. `get_cluster_resources` with type `storage`: used and total space per storage, per node.
2. `get_cluster_resources` with type `node`: CPU and memory use per node.
3. `get_cluster_resources` with type `vm`: the ten guests using the most memory, disk and CPU.

Flag anything above {threshold}% as at risk. Show a table per section, sorted by use. Finish with \
where new guests should go, and what to clean up or grow first."""


def _safe_change(args: dict[str, str]) -> str:
    vmid = args.get("vmid", "<vmid>")
    change = args.get("change", "the change I describe next")
    return f"""I want to make this change to guest {vmid}: {change}

Do it safely, step by step:

1. Find the guest with `get_cluster_resources` (type `vm`): its node, and whether it is a VM \
(qemu) or a container (lxc). Check its state with `get_vm_status` or `get_container_status`.
2. Take a snapshot named `before-change` with `create_vm_snapshot` or `create_container_snapshot`, \
passing `wait: true`. Stop if it does not finish with ok: true.
3. Tell me exactly what you will run for the change, and wait for my go-ahead.
4. Make the change, using `wait: true` on any tool that offers it.
5. Verify the guest is healthy afterwards.
6. If anything looks wrong, offer to roll back with `rollback_vm_snapshot` or \
`rollback_container_snapshot` to `before-change`. Once I confirm all is well, offer to delete \
the snapshot."""


def _failed_tasks(args: dict[str, str]) -> str:
    hours = args.get("hours") or "24"
    return f"""Find out what failed on my Proxmox cluster in the last {hours} hours. Only read; change nothing.

1. `list_cluster_tasks`, keeping tasks that ended in the last {hours} hours with a status other than OK.
2. For each, read the end of its log with `get_task_log` (use the task's node and upid).
3. Group the failures by cause: backups, migrations, storage, permissions, and anything else.

For each group: how many, which nodes and guests, the key log line, the likely cause, and the \
fix. Put repeat offenders first."""


def _decommission(args: dict[str, str]) -> str:
    vmid = args.get("vmid", "<vmid>")
    return f"""Help me retire guest {vmid} safely. Ask before every step that changes anything.

1. Find it with `get_cluster_resources` (type `vm`): node, type, name and state.
2. Check for a recent backup: `list_storage` for backup-capable storage, then \
`list_storage_content` with content `backup` and vmid {vmid}.
3. If there is no backup from the last 24 hours, offer a final one with `backup_vm` \
(`wait: true`) and check it finished with ok: true.
4. Show me what will be deleted (name, disks, IPs if known) and wait for my explicit yes.
5. Stop it with `stop_vm` (or the container equivalent) using `wait: true`.
6. Only after a second confirmation, delete it with `delete_vm` or `delete_container`, with `wait: true`.

If the server says the guest is protected, stop and tell me; do not look for a way around it."""


def _arg(name: str, description: str, required: bool = False) -> PromptArgument:
    return PromptArgument(name=name, description=description, required=required)


SPECS: list[Spec] = [
    Spec(
        "cluster_health_check",
        "Cluster health check",
        "Read-only health check: quorum, nodes, guests, failed tasks, HA and Ceph, by severity.",
        _health,
    ),
    Spec(
        "capacity_report",
        "Capacity report",
        "Read-only storage, CPU and memory report with the biggest consumers and risks.",
        _capacity,
        [_arg("threshold_percent", "Flag use above this percentage (default 80)")],
    ),
    Spec(
        "safe_change",
        "Snapshot, change, verify",
        "Snapshot a guest, make a change after your go-ahead, verify, and offer a rollback.",
        _safe_change,
        [_arg("vmid", "Guest ID", True), _arg("change", "What to change", True)],
    ),
    Spec(
        "investigate_failed_tasks",
        "Investigate failed tasks",
        "Read-only: find failed tasks, read their logs, and group them by cause with fixes.",
        _failed_tasks,
        [_arg("hours", "How far back to look (default 24)")],
    ),
    Spec(
        "decommission_guest",
        "Decommission a guest",
        "Back up, stop and delete a guest, asking before every change.",
        _decommission,
        [_arg("vmid", "Guest ID", True)],
    ),
]
BY_NAME = {s.name: s for s in SPECS}


def list_prompts() -> list[Prompt]:
    return [
        Prompt(name=s.name, title=s.title, description=s.description, arguments=s.arguments)
        for s in SPECS
    ]


def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    spec = BY_NAME.get(name)
    if spec is None:
        raise ValueError(f"Unknown prompt: {name}")
    args = {k: str(v) for k, v in (arguments or {}).items() if v not in (None, "")}
    missing = [a.name for a in spec.arguments if a.required and a.name not in args]
    if missing:
        raise ValueError(f"Prompt {name} needs: {', '.join(missing)}")
    text = spec.render(args)
    return GetPromptResult(
        description=spec.description,
        messages=[PromptMessage(role="user", content=TextContent(type="text", text=text))],
    )
