"""Node-level tools: status, config, packages and kernels, APT repositories, subscription, network,
DNS, time, services, syslog, journal, hardware, RRD."""

from __future__ import annotations

import re
from typing import Any

from ..client import ProxmoxClient

NODE = {"type": "string", "description": "Node name (e.g. pve01)"}
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731


TOOLS = [
    {
        "name": "list_nodes",
        "description": "List all nodes in the Proxmox cluster with status and resource usage.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_node_status",
        "description": "Get detailed status and resource usage for a specific node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_node_config",
        "description": "Get node configuration: notes, Wake-on-LAN, on-boot delay, ballooning target, location, ACME.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "property": OPT_STR("Only this setting, e.g. wakeonlan or acme"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_node_version",
        "description": "Get Proxmox VE version information for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_node_time",
        "description": "Get current time and timezone for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "set_node_time",
        "description": "Set timezone for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "timezone": OPT_STR("Timezone (e.g. America/New_York)"),
            },
            "required": ["node", "timezone"],
        },
    },
    {
        "name": "get_node_dns",
        "description": "Get DNS configuration for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "set_node_dns",
        "description": "Set DNS configuration for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "search": OPT_STR("DNS search domain"),
                "dns1": OPT_STR("Primary DNS server IP"),
                "dns2": OPT_STR("Secondary DNS server IP"),
                "dns3": OPT_STR("Tertiary DNS server IP"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_node_hosts",
        "description": "Get /etc/hosts content for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "set_node_hosts",
        "description": "Write /etc/hosts content for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "data": OPT_STR("Full /etc/hosts content"),
                "digest": OPT_STR("SHA1 digest (prevent race condition)"),
            },
            "required": ["node", "data"],
        },
    },
    {
        "name": "get_node_network",
        "description": "List network interfaces configured on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "type": OPT_STR("Filter by interface type (bridge, bond, eth, alias, vlan, OVSBridge, OVSBond, OVSPort, OVSIntPort, any_bridge, any_local_bridge)"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_node_network_interface",
        "description": "Get configuration for a specific network interface on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "iface": OPT_STR("Interface name (e.g. eth0, vmbr0)"),
            },
            "required": ["node", "iface"],
        },
    },
    {
        "name": "apply_node_network",
        "description": "Apply pending network configuration changes on a node (reload interfaces).",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "revert_node_network",
        "description": "Revert pending network configuration changes on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_node_netstat",
        "description": "Get network statistics for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "list_node_services",
        "description": "List all systemd services on a node with their state.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_node_service_state",
        "description": "Get the state of a specific service on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "service": OPT_STR("Service name (e.g. pvedaemon, sshd, pveproxy)"),
            },
            "required": ["node", "service"],
        },
    },
    {
        "name": "start_node_service",
        "description": "Start a systemd service on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "service": OPT_STR("Service name"),
            },
            "required": ["node", "service"],
        },
    },
    {
        "name": "stop_node_service",
        "description": "Stop a systemd service on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "service": OPT_STR("Service name"),
            },
            "required": ["node", "service"],
        },
    },
    {
        "name": "restart_node_service",
        "description": "Restart a systemd service on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "service": OPT_STR("Service name"),
            },
            "required": ["node", "service"],
        },
    },
    {
        "name": "reload_node_service",
        "description": "Reload a systemd service on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "service": OPT_STR("Service name"),
            },
            "required": ["node", "service"],
        },
    },
    {
        "name": "get_node_syslog",
        "description": "Get syslog entries from a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "limit": OPT_INT("Max entries to return"),
                "start": OPT_INT("Start line number"),
                "since": OPT_STR("Show entries since this date (YYYY-MM-DD)"),
                "until": OPT_STR("Show entries until this date (YYYY-MM-DD)"),
                "service": OPT_STR("Filter by service name"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_node_journal",
        "description": "Get systemd journal entries from a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "limit": OPT_INT("Max entries to return"),
                "startcursor": OPT_STR("Start at this cursor"),
                "endcursor": OPT_STR("End at this cursor"),
                "since": OPT_INT("Show entries since Unix timestamp"),
                "until": OPT_INT("Show entries until Unix timestamp"),
                "lastentries": OPT_INT("Show last N entries"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_node_report",
        "description": "Get a full diagnostic report for a node (OS, hardware, config).",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_node_subscription",
        "description": "Get Proxmox subscription info for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_node_apt_update",
        "description": "List available APT package updates on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_node_apt_changelog",
        "description": "Get changelog for an APT package on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("Package name"),
                "version": OPT_STR("Package version (optional)"),
            },
            "required": ["node", "name"],
        },
    },
    {
        "name": "get_node_apt_versions",
        "description": (
            "Installed versions of the main Proxmox packages on a node, kernels included (like pveversion -v). "
            "The proxmox-ve entry carries RunningKernel."
        ),
        "inputSchema": {"type": "object", "properties": {"node": NODE}, "required": ["node"]},
    },
    {
        "name": "get_node_kernel",
        "description": (
            "Which kernel a node is running and which kernels are installed, e.g. to check whether the opt-in "
            "7.3 kernel is installed and in use. installed_series lists the kernel series whose meta package "
            "(proxmox-kernel-7.3) is installed. Installing a kernel or pinning one is a root-shell step "
            "(apt, proxmox-boot-tool), not an API call."
        ),
        "inputSchema": {"type": "object", "properties": {"node": NODE}, "required": ["node"]},
    },
    {
        "name": "get_node_apt_history",
        "description": "Past APT transactions on a node, newest first: what was installed, upgraded or removed, and when.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "limit": OPT_INT("At most this many transactions"),
                "package": OPT_STR("Only transactions that changed this package"),
                "since": OPT_INT("Only transactions started at or after this Unix time"),
                "until": OPT_INT("Only transactions started at or before this Unix time"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_node_apt_repositories",
        "description": (
            "A node's APT repositories: each file and repository with its index, warnings (such as a "
            "missing or duplicate Proxmox repository), and the standard repositories with their handles."
        ),
        "inputSchema": {"type": "object", "properties": {"node": NODE}, "required": ["node"]},
    },
    {
        "name": "refresh_node_apt_index",
        "description": "Refresh a node's package index (apt update), so get_node_apt_update lists current updates. Returns a task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "notify": OPT_BOOL("Send a notification about new packages"),
                "quiet": OPT_BOOL("Log output without progress indicators"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "set_node_apt_repository",
        "description": "Enable or disable one APT repository, named by its file path and index from get_node_apt_repositories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "path": OPT_STR("Repository file, e.g. /etc/apt/sources.list.d/pve-enterprise.sources"),
                "index": OPT_INT("Index of the repository within the file, from 0"),
                "enabled": OPT_BOOL("Enable (true) or disable (false)"),
                "digest": OPT_STR("Digest from get_node_apt_repositories, to refuse if the files changed"),
            },
            "required": ["node", "path", "index", "enabled"],
        },
    },
    {
        "name": "add_node_apt_repository",
        "description": (
            "Add a standard Proxmox repository by its handle, as listed in get_node_apt_repositories "
            "(e.g. no-subscription, test, enterprise)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "handle": OPT_STR("Repository handle"),
                "digest": OPT_STR("Digest from get_node_apt_repositories"),
            },
            "required": ["node", "handle"],
        },
    },
    {
        "name": "set_node_subscription_key",
        "description": "Set a node's Proxmox VE subscription key.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "key": OPT_STR("Subscription key")},
            "required": ["node", "key"],
        },
    },
    {
        "name": "refresh_node_subscription",
        "description": "Check a node's subscription with the Proxmox server and update its status.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE, "force": OPT_BOOL("Check now even if the cached status is still valid")},
            "required": ["node"],
        },
    },
    {
        "name": "delete_node_subscription",
        "description": "Remove a node's subscription key.",
        "inputSchema": {"type": "object", "properties": {"node": NODE}, "required": ["node"]},
    },
    {
        "name": "set_node_config",
        "description": (
            "Set node options: notes, Wake-on-LAN (wakeonlan needs the MAC set here), the delay before "
            "on-boot guests start, the ballooning target, location and ACME domains."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "description": OPT_STR("Node notes, shown in the web interface"),
                "wakeonlan": OPT_STR("Wake-on-LAN: mac=<MAC>[,bind-interface=<iface>][,broadcast-address=<IPv4>]"),
                "startall-onboot-delay": OPT_INT("Seconds to wait before starting on-boot guests"),
                "ballooning-target": OPT_INT("RAM usage target for ballooning, percent of total memory"),
                "location": OPT_STR("Node location: latitude=<n>,longitude=<n>[,name=<name>]"),
                "acme": OPT_STR("ACME settings: account=<name>,domains=<domain;domain>"),
                "acmedomain0": OPT_STR("ACME domain: domain=<name>[,plugin=<plugin>][,alias=<domain>]"),
                "delete": OPT_STR("Settings to remove, comma-separated"),
                "digest": OPT_STR("Config digest, to refuse if the config changed meanwhile"),
            },
            "patternProperties": {"^acmedomain[1-5]$": {"type": "string"}},
            "required": ["node"],
        },
    },
    {
        "name": "get_node_hardware",
        "description": "List PCI devices and hardware info for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_node_rrd",
        "description": "Get RRD statistics graph data for a node (returns base64 PNG).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "ds": OPT_STR("Data source (cpu, memtotal, memused, netin, netout, etc.)"),
                "timeframe": OPT_STR("Timeframe: hour, day, week, month, year"),
                "cf": OPT_STR("Consolidation function: AVERAGE or MAX"),
            },
            "required": ["node", "ds", "timeframe"],
        },
    },
    {
        "name": "get_node_rrddata",
        "description": "Get RRD statistics data points for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "timeframe": OPT_STR("Timeframe: hour, day, week, month, year"),
                "cf": OPT_STR("Consolidation function: AVERAGE or MAX"),
            },
            "required": ["node", "timeframe"],
        },
    },
    {
        "name": "node_shutdown",
        "description": "Shutdown or reboot a Proxmox node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "command": OPT_STR("Command: shutdown, reboot, or suspend"),
            },
            "required": ["node", "command"],
        },
    },
    {
        "name": "node_startall",
        "description": "Start all VMs and containers on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vms": OPT_STR("Comma-separated list of VMIDs to start (optional, defaults to all)"),
                "force": OPT_STR("Force start even if HA managed (true/false)"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "node_stopall",
        "description": "Stop all VMs and containers on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vms": OPT_STR("Comma-separated list of VMIDs to stop (optional)"),
                "force_stop": OPT_INT("Force stop after N seconds timeout"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "node_migrateall",
        "description": "Migrate all VMs and containers from a node to a target node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "target": OPT_STR("Target node name"),
                "maxworkers": OPT_INT("Max simultaneous migrations"),
                "vms": OPT_STR("Comma-separated list of VMIDs to migrate (optional)"),
                "with_local_disks": OPT_STR("Also migrate local disk images (true/false)"),
            },
            "required": ["node", "target"],
        },
    },
    {
        "name": "node_suspendall",
        "description": "Suspend all VMs on a node (to RAM), e.g. before maintenance. Give vms to suspend only some.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vms": OPT_STR("Comma-separated VMIDs (default: all VMs on the node)"),
                "max-workers": OPT_INT("How many to suspend at once"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_node_aplinfo",
        "description": "Get available LXC appliance/template info for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_node_capabilities_qemu",
        "description": "Get QEMU capabilities for a node (CPU types, machine types, migration options).",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "get_node_scan",
        "description": (
            "Find storage a node can use before adding it: NFS exports, SMB shares, Proxmox Backup Server "
            "datastores, iSCSI or NVMe-oF targets, or local LVM, LVM-thin and ZFS. Inputs by type: nfs needs server; "
            "cifs needs server (username, password, domain optional); pbs needs server, username and password "
            "(fingerprint, port optional); iscsi and nvmeof need portal; lvmthin needs vg."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "type": {
                    "type": "string",
                    "enum": ["nfs", "cifs", "pbs", "iscsi", "nvmeof", "lvm", "lvmthin", "zfs"],
                    "description": "What to scan for",
                },
                "server": OPT_STR("Server name or address (nfs, cifs, pbs)"),
                "portal": OPT_STR("Portal or discovery address, optional port (iscsi, nvmeof)"),
                "username": OPT_STR("User name, or API token ID for pbs (cifs, pbs)"),
                "password": OPT_STR("Password, or API token secret for pbs (cifs, pbs)"),
                "domain": OPT_STR("SMB domain or workgroup (cifs)"),
                "fingerprint": OPT_STR("Server certificate SHA-256 fingerprint (pbs)"),
                "port": OPT_INT("Port (pbs)"),
                "vg": OPT_STR("Volume group (lvmthin)"),
            },
            "required": ["node", "type"],
        },
    },
    {
        "name": "wakeonlan",
        "description": "Wake a node via Wake-on-LAN.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
]


_KERNEL_PACKAGE = re.compile(r"(?:proxmox|pve)-kernel-\d")
_KERNEL_SERIES = re.compile(r"proxmox-kernel-(\d+\.\d+)")


def _kernel_summary(response: Any) -> dict[str, Any]:
    """Running kernel, installed kernel packages and series, from /apt/versions."""
    packages = (response or {}).get("data") or []
    installed = [p for p in packages if p.get("CurrentState", "Installed") == "Installed"]
    running = next((p.get("RunningKernel") for p in packages if p.get("Package") == "proxmox-ve"), None)
    series = sorted(
        {m[1] for p in installed if (m := _KERNEL_SERIES.fullmatch(p.get("Package", "")))},
        key=lambda s: tuple(int(x) for x in s.split(".")),
    )
    running_series = re.match(r"\d+\.\d+", running or "")
    return {
        "running_kernel": running,
        "running_series": running_series[0] if running_series else None,
        "installed_series": series,
        "kernel_packages": [
            {"package": p["Package"], "version": p.get("OldVersion") or p.get("Version")}
            for p in installed
            if _KERNEL_PACKAGE.match(p.get("Package", ""))
        ],
    }


# Inputs each /scan/{type} endpoint takes, and the ones it requires.
_SCAN_INPUTS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "nfs": (("server",), ("server",)),
    "cifs": (("server", "username", "password", "domain"), ("server",)),
    "pbs": (("server", "username", "password", "fingerprint", "port"), ("server", "username", "password")),
    "iscsi": (("portal",), ("portal",)),
    "nvmeof": (("portal",), ("portal",)),
    "lvm": ((), ()),
    "lvmthin": (("vg",), ("vg",)),
    "zfs": ((), ()),
}


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    # Declared once so mypy does not infer a narrow key type from the first dict literal.
    params: dict[str, Any]
    data: dict[str, Any]
    node = args.get("node", "")

    if name == "list_nodes":
        return await client.get("/nodes")

    elif name == "get_node_status":
        return await client.get(f"/nodes/{node}/status")

    elif name == "get_node_config":
        params = {"property": args["property"]} if "property" in args else None
        return await client.get(f"/nodes/{node}/config", params)

    elif name == "get_node_apt_versions":
        return await client.get(f"/nodes/{node}/apt/versions")

    elif name == "get_node_kernel":
        return _kernel_summary(await client.get(f"/nodes/{node}/apt/versions"))

    elif name == "get_node_apt_history":
        params = {k: args[k] for k in ("limit", "package", "since", "until") if k in args}
        return await client.get(f"/nodes/{node}/apt/history", params or None)

    elif name == "get_node_apt_repositories":
        return await client.get(f"/nodes/{node}/apt/repositories")

    elif name == "refresh_node_apt_index":
        data = {k: args[k] for k in ("notify", "quiet") if k in args}
        return await client.post(f"/nodes/{node}/apt/update", data or None)

    elif name == "set_node_apt_repository":
        data = {k: args[k] for k in ("path", "index", "enabled", "digest") if k in args}
        return await client.post(f"/nodes/{node}/apt/repositories", data)

    elif name == "add_node_apt_repository":
        data = {k: args[k] for k in ("handle", "digest") if k in args}
        return await client.put(f"/nodes/{node}/apt/repositories", data)

    elif name == "set_node_subscription_key":
        return await client.put(f"/nodes/{node}/subscription", {"key": args["key"]})

    elif name == "refresh_node_subscription":
        data = {"force": args["force"]} if "force" in args else None
        return await client.post(f"/nodes/{node}/subscription", data)

    elif name == "delete_node_subscription":
        return await client.delete(f"/nodes/{node}/subscription")

    elif name == "set_node_config":
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.put(f"/nodes/{node}/config", data)

    elif name == "node_suspendall":
        data = {k: args[k] for k in ("vms", "max-workers") if k in args}
        return await client.post(f"/nodes/{node}/suspendall", data or None)

    elif name == "get_node_version":
        return await client.get(f"/nodes/{node}/version")

    elif name == "get_node_time":
        return await client.get(f"/nodes/{node}/time")

    elif name == "set_node_time":
        return await client.put(f"/nodes/{node}/time", {"timezone": args["timezone"]})

    elif name == "get_node_dns":
        return await client.get(f"/nodes/{node}/dns")

    elif name == "set_node_dns":
        data = {k: args[k] for k in ("search", "dns1", "dns2", "dns3") if k in args}
        return await client.put(f"/nodes/{node}/dns", data)

    elif name == "get_node_hosts":
        return await client.get(f"/nodes/{node}/hosts")

    elif name == "set_node_hosts":
        data = {"data": args["data"]}
        if "digest" in args:
            data["digest"] = args["digest"]
        return await client.post(f"/nodes/{node}/hosts", data)

    elif name == "get_node_network":
        params = {}
        if "type" in args:
            params["type"] = args["type"]
        return await client.get(f"/nodes/{node}/network", params or None)

    elif name == "get_node_network_interface":
        return await client.get(f"/nodes/{node}/network/{args['iface']}")

    elif name == "apply_node_network":
        return await client.put(f"/nodes/{node}/network")

    elif name == "revert_node_network":
        return await client.delete(f"/nodes/{node}/network")

    elif name == "get_node_netstat":
        return await client.get(f"/nodes/{node}/netstat")

    elif name == "list_node_services":
        return await client.get(f"/nodes/{node}/services")

    elif name == "get_node_service_state":
        return await client.get(f"/nodes/{node}/services/{args['service']}/state")

    elif name == "start_node_service":
        return await client.post(f"/nodes/{node}/services/{args['service']}/start")

    elif name == "stop_node_service":
        return await client.post(f"/nodes/{node}/services/{args['service']}/stop")

    elif name == "restart_node_service":
        return await client.post(f"/nodes/{node}/services/{args['service']}/restart")

    elif name == "reload_node_service":
        return await client.post(f"/nodes/{node}/services/{args['service']}/reload")

    elif name == "get_node_syslog":
        params = {k: args[k] for k in ("limit", "start", "since", "until", "service") if k in args}
        return await client.get(f"/nodes/{node}/syslog", params or None)

    elif name == "get_node_journal":
        params = {k: args[k] for k in ("limit", "startcursor", "endcursor", "since", "until", "lastentries") if k in args}
        return await client.get(f"/nodes/{node}/journal", params or None)

    elif name == "get_node_report":
        return await client.get(f"/nodes/{node}/report")

    elif name == "get_node_subscription":
        return await client.get(f"/nodes/{node}/subscription")

    elif name == "get_node_apt_update":
        return await client.get(f"/nodes/{node}/apt/update")

    elif name == "get_node_apt_changelog":
        params = {"name": args["name"]}
        if "version" in args:
            params["version"] = args["version"]
        return await client.get(f"/nodes/{node}/apt/changelog", params)

    elif name == "get_node_hardware":
        return await client.get(f"/nodes/{node}/hardware")

    elif name == "get_node_rrd":
        params = {"ds": args["ds"], "timeframe": args["timeframe"]}
        if "cf" in args:
            params["cf"] = args["cf"]
        return await client.get(f"/nodes/{node}/rrd", params)

    elif name == "get_node_rrddata":
        params = {"timeframe": args["timeframe"]}
        if "cf" in args:
            params["cf"] = args["cf"]
        return await client.get(f"/nodes/{node}/rrddata", params)

    elif name == "node_shutdown":
        return await client.post(f"/nodes/{node}/status", {"command": args["command"]})

    elif name == "node_startall":
        data = {}
        if "vms" in args:
            data["vms"] = args["vms"]
        if "force" in args:
            data["force"] = args["force"]
        return await client.post(f"/nodes/{node}/startall", data or None)

    elif name == "node_stopall":
        data = {}
        if "vms" in args:
            data["vms"] = args["vms"]
        if "force_stop" in args:
            data["force-stop"] = args["force_stop"]
        return await client.post(f"/nodes/{node}/stopall", data or None)

    elif name == "node_migrateall":
        data = {"target": args["target"]}
        for k in ("maxworkers", "vms", "with_local_disks"):
            if k in args:
                data[k.replace("_", "-")] = args[k]
        return await client.post(f"/nodes/{node}/migrateall", data)

    elif name == "get_node_aplinfo":
        return await client.get(f"/nodes/{node}/aplinfo")

    elif name == "get_node_capabilities_qemu":
        return await client.get(f"/nodes/{node}/capabilities/qemu")

    elif name == "get_node_scan":
        scan = args["type"]
        if scan not in _SCAN_INPUTS:
            raise ValueError(f"Unknown scan type {scan!r}: use one of {', '.join(_SCAN_INPUTS)}")
        allowed, needed = _SCAN_INPUTS[scan]
        missing = [k for k in needed if k not in args]
        if missing:
            raise ValueError(f"A {scan} scan needs {', '.join(missing)}")
        params = {k: args[k] for k in allowed if k in args}
        return await client.get(f"/nodes/{node}/scan/{scan}", params or None)

    elif name == "wakeonlan":
        return await client.post(f"/nodes/{node}/wakeonlan")

    raise ValueError(f"Unknown tool: {name}")
