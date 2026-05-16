"""LXC container tools: lifecycle, config, snapshots, firewall, migration, clone, RRD."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

NODE = {"type": "string", "description": "Node name (e.g. pve01)"}
VMID = {"type": "integer", "description": "Container ID"}
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731


TOOLS = [
    {
        "name": "list_containers",
        "description": "List all LXC containers on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_container_status",
        "description": "Get current running status of an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "get_container_config",
        "description": "Get configuration of an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "current": OPT_BOOL("Return current running config"),
                "snapshot": OPT_STR("Return config from this snapshot"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "set_container_config",
        "description": "Update LXC container configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "hostname": OPT_STR("Container hostname"),
                "description": OPT_STR("Container description"),
                "memory": OPT_INT("RAM in MB"),
                "swap": OPT_INT("Swap in MB"),
                "cores": OPT_INT("CPU cores"),
                "cpulimit": OPT_STR("CPU limit (e.g. 0.5)"),
                "cpuunits": OPT_INT("CPU weight (default 1024)"),
                "onboot": OPT_BOOL("Start on boot"),
                "startup": OPT_STR("Startup order (e.g. order=1,up=10,down=5)"),
                "net0": OPT_STR("Network interface 0 (e.g. name=eth0,bridge=vmbr0,ip=dhcp)"),
                "net1": OPT_STR("Network interface 1"),
                "mp0": OPT_STR("Mount point 0 (e.g. local-lvm:10,mp=/data)"),
                "tags": OPT_STR("Tags (semicolon-separated)"),
                "features": OPT_STR("Features (e.g. nesting=1,keyctl=1)"),
                "delete": OPT_STR("Comma-separated list of config keys to delete"),
                "digest": OPT_STR("SHA1 digest to prevent race conditions"),
                "unprivileged": OPT_BOOL("Run as unprivileged container"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "get_container_pending",
        "description": "Get pending config changes for an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "start_container",
        "description": "Start an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "skiplock": OPT_BOOL("Skip lock check"),
                "debug": OPT_BOOL("Enable debug output"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "stop_container",
        "description": "Force-stop an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "skiplock": OPT_BOOL("Skip lock check"),
                "overrule-shutdown": OPT_BOOL("Overrule shutdown sequence"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "shutdown_container",
        "description": "Gracefully shutdown an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "timeout": OPT_INT("Timeout in seconds"),
                "forceStop": OPT_BOOL("Force stop if shutdown times out"),
                "skiplock": OPT_BOOL("Skip lock check"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "reboot_container",
        "description": "Reboot an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "timeout": OPT_INT("Timeout in seconds"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "suspend_container",
        "description": "Suspend an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "resume_container",
        "description": "Resume a suspended LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "create_container",
        "description": "Create a new LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": OPT_INT("Container ID (omit to auto-assign)"),
                "ostemplate": OPT_STR("Template (e.g. local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst)"),
                "hostname": OPT_STR("Container hostname"),
                "memory": OPT_INT("RAM in MB (default 512)"),
                "swap": OPT_INT("Swap in MB (default 512)"),
                "cores": OPT_INT("CPU cores"),
                "rootfs": OPT_STR("Root filesystem (e.g. local-lvm:8)"),
                "net0": OPT_STR("Network interface 0"),
                "password": OPT_STR("Root password"),
                "ssh-public-keys": OPT_STR("SSH public keys"),
                "onboot": OPT_BOOL("Start on boot"),
                "unprivileged": OPT_BOOL("Unprivileged container (default true)"),
                "features": OPT_STR("Features (e.g. nesting=1)"),
                "tags": OPT_STR("Tags (semicolon-separated)"),
                "pool": OPT_STR("Resource pool"),
                "storage": OPT_STR("Default storage for rootfs"),
                "start": OPT_BOOL("Start container after creation"),
                "description": OPT_STR("Container description"),
            },
            "required": ["node", "ostemplate"],
        },
    },
    {
        "name": "clone_container",
        "description": "Clone an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "newid": OPT_INT("New container ID (omit to auto-assign)"),
                "hostname": OPT_STR("Hostname for the clone"),
                "description": OPT_STR("Description for the clone"),
                "full": OPT_BOOL("Full clone (true) or linked clone (false)"),
                "storage": OPT_STR("Target storage for full clone"),
                "pool": OPT_STR("Resource pool"),
                "target": OPT_STR("Target node"),
                "snapname": OPT_STR("Clone from this snapshot"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "delete_container",
        "description": "Delete an LXC container and its disks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "purge": OPT_BOOL("Remove from HA, replication, jobs, and backup configs"),
                "destroy-unreferenced-disks": OPT_BOOL("Destroy unreferenced disk volumes"),
                "force": OPT_BOOL("Force stop before delete if running"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "resize_container_disk",
        "description": "Resize an LXC container disk.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "disk": OPT_STR("Disk to resize (e.g. rootfs, mp0)"),
                "size": OPT_STR("New size or increment (e.g. 20G or +5G)"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["node", "vmid", "disk", "size"],
        },
    },
    {
        "name": "move_container_disk",
        "description": "Move an LXC container disk to another storage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "disk": OPT_STR("Disk to move (e.g. rootfs, mp0)"),
                "storage": OPT_STR("Target storage ID"),
                "delete": OPT_BOOL("Delete original after move"),
                "digest": OPT_STR("Config digest"),
                "bwlimit": OPT_INT("Bandwidth limit in KB/s"),
                "target-vmid": OPT_INT("Move to another container"),
                "target-disk": OPT_STR("Target disk slot"),
            },
            "required": ["node", "vmid", "disk", "storage"],
        },
    },
    {
        "name": "migrate_container",
        "description": "Migrate an LXC container to another node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "target": OPT_STR("Target node name"),
                "online": OPT_BOOL("Live migration"),
                "restart": OPT_BOOL("Use restart migration"),
                "timeout": OPT_INT("Timeout for restart migration"),
                "bwlimit": OPT_INT("Bandwidth limit in KB/s"),
                "targetstorage": OPT_STR("Target storage ID"),
            },
            "required": ["node", "vmid", "target"],
        },
    },
    {
        "name": "list_container_snapshots",
        "description": "List all snapshots of an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "create_container_snapshot",
        "description": "Create a snapshot of an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "snapname": OPT_STR("Snapshot name"),
                "description": OPT_STR("Snapshot description"),
            },
            "required": ["node", "vmid", "snapname"],
        },
    },
    {
        "name": "rollback_container_snapshot",
        "description": "Rollback an LXC container to a snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "snapname": OPT_STR("Snapshot name"),
                "start": OPT_BOOL("Start container after rollback"),
            },
            "required": ["node", "vmid", "snapname"],
        },
    },
    {
        "name": "delete_container_snapshot",
        "description": "Delete an LXC container snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "snapname": OPT_STR("Snapshot name"),
                "force": OPT_BOOL("Force removal even if broken"),
            },
            "required": ["node", "vmid", "snapname"],
        },
    },
    {
        "name": "get_container_firewall_rules",
        "description": "List firewall rules for an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "add_container_firewall_rule",
        "description": "Add a firewall rule to an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "type": OPT_STR("Rule type: in or out"),
                "action": OPT_STR("Action: ACCEPT, DROP, or REJECT"),
                "proto": OPT_STR("Protocol: tcp, udp, icmp, etc."),
                "dport": OPT_STR("Destination port or range"),
                "sport": OPT_STR("Source port"),
                "source": OPT_STR("Source address or CIDR"),
                "dest": OPT_STR("Destination address or CIDR"),
                "comment": OPT_STR("Rule comment"),
                "enable": OPT_INT("Enable: 1 or 0"),
                "pos": OPT_INT("Insert at position"),
            },
            "required": ["node", "vmid", "type", "action"],
        },
    },
    {
        "name": "delete_container_firewall_rule",
        "description": "Delete a firewall rule from an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "pos": OPT_INT("Rule position"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["node", "vmid", "pos"],
        },
    },
    {
        "name": "get_container_firewall_options",
        "description": "Get firewall options for an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "set_container_firewall_options",
        "description": "Set firewall options for an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "enable": OPT_INT("Enable firewall: 1 or 0"),
                "dhcp": OPT_INT("Allow DHCP: 1 or 0"),
                "macfilter": OPT_INT("Enable MAC filtering: 1 or 0"),
                "ndp": OPT_INT("Allow NDP: 1 or 0"),
                "radv": OPT_INT("Allow router advertisements: 1 or 0"),
                "ipfilter": OPT_INT("Enable IP filter: 1 or 0"),
                "log_level_in": OPT_STR("Log level for inbound traffic"),
                "log_level_out": OPT_STR("Log level for outbound traffic"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "get_container_rrddata",
        "description": "Get RRD statistics data points for an LXC container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "timeframe": OPT_STR("Timeframe: hour, day, week, month, year"),
                "cf": OPT_STR("Consolidation function: AVERAGE or MAX"),
            },
            "required": ["node", "vmid", "timeframe"],
        },
    },
    {
        "name": "convert_container_to_template",
        "description": "Convert an LXC container to a template.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    node = args.get("node", "")
    vmid = args.get("vmid", "")
    base = f"/nodes/{node}/lxc"
    ct = f"{base}/{vmid}"

    if name == "list_containers":
        return await client.get(base)

    elif name == "get_container_status":
        return await client.get(f"{ct}/status/current")

    elif name == "get_container_config":
        params: dict[str, Any] = {}
        if args.get("current"):
            params["current"] = 1
        if "snapshot" in args:
            params["snapshot"] = args["snapshot"]
        return await client.get(f"{ct}/config", params or None)

    elif name == "set_container_config":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.put(f"{ct}/config", data)

    elif name == "get_container_pending":
        return await client.get(f"{ct}/pending")

    elif name == "start_container":
        data = {k: args[k] for k in ("skiplock", "debug") if k in args}
        return await client.post(f"{ct}/status/start", data or None)

    elif name == "stop_container":
        data = {k: args[k] for k in ("skiplock", "overrule-shutdown") if k in args}
        return await client.post(f"{ct}/status/stop", data or None)

    elif name == "shutdown_container":
        data = {k: args[k] for k in ("timeout", "forceStop", "skiplock") if k in args}
        return await client.post(f"{ct}/status/shutdown", data or None)

    elif name == "reboot_container":
        data = {k: args[k] for k in ("timeout",) if k in args}
        return await client.post(f"{ct}/status/reboot", data or None)

    elif name == "suspend_container":
        return await client.post(f"{ct}/status/suspend")

    elif name == "resume_container":
        return await client.post(f"{ct}/status/resume")

    elif name == "create_container":
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(base, data)

    elif name == "clone_container":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.post(f"{ct}/clone", data)

    elif name == "delete_container":
        params = {k: args[k] for k in ("purge", "destroy-unreferenced-disks", "force") if k in args}
        return await client.delete(ct, params or None)

    elif name == "resize_container_disk":
        data = {"disk": args["disk"], "size": args["size"]}
        if "digest" in args:
            data["digest"] = args["digest"]
        return await client.put(f"{ct}/resize", data)

    elif name == "move_container_disk":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.post(f"{ct}/move_volume", data)

    elif name == "migrate_container":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.post(f"{ct}/migrate", data)

    elif name == "list_container_snapshots":
        return await client.get(f"{ct}/snapshot")

    elif name == "create_container_snapshot":
        data = {"snapname": args["snapname"]}
        if "description" in args:
            data["description"] = args["description"]
        return await client.post(f"{ct}/snapshot", data)

    elif name == "rollback_container_snapshot":
        data = {}
        if "start" in args:
            data["start"] = args["start"]
        return await client.post(f"{ct}/snapshot/{args['snapname']}/rollback", data or None)

    elif name == "delete_container_snapshot":
        params = {}
        if "force" in args:
            params["force"] = args["force"]
        return await client.delete(f"{ct}/snapshot/{args['snapname']}", params or None)

    elif name == "get_container_firewall_rules":
        return await client.get(f"{ct}/firewall/rules")

    elif name == "add_container_firewall_rule":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.post(f"{ct}/firewall/rules", data)

    elif name == "delete_container_firewall_rule":
        params = {}
        if "digest" in args:
            params["digest"] = args["digest"]
        return await client.delete(f"{ct}/firewall/rules/{args['pos']}", params or None)

    elif name == "get_container_firewall_options":
        return await client.get(f"{ct}/firewall/options")

    elif name == "set_container_firewall_options":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.put(f"{ct}/firewall/options", data)

    elif name == "get_container_rrddata":
        params = {"timeframe": args["timeframe"]}
        if "cf" in args:
            params["cf"] = args["cf"]
        return await client.get(f"{ct}/rrddata", params)

    elif name == "convert_container_to_template":
        return await client.post(f"{ct}/template")

    raise ValueError(f"Unknown tool: {name}")
