"""Disk tools: list, SMART, LVM, LVM-thin, ZFS, directory, wipe."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

NODE = {"type": "string", "description": "Node name (e.g. pve01)"}
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731


TOOLS = [
    {
        "name": "list_node_disks",
        "description": "List all physical disks on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "include-partitions": OPT_BOOL("Include disk partitions"),
                "skipsmart": OPT_BOOL("Skip SMART data"),
                "type": OPT_STR("Filter by type: hdd, ssd, nvme, usb, or unknown"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_disk_smart",
        "description": "Get SMART health data for a disk.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "disk": OPT_STR("Disk path (e.g. /dev/sda)"),
                "healthonly": OPT_BOOL("Return health status only"),
            },
            "required": ["node", "disk"],
        },
    },
    {
        "name": "wipe_disk",
        "description": "Wipe a disk (destroy all data). USE WITH CAUTION.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "disk": OPT_STR("Disk path (e.g. /dev/sdb)"),
            },
            "required": ["node", "disk"],
        },
    },
    {
        "name": "init_disk_gpt",
        "description": "Initialize a disk with a GPT partition table.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "disk": OPT_STR("Disk path (e.g. /dev/sdb)"),
                "uuid": OPT_STR("Specify a custom GPT UUID"),
            },
            "required": ["node", "disk"],
        },
    },
    # --- LVM ---
    {
        "name": "list_lvm_groups",
        "description": "List LVM volume groups on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "create_lvm_group",
        "description": "Create an LVM volume group on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Volume group name"),
                "device": OPT_STR("Disk device (e.g. /dev/sdb)"),
                "add_storage": OPT_BOOL("Add as storage to Proxmox"),
            },
            "required": ["node", "name", "device"],
        },
    },
    {
        "name": "delete_lvm_group",
        "description": "Delete an LVM volume group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Volume group name"),
                "cleanup-config": OPT_BOOL("Remove associated storage config"),
                "cleanup-disks": OPT_BOOL("Wipe LVM metadata from disks"),
            },
            "required": ["node", "name"],
        },
    },
    # --- LVM thin ---
    {
        "name": "list_lvmthin_pools",
        "description": "List LVM thin pools on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vg": OPT_STR("Filter by volume group name"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "create_lvmthin_pool",
        "description": "Create an LVM thin pool on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Thin pool name"),
                "device": OPT_STR("Disk device (e.g. /dev/sdb)"),
                "add_storage": OPT_BOOL("Add as storage"),
            },
            "required": ["node", "name", "device"],
        },
    },
    {
        "name": "delete_lvmthin_pool",
        "description": "Delete an LVM thin pool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Thin pool name"),
                "volume-group": OPT_STR("Volume group name"),
                "cleanup-config": OPT_BOOL("Remove storage config"),
                "cleanup-disks": OPT_BOOL("Wipe metadata from disks"),
            },
            "required": ["node", "name", "volume-group"],
        },
    },
    # --- ZFS ---
    {
        "name": "list_zfs_pools",
        "description": "List ZFS pools on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_zfs_pool",
        "description": "Get details for a specific ZFS pool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("ZFS pool name"),
            },
            "required": ["node", "name"],
        },
    },
    {
        "name": "create_zfs_pool",
        "description": "Create a ZFS pool on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Pool name"),
                "devices": OPT_STR("Comma-separated device paths"),
                "raidlevel": OPT_STR("RAID level: single, mirror, raidz, raidz2, raidz3, draid, etc."),
                "ashift": OPT_INT("Ashift value (9-16, 0=auto)"),
                "compression": OPT_STR("Compression: on, off, lzjb, lz4, zle, gzip, zstd"),
                "add_storage": OPT_BOOL("Add as storage"),
            },
            "required": ["node", "name", "devices", "raidlevel"],
        },
    },
    {
        "name": "delete_zfs_pool",
        "description": "Delete a ZFS pool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Pool name"),
                "cleanup-config": OPT_BOOL("Remove storage config"),
                "cleanup-disks": OPT_BOOL("Wipe disk labels"),
                "force": OPT_BOOL("Force deletion even if in use"),
            },
            "required": ["node", "name"],
        },
    },
    # --- Directory storage ---
    {
        "name": "list_directory_storage",
        "description": "List directory-based storages on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "create_directory_storage",
        "description": "Create a directory-based storage on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Storage name"),
                "path": OPT_STR("Directory path"),
                "device": OPT_STR("Disk device to format and mount (optional)"),
                "filesystem": OPT_STR("Filesystem: ext4, xfs (only if device is specified)"),
                "add_storage": OPT_BOOL("Add as Proxmox storage"),
            },
            "required": ["node", "name", "path"],
        },
    },
    {
        "name": "delete_directory_storage",
        "description": "Delete a directory-based storage on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Storage name"),
                "cleanup-config": OPT_BOOL("Remove storage config"),
                "cleanup-disks": OPT_BOOL("Unmount and wipe disk"),
            },
            "required": ["node", "name"],
        },
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    node = args.get("node", "")

    if name == "list_node_disks":
        params = {k: args[k] for k in ("include-partitions", "skipsmart", "type") if k in args}
        return await client.get(f"/nodes/{node}/disks/list", params or None)

    elif name == "get_disk_smart":
        params: dict[str, Any] = {"disk": args["disk"]}
        if "healthonly" in args:
            params["healthonly"] = args["healthonly"]
        return await client.get(f"/nodes/{node}/disks/smart", params)

    elif name == "wipe_disk":
        return await client.put(f"/nodes/{node}/disks/wipedisk", {"disk": args["disk"]})

    elif name == "init_disk_gpt":
        data = {"disk": args["disk"]}
        if "uuid" in args:
            data["uuid"] = args["uuid"]
        return await client.post(f"/nodes/{node}/disks/initgpt", data)

    elif name == "list_lvm_groups":
        return await client.get(f"/nodes/{node}/disks/lvm")

    elif name == "create_lvm_group":
        data = {"name": args["name"], "device": args["device"]}
        if "add_storage" in args:
            data["add_storage"] = args["add_storage"]
        return await client.post(f"/nodes/{node}/disks/lvm", data)

    elif name == "delete_lvm_group":
        params = {k: args[k] for k in ("cleanup-config", "cleanup-disks") if k in args}
        return await client.delete(f"/nodes/{node}/disks/lvm/{args['name']}", params or None)

    elif name == "list_lvmthin_pools":
        params = {k: args[k] for k in ("vg",) if k in args}
        return await client.get(f"/nodes/{node}/disks/lvmthin", params or None)

    elif name == "create_lvmthin_pool":
        data = {"name": args["name"], "device": args["device"]}
        if "add_storage" in args:
            data["add_storage"] = args["add_storage"]
        return await client.post(f"/nodes/{node}/disks/lvmthin", data)

    elif name == "delete_lvmthin_pool":
        params = {k: args[k] for k in ("cleanup-config", "cleanup-disks") if k in args}
        params["volume-group"] = args["volume-group"]
        return await client.delete(f"/nodes/{node}/disks/lvmthin/{args['name']}", params)

    elif name == "list_zfs_pools":
        return await client.get(f"/nodes/{node}/disks/zfs")

    elif name == "get_zfs_pool":
        return await client.get(f"/nodes/{node}/disks/zfs/{args['name']}")

    elif name == "create_zfs_pool":
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(f"/nodes/{node}/disks/zfs", data)

    elif name == "delete_zfs_pool":
        params = {k: args[k] for k in ("cleanup-config", "cleanup-disks", "force") if k in args}
        return await client.delete(f"/nodes/{node}/disks/zfs/{args['name']}", params or None)

    elif name == "list_directory_storage":
        return await client.get(f"/nodes/{node}/disks/directory")

    elif name == "create_directory_storage":
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(f"/nodes/{node}/disks/directory", data)

    elif name == "delete_directory_storage":
        params = {k: args[k] for k in ("cleanup-config", "cleanup-disks") if k in args}
        return await client.delete(f"/nodes/{node}/disks/directory/{args['name']}", params or None)

    raise ValueError(f"Unknown tool: {name}")
