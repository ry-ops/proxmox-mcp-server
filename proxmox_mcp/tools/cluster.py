"""Cluster tools: status, resources, HA, replication, backup schedules, tasks, options, SDN, bulk actions."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731


TOOLS = [
    {
        "name": "get_cluster_status",
        "description": "Get overall cluster status (nodes, quorum).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_cluster_resources",
        "description": "Get all cluster resources (nodes, VMs, containers, storage, pools) with usage stats.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": OPT_STR("Filter by type: vm, storage, node, sdn"),
            },
        },
    },
    {
        "name": "get_cluster_version",
        "description": "Get Proxmox VE API version.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_cluster_nextid",
        "description": "Get the next available VM/CT ID in the cluster.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vmid": OPT_INT("Suggest a specific VMID to check (optional)"),
            },
        },
    },
    {
        "name": "get_cluster_options",
        "description": "Get cluster-wide configuration options.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_cluster_options",
        "description": "Set cluster-wide configuration options.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyboard": OPT_STR("Default keyboard layout (e.g. en-us)"),
                "language": OPT_STR("Default language"),
                "email_from": OPT_STR("From address for cluster emails"),
                "max_workers": OPT_INT("Max migration workers"),
                "migration_cidr": OPT_STR("CIDR for migration network"),
                "migration_type": OPT_STR("Migration type: secure or insecure"),
                "next-id": OPT_STR("Next VM ID config (lower, upper)"),
                "notify": OPT_STR("Notification policy"),
                "registered-tags": OPT_STR("Allowed tags"),
                "tag-style": OPT_STR("Tag display style"),
                "delete": OPT_STR("Comma-separated keys to delete"),
            },
        },
    },
    {
        "name": "get_cluster_log",
        "description": "Get cluster-wide log entries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "max": OPT_INT("Maximum number of entries to return"),
            },
        },
    },
    {
        "name": "list_cluster_tasks",
        "description": "List recent cluster-wide tasks.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # --- Node tasks ---
    {
        "name": "list_node_tasks",
        "description": "List running and recent tasks on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": OPT_STR("Node name"),
                "limit": OPT_INT("Max tasks to return (default 50)"),
                "start": OPT_INT("Start offset"),
                "source": OPT_STR("Task source filter: all, archive, or active"),
                "statusfilter": OPT_STR("Filter by status: ok, error, warning, unknown"),
                "typefilter": OPT_STR("Filter by task type"),
                "userfilter": OPT_STR("Filter by user"),
                "vmid": OPT_INT("Filter by VM/CT ID"),
                "since": OPT_INT("Show tasks since Unix timestamp"),
                "until": OPT_INT("Show tasks until Unix timestamp"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_task_status",
        "description": "Get status of a specific task by UPID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": OPT_STR("Node name"),
                "upid": OPT_STR("Task UPID"),
            },
            "required": ["node", "upid"],
        },
    },
    {
        "name": "get_task_log",
        "description": "Get log output of a specific task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": OPT_STR("Node name"),
                "upid": OPT_STR("Task UPID"),
                "limit": OPT_INT("Max log lines"),
                "start": OPT_INT("Start offset"),
                "download": OPT_BOOL("Return full log for download"),
            },
            "required": ["node", "upid"],
        },
    },
    {
        "name": "stop_task",
        "description": "Stop/cancel a running task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": OPT_STR("Node name"),
                "upid": OPT_STR("Task UPID"),
            },
            "required": ["node", "upid"],
        },
    },
    # --- HA ---
    {
        "name": "list_ha_resources",
        "description": "List all HA-managed resources.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": OPT_STR("Filter by type: ct or vm"),
            },
        },
    },
    {
        "name": "get_ha_resource",
        "description": "Get HA configuration for a specific resource.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sid": OPT_STR("Resource SID (e.g. vm:100 or ct:106)"),
            },
            "required": ["sid"],
        },
    },
    {
        "name": "add_ha_resource",
        "description": "Add a resource to HA management.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sid": OPT_STR("Resource SID (e.g. vm:100)"),
                "state": OPT_STR("Desired HA state: started, stopped, enabled, disabled, ignored"),
                "group": OPT_STR("HA group"),
                "max_restart": OPT_INT("Max restart attempts"),
                "max_relocate": OPT_INT("Max relocation attempts"),
                "comment": OPT_STR("Comment"),
            },
            "required": ["sid"],
        },
    },
    {
        "name": "update_ha_resource",
        "description": "Update HA configuration for a resource.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sid": OPT_STR("Resource SID"),
                "state": OPT_STR("Desired state: started, stopped, enabled, disabled, ignored"),
                "group": OPT_STR("HA group"),
                "max_restart": OPT_INT("Max restart attempts"),
                "max_relocate": OPT_INT("Max relocation attempts"),
                "comment": OPT_STR("Comment"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["sid"],
        },
    },
    {
        "name": "delete_ha_resource",
        "description": "Remove a resource from HA management.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sid": OPT_STR("Resource SID"),
            },
            "required": ["sid"],
        },
    },
    {
        "name": "list_ha_groups",
        "description": "List all HA groups.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_ha_status",
        "description": "Get HA manager status.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # --- Replication ---
    {
        "name": "list_replication_jobs",
        "description": "List all replication jobs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "guest": OPT_INT("Filter by guest VMID"),
            },
        },
    },
    {
        "name": "get_replication_job",
        "description": "Get configuration of a replication job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Replication job ID (e.g. 100-0)"),
            },
            "required": ["id"],
        },
    },
    {
        "name": "create_replication_job",
        "description": "Create a new replication job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Job ID (format: <vmid>-<jobnum>, e.g. 100-0)"),
                "target": OPT_STR("Target node name"),
                "type": OPT_STR("Job type (always 'local')"),
                "schedule": OPT_STR("Schedule (e.g. */15 or hourly)"),
                "rate": OPT_INT("Rate limit in MB/s"),
                "comment": OPT_STR("Comment"),
                "disable": OPT_BOOL("Disable job"),
            },
            "required": ["id", "target", "type"],
        },
    },
    {
        "name": "update_replication_job",
        "description": "Update a replication job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Job ID"),
                "schedule": OPT_STR("Schedule"),
                "rate": OPT_INT("Rate limit in MB/s"),
                "comment": OPT_STR("Comment"),
                "disable": OPT_BOOL("Disable job"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["id"],
        },
    },
    {
        "name": "delete_replication_job",
        "description": "Delete a replication job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Job ID"),
                "force": OPT_BOOL("Force deletion even if running"),
                "keep": OPT_BOOL("Keep replicated snapshots on target"),
            },
            "required": ["id"],
        },
    },
    # --- Backup schedules ---
    {
        "name": "list_backup_jobs",
        "description": "List all scheduled backup jobs.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_backup_job",
        "description": "Get a scheduled backup job configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Backup job ID"),
            },
            "required": ["id"],
        },
    },
    {
        "name": "create_backup_job",
        "description": "Create a new scheduled backup job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Job ID (auto-generated if omitted)"),
                "node": OPT_STR("Node to run backup on"),
                "vmid": OPT_STR("Comma-separated VMIDs (or 'all')"),
                "all": OPT_BOOL("Backup all guests"),
                "storage": OPT_STR("Target storage ID"),
                "schedule": OPT_STR("Schedule (e.g. daily, 02:00, or cron expression)"),
                "mode": OPT_STR("Backup mode: snapshot, suspend, or stop"),
                "compress": OPT_STR("Compression: 0, lzo, gzip, or zstd"),
                "mailnotification": OPT_STR("Email notification: always or failure"),
                "mailto": OPT_STR("Email address"),
                "notes-template": OPT_STR("Notes template"),
                "prune-backups": OPT_STR("Prune policy (e.g. keep-last=7,keep-weekly=4)"),
                "enabled": OPT_BOOL("Enable job"),
                "bwlimit": OPT_INT("Bandwidth limit in KB/s"),
                "protected": OPT_BOOL("Mark backups as protected"),
                "pool": OPT_STR("Backup VMs in this pool"),
                "comment": OPT_STR("Job comment"),
            },
        },
    },
    {
        "name": "update_backup_job",
        "description": "Update a scheduled backup job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Job ID"),
                "schedule": OPT_STR("New schedule"),
                "storage": OPT_STR("Target storage"),
                "vmid": OPT_STR("VMIDs to backup"),
                "enabled": OPT_BOOL("Enable/disable job"),
                "prune-backups": OPT_STR("Prune policy"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["id"],
        },
    },
    {
        "name": "delete_backup_job",
        "description": "Delete a scheduled backup job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Job ID"),
            },
            "required": ["id"],
        },
    },
    # --- Bulk guest actions ---
    {
        "name": "bulk_start_guests",
        "description": "Start multiple VMs/containers at once.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vms": OPT_STR("Comma-separated VMIDs to start"),
                "force": OPT_BOOL("Force start even if HA managed"),
            },
        },
    },
    {
        "name": "bulk_shutdown_guests",
        "description": "Shutdown multiple VMs/containers at once.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vms": OPT_STR("Comma-separated VMIDs"),
                "force_stop": OPT_INT("Force stop after N seconds"),
            },
        },
    },
    {
        "name": "bulk_migrate_guests",
        "description": "Migrate multiple VMs/containers to a target node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": OPT_STR("Target node"),
                "vms": OPT_STR("Comma-separated VMIDs"),
                "maxworkers": OPT_INT("Max simultaneous migrations"),
                "with_local_disks": OPT_BOOL("Migrate local disks too"),
            },
            "required": ["target"],
        },
    },
    # --- Metrics ---
    {
        "name": "list_metrics_servers",
        "description": "List configured external metrics servers (InfluxDB, Graphite).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_metrics_server",
        "description": "Add an external metrics server.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Server ID"),
                "type": OPT_STR("Type: influxdb or graphite"),
                "server": OPT_STR("Server hostname/IP"),
                "port": OPT_INT("Server port"),
                "disable": OPT_BOOL("Disable this metrics server"),
                "timeout": OPT_INT("Connection timeout in seconds"),
                "path": OPT_STR("Graphite: path prefix"),
                "protocol": OPT_STR("InfluxDB: udp or http or https"),
                "organization": OPT_STR("InfluxDB: organization name"),
                "bucket": OPT_STR("InfluxDB: bucket name"),
                "token": OPT_STR("InfluxDB: authentication token"),
                "mtu": OPT_INT("UDP MTU"),
                "api-path-prefix": OPT_STR("InfluxDB API path prefix"),
                "max-body-size": OPT_INT("InfluxDB HTTP max body size in bytes"),
                "verify-certificate": OPT_BOOL("Verify SSL certificate"),
            },
            "required": ["id", "type", "server", "port"],
        },
    },
    {
        "name": "delete_metrics_server",
        "description": "Remove an external metrics server.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Server ID"),
            },
            "required": ["id"],
        },
    },
    # --- Jobs ---
    {
        "name": "list_realm_sync_jobs",
        "description": "List realm sync jobs.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "analyze_schedule",
        "description": "Analyze a Proxmox schedule string and return next execution times.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schedule": OPT_STR("Schedule string to analyze (e.g. daily, */15, 02:30)"),
                "iterations": OPT_INT("Number of next execution times to return"),
                "starttime": OPT_INT("Start time as Unix timestamp (default now)"),
            },
            "required": ["schedule"],
        },
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    if name == "get_cluster_status":
        return await client.get("/cluster/status")

    elif name == "get_cluster_resources":
        params = {k: args[k] for k in ("type",) if k in args}
        return await client.get("/cluster/resources", params or None)

    elif name == "get_cluster_version":
        return await client.get("/version")

    elif name == "get_cluster_nextid":
        params = {k: args[k] for k in ("vmid",) if k in args}
        return await client.get("/cluster/nextid", params or None)

    elif name == "get_cluster_options":
        return await client.get("/cluster/options")

    elif name == "set_cluster_options":
        data = {k: v for k, v in args.items()}
        return await client.put("/cluster/options", data)

    elif name == "get_cluster_log":
        params = {k: args[k] for k in ("max",) if k in args}
        return await client.get("/cluster/log", params or None)

    elif name == "list_cluster_tasks":
        return await client.get("/cluster/tasks")

    elif name == "list_node_tasks":
        node = args["node"]
        params = {k: args[k] for k in ("limit", "start", "source", "statusfilter", "typefilter", "userfilter", "vmid", "since", "until") if k in args}
        return await client.get(f"/nodes/{node}/tasks", params or None)

    elif name == "get_task_status":
        return await client.get(f"/nodes/{args['node']}/tasks/{args['upid']}/status")

    elif name == "get_task_log":
        params = {k: args[k] for k in ("limit", "start", "download") if k in args}
        return await client.get(f"/nodes/{args['node']}/tasks/{args['upid']}/log", params or None)

    elif name == "stop_task":
        return await client.delete(f"/nodes/{args['node']}/tasks/{args['upid']}")

    elif name == "list_ha_resources":
        params = {k: args[k] for k in ("type",) if k in args}
        return await client.get("/cluster/ha/resources", params or None)

    elif name == "get_ha_resource":
        return await client.get(f"/cluster/ha/resources/{args['sid']}")

    elif name == "add_ha_resource":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/ha/resources", data)

    elif name == "update_ha_resource":
        sid = args["sid"]
        data = {k: v for k, v in args.items() if k != "sid"}
        return await client.put(f"/cluster/ha/resources/{sid}", data)

    elif name == "delete_ha_resource":
        return await client.delete(f"/cluster/ha/resources/{args['sid']}")

    elif name == "list_ha_groups":
        return await client.get("/cluster/ha/groups")

    elif name == "get_ha_status":
        return await client.get("/cluster/ha/status/current")

    elif name == "list_replication_jobs":
        params = {k: args[k] for k in ("guest",) if k in args}
        return await client.get("/cluster/replication", params or None)

    elif name == "get_replication_job":
        return await client.get(f"/cluster/replication/{args['id']}")

    elif name == "create_replication_job":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/replication", data)

    elif name == "update_replication_job":
        job_id = args["id"]
        data = {k: v for k, v in args.items() if k != "id"}
        return await client.put(f"/cluster/replication/{job_id}", data)

    elif name == "delete_replication_job":
        params = {k: args[k] for k in ("force", "keep") if k in args}
        return await client.delete(f"/cluster/replication/{args['id']}", params or None)

    elif name == "list_backup_jobs":
        return await client.get("/cluster/backup")

    elif name == "get_backup_job":
        return await client.get(f"/cluster/backup/{args['id']}")

    elif name == "create_backup_job":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/backup", data)

    elif name == "update_backup_job":
        job_id = args["id"]
        data = {k: v for k, v in args.items() if k != "id"}
        return await client.put(f"/cluster/backup/{job_id}", data)

    elif name == "delete_backup_job":
        return await client.delete(f"/cluster/backup/{args['id']}")

    elif name == "bulk_start_guests":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/bulk-action/guest/start", data or None)

    elif name == "bulk_shutdown_guests":
        data = {}
        if "vms" in args:
            data["vms"] = args["vms"]
        if "force_stop" in args:
            data["force-stop"] = args["force_stop"]
        return await client.post("/cluster/bulk-action/guest/shutdown", data or None)

    elif name == "bulk_migrate_guests":
        data = {"target": args["target"]}
        if "vms" in args:
            data["vms"] = args["vms"]
        if "maxworkers" in args:
            data["maxworkers"] = args["maxworkers"]
        if "with_local_disks" in args:
            data["with-local-disks"] = args["with_local_disks"]
        return await client.post("/cluster/bulk-action/guest/migrate", data)

    elif name == "list_metrics_servers":
        return await client.get("/cluster/metrics/server")

    elif name == "create_metrics_server":
        server_id = args["id"]
        data = {k: v for k, v in args.items() if k != "id"}
        return await client.post(f"/cluster/metrics/server/{server_id}", data)

    elif name == "delete_metrics_server":
        return await client.delete(f"/cluster/metrics/server/{args['id']}")

    elif name == "list_realm_sync_jobs":
        return await client.get("/cluster/jobs/realm-sync")

    elif name == "analyze_schedule":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/jobs/schedule-analyze", data)

    raise ValueError(f"Unknown tool: {name}")
