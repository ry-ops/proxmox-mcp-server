"""Node-level tools: status, config, network, DNS, time, services, syslog, journal, hardware, RRD."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

NODE = {"type": "string", "description": "Node name (e.g. pve01)"}
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731


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
        "description": "Get node configuration (wake-on-LAN MAC, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
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
        "description": "Scan for available storage, iSCSI targets, or other resources on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "type": OPT_STR("Scan type: zfs, lvm, lvmthin, iscsi, nfs, cifs, glusterfs, pbs, dir"),
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


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    node = args.get("node", "")

    if name == "list_nodes":
        return await client.get("/nodes")

    elif name == "get_node_status":
        return await client.get(f"/nodes/{node}/status")

    elif name == "get_node_config":
        return await client.get(f"/nodes/{node}/config")

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
        data: dict[str, Any] = {}
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
        return await client.get(f"/nodes/{node}/scan/{args['type']}")

    elif name == "wakeonlan":
        return await client.post(f"/nodes/{node}/wakeonlan")

    raise ValueError(f"Unknown tool: {name}")
