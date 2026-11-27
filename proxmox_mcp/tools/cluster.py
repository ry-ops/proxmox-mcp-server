"""Cluster tools: status, resources, HA, replication, backup schedules, tasks, options, SDN, bulk actions."""

from __future__ import annotations

import re
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
        "description": (
            "Set cluster-wide options (datacenter.cfg). Structured options take Proxmox's key=value,key=value form, "
            "e.g. migration: type=secure,network=10.10.0.0/24."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "migration": OPT_STR("Migration settings: type=secure|insecure[,network=<CIDR>]"),
                "replication": OPT_STR("Storage replication settings: type=secure|insecure[,network=<CIDR>]"),
                "crs": OPT_STR(
                    "Cluster resource scheduling: ha=basic|static|dynamic[,ha-rebalance-on-start=1]"
                    "[,ha-auto-rebalance=1,ha-auto-rebalance-threshold=<n>,ha-auto-rebalance-margin=<n>,"
                    "ha-auto-rebalance-method=bruteforce|topsis,ha-auto-rebalance-hold-duration=<n>]"
                ),
                "ha": OPT_STR("HA settings: shutdown_policy=freeze|failover|conditional|migrate"),
                "fencing": OPT_STR("HA fencing mode: watchdog (default), hardware or both"),
                "next-id": OPT_STR("Free-VMID range for auto-selection: lower=<n>,upper=<n>[,unique=1][,enforce=1]"),
                "token-policy": OPT_STR(
                    "API token policy, e.g. max-lifetime=<seconds>,require-expiry=1,require-privilege-separation=1"
                    "[,disallow-expiry-extension=1][,default-to-max-lifetime=1][,allow-extension-on-regenerate=1]"
                ),
                "user-tag-access": OPT_STR("Which tags users may set: user-allow=none|list|existing|free[,user-allow-list=<a;b>]"),
                "registered-tags": OPT_STR("Tags only Sys.Modify on / may set or delete (semicolon-separated)"),
                "tag-style": OPT_STR(
                    "Tag display: shape=full|circle|dense|none[,ordering=config|alphabetical][,case-sensitive=1][,color-map=<tag:hex;...>]"
                ),
                "notify": OPT_STR(
                    "Notification policy: fencing=always|never, package-updates=auto|always|never, replication=always|never"
                ),
                "bwlimit": OPT_STR("I/O bandwidth limits in KiB/s: default=<n>,clone=<n>,migration=<n>,move=<n>,restore=<n>"),
                "max_workers": OPT_INT("Workers per node for bulk actions and HA tasks"),
                "email_from": OPT_STR("From address for cluster emails"),
                "keyboard": OPT_STR("Default keyboard layout for VNC (e.g. en-us)"),
                "language": OPT_STR("Default web interface language"),
                "console": OPT_STR("Default console viewer: html5, xtermjs, vv or applet"),
                "mac_prefix": OPT_STR("Prefix for generated guest MAC addresses (default BC:24:11)"),
                "http_proxy": OPT_STR("HTTP proxy for downloads, e.g. http://host:port/"),
                "consent-text": OPT_STR("Text shown before login, base64-encoded"),
                "webauthn": OPT_STR("WebAuthn settings: rp=<name>,origin=<https://host:8006>,id=<host>[,allow-subdomains=1]"),
                "u2f": OPT_STR("U2F settings: appid=<url>,origin=<url>"),
                "description": OPT_STR("Datacenter notes, shown in the web interface"),
                "location": OPT_STR("Cluster location: latitude=<n>,longitude=<n>[,name=<name>]"),
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
                "group": OPT_STR("HA group (deprecated in Proxmox VE 9 in favour of HA rules)"),
                "max_restart": OPT_INT("Max restart attempts"),
                "max_relocate": OPT_INT("Max relocation attempts"),
                "failback": OPT_BOOL("Move back to the highest-priority node in its node-affinity rule when that node returns"),
                "auto-rebalance": OPT_BOOL("Allow the HA manager to move it during automatic rebalancing"),
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
                "group": OPT_STR("HA group (deprecated in Proxmox VE 9 in favour of HA rules)"),
                "max_restart": OPT_INT("Max restart attempts"),
                "max_relocate": OPT_INT("Max relocation attempts"),
                "failback": OPT_BOOL("Move back to the highest-priority node in its node-affinity rule when that node returns"),
                "auto-rebalance": OPT_BOOL("Allow the HA manager to move it during automatic rebalancing"),
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
                "purge": OPT_BOOL("Also remove it from HA rules, deleting rules left with no other resource"),
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
    {
        "name": "get_ha_manager_status",
        "description": (
            "Get the full HA manager state: the CRM master, each node's LRM and its mode (active, "
            "maintenance), fencing and watchdog state, and every resource's state as the manager sees it."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_ha_rules",
        "description": (
            "List HA rules. Proxmox VE 9 replaces HA groups with rules: node-affinity rules keep resources "
            "on (or off) chosen nodes, resource-affinity rules keep resources together or apart."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["node-affinity", "resource-affinity"], "description": "Only this rule type"},
                "resource": OPT_STR("Only rules that affect this resource (e.g. vm:100)"),
            },
        },
    },
    {
        "name": "get_ha_rule",
        "description": "Get one HA rule.",
        "inputSchema": {
            "type": "object",
            "properties": {"rule": OPT_STR("Rule ID")},
            "required": ["rule"],
        },
    },
    {
        "name": "create_ha_rule",
        "description": (
            "Create an HA rule. node-affinity: resources and nodes (node[:priority],..., higher priority "
            "preferred); strict=true limits the resources to those nodes and stops them if none is up. "
            "resource-affinity: resources (two or more) and affinity; these rules are always strict."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "rule": OPT_STR("Rule ID (letters, digits, - and _; starts with a letter)"),
                "type": {"type": "string", "enum": ["node-affinity", "resource-affinity"], "description": "Rule type"},
                "resources": OPT_STR("HA resources, e.g. vm:100,ct:101"),
                "nodes": OPT_STR("node-affinity only: nodes with optional priority, e.g. pve1:2,pve2:1,pve3"),
                "affinity": {"type": "string", "enum": ["positive", "negative"], "description": (
                        "node-affinity: positive (default) keeps the resources on the given nodes, negative keeps them off. "
                        "resource-affinity (required): positive keeps the resources together on one node, negative on separate nodes"
                    )},
                "strict": OPT_BOOL("node-affinity only: restrict the resources to the nodes (default false)"),
                "comment": OPT_STR("Description"),
                "disable": OPT_BOOL("Create the rule disabled"),
            },
            "required": ["rule", "type", "resources"],
        },
    },
    {
        "name": "update_ha_rule",
        "description": "Update an HA rule. Give its type; only the fields you pass change.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "rule": OPT_STR("Rule ID"),
                "type": {"type": "string", "enum": ["node-affinity", "resource-affinity"], "description": "Rule type"},
                "resources": OPT_STR("HA resources, e.g. vm:100,ct:101"),
                "nodes": OPT_STR("node-affinity only: nodes with optional priority"),
                "affinity": {"type": "string", "enum": ["positive", "negative"], "description": (
                        "node-affinity: positive (default) keeps the resources on the given nodes, negative keeps them off. "
                        "resource-affinity (required): positive keeps the resources together on one node, negative on separate nodes"
                    )},
                "strict": OPT_BOOL("node-affinity only: restrict the resources to the nodes"),
                "comment": OPT_STR("Description"),
                "disable": OPT_BOOL("Disable or enable the rule"),
                "delete": OPT_STR("Settings to remove, comma-separated"),
                "digest": OPT_STR("Config digest, to refuse the change if the rule changed meanwhile"),
            },
            "required": ["rule", "type"],
        },
    },
    {
        "name": "delete_ha_rule",
        "description": "Delete an HA rule. The resources stay HA-managed, without this constraint.",
        "inputSchema": {
            "type": "object",
            "properties": {"rule": OPT_STR("Rule ID")},
            "required": ["rule"],
        },
    },
    {
        "name": "migrate_ha_resource",
        "description": (
            "Live-migrate an HA-managed guest through the HA manager, which a plain migrate_vm can't do "
            "for HA guests. Returns the resources blocking the move (and the rule causing it) and any that "
            "move with it because of a positive resource-affinity rule."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sid": OPT_STR("HA resource, e.g. vm:100 or ct:101 (a bare ID means that guest)"),
                "node": OPT_STR("Target node"),
                "with-conntrack-state": OPT_BOOL("VMs: carry the firewall's connection-tracking entries over"),
                "skip-config-check": OPT_BOOL("Skip checking that the target can parse the guest's config"),
            },
            "required": ["sid", "node"],
        },
    },
    {
        "name": "relocate_ha_resource",
        "description": (
            "Relocate an HA-managed guest: stop it on its node and start it on the target. Use when live "
            "migration isn't possible. The guest is down in between."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sid": OPT_STR("HA resource, e.g. vm:100 or ct:101"),
                "node": OPT_STR("Target node"),
            },
            "required": ["sid", "node"],
        },
    },
    {
        "name": "set_node_maintenance",
        "description": (
            "Put a node into HA maintenance mode, or take it out. Enabling moves the node's HA-managed "
            "guests to other nodes (respecting HA rules) and keeps new ones off until it's disabled."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": OPT_STR("Node name"),
                "maintenance-mode": {"type": "string", "enum": ["enable", "disable"], "description": "enable or disable"},
            },
            "required": ["node", "maintenance-mode"],
        },
    },
    {
        "name": "disarm_ha",
        "description": (
            "Disarm the HA stack cluster-wide, releasing every watchdog, for network or corosync work. "
            "Nodes are not fenced while disarmed. freeze: HA ignores new commands and state changes; "
            "ignore: resources are left to you, outside HA. Re-arm with arm_ha."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "resource-mode": {"type": "string", "enum": ["freeze", "ignore"], "description": "How HA treats resources while disarmed"},
            },
            "required": ["resource-mode"],
        },
    },
    {
        "name": "arm_ha",
        "description": "Re-arm the HA stack after disarm_ha.",
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
                "fleecing": OPT_STR("VMs only: fleecing, e.g. enabled=1,storage=local-lvm, so a slow backup target doesn't stall the guest"),
                "pbs-change-detection-mode": OPT_STR("Containers to Proxmox Backup Server: legacy, data or metadata"),
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
                "fleecing": OPT_STR("VMs only: fleecing, e.g. enabled=1,storage=local-lvm"),
                "pbs-change-detection-mode": OPT_STR("Containers to Proxmox Backup Server: legacy, data or metadata"),
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


_SID = re.compile(r"(?:(?:vm|ct):)?\d+")
_CONFIG_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


def _sid(args: dict[str, Any]) -> str:
    """The HA resource ID for a path: vm:100, ct:101 or a bare guest ID."""
    sid = str(args["sid"]).strip()
    if not _SID.fullmatch(sid):
        raise ValueError(f"sid must look like vm:100, ct:101 or 100, got {sid!r}")
    return sid


def _rule(args: dict[str, Any]) -> str:
    rule = str(args["rule"]).strip()
    if not _CONFIG_ID.fullmatch(rule):
        raise ValueError(f"rule must start with a letter and use only letters, digits, - and _, got {rule!r}")
    return rule


def _check_rule_fields(args: dict[str, Any], creating: bool) -> None:
    """Catch the mix-ups Proxmox would reject, with a clearer message."""
    _rule(args)
    if args["type"] == "resource-affinity":
        wrong = [k for k in ("nodes", "strict") if k in args]
        if wrong:
            raise ValueError(f"{', '.join(wrong)} only apply to node-affinity rules")
        if creating and "affinity" not in args:
            raise ValueError("A resource-affinity rule needs affinity: positive (together) or negative (apart)")
    elif creating and "nodes" not in args:
        raise ValueError("A node-affinity rule needs nodes, e.g. pve1:2,pve2:1")


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
        data = dict(args.items())
        # Earlier versions offered migration_type and migration_cidr, which aren't API options:
        # Proxmox takes one `migration` property. Translate them for older callers.
        legacy_type, legacy_net = data.pop("migration_type", None), data.pop("migration_cidr", None)
        if (legacy_type or legacy_net) and "migration" not in data:
            parts = [f"type={legacy_type or 'secure'}"] + ([f"network={legacy_net}"] if legacy_net else [])
            data["migration"] = ",".join(parts)
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
        return await client.get(f"/cluster/ha/resources/{_sid(args)}")

    elif name == "add_ha_resource":
        data = dict(args.items())
        return await client.post("/cluster/ha/resources", data)

    elif name == "update_ha_resource":
        data = {k: v for k, v in args.items() if k != "sid"}
        return await client.put(f"/cluster/ha/resources/{_sid(args)}", data)

    elif name == "delete_ha_resource":
        params = {"purge": args["purge"]} if "purge" in args else None
        return await client.delete(f"/cluster/ha/resources/{_sid(args)}", params)

    elif name == "list_ha_groups":
        return await client.get("/cluster/ha/groups")

    elif name == "get_ha_status":
        return await client.get("/cluster/ha/status/current")

    elif name == "get_ha_manager_status":
        return await client.get("/cluster/ha/status/manager_status")

    elif name == "list_ha_rules":
        params = {k: args[k] for k in ("type", "resource") if k in args}
        return await client.get("/cluster/ha/rules", params or None)

    elif name == "get_ha_rule":
        return await client.get(f"/cluster/ha/rules/{_rule(args)}")

    elif name == "create_ha_rule":
        _check_rule_fields(args, creating=True)
        return await client.post("/cluster/ha/rules", dict(args.items()))

    elif name == "update_ha_rule":
        _check_rule_fields(args, creating=False)
        data = {k: v for k, v in args.items() if k != "rule"}
        return await client.put(f"/cluster/ha/rules/{_rule(args)}", data)

    elif name == "delete_ha_rule":
        return await client.delete(f"/cluster/ha/rules/{_rule(args)}")

    elif name in ("migrate_ha_resource", "relocate_ha_resource"):
        action = "migrate" if name == "migrate_ha_resource" else "relocate"
        data = {k: v for k, v in args.items() if k != "sid"}
        return await client.post(f"/cluster/ha/resources/{_sid(args)}/{action}", data)

    elif name == "set_node_maintenance":
        return await client.put(f"/nodes/{args['node']}/maintenance", {"maintenance-mode": args["maintenance-mode"]})

    elif name == "disarm_ha":
        return await client.post("/cluster/ha/status/disarm-ha", {"resource-mode": args["resource-mode"]})

    elif name == "arm_ha":
        return await client.post("/cluster/ha/status/arm-ha")

    elif name == "list_replication_jobs":
        params = {k: args[k] for k in ("guest",) if k in args}
        return await client.get("/cluster/replication", params or None)

    elif name == "get_replication_job":
        return await client.get(f"/cluster/replication/{args['id']}")

    elif name == "create_replication_job":
        data = dict(args.items())
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
        data = dict(args.items())
        return await client.post("/cluster/backup", data)

    elif name == "update_backup_job":
        job_id = args["id"]
        data = {k: v for k, v in args.items() if k != "id"}
        return await client.put(f"/cluster/backup/{job_id}", data)

    elif name == "delete_backup_job":
        return await client.delete(f"/cluster/backup/{args['id']}")

    elif name == "bulk_start_guests":
        data = dict(args.items())
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
        data = dict(args.items())
        return await client.post("/cluster/jobs/schedule-analyze", data)

    raise ValueError(f"Unknown tool: {name}")
