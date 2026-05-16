"""QEMU/KVM VM tools: lifecycle, config, snapshots, migration, clone, resize, firewall, RRD, backup."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

NODE = {"type": "string", "description": "Node name (e.g. pve01)"}
VMID = {"type": "integer", "description": "VM ID"}
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731


TOOLS = [
    # --- Listing ---
    {
        "name": "list_vms",
        "description": "List all QEMU VMs on a node or cluster-wide.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": {**NODE, "description": "Node name (optional — omit for cluster-wide)"},
            },
        },
    },
    # --- Status & Config ---
    {
        "name": "get_vm_status",
        "description": "Get current running status of a VM (CPU, memory, uptime, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "get_vm_config",
        "description": "Get the configuration of a VM (hardware, boot, network, disks).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "current": OPT_BOOL("Get current live config (true) or stored config (false)"),
                "snapshot": OPT_STR("Get config from a specific snapshot"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "set_vm_config",
        "description": "Update VM configuration. Accepts any Proxmox VM config key as a parameter.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "name": OPT_STR("VM name"),
                "description": OPT_STR("VM description"),
                "memory": OPT_INT("RAM in MB"),
                "cores": OPT_INT("Number of CPU cores"),
                "sockets": OPT_INT("Number of CPU sockets"),
                "cpu": OPT_STR("CPU type (e.g. host, kvm64, x86-64-v3)"),
                "onboot": OPT_BOOL("Start on boot"),
                "startup": OPT_STR("Startup/shutdown order (e.g. order=1,up=10,down=5)"),
                "hotplug": OPT_STR("Hotplug features (network,disk,cpu,memory,usb)"),
                "agent": OPT_STR("QEMU guest agent config (e.g. enabled=1)"),
                "net0": OPT_STR("Network interface 0 config (e.g. virtio,bridge=vmbr0)"),
                "net1": OPT_STR("Network interface 1 config"),
                "scsi0": OPT_STR("SCSI disk 0 config"),
                "ide2": OPT_STR("IDE device 2 config (e.g. for ISO)"),
                "boot": OPT_STR("Boot order (e.g. order=scsi0;ide2)"),
                "tags": OPT_STR("Tags (semicolon-separated)"),
                "delete": OPT_STR("Comma-separated list of config keys to delete"),
                "digest": OPT_STR("SHA1 digest to prevent race conditions"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "get_vm_pending",
        "description": "Get pending config changes for a VM (applied on next start).",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    # --- Lifecycle ---
    {
        "name": "start_vm",
        "description": "Start a virtual machine.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "skiplock": OPT_BOOL("Skip lock check"),
                "timeout": OPT_INT("Timeout in seconds"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "stop_vm",
        "description": "Force-stop a virtual machine (hard power off).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "timeout": OPT_INT("Timeout in seconds"),
                "skiplock": OPT_BOOL("Skip lock check"),
                "keepActive": OPT_BOOL("Keep VM disks active after stop"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "shutdown_vm",
        "description": "Gracefully shut down a VM via ACPI signal.",
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
        "name": "reboot_vm",
        "description": "Reboot a virtual machine (ACPI reboot).",
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
        "name": "reset_vm",
        "description": "Hard-reset a virtual machine (like pressing the reset button).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "skiplock": OPT_BOOL("Skip lock check"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "suspend_vm",
        "description": "Suspend a virtual machine to RAM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "skiplock": OPT_BOOL("Skip lock check"),
                "todisk": OPT_BOOL("Suspend to disk instead of RAM"),
                "statestorage": OPT_STR("Storage for suspend-to-disk state file"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "resume_vm",
        "description": "Resume a suspended virtual machine.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "skiplock": OPT_BOOL("Skip lock check"),
                "nocheck": OPT_BOOL("Skip check for lock"),
            },
            "required": ["node", "vmid"],
        },
    },
    # --- Create / Clone / Delete ---
    {
        "name": "create_vm",
        "description": "Create a new QEMU VM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": OPT_INT("VM ID (omit to auto-assign)"),
                "name": OPT_STR("VM name"),
                "memory": OPT_INT("RAM in MB (default 512)"),
                "cores": OPT_INT("CPU cores (default 1)"),
                "sockets": OPT_INT("CPU sockets (default 1)"),
                "cpu": OPT_STR("CPU type (e.g. host)"),
                "ostype": OPT_STR("OS type: l26, l24, win10, win11, win2022, other, etc."),
                "scsihw": OPT_STR("SCSI hardware type (virtio-scsi-pci, lsi, etc.)"),
                "scsi0": OPT_STR("SCSI disk 0 (e.g. local-lvm:32)"),
                "ide2": OPT_STR("IDE device 2 (e.g. local:iso/ubuntu.iso,media=cdrom)"),
                "net0": OPT_STR("Network interface 0 (e.g. virtio,bridge=vmbr0)"),
                "boot": OPT_STR("Boot order (e.g. order=scsi0;ide2)"),
                "onboot": OPT_BOOL("Start on boot"),
                "agent": OPT_STR("QEMU agent config (e.g. enabled=1)"),
                "description": OPT_STR("VM description"),
                "tags": OPT_STR("Tags (semicolon-separated)"),
                "pool": OPT_STR("Resource pool"),
                "start": OPT_BOOL("Start VM after creation"),
                "template": OPT_BOOL("Create as template"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "clone_vm",
        "description": "Clone a VM to a new VM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "newid": OPT_INT("New VM ID (omit to auto-assign)"),
                "name": OPT_STR("Name for the clone"),
                "description": OPT_STR("Description for the clone"),
                "full": OPT_BOOL("Full clone (true) or linked clone (false)"),
                "storage": OPT_STR("Target storage for full clone"),
                "pool": OPT_STR("Resource pool for the clone"),
                "target": OPT_STR("Target node (for cross-node clone)"),
                "snapname": OPT_STR("Clone from this snapshot"),
                "format": OPT_STR("Disk format: raw, qcow2, vmdk"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "delete_vm",
        "description": "Delete a VM and optionally its disks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "destroy-unreferenced-disks": OPT_BOOL("Also destroy disks not referenced in config"),
                "purge": OPT_BOOL("Remove from HA, replication, jobs, and backup configs"),
                "skiplock": OPT_BOOL("Skip lock check"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "convert_vm_to_template",
        "description": "Convert a VM to a template.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "disk": OPT_STR("Disk to convert to base image (optional)"),
            },
            "required": ["node", "vmid"],
        },
    },
    # --- Snapshots ---
    {
        "name": "list_vm_snapshots",
        "description": "List all snapshots of a VM.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "create_vm_snapshot",
        "description": "Create a snapshot of a VM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "snapname": OPT_STR("Snapshot name (no spaces)"),
                "description": OPT_STR("Snapshot description"),
                "vmstate": OPT_BOOL("Include VM RAM state in snapshot"),
            },
            "required": ["node", "vmid", "snapname"],
        },
    },
    {
        "name": "get_vm_snapshot_config",
        "description": "Get the VM config at a specific snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "snapname": OPT_STR("Snapshot name"),
            },
            "required": ["node", "vmid", "snapname"],
        },
    },
    {
        "name": "rollback_vm_snapshot",
        "description": "Rollback a VM to a snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "snapname": OPT_STR("Snapshot name to roll back to"),
                "start": OPT_BOOL("Start VM after rollback"),
            },
            "required": ["node", "vmid", "snapname"],
        },
    },
    {
        "name": "delete_vm_snapshot",
        "description": "Delete a VM snapshot.",
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
    # --- Migration ---
    {
        "name": "migrate_vm",
        "description": "Migrate a VM to another node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "target": OPT_STR("Target node name"),
                "online": OPT_BOOL("Live migration (VM stays running)"),
                "with-local-disks": OPT_BOOL("Also migrate local disks"),
                "targetstorage": OPT_STR("Target storage mapping (e.g. local-lvm or 0:local-lvm)"),
                "bwlimit": OPT_INT("Bandwidth limit in KB/s"),
                "force": OPT_BOOL("Allow migration even with local resources"),
                "migration_type": OPT_STR("Migration type: secure, insecure, websocket"),
                "migration_network": OPT_STR("CIDR of migration network"),
            },
            "required": ["node", "vmid", "target"],
        },
    },
    {
        "name": "get_vm_migrate_preconditions",
        "description": "Check migration preconditions for a VM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "target": OPT_STR("Target node"),
            },
            "required": ["node", "vmid", "target"],
        },
    },
    # --- Disks ---
    {
        "name": "resize_vm_disk",
        "description": "Resize a VM disk.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "disk": OPT_STR("Disk identifier (e.g. scsi0, virtio0)"),
                "size": OPT_STR("New size or increment (e.g. 50G or +10G)"),
                "skiplock": OPT_BOOL("Skip lock check"),
                "digest": OPT_STR("Config digest for race condition prevention"),
            },
            "required": ["node", "vmid", "disk", "size"],
        },
    },
    {
        "name": "move_vm_disk",
        "description": "Move a VM disk to another storage or detach it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "disk": OPT_STR("Disk to move (e.g. scsi0)"),
                "storage": OPT_STR("Target storage ID"),
                "format": OPT_STR("Target format: raw, qcow2, vmdk"),
                "delete": OPT_BOOL("Delete original disk after move"),
                "digest": OPT_STR("Config digest"),
                "bwlimit": OPT_INT("Bandwidth limit in KB/s"),
                "target-vmid": OPT_INT("Move disk to another VM"),
                "target-disk": OPT_STR("Target disk slot on destination VM"),
            },
            "required": ["node", "vmid", "disk"],
        },
    },
    {
        "name": "unlink_vm_disk",
        "description": "Unlink/detach disks from a VM config (optionally destroy them).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "idlist": OPT_STR("Comma-separated list of disk IDs to unlink (e.g. scsi0,scsi1)"),
                "force": OPT_BOOL("Force removal (destroy disk images)"),
            },
            "required": ["node", "vmid", "idlist"],
        },
    },
    {
        "name": "import_vm_disk",
        "description": "Import an external disk image into a storage for a VM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "source": OPT_STR("Path to source disk image"),
                "storage": OPT_STR("Target storage ID"),
                "format": OPT_STR("Format: raw, qcow2, vmdk"),
            },
            "required": ["node", "vmid", "source", "storage"],
        },
    },
    # --- Firewall ---
    {
        "name": "get_vm_firewall_rules",
        "description": "List firewall rules for a VM.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "add_vm_firewall_rule",
        "description": "Add a firewall rule to a VM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "type": OPT_STR("Rule type: in or out"),
                "action": OPT_STR("Action: ACCEPT, DROP, or REJECT"),
                "proto": OPT_STR("Protocol: tcp, udp, icmp, etc."),
                "dport": OPT_STR("Destination port or port range (e.g. 22 or 80:443)"),
                "sport": OPT_STR("Source port"),
                "source": OPT_STR("Source address or CIDR"),
                "dest": OPT_STR("Destination address or CIDR"),
                "comment": OPT_STR("Rule comment"),
                "enable": OPT_INT("Enable rule: 1 or 0"),
                "pos": OPT_INT("Insert at position"),
            },
            "required": ["node", "vmid", "type", "action"],
        },
    },
    {
        "name": "delete_vm_firewall_rule",
        "description": "Delete a firewall rule from a VM.",
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
        "name": "get_vm_firewall_options",
        "description": "Get firewall options for a VM.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "set_vm_firewall_options",
        "description": "Set firewall options for a VM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "enable": OPT_INT("Enable firewall: 1 or 0"),
                "dhcp": OPT_INT("Allow DHCP: 1 or 0"),
                "macfilter": OPT_INT("Enable MAC filtering: 1 or 0"),
                "ndp": OPT_INT("Allow NDP (IPv6): 1 or 0"),
                "radv": OPT_INT("Allow router advertisements: 1 or 0"),
                "ipfilter": OPT_INT("Enable IP filtering: 1 or 0"),
                "log_level_in": OPT_STR("Log level for inbound: emerg, alert, crit, err, warning, notice, info, debug, nolog"),
                "log_level_out": OPT_STR("Log level for outbound"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "get_vm_firewall_log",
        "description": "Get firewall log for a VM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "limit": OPT_INT("Max entries"),
                "start": OPT_INT("Start offset"),
            },
            "required": ["node", "vmid"],
        },
    },
    # --- RRD / Monitoring ---
    {
        "name": "get_vm_rrddata",
        "description": "Get RRD statistics data points for a VM.",
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
    # --- Agent ---
    {
        "name": "vm_agent_exec",
        "description": "Execute a command inside a VM via QEMU guest agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "command": OPT_STR("Command to execute"),
                "input-data": OPT_STR("Stdin data for the command"),
            },
            "required": ["node", "vmid", "command"],
        },
    },
    {
        "name": "vm_agent_get_fsinfo",
        "description": "Get filesystem info from inside a VM via QEMU guest agent.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "vm_agent_get_network_interfaces",
        "description": "Get network interface info from inside a VM via QEMU guest agent.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "vm_agent_get_osinfo",
        "description": "Get OS info from inside a VM via QEMU guest agent.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "vm_agent_ping",
        "description": "Ping the QEMU guest agent inside a VM.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "vmid": VMID},
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "vm_agent_set_user_password",
        "description": "Set a user password inside a VM via QEMU guest agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "username": OPT_STR("Username"),
                "password": OPT_STR("New password"),
                "crypted": OPT_BOOL("Password is already hashed (true) or plaintext (false)"),
            },
            "required": ["node", "vmid", "username", "password"],
        },
    },
    # --- Features ---
    {
        "name": "get_vm_feature",
        "description": "Check if a VM supports a specific feature (e.g. snapshot, clone, copy).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "feature": OPT_STR("Feature: snapshot, snapshot-template, copy, or clone"),
                "snapname": OPT_STR("Check feature for a specific snapshot"),
            },
            "required": ["node", "vmid", "feature"],
        },
    },
    # --- VNC / Console ---
    {
        "name": "get_vm_vnc_proxy",
        "description": "Get a VNC proxy ticket for a VM console.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "websocket": OPT_BOOL("Use WebSocket transport"),
                "generate-password": OPT_BOOL("Generate and return VNC password"),
            },
            "required": ["node", "vmid"],
        },
    },
    {
        "name": "get_vm_spice_proxy",
        "description": "Get a SPICE proxy config for a VM console.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "proxy": OPT_STR("SPICE proxy server address"),
            },
            "required": ["node", "vmid"],
        },
    },
    # --- Cloudinit ---
    {
        "name": "get_vm_cloudinit",
        "description": "Get cloud-init config dump for a VM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": VMID,
                "type": OPT_STR("Dump type: user, network, or meta"),
            },
            "required": ["node", "vmid", "type"],
        },
    },
    {
        "name": "regenerate_vm_cloudinit",
        "description": "Regenerate cloud-init config ISO for a VM.",
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
    base = f"/nodes/{node}/qemu"
    vm = f"{base}/{vmid}"

    if name == "list_vms":
        if node:
            return await client.get(f"/nodes/{node}/qemu")
        nodes_r = await client.get("/nodes")
        all_vms = []
        for n in nodes_r["data"]:
            vms = await client.get(f"/nodes/{n['node']}/qemu")
            for v in vms["data"]:
                v["node"] = n["node"]
                all_vms.append(v)
        return {"data": all_vms}

    elif name == "get_vm_status":
        return await client.get(f"{vm}/status/current")

    elif name == "get_vm_config":
        params: dict[str, Any] = {}
        if args.get("current"):
            params["current"] = 1
        if "snapshot" in args:
            params["snapshot"] = args["snapshot"]
        return await client.get(f"{vm}/config", params or None)

    elif name == "set_vm_config":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.put(f"{vm}/config", data)

    elif name == "get_vm_pending":
        return await client.get(f"{vm}/pending")

    elif name == "start_vm":
        data = {k: args[k] for k in ("skiplock", "timeout") if k in args}
        return await client.post(f"{vm}/status/start", data or None)

    elif name == "stop_vm":
        data = {k: args[k] for k in ("timeout", "skiplock", "keepActive") if k in args}
        return await client.post(f"{vm}/status/stop", data or None)

    elif name == "shutdown_vm":
        data = {k: args[k] for k in ("timeout", "forceStop", "skiplock") if k in args}
        return await client.post(f"{vm}/status/shutdown", data or None)

    elif name == "reboot_vm":
        data = {k: args[k] for k in ("timeout",) if k in args}
        return await client.post(f"{vm}/status/reboot", data or None)

    elif name == "reset_vm":
        data = {k: args[k] for k in ("skiplock",) if k in args}
        return await client.post(f"{vm}/status/reset", data or None)

    elif name == "suspend_vm":
        data = {k: args[k] for k in ("skiplock", "todisk", "statestorage") if k in args}
        return await client.post(f"{vm}/status/suspend", data or None)

    elif name == "resume_vm":
        data = {k: args[k] for k in ("skiplock", "nocheck") if k in args}
        return await client.post(f"{vm}/status/resume", data or None)

    elif name == "create_vm":
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(base, data)

    elif name == "clone_vm":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.post(f"{vm}/clone", data)

    elif name == "delete_vm":
        params = {k: args[k] for k in ("destroy-unreferenced-disks", "purge", "skiplock") if k in args}
        return await client.delete(vm, params or None)

    elif name == "convert_vm_to_template":
        data = {}
        if "disk" in args:
            data["disk"] = args["disk"]
        return await client.post(f"{vm}/template", data or None)

    elif name == "list_vm_snapshots":
        return await client.get(f"{vm}/snapshot")

    elif name == "create_vm_snapshot":
        data = {"snapname": args["snapname"]}
        for k in ("description", "vmstate"):
            if k in args:
                data[k] = args[k]
        return await client.post(f"{vm}/snapshot", data)

    elif name == "get_vm_snapshot_config":
        return await client.get(f"{vm}/snapshot/{args['snapname']}/config")

    elif name == "rollback_vm_snapshot":
        data = {}
        if "start" in args:
            data["start"] = args["start"]
        return await client.post(f"{vm}/snapshot/{args['snapname']}/rollback", data or None)

    elif name == "delete_vm_snapshot":
        params = {}
        if "force" in args:
            params["force"] = args["force"]
        return await client.delete(f"{vm}/snapshot/{args['snapname']}", params or None)

    elif name == "migrate_vm":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.post(f"{vm}/migrate", data)

    elif name == "get_vm_migrate_preconditions":
        return await client.get(f"{vm}/migrate", {"target": args["target"]})

    elif name == "resize_vm_disk":
        data = {"disk": args["disk"], "size": args["size"]}
        for k in ("skiplock", "digest"):
            if k in args:
                data[k] = args[k]
        return await client.put(f"{vm}/resize", data)

    elif name == "move_vm_disk":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.post(f"{vm}/move_disk", data)

    elif name == "unlink_vm_disk":
        data = {"idlist": args["idlist"]}
        if "force" in args:
            data["force"] = args["force"]
        return await client.put(f"{vm}/unlink", data)

    elif name == "import_vm_disk":
        data = {"source": args["source"], "storage": args["storage"]}
        if "format" in args:
            data["format"] = args["format"]
        return await client.post(f"{vm}/importdisk", data)

    elif name == "get_vm_firewall_rules":
        return await client.get(f"{vm}/firewall/rules")

    elif name == "add_vm_firewall_rule":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.post(f"{vm}/firewall/rules", data)

    elif name == "delete_vm_firewall_rule":
        params = {}
        if "digest" in args:
            params["digest"] = args["digest"]
        return await client.delete(f"{vm}/firewall/rules/{args['pos']}", params or None)

    elif name == "get_vm_firewall_options":
        return await client.get(f"{vm}/firewall/options")

    elif name == "set_vm_firewall_options":
        data = {k: v for k, v in args.items() if k not in ("node", "vmid")}
        return await client.put(f"{vm}/firewall/options", data)

    elif name == "get_vm_firewall_log":
        params = {k: args[k] for k in ("limit", "start") if k in args}
        return await client.get(f"{vm}/firewall/log", params or None)

    elif name == "get_vm_rrddata":
        params = {"timeframe": args["timeframe"]}
        if "cf" in args:
            params["cf"] = args["cf"]
        return await client.get(f"{vm}/rrddata", params)

    elif name == "vm_agent_exec":
        data = {"command": args["command"]}
        if "input-data" in args:
            data["input-data"] = args["input-data"]
        return await client.post(f"{vm}/agent/exec", data)

    elif name == "vm_agent_get_fsinfo":
        return await client.get(f"{vm}/agent/get-fsinfo")

    elif name == "vm_agent_get_network_interfaces":
        return await client.get(f"{vm}/agent/network-get-interfaces")

    elif name == "vm_agent_get_osinfo":
        return await client.get(f"{vm}/agent/get-osinfo")

    elif name == "vm_agent_ping":
        return await client.post(f"{vm}/agent/ping")

    elif name == "vm_agent_set_user_password":
        data = {"username": args["username"], "password": args["password"]}
        if "crypted" in args:
            data["crypted"] = args["crypted"]
        return await client.post(f"{vm}/agent/set-user-password", data)

    elif name == "get_vm_feature":
        params = {"feature": args["feature"]}
        if "snapname" in args:
            params["snapname"] = args["snapname"]
        return await client.get(f"{vm}/feature", params)

    elif name == "get_vm_vnc_proxy":
        data = {k: args[k] for k in ("websocket", "generate-password") if k in args}
        return await client.post(f"{vm}/vncproxy", data or None)

    elif name == "get_vm_spice_proxy":
        data = {}
        if "proxy" in args:
            data["proxy"] = args["proxy"]
        return await client.post(f"{vm}/spiceproxy", data or None)

    elif name == "get_vm_cloudinit":
        return await client.get(f"{vm}/cloudinit/dump", {"type": args["type"]})

    elif name == "regenerate_vm_cloudinit":
        return await client.put(f"{vm}/cloudinit")

    raise ValueError(f"Unknown tool: {name}")
