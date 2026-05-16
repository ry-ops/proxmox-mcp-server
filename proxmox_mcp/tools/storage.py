"""Storage tools: list, status, content, backup/restore, vzdump, ISO/template management."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

NODE = {"type": "string", "description": "Node name (e.g. pve01)"}
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731


TOOLS = [
    # --- Cluster-level storage config ---
    {
        "name": "list_storage",
        "description": "List all storage configurations in the cluster.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": {**NODE, "description": "Node name (optional — omit for cluster-wide config)"},
                "type": OPT_STR("Filter by storage type: dir, lvm, lvmthin, zfspool, nfs, cifs, rbd, pbs, glusterfs, iscsi, etc."),
                "enabled": OPT_BOOL("Filter by enabled state"),
            },
        },
    },
    {
        "name": "get_storage_config",
        "description": "Get configuration for a specific storage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "storage": OPT_STR("Storage ID"),
            },
            "required": ["storage"],
        },
    },
    {
        "name": "create_storage",
        "description": "Create a new storage configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "storage": OPT_STR("Storage ID (unique name)"),
                "type": OPT_STR("Storage type: dir, lvm, lvmthin, zfspool, nfs, cifs, rbd, pbs, btrfs"),
                "path": OPT_STR("Path for dir/btrfs storage"),
                "server": OPT_STR("Server for NFS/CIFS/PBS storage"),
                "export": OPT_STR("NFS export path"),
                "share": OPT_STR("CIFS share name"),
                "username": OPT_STR("Username for CIFS/PBS"),
                "password": OPT_STR("Password for CIFS/PBS"),
                "vgname": OPT_STR("LVM volume group name"),
                "thinpool": OPT_STR("LVM thin pool name"),
                "pool": OPT_STR("ZFS pool or Ceph pool name"),
                "content": OPT_STR("Allowed content types (comma-separated): images,rootdir,vztmpl,backup,iso,snippets"),
                "nodes": OPT_STR("Comma-separated list of nodes that can use this storage (empty=all)"),
                "shared": OPT_BOOL("Storage is shared between nodes"),
                "disable": OPT_BOOL("Disable storage"),
                "maxfiles": OPT_INT("Max backup files per VM/CT (0=unlimited)"),
            },
            "required": ["storage", "type"],
        },
    },
    {
        "name": "update_storage",
        "description": "Update an existing storage configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "storage": OPT_STR("Storage ID"),
                "content": OPT_STR("Allowed content types"),
                "nodes": OPT_STR("Allowed nodes"),
                "shared": OPT_BOOL("Shared storage"),
                "disable": OPT_BOOL("Disable storage"),
                "maxfiles": OPT_INT("Max backup files per VM/CT"),
                "delete": OPT_STR("Comma-separated config keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["storage"],
        },
    },
    {
        "name": "delete_storage",
        "description": "Delete a storage configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "storage": OPT_STR("Storage ID"),
            },
            "required": ["storage"],
        },
    },
    # --- Node storage status ---
    {
        "name": "get_node_storage_status",
        "description": "Get status and usage for a specific storage on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "storage": OPT_STR("Storage ID"),
            },
            "required": ["node", "storage"],
        },
    },
    # --- Storage content (volumes) ---
    {
        "name": "list_storage_content",
        "description": "List volumes/content in a storage on a node (ISOs, backups, disk images, templates).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "storage": OPT_STR("Storage ID"),
                "content": OPT_STR("Filter by content type: images, iso, vztmpl, backup, rootdir, snippets"),
                "vmid": OPT_INT("Filter by VM/CT ID"),
            },
            "required": ["node", "storage"],
        },
    },
    {
        "name": "get_storage_volume_info",
        "description": "Get info about a specific volume in storage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "storage": OPT_STR("Storage ID"),
                "volume": OPT_STR("Volume ID (e.g. local:iso/ubuntu.iso or local-lvm:vm-100-disk-0)"),
            },
            "required": ["node", "storage", "volume"],
        },
    },
    {
        "name": "delete_storage_volume",
        "description": "Delete a volume from storage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "storage": OPT_STR("Storage ID"),
                "volume": OPT_STR("Volume ID to delete"),
                "delay": OPT_INT("Add task to queue with this delay in seconds"),
            },
            "required": ["node", "storage", "volume"],
        },
    },
    {
        "name": "copy_storage_volume",
        "description": "Copy a volume to another storage/VM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "storage": OPT_STR("Source storage ID"),
                "volume": OPT_STR("Source volume ID"),
                "target": OPT_STR("Target volume ID"),
                "target_node": OPT_STR("Target node (optional)"),
            },
            "required": ["node", "storage", "volume", "target"],
        },
    },
    {
        "name": "download_url_to_storage",
        "description": "Download a file (ISO, template) from a URL directly to storage on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "storage": OPT_STR("Storage ID"),
                "url": OPT_STR("Download URL"),
                "content": OPT_STR("Content type: iso or vztmpl"),
                "filename": OPT_STR("Target filename"),
                "checksum": OPT_STR("Expected checksum"),
                "checksum_algorithm": OPT_STR("Checksum algorithm: md5, sha1, sha224, sha256, sha384, sha512"),
                "verify_certificates": OPT_BOOL("Verify SSL certificates (default true)"),
            },
            "required": ["node", "storage", "url", "content", "filename"],
        },
    },
    # --- Backup (vzdump) ---
    {
        "name": "backup_vm",
        "description": "Create a backup of a VM or container using vzdump.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": OPT_INT("VM/CT ID to backup"),
                "storage": OPT_STR("Target storage ID for backup"),
                "mode": OPT_STR("Backup mode: snapshot, suspend, or stop"),
                "compress": OPT_STR("Compression: 0 (none), lzo, gzip, or zstd"),
                "notes-template": OPT_STR("Notes template for backup"),
                "protected": OPT_BOOL("Mark backup as protected"),
                "mailnotification": OPT_STR("Send email on: always or failure"),
                "mailto": OPT_STR("Email address for notifications"),
                "maxfiles": OPT_INT("Max backup count per guest (deprecated, use prune-backups)"),
                "prune-backups": OPT_STR("Prune policy (e.g. keep-last=3)"),
                "bwlimit": OPT_INT("Bandwidth limit in KB/s"),
                "ionice": OPT_INT("I/O nice priority"),
                "pigz": OPT_INT("Use pigz for gzip compression with N cores"),
                "remove": OPT_BOOL("Remove old backups according to prune policy"),
                "all": OPT_BOOL("Backup all guests"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "restore_vm_backup",
        "description": "Restore a VM from a backup file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": OPT_INT("Target VM ID (use 0 to auto-assign)"),
                "archive": OPT_STR("Backup archive volume ID (e.g. local:backup/vzdump-qemu-100-2024_01_01.vma.zst)"),
                "storage": OPT_STR("Target storage for restored disks"),
                "name": OPT_STR("VM name override"),
                "force": OPT_BOOL("Overwrite existing VM if VMID exists"),
                "unique": OPT_BOOL("Assign unique MAC addresses"),
                "start": OPT_BOOL("Start VM after restore"),
                "bwlimit": OPT_INT("Bandwidth limit in KB/s"),
                "pool": OPT_STR("Resource pool"),
                "live-restore": OPT_BOOL("Start VM immediately and restore in background"),
            },
            "required": ["node", "vmid", "archive"],
        },
    },
    {
        "name": "restore_container_backup",
        "description": "Restore an LXC container from a backup file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": OPT_INT("Target container ID"),
                "ostemplate": OPT_STR("Backup archive volume ID (e.g. local:backup/vzdump-lxc-106-2024_01_01.tar.zst)"),
                "storage": OPT_STR("Target storage for rootfs"),
                "hostname": OPT_STR("Hostname override"),
                "force": OPT_BOOL("Overwrite existing container"),
                "unique": OPT_BOOL("Assign unique MAC addresses"),
                "start": OPT_BOOL("Start container after restore"),
                "bwlimit": OPT_INT("Bandwidth limit in KB/s"),
                "pool": OPT_STR("Resource pool"),
                "unprivileged": OPT_BOOL("Create as unprivileged container"),
            },
            "required": ["node", "vmid", "ostemplate"],
        },
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    if name == "list_storage":
        node = args.get("node")
        if node:
            params = {k: args[k] for k in ("type",) if k in args}
            return await client.get(f"/nodes/{node}/storage", params or None)
        params = {k: args[k] for k in ("type", "enabled") if k in args}
        return await client.get("/storage", params or None)

    elif name == "get_storage_config":
        return await client.get(f"/storage/{args['storage']}")

    elif name == "create_storage":
        data = {k: v for k, v in args.items()}
        return await client.post("/storage", data)

    elif name == "update_storage":
        storage = args["storage"]
        data = {k: v for k, v in args.items() if k != "storage"}
        return await client.put(f"/storage/{storage}", data)

    elif name == "delete_storage":
        return await client.delete(f"/storage/{args['storage']}")

    elif name == "get_node_storage_status":
        return await client.get(f"/nodes/{args['node']}/storage/{args['storage']}/status")

    elif name == "list_storage_content":
        params = {k: args[k] for k in ("content", "vmid") if k in args}
        return await client.get(f"/nodes/{args['node']}/storage/{args['storage']}/content", params or None)

    elif name == "get_storage_volume_info":
        from urllib.parse import quote
        vol = quote(args["volume"], safe="")
        return await client.get(f"/nodes/{args['node']}/storage/{args['storage']}/content/{vol}")

    elif name == "delete_storage_volume":
        from urllib.parse import quote
        vol = quote(args["volume"], safe="")
        params = {}
        if "delay" in args:
            params["delay"] = args["delay"]
        return await client.delete(f"/nodes/{args['node']}/storage/{args['storage']}/content/{vol}", params or None)

    elif name == "copy_storage_volume":
        data = {"target": args["target"]}
        if "target_node" in args:
            data["target_node"] = args["target_node"]
        from urllib.parse import quote
        vol = quote(args["volume"], safe="")
        return await client.post(f"/nodes/{args['node']}/storage/{args['storage']}/content/{vol}", data)

    elif name == "download_url_to_storage":
        data = {k: v for k, v in args.items() if k not in ("node", "storage")}
        return await client.post(f"/nodes/{args['node']}/storage/{args['storage']}/download-url", data)

    elif name == "backup_vm":
        node = args["node"]
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(f"/nodes/{node}/vzdump", data)

    elif name == "restore_vm_backup":
        node = args["node"]
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(f"/nodes/{node}/qemu", data)

    elif name == "restore_container_backup":
        node = args["node"]
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(f"/nodes/{node}/lxc", data)

    raise ValueError(f"Unknown tool: {name}")
