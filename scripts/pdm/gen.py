#!/usr/bin/env python3
"""Generate the PDM toolset spec and the ROADMAP map from PDM's published API schema.

    python3 scripts/pdm/gen.py path/to/apidoc.js

apidoc.js is PDM's API viewer data: https://pdm.proxmox.com/docs/api-viewer/apidoc.js.
Writes proxmox_mcp/tools/pdm_spec.json (the phase 1 and 2 tools) and
scripts/pdm/roadmap-section.md (the ROADMAP section with every endpoint). Every endpoint
must match exactly one rule; the script fails on any it can't place.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter, OrderedDict
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC_OUT = ROOT / "proxmox_mcp" / "tools" / "pdm_spec.json"
CARD = ROOT / "agent-card.json"
ROADMAP_OUT = pathlib.Path(__file__).with_name("roadmap-section.md")

P1, P2, P3, NO = "1", "2", "3", "-"

# (method regex, path regex, phase, tool name or reason[, "desc:<exact description>"]).
# First match wins. {T} stands for qemu|lxc: both share one tool with a `type` input.
RULES: list[tuple[str, ...]] = [
    # --- not planned ---
    ("GET", r".*", NO, "index", "desc:Directory index."),
    ("GET", r".*/vncwebsocket", NO, "interactive console (websocket), not usable over MCP"),
    ("POST", r".*/termproxy", NO, "interactive console (terminal proxy), not usable over MCP"),
    ("POST", r".*/vncproxy", NO, "interactive console (VNC proxy), not usable over MCP"),
    ("POST", r"/access/ticket", NO, "login handshake; the client authenticates with an API token"),
    ("DELETE", r"/access/ticket", NO, "logout for browser sessions; tokens don't use tickets"),
    ("POST", r"/access/openid/(auth-url|login)", NO, "browser OpenID login flow"),
    ("POST", r"/auto-install/answer", NO, "called by the Proxmox installer, not by people"),
    ("GET", r"/nodes", NO, "compatibility shim; PDM has one node, `localhost`"),
    # --- phase 1: read ---
    ("GET", r"/ping", P1, "pdm_ping"),
    ("GET", r"/version", P1, "pdm_version"),
    ("GET", r"/remotes/remote", P1, "pdm_list_remotes"),
    ("GET", r"/remotes/remote/\{id\}/config", P1, "pdm_get_remote_config"),
    ("GET", r"/remotes/remote/\{id\}/version", P1, "pdm_get_remote_version"),
    ("GET", r"/remotes/remote/\{id\}/rrddata", P1, "pdm_get_remote_rrddata"),
    ("GET", r"/remotes/metric-collection/status", P1, "pdm_metric_collection_status"),
    ("GET", r"/remotes/tasks/list", P1, "pdm_list_remote_tasks"),
    ("GET", r"/remotes/tasks/statistics", P1, "pdm_remote_task_statistics"),
    ("GET", r"/remotes/updates/summary", P1, "pdm_update_summary"),
    ("GET", r"/resources/list", P1, "pdm_list_resources"),
    ("GET", r"/resources/status", P1, "pdm_resource_status"),
    ("GET", r"/resources/top-entities", P1, "pdm_top_entities"),
    ("GET", r"/resources/subscription", P1, "pdm_subscription_status"),
    ("GET", r"/resources/location-info", P1, "pdm_location_info"),
    ("GET", r"/pve/remotes", P1, "pdm_pve_list_remotes"),
    ("GET", r"/pve/remotes/\{remote\}/cluster-status", P1, "pdm_pve_cluster_status"),
    ("GET", r"/pve/remotes/\{remote\}/cluster-nextid", P1, "pdm_pve_next_vmid"),
    ("GET", r"/pve/remotes/\{remote\}/options", P1, "pdm_pve_cluster_options"),
    ("GET", r"/pve/remotes/\{remote\}/resources", P1, "pdm_pve_resources"),
    ("GET", r"/pve/remotes/\{remote\}/updates", P1, "pdm_pve_updates"),
    ("GET", r"/pve/remotes/\{remote\}/nodes", P1, "pdm_pve_list_nodes"),
    ("GET", r"/pve/remotes/\{remote\}/nodes/\{node\}/status", P1, "pdm_pve_node_status"),
    ("GET", r"/pve/remotes/\{remote\}/nodes/\{node\}/config", P1, "pdm_pve_node_config"),
    ("GET", r"/pve/remotes/\{remote\}/nodes/\{node\}/network", P1, "pdm_pve_node_network"),
    ("GET", r"/pve/remotes/\{remote\}/nodes/\{node\}/rrddata", P1, "pdm_pve_node_rrddata"),
    (
        "GET",
        r"/pve/remotes/\{remote\}/nodes/\{node\}/subscription",
        P1,
        "pdm_pve_node_subscription",
    ),
    ("GET", r"/pve/remotes/\{remote\}/nodes/\{node\}/storage", P1, "pdm_pve_list_storage"),
    (
        "GET",
        r"/pve/remotes/\{remote\}/nodes/\{node\}/storage/\{storage\}/status",
        P1,
        "pdm_pve_storage_status",
    ),
    (
        "GET",
        r"/pve/remotes/\{remote\}/nodes/\{node\}/storage/\{storage\}/rrddata",
        P1,
        "pdm_pve_storage_rrddata",
    ),
    ("GET", r"/pve/remotes/\{remote\}/nodes/\{node\}/apt/update", P1, "pdm_pve_node_apt_updates"),
    (
        "GET",
        r"/pve/remotes/\{remote\}/nodes/\{node\}/apt/repositories",
        P1,
        "pdm_pve_node_apt_repositories",
    ),
    (
        "GET",
        r"/pve/remotes/\{remote\}/nodes/\{node\}/apt/changelog",
        P1,
        "pdm_pve_node_apt_changelog",
    ),
    (
        "GET",
        r"/pve/remotes/\{remote\}/nodes/\{node\}/sdn/vnets/\{vnet\}/mac-vrf",
        P1,
        "pdm_pve_sdn_vnet_mac_vrf",
    ),
    (
        "GET",
        r"/pve/remotes/\{remote\}/nodes/\{node\}/sdn/zones/\{zone\}/ip-vrf",
        P1,
        "pdm_pve_sdn_zone_ip_vrf",
    ),
    (
        "GET",
        r"/pve/remotes/\{remote\}/firewall/(options|rules|status)",
        P1,
        "pdm_pve_cluster_firewall",
    ),
    (
        "GET",
        r"/pve/remotes/\{remote\}/nodes/\{node\}/firewall/(options|rules|status)",
        P1,
        "pdm_pve_node_firewall",
    ),
    ("GET", r"/pve/firewall/status", P1, "pdm_pve_firewall_status_all"),
    ("GET", r"/pve/remotes/\{remote\}/\{T\}", P1, "pdm_pve_list_guests"),
    ("GET", r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/config", P1, "pdm_pve_guest_config"),
    ("GET", r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/pending", P1, "pdm_pve_guest_pending"),
    ("GET", r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/status", P1, "pdm_pve_guest_status"),
    ("GET", r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/rrddata", P1, "pdm_pve_guest_rrddata"),
    ("GET", r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/snapshot", P1, "pdm_pve_list_snapshots"),
    (
        "GET",
        r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/firewall/(options|rules)",
        P1,
        "pdm_pve_guest_firewall",
    ),
    ("GET", r"/pve/remotes/\{remote\}/qemu/\{vmid\}/migrate", P1, "pdm_pve_migrate_preconditions"),
    ("GET", r"/pve/remotes/\{remote\}/tasks", P1, "pdm_pve_list_tasks"),
    ("GET", r"/pve/remotes/\{remote\}/tasks/\{upid\}/status", P1, "pdm_pve_task_status"),
    ("GET", r"/pve/remotes/\{remote\}/tasks/\{upid\}/log", P1, "pdm_pve_task_log"),
    ("GET", r"/pbs/remotes", P1, "pdm_pbs_list_remotes"),
    ("GET", r"/pbs/remotes/\{remote\}/status", P1, "pdm_pbs_status"),
    ("GET", r"/pbs/remotes/\{remote\}/rrddata", P1, "pdm_pbs_rrddata"),
    ("GET", r"/pbs/remotes/\{remote\}/datastore", P1, "pdm_pbs_list_datastores"),
    (
        "GET",
        r"/pbs/remotes/\{remote\}/datastore/\{datastore\}/namespaces",
        P1,
        "pdm_pbs_list_namespaces",
    ),
    (
        "GET",
        r"/pbs/remotes/\{remote\}/datastore/\{datastore\}/snapshots",
        P1,
        "pdm_pbs_list_snapshots",
    ),
    (
        "GET",
        r"/pbs/remotes/\{remote\}/datastore/\{datastore\}/rrddata",
        P1,
        "pdm_pbs_datastore_rrddata",
    ),
    ("GET", r"/pbs/remotes/\{remote\}/nodes/\{node\}/apt/update", P1, "pdm_pbs_node_apt_updates"),
    (
        "GET",
        r"/pbs/remotes/\{remote\}/nodes/\{node\}/apt/repositories",
        P1,
        "pdm_pbs_node_apt_repositories",
    ),
    (
        "GET",
        r"/pbs/remotes/\{remote\}/nodes/\{node\}/apt/changelog",
        P1,
        "pdm_pbs_node_apt_changelog",
    ),
    (
        "GET",
        r"/pbs/remotes/\{remote\}/nodes/\{node\}/subscription",
        P1,
        "pdm_pbs_node_subscription",
    ),
    ("GET", r"/pbs/remotes/\{remote\}/tasks", P1, "pdm_pbs_list_tasks"),
    ("GET", r"/pbs/remotes/\{remote\}/tasks/\{upid\}/status", P1, "pdm_pbs_task_status"),
    ("GET", r"/pbs/remotes/\{remote\}/tasks/\{upid\}/log", P1, "pdm_pbs_task_log"),
    ("GET", r"/sdn/(zones|vnets|controllers)", P1, "pdm_sdn_list"),
    ("GET", r"/ceph/clusters", P1, "pdm_ceph_list_clusters"),
    (
        "GET",
        r"/ceph/clusters/\{cluster\}/(summary|status|flags|fs|mds|mgr|mon|osd-tree|pools)",
        P1,
        "pdm_ceph_cluster",
    ),
    ("GET", r"/nodes/\{node\}/tasks", P1, "pdm_list_tasks"),
    ("GET", r"/nodes/\{node\}/tasks/\{upid\}/status", P1, "pdm_task_status"),
    ("GET", r"/nodes/\{node\}/tasks/\{upid\}/log", P1, "pdm_task_log"),
    ("GET", r"/nodes/\{node\}/status", P1, "pdm_node_status"),
    ("GET", r"/access/permissions", P1, "pdm_my_permissions"),
    # --- phase 2: actions ---
    ("POST", r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/start", P2, "pdm_pve_start_guest"),
    ("POST", r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/stop", P2, "pdm_pve_stop_guest"),
    ("POST", r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/shutdown", P2, "pdm_pve_shutdown_guest"),
    ("POST", r"/pve/remotes/\{remote\}/qemu/\{vmid\}/resume", P2, "pdm_pve_resume_vm"),
    ("POST", r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/snapshot", P2, "pdm_pve_create_snapshot"),
    (
        "DELETE",
        r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/snapshot/\{snapname\}",
        P2,
        "pdm_pve_delete_snapshot",
    ),
    (
        "POST",
        r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/snapshot/\{snapname\}/rollback",
        P2,
        "pdm_pve_rollback_snapshot",
    ),
    (
        "PUT",
        r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/snapshot/\{snapname\}/config",
        P2,
        "pdm_pve_update_snapshot",
    ),
    ("POST", r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/migrate", P2, "pdm_pve_migrate_guest"),
    (
        "POST",
        r"/pve/remotes/\{remote\}/\{T\}/\{vmid\}/remote-migrate",
        P2,
        "pdm_pve_remote_migrate_guest",
    ),
    ("DELETE", r"/pve/remotes/\{remote\}/tasks/\{upid\}", P2, "pdm_pve_stop_task"),
    ("DELETE", r"/pbs/remotes/\{remote\}/tasks/\{upid\}", P2, "pdm_pbs_stop_task"),
    ("DELETE", r"/nodes/\{node\}/tasks/\{upid\}", P2, "pdm_stop_task"),
    ("POST", r"/pve/remotes/\{remote\}/nodes/\{node\}/apt/update", P2, "pdm_pve_node_apt_refresh"),
    ("POST", r"/pbs/remotes/\{remote\}/nodes/\{node\}/apt/update", P2, "pdm_pbs_node_apt_refresh"),
    ("POST", r"/remotes/updates/refresh", P2, "pdm_refresh_updates"),
    ("POST", r"/remotes/tasks/refresh", P2, "pdm_refresh_remote_tasks"),
    ("POST", r"/remotes/metric-collection/trigger", P2, "pdm_collect_metrics"),
    # --- phase 3: later ---
    (".*", r"/remotes/remote(/\{id\})?", P3, "remote management"),
    ("POST", r"/remotes/remote/\{id\}/probe-certificate", P3, "remote management"),
    ("POST", r"/(pve|pbs)/(scan|probe-tls)", P3, "remote management"),
    ("GET", r"/(pve|pbs)/realms", P3, "remote management"),
    ("PUT", r"/pve/.*/firewall/options", P3, "firewall writes"),
    ("POST", r"/sdn/(zones|vnets)", P3, "SDN writes"),
    (".*", r"/subscriptions/.*", P3, "subscription key pool"),
    (".*", r"/auto-install/.*", P3, "automated installation"),
    (".*", r"/config/views.*", P3, "views"),
    (".*", r"/config/notes", P3, "notes"),
    (".*", r"/config/(acme|certificate).*", P3, "PDM certificates and ACME"),
    (".*", r"/nodes/\{node\}/certificates.*", P3, "PDM certificates and ACME"),
    (".*", r"/config/access.*", P3, "PDM realms and TFA settings"),
    (".*", r"/access/.*", P3, "PDM users, tokens, ACLs and TFA"),
    (
        ".*",
        r"/nodes/\{node\}/(apt|dns|network|time|config|subscription|report|journal|syslog|rrddata|sdn).*",
        P3,
        "PDM host administration",
    ),
    ("POST", r"/nodes/\{node\}/status", P3, "PDM host administration"),
]

AREAS = [
    ("/remotes", "Remotes, cross-remote tasks, updates and metrics"),
    ("/resources", "Resources across all remotes"),
    ("/pve", "Proxmox VE remotes"),
    ("/pbs", "Proxmox Backup Server remotes"),
    ("/sdn", "SDN across remotes"),
    ("/ceph", "Ceph clusters"),
    ("/subscriptions", "Subscription key pool"),
    ("/auto-install", "Automated installation"),
    ("/config", "PDM configuration"),
    ("/access", "PDM access control"),
    ("/nodes", "The PDM host itself"),
]

# Tool descriptions, written for people and models choosing a tool. Several PDM schema
# descriptions are copy-paste leftovers ("Get the status of a qemu VM" for storage status).
DESCRIPTIONS = {
    "pdm_ping": "Check that Proxmox Datacenter Manager answers (returns pong).",
    "pdm_version": "Proxmox Datacenter Manager version and release.",
    "pdm_list_remotes": "List every remote (Proxmox VE cluster or Backup Server) PDM manages.",
    "pdm_get_remote_config": "The stored connection settings of one remote (secrets are not returned).",
    "pdm_get_remote_version": "The Proxmox VE or Backup Server version a remote runs.",
    "pdm_get_remote_rrddata": "Metric-collection statistics for one remote over a timeframe.",
    "pdm_metric_collection_status": "When PDM last collected metrics from each remote, and any errors.",
    "pdm_list_remote_tasks": "Tasks across all remotes, newest first (filter by remote, type or state).",
    "pdm_remote_task_statistics": "Task counts across remotes by type and outcome.",
    "pdm_update_summary": "Pending package updates on every remote node, as PDM last saw them.",
    "pdm_list_resources": "Every guest, node, storage and datastore across all remotes, with status.",
    "pdm_resource_status": "Counts of resources by type and state across all remotes.",
    "pdm_top_entities": "The guests and nodes using the most CPU or memory across all remotes.",
    "pdm_subscription_status": "Subscription status of every remote.",
    "pdm_location_info": "Location information for remotes, optionally within one view.",
    "pdm_pve_list_remotes": "List the Proxmox VE remotes.",
    "pdm_pve_cluster_status": "Cluster and node membership status of a Proxmox VE remote.",
    "pdm_pve_next_vmid": "The next free VMID on a Proxmox VE remote, e.g. for a migration target.",
    "pdm_pve_cluster_options": "Datacenter options of a Proxmox VE remote.",
    "pdm_pve_resources": "Resources of one Proxmox VE remote (guests, nodes, storage, SDN).",
    "pdm_pve_updates": "Cached package update information for a Proxmox VE remote.",
    "pdm_pve_list_nodes": "Nodes of a Proxmox VE remote.",
    "pdm_pve_node_status": "Status of one node of a Proxmox VE remote (CPU, memory, uptime, versions).",
    "pdm_pve_node_config": "Configuration of one node of a Proxmox VE remote.",
    "pdm_pve_node_network": "Network interfaces of one node of a Proxmox VE remote.",
    "pdm_pve_node_rrddata": "Metrics of one node of a Proxmox VE remote over a timeframe.",
    "pdm_pve_node_subscription": "Subscription of one node of a Proxmox VE remote.",
    "pdm_pve_list_storage": "Storage on one node of a Proxmox VE remote, with usage.",
    "pdm_pve_storage_status": "Status and usage of one storage on a node of a Proxmox VE remote.",
    "pdm_pve_storage_rrddata": "Metrics of one storage on a node of a Proxmox VE remote over a timeframe.",
    "pdm_pve_node_apt_updates": "Available package updates on one node of a Proxmox VE remote.",
    "pdm_pve_node_apt_repositories": "APT repositories configured on one node of a Proxmox VE remote.",
    "pdm_pve_node_apt_changelog": "Changelog of a package on one node of a Proxmox VE remote.",
    "pdm_pve_sdn_vnet_mac_vrf": "MAC-VRF of an EVPN VNet on a node of a Proxmox VE remote.",
    "pdm_pve_sdn_zone_ip_vrf": "IP-VRF of an EVPN zone on a node of a Proxmox VE remote.",
    "pdm_pve_cluster_firewall": "Cluster firewall of a Proxmox VE remote: section options, rules or status.",
    "pdm_pve_node_firewall": "Node firewall on a Proxmox VE remote: section options, rules or status.",
    "pdm_pve_firewall_status_all": "Firewall status of every Proxmox VE remote.",
    "pdm_pve_list_guests": "VMs (type qemu) or containers (type lxc) on a Proxmox VE remote.",
    "pdm_pve_guest_config": "Configuration of a VM or container on a Proxmox VE remote.",
    "pdm_pve_guest_pending": "Pending (not yet applied) configuration of a VM or container.",
    "pdm_pve_guest_status": "Current status of a VM or container on a Proxmox VE remote.",
    "pdm_pve_guest_rrddata": "Metrics of a VM or container over a timeframe.",
    "pdm_pve_list_snapshots": "Snapshots of a VM or container on a Proxmox VE remote.",
    "pdm_pve_guest_firewall": "Firewall of a VM or container: section options or rules.",
    "pdm_pve_migrate_preconditions": "Whether a VM can migrate within its cluster, and to which nodes.",
    "pdm_pve_list_tasks": "Tasks on a Proxmox VE remote, optionally for one node.",
    "pdm_pve_task_status": "Status of a task on a Proxmox VE remote.",
    "pdm_pve_task_log": "Log of a task on a Proxmox VE remote.",
    "pdm_pbs_list_remotes": "List the Proxmox Backup Server remotes.",
    "pdm_pbs_status": "Status of a Proxmox Backup Server remote (CPU, memory, uptime).",
    "pdm_pbs_rrddata": "Metrics of a Proxmox Backup Server remote over a timeframe.",
    "pdm_pbs_list_datastores": "Datastores of a Proxmox Backup Server remote.",
    "pdm_pbs_list_namespaces": "Namespaces of a datastore on a Proxmox Backup Server remote.",
    "pdm_pbs_list_snapshots": "Backup snapshots in a datastore on a Proxmox Backup Server remote.",
    "pdm_pbs_datastore_rrddata": "Metrics of a datastore on a Proxmox Backup Server remote.",
    "pdm_pbs_node_apt_updates": "Available package updates on a Proxmox Backup Server remote.",
    "pdm_pbs_node_apt_repositories": "APT repositories configured on a Proxmox Backup Server remote.",
    "pdm_pbs_node_apt_changelog": "Changelog of a package on a Proxmox Backup Server remote.",
    "pdm_pbs_node_subscription": "Subscription of a Proxmox Backup Server remote.",
    "pdm_pbs_list_tasks": "Tasks on a Proxmox Backup Server remote.",
    "pdm_pbs_task_status": "Status of a task on a Proxmox Backup Server remote.",
    "pdm_pbs_task_log": "Log of a task on a Proxmox Backup Server remote.",
    "pdm_sdn_list": "SDN across Proxmox VE remotes: section zones, vnets or controllers.",
    "pdm_ceph_list_clusters": "Ceph clusters PDM knows of.",
    "pdm_ceph_cluster": "One Ceph cluster: section summary, status, flags, fs, mds, mgr, mon, osd-tree or pools.",
    "pdm_list_tasks": "Tasks that PDM itself ran (refreshes, metric collection).",
    "pdm_task_status": "Status of a task PDM itself ran.",
    "pdm_task_log": "Log of a task PDM itself ran.",
    "pdm_node_status": "CPU, memory and disk usage of the PDM host.",
    "pdm_my_permissions": "The permissions of this server's PDM token.",
    "pdm_pve_start_guest": "Start a VM or container on a Proxmox VE remote.",
    "pdm_pve_stop_guest": "Stop a VM or container immediately (like pulling the plug).",
    "pdm_pve_shutdown_guest": "Shut down a VM or container cleanly.",
    "pdm_pve_resume_vm": "Resume a paused or suspended VM.",
    "pdm_pve_create_snapshot": "Create a snapshot of a VM or container.",
    "pdm_pve_delete_snapshot": "Delete a snapshot of a VM or container.",
    "pdm_pve_rollback_snapshot": "Roll a VM or container back to a snapshot. Changes since then are lost.",
    "pdm_pve_update_snapshot": "Change a snapshot's description.",
    "pdm_pve_migrate_guest": "Migrate a VM or container to another node in the same cluster.",
    "pdm_pve_remote_migrate_guest": (
        "Migrate a VM or container to another Proxmox VE remote (another cluster). With delete, "
        "the original is removed after a successful migration."
    ),
    "pdm_pve_stop_task": "Stop a running task on a Proxmox VE remote.",
    "pdm_pbs_stop_task": "Stop a running task on a Proxmox Backup Server remote.",
    "pdm_stop_task": "Stop a running task of PDM itself.",
    "pdm_pve_node_apt_refresh": "Refresh the package lists on one node of a Proxmox VE remote (apt update).",
    "pdm_pbs_node_apt_refresh": "Refresh the package lists on a Proxmox Backup Server remote (apt update).",
    "pdm_refresh_updates": "Make PDM refresh the update summary of every remote now.",
    "pdm_refresh_remote_tasks": "Make PDM refresh its cache of remote tasks now.",
    "pdm_collect_metrics": "Make PDM collect metrics now, from one remote or all of them.",
}

DESTRUCTIVE = {
    "pdm_pve_stop_guest",
    "pdm_pve_shutdown_guest",
    "pdm_pve_delete_snapshot",
    "pdm_pve_rollback_snapshot",
    "pdm_pve_migrate_guest",
    "pdm_pve_remote_migrate_guest",
    "pdm_pve_stop_task",
    "pdm_pbs_stop_task",
    "pdm_stop_task",
}

# Path parameters get clearer input names where PDM's are generic.
RENAME = {"/remotes/remote/{id}": {"id": "remote"}}


def norm(path: str) -> str:
    return re.sub(r"/(qemu|lxc)(?=/|$)", "/{T}", path)


def classify(method: str, path: str, desc: str) -> tuple[str, str] | None:
    for rule in RULES:
        m, rx, phase, what = rule[:4]
        only = rule[4] if len(rule) > 4 else None
        if not re.fullmatch(m, method):
            continue
        if only:
            if desc.strip() == only[len("desc:") :]:
                return phase, what
            continue
        if re.fullmatch(rx, norm(path)) or re.fullmatch(rx, path):
            return phase, what
    return None


def area_of(path: str) -> str:
    if path in ("/", "/ping", "/version"):
        return "Root, version and ping"
    for prefix, title in AREAS:
        if path == prefix or path.startswith(prefix + "/"):
            return title
    raise ValueError(path)


def load_schema(apidoc: str) -> list[dict[str, Any]]:
    text = pathlib.Path(apidoc).read_text()
    start = text.index("[", text.index("apiSchema"))
    schema, _ = json.JSONDecoder().raw_decode(text[start:])
    rows: list[dict[str, Any]] = []

    def walk(nodes: list[dict[str, Any]]) -> None:
        for node in nodes:
            for method, info in (node.get("info") or {}).items():
                rows.append({"method": method, "path": node["path"], "info": info})
            walk(node.get("children") or [])

    walk(schema)
    return rows


def params_of(info: dict[str, Any]) -> dict[str, Any]:
    """Every parameter of an endpoint. PDM's schema splits some into `allOf` parts."""
    found: dict[str, Any] = {}

    def collect(node: Any) -> None:
        if not isinstance(node, dict):
            return
        found.update(node.get("properties") or {})
        for part in node.get("allOf") or []:
            collect(part)

    collect(info.get("parameters"))
    return found


def json_schema(prop: dict[str, Any]) -> dict[str, Any]:
    """A JSON Schema property from a PDM parameter (patterns kept apart: they're Perl-style)."""
    out: dict[str, Any] = {}
    kind = prop.get("type")
    if kind in ("string", "integer", "boolean", "number", "array", "object"):
        out["type"] = kind
    desc = (prop.get("description") or "").strip().split("\n\n")[0].replace("\n", " ")
    if prop.get("default") is not None:
        desc += f" (default: {json.dumps(prop['default'])})"
    if desc:
        out["description"] = desc
    for key in ("enum", "minimum", "maximum", "minLength", "maxLength"):
        if key in prop:
            out[key] = prop[key]
    if kind == "array" and isinstance(prop.get("items"), dict):
        out["items"] = json_schema(prop["items"])
    return out


def py_pattern(prop: dict[str, Any]) -> str | None:
    pattern = prop.get("pattern")
    if not isinstance(pattern, str) or not pattern.startswith("/"):
        return None
    return pattern[1 : pattern.rindex("/")]


def selector_of(tool: str, path: str) -> tuple[str, str] | None:
    """The tool input that picks this endpoint among several, and its value."""
    m = re.search(r"/(qemu|lxc)(/|$)", path)
    if m and tool not in ("pdm_pve_resume_vm", "pdm_pve_migrate_preconditions"):
        return "type", m[1]
    m = re.fullmatch(
        r".*/(?:firewall|sdn|clusters/\{cluster\})/(options|rules|status|zones|vnets|controllers|summary|flags|fs|mds|mgr|mon|osd-tree|pools)",
        path,
    )
    if m and tool in (
        "pdm_pve_cluster_firewall",
        "pdm_pve_node_firewall",
        "pdm_pve_guest_firewall",
        "pdm_ceph_cluster",
    ):
        return "section", m[1]
    m = re.fullmatch(r"/sdn/(zones|vnets|controllers)", path)
    if m and tool == "pdm_sdn_list":
        return "section", m[1]
    return None


def build_tools(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_tool: dict[str, list[dict[str, Any]]] = OrderedDict()
    for r in rows:
        if r["phase"] in (P1, P2):
            by_tool.setdefault(r["what"], []).append(r)
    tools = []
    for name, eps in by_tool.items():
        props: dict[str, Any] = {}
        patterns: dict[str, str] = {}
        required_sets = []
        endpoints = []
        selector_values: dict[str, list[str]] = {}
        defaults: dict[str, Any] = {}
        waitable = False
        for r in eps:
            info = r["info"]
            params = params_of(info)
            rename = RENAME.get(re.sub(r"/(config|version|rrddata)$", "", r["path"]), {})
            path = r["path"]
            for old, new in rename.items():
                path = path.replace("{" + old + "}", "{" + new + "}")
            required = set()
            for pname, prop in params.items():
                pname = rename.get(pname, pname)
                schema = json_schema(prop)
                if pname in props and props[pname].get("type") != schema.get("type"):
                    raise SystemExit(f"{name}: parameter {pname} has two types")
                props.setdefault(pname, schema)
                if (pat := py_pattern(prop)) is not None:
                    patterns.setdefault(pname, pat)
                if not prop.get("optional"):
                    if prop.get("default") is None:
                        required.add(pname)
                    else:
                        # PDM requires it but documents a default (guest config's `state` is
                        # "pending"): optional for callers, and the server sends the default.
                        defaults.setdefault(pname, prop["default"])
            # PDM's schema leaves some path parameters out (/nodes/{node}/tasks has no `node`).
            for pname in re.findall(r"\{([^}]+)\}", path):
                if pname not in props:
                    props[pname] = {
                        "type": "string",
                        "description": f"The {pname} in the API path.",
                    }
                required.add(pname)
                params = {**params, pname: {}}
            required_sets.append(required)
            sel = selector_of(name, r["path"])
            ep: dict[str, Any] = {
                "method": r["method"],
                "path": path,
                "params": sorted(rename.get(k, k) for k in params),
            }
            if sel:
                ep["when"] = {sel[0]: sel[1]}
                selector_values.setdefault(sel[0], []).append(sel[1])
            endpoints.append(ep)
            returns = info.get("returns") or {}
            rdesc = returns.get("description") or ""
            if r["method"] != "GET" and ("UPID" in rdesc or "Task Identifier" in rdesc):
                waitable = True
        if len(endpoints) > 1 and not selector_values:
            raise SystemExit(f"{name}: several endpoints but no selector")
        for key, values in selector_values.items():
            if key in props:
                raise SystemExit(f"{name}: selector {key} collides with a PDM parameter")
            label = {"type": "qemu (VM) or lxc (container)"}.get(key, "which part to read")
            props[key] = {"type": "string", "enum": values, "description": label.capitalize()}
        required = set.intersection(*required_sets) | set(selector_values)
        kind = (
            "read"
            if all(e["method"] == "GET" for e in endpoints)
            else ("destructive" if name in DESTRUCTIVE else "write")
        )
        tools.append(
            {
                "name": name,
                "phase": eps[0]["phase"],
                "kind": kind,
                "waitable": waitable,
                "description": DESCRIPTIONS[name],
                "endpoints": endpoints,
                "patterns": patterns,
                "defaults": defaults,
                "inputSchema": {
                    "type": "object",
                    "properties": dict(
                        sorted(props.items(), key=lambda kv: (kv[0] not in required, kv[0]))
                    ),
                    "required": sorted(required),
                },
            }
        )
    missing = set(DESCRIPTIONS) ^ {t["name"] for t in tools}
    if missing:
        raise SystemExit(f"descriptions and tools differ: {sorted(missing)}")
    return sorted(tools, key=lambda t: t["name"])


def roadmap_section(rows: list[dict[str, Any]], tools: list[dict[str, Any]]) -> str:
    count = Counter(r["phase"] for r in rows)
    t1 = [t["name"] for t in tools if t["phase"] == P1]
    t2 = [t["name"] for t in tools if t["phase"] == P2]
    out = [
        f"#### Phase 1: read ({len(t1)} tools)",
        "",
        ", ".join(f"`{t}`" for t in t1) + ".",
        "",
        f"#### Phase 2: actions ({len(t2)} tools)",
        "",
        ", ".join(f"`{t}`" for t in t2) + ".",
        "",
        "#### Phase 3: later",
        "",
    ]
    groups: dict[str, int] = OrderedDict()
    for r in rows:
        if r["phase"] == P3:
            groups[r["what"]] = groups.get(r["what"], 0) + 1
    out += [f"- {g[0].upper() + g[1:]} ({n} endpoints)" for g, n in groups.items()]
    out += ["", "#### Not planned", ""]
    reasons = Counter(r["what"] for r in rows if r["phase"] == NO)
    for reason, n in reasons.items():
        label = (
            "Directory indexes (navigation only; each tool calls the endpoint it needs)"
            if reason == "index"
            else reason[0].upper() + reason[1:]
        )
        out.append(f"- {label}: {n}")
    out += [
        "",
        "#### Full API map",
        "",
        "<details>",
        f"<summary>All {len(rows)} endpoints, by area</summary>",
        "",
    ]
    areas: dict[str, list[dict[str, Any]]] = OrderedDict()
    for r in rows:
        areas.setdefault(r["area"], []).append(r)
    for area, items in areas.items():
        out += [
            f"**{area}**",
            "",
            "| Method | Path | Phase | Tool or reason |",
            "|---|---|---|---|",
        ]
        for r in sorted(items, key=lambda r: (r["path"], r["method"])):
            phase = "—" if r["phase"] == NO else r["phase"]
            cell = (
                f"`{r['what']}`"
                if r["phase"] in (P1, P2)
                else ("directory index" if r["what"] == "index" else r["what"])
            )
            out.append(f"| {r['method']} | `{r['path']}` | {phase} | {cell} |")
        out.append("")
    out += ["</details>", ""]
    summary = (
        f"{len(rows)} endpoints: {count[P1]} in phase 1, {count[P2]} in phase 2, "
        f"{count[P3]} in phase 3, {count[NO]} not planned."
    )
    return summary + "\n\n" + "\n".join(out)


def update_agent_card(tools: list[dict[str, Any]]) -> None:
    """Write the PDM tools into agent-card.json as the datacenter_manager skill."""
    card = json.loads(CARD.read_text())
    caps = []
    for t in tools:
        props = t["inputSchema"]["properties"]
        required = t["inputSchema"]["required"]
        inputs = [k for k in props if k in required] + [
            f"{k} (optional)" for k in props if k not in required
        ]
        if t["waitable"]:
            inputs.append("wait (optional)")
        caps.append(
            {
                "name": t["name"],
                "description": t["description"],
                "inputs": inputs,
                "read_only": t["kind"] == "read",
                "destructive": t["kind"] == "destructive",
            }
        )
    skill = {
        "category": "datacenter_manager",
        "description": (
            "Proxmox Datacenter Manager: many Proxmox VE clusters and Backup Servers through one "
            "PDM. Loads when PDM_HOST is set."
        ),
        "capabilities": caps,
    }
    card["skills"] = [s for s in card["skills"] if s.get("category") != "datacenter_manager"] + [
        skill
    ]
    CARD.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    rows = load_schema(sys.argv[1])
    unmapped = []
    for r in rows:
        c = classify(r["method"], r["path"], r["info"].get("description") or "")
        if c is None:
            unmapped.append(f"{r['method']} {r['path']}")
            continue
        r["phase"], r["what"] = c
        r["area"] = area_of(r["path"])
    if unmapped:
        raise SystemExit("Unmapped endpoints:\n  " + "\n  ".join(unmapped))
    tools = build_tools(rows)
    SPEC_OUT.write_text(json.dumps({"endpoint_count": len(rows), "tools": tools}, indent=1) + "\n")
    ROADMAP_OUT.write_text(roadmap_section(rows, tools))
    update_agent_card(tools)
    print(f"{len(rows)} endpoints, {len(tools)} tools -> {SPEC_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
