"""Ceph tools: status, OSD, MON, MGR, MDS, pools, crush, fs, config."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

NODE = {"type": "string", "description": "Node name (e.g. pve01)"}
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731


TOOLS = [
    # --- Status ---
    {
        "name": "get_ceph_status",
        "description": "Get Ceph cluster status from a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_cluster_ceph_status",
        "description": "Get Ceph cluster status from cluster level.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_ceph_crush",
        "description": "Get the CRUSH map for the Ceph cluster.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_ceph_log",
        "description": "Get Ceph log entries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "limit": OPT_INT("Max entries"),
            },
            "required": ["node"],
        },
    },
    # --- Config ---
    {
        "name": "get_ceph_config",
        "description": "Get raw Ceph configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_ceph_config_db",
        "description": "Get Ceph config-key database.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    # --- OSD ---
    {
        "name": "list_ceph_osds",
        "description": "List all Ceph OSDs.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "create_ceph_osd",
        "description": "Create a new Ceph OSD on a disk.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "dev": OPT_STR("Block device path (e.g. /dev/sdb)"),
                "db_dev": OPT_STR("DB device (optional, for BlueStore)"),
                "wal_dev": OPT_STR("WAL device (optional, for BlueStore)"),
                "encrypted": OPT_BOOL("Encrypt OSD"),
                "crush-device-class": OPT_STR("Device class: hdd, ssd, or nvme"),
            },
            "required": ["node", "dev"],
        },
    },
    {
        "name": "delete_ceph_osd",
        "description": "Destroy a Ceph OSD.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "osdid": OPT_INT("OSD ID"),
                "cleanup": OPT_BOOL("Wipe the OSD disk"),
                "destroy": OPT_BOOL("Mark OSD as destroyed"),
            },
            "required": ["node", "osdid"],
        },
    },
    {
        "name": "set_ceph_osd_in",
        "description": "Mark a Ceph OSD as 'in' (active in cluster).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "osdid": OPT_INT("OSD ID"),
            },
            "required": ["node", "osdid"],
        },
    },
    {
        "name": "set_ceph_osd_out",
        "description": "Mark a Ceph OSD as 'out' (inactive).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "osdid": OPT_INT("OSD ID"),
            },
            "required": ["node", "osdid"],
        },
    },
    # --- MON ---
    {
        "name": "list_ceph_mons",
        "description": "List Ceph monitor daemons.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "create_ceph_mon",
        "description": "Create a Ceph monitor on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "monid": OPT_STR("Monitor ID (defaults to node name)"),
                "mon-address": OPT_STR("Monitor IP address"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "delete_ceph_mon",
        "description": "Remove a Ceph monitor.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "monid": OPT_STR("Monitor ID"),
            },
            "required": ["node", "monid"],
        },
    },
    # --- MGR ---
    {
        "name": "list_ceph_mgrs",
        "description": "List Ceph manager daemons.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "create_ceph_mgr",
        "description": "Create a Ceph manager daemon on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "id": OPT_STR("Manager ID (optional)"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "delete_ceph_mgr",
        "description": "Remove a Ceph manager daemon.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "id": OPT_STR("Manager ID"),
            },
            "required": ["node", "id"],
        },
    },
    # --- MDS ---
    {
        "name": "list_ceph_mds",
        "description": "List Ceph MDS (metadata server) daemons.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "create_ceph_mds",
        "description": "Create a Ceph MDS daemon.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("MDS name (optional)"),
                "hotstandby": OPT_BOOL("Create as hot standby"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "delete_ceph_mds",
        "description": "Remove a Ceph MDS daemon.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("MDS name"),
            },
            "required": ["node", "name"],
        },
    },
    # --- Pools ---
    {
        "name": "list_ceph_pools",
        "description": "List Ceph storage pools.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_ceph_pool",
        "description": "Get details of a specific Ceph pool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Pool name"),
            },
            "required": ["node", "name"],
        },
    },
    {
        "name": "create_ceph_pool",
        "description": "Create a new Ceph storage pool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Pool name"),
                "size": OPT_INT("Replication factor (default 3)"),
                "min_size": OPT_INT("Minimum replicas for I/O (default 2)"),
                "pg_num": OPT_INT("Number of placement groups (default 128)"),
                "pg_autoscale_mode": OPT_STR("PG autoscale mode: on, off, or warn"),
                "crush_rule": OPT_STR("CRUSH rule name"),
                "application": OPT_STR("Pool application: rbd, cephfs, or rgw"),
                "add_storages": OPT_BOOL("Add as Proxmox storage"),
            },
            "required": ["node", "name"],
        },
    },
    {
        "name": "update_ceph_pool",
        "description": "Update a Ceph pool configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Pool name"),
                "size": OPT_INT("Replication factor"),
                "min_size": OPT_INT("Minimum replicas"),
                "pg_num": OPT_INT("Placement groups"),
                "pg_autoscale_mode": OPT_STR("PG autoscale mode"),
                "crush_rule": OPT_STR("CRUSH rule"),
                "application": OPT_STR("Pool application"),
            },
            "required": ["node", "name"],
        },
    },
    {
        "name": "delete_ceph_pool",
        "description": "Delete a Ceph pool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Pool name"),
                "force": OPT_BOOL("Force deletion"),
                "remove_storages": OPT_BOOL("Remove associated storage config"),
                "remove_ecprofile": OPT_BOOL("Remove erasure code profile"),
            },
            "required": ["node", "name"],
        },
    },
    # --- Filesystem ---
    {
        "name": "list_ceph_fs",
        "description": "List CephFS filesystems.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "create_ceph_fs",
        "description": "Create a CephFS filesystem.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Filesystem name (default cephfs)"),
                "add-storage": OPT_BOOL("Add as Proxmox storage"),
                "pg_num": OPT_INT("Placement groups for metadata pool"),
            },
            "required": ["node"],
        },
    },
    # --- Start/Stop/Restart ---
    {
        "name": "start_ceph",
        "description": "Start Ceph services on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "service": OPT_STR("Specific service to start (optional)"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "stop_ceph",
        "description": "Stop Ceph services on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "service": OPT_STR("Specific service to stop (optional)"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "restart_ceph",
        "description": "Restart Ceph services on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "service": OPT_STR("Specific service to restart (optional)"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_cluster_ceph_metadata",
        "description": "Get Ceph daemon metadata (versions, host info).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": OPT_STR("Filter by daemon type: mon, mgr, mds, osd"),
            },
        },
    },
    {
        "name": "get_cluster_ceph_flags",
        "description": "Get Ceph cluster flags (e.g. noout, norebalance, noscrub).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_cluster_ceph_flags",
        "description": "Set Ceph cluster flags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "noout": OPT_BOOL("Set/unset noout flag"),
                "norebalance": OPT_BOOL("Set/unset norebalance flag"),
                "noscrub": OPT_BOOL("Set/unset noscrub flag"),
                "nodeep-scrub": OPT_BOOL("Set/unset nodeep-scrub flag"),
                "noin": OPT_BOOL("Set/unset noin flag"),
                "nobackfill": OPT_BOOL("Set/unset nobackfill flag"),
                "norecovery": OPT_BOOL("Set/unset norecovery flag"),
                "pause": OPT_BOOL("Set/unset pause flag"),
                "noup": OPT_BOOL("Set/unset noup flag"),
                "nodown": OPT_BOOL("Set/unset nodown flag"),
            },
        },
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    node = args.get("node", "")

    if name == "get_ceph_status":
        return await client.get(f"/nodes/{node}/ceph/status")

    elif name == "get_cluster_ceph_status":
        return await client.get("/cluster/ceph/status")

    elif name == "get_ceph_crush":
        return await client.get(f"/nodes/{node}/ceph/crush")

    elif name == "get_ceph_log":
        params = {k: args[k] for k in ("limit",) if k in args}
        return await client.get(f"/nodes/{node}/ceph/log", params or None)

    elif name == "get_ceph_config":
        return await client.get(f"/nodes/{node}/ceph/cfg/raw")

    elif name == "get_ceph_config_db":
        return await client.get(f"/nodes/{node}/ceph/cfg/db")

    elif name == "list_ceph_osds":
        return await client.get(f"/nodes/{node}/ceph/osd")

    elif name == "create_ceph_osd":
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(f"/nodes/{node}/ceph/osd", data)

    elif name == "delete_ceph_osd":
        params = {k: args[k] for k in ("cleanup", "destroy") if k in args}
        return await client.delete(f"/nodes/{node}/ceph/osd/{args['osdid']}", params or None)

    elif name == "set_ceph_osd_in":
        return await client.post(f"/nodes/{node}/ceph/osd/{args['osdid']}/in")

    elif name == "set_ceph_osd_out":
        return await client.post(f"/nodes/{node}/ceph/osd/{args['osdid']}/out")

    elif name == "list_ceph_mons":
        return await client.get(f"/nodes/{node}/ceph/mon")

    elif name == "create_ceph_mon":
        data = {k: v for k, v in args.items() if k not in ("node",)}
        return await client.post(f"/nodes/{node}/ceph/mon", data or None)

    elif name == "delete_ceph_mon":
        return await client.delete(f"/nodes/{node}/ceph/mon/{args['monid']}")

    elif name == "list_ceph_mgrs":
        return await client.get(f"/nodes/{node}/ceph/mgr")

    elif name == "create_ceph_mgr":
        data = {k: v for k, v in args.items() if k not in ("node",)}
        return await client.post(f"/nodes/{node}/ceph/mgr", data or None)

    elif name == "delete_ceph_mgr":
        return await client.delete(f"/nodes/{node}/ceph/mgr/{args['id']}")

    elif name == "list_ceph_mds":
        return await client.get(f"/nodes/{node}/ceph/mds")

    elif name == "create_ceph_mds":
        data = {k: v for k, v in args.items() if k not in ("node",)}
        return await client.post(f"/nodes/{node}/ceph/mds", data or None)

    elif name == "delete_ceph_mds":
        return await client.delete(f"/nodes/{node}/ceph/mds/{args['name']}")

    elif name == "list_ceph_pools":
        return await client.get(f"/nodes/{node}/ceph/pool")

    elif name == "get_ceph_pool":
        return await client.get(f"/nodes/{node}/ceph/pool/{args['name']}")

    elif name == "create_ceph_pool":
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(f"/nodes/{node}/ceph/pool", data)

    elif name == "update_ceph_pool":
        pool_name = args["name"]
        data = {k: v for k, v in args.items() if k not in ("node", "name")}
        return await client.put(f"/nodes/{node}/ceph/pool/{pool_name}", data)

    elif name == "delete_ceph_pool":
        params = {k: args[k] for k in ("force", "remove_storages", "remove_ecprofile") if k in args}
        return await client.delete(f"/nodes/{node}/ceph/pool/{args['name']}", params or None)

    elif name == "list_ceph_fs":
        return await client.get(f"/nodes/{node}/ceph/fs")

    elif name == "create_ceph_fs":
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(f"/nodes/{node}/ceph/fs", data or None)

    elif name == "start_ceph":
        data = {}
        if "service" in args:
            data["service"] = args["service"]
        return await client.post(f"/nodes/{node}/ceph/start", data or None)

    elif name == "stop_ceph":
        data = {}
        if "service" in args:
            data["service"] = args["service"]
        return await client.post(f"/nodes/{node}/ceph/stop", data or None)

    elif name == "restart_ceph":
        data = {}
        if "service" in args:
            data["service"] = args["service"]
        return await client.post(f"/nodes/{node}/ceph/restart", data or None)

    elif name == "get_cluster_ceph_metadata":
        params = {k: args[k] for k in ("type",) if k in args}
        return await client.get("/cluster/ceph/metadata", params or None)

    elif name == "get_cluster_ceph_flags":
        return await client.get("/cluster/ceph/flags")

    elif name == "set_cluster_ceph_flags":
        data = {k: v for k, v in args.items()}
        return await client.put("/cluster/ceph/flags", data)

    raise ValueError(f"Unknown tool: {name}")
