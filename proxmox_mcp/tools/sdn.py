"""SDN tools: zones, vnets, subnets, fabrics, controllers, IPAM."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

NODE = {"type": "string", "description": "Node name (e.g. pve01)"}
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731


TOOLS = [
    # --- SDN top-level ---
    {
        "name": "apply_sdn",
        "description": "Apply pending SDN configuration changes cluster-wide.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # --- Zones ---
    {
        "name": "list_sdn_zones",
        "description": "List all SDN zones.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pending": OPT_BOOL("Include pending changes"),
                "running": OPT_BOOL("Include running state"),
                "type": OPT_STR("Filter by type: simple, vlan, qinq, vxlan, evpn"),
            },
        },
    },
    {
        "name": "get_sdn_zone",
        "description": "Get configuration of a specific SDN zone.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "zone": OPT_STR("Zone ID"),
                "pending": OPT_BOOL("Show pending changes"),
                "running": OPT_BOOL("Show running state"),
            },
            "required": ["zone"],
        },
    },
    {
        "name": "create_sdn_zone",
        "description": "Create a new SDN zone.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "zone": OPT_STR("Zone ID"),
                "type": OPT_STR("Zone type: simple, vlan, qinq, vxlan, or evpn"),
                "bridge": OPT_STR("Linux bridge name (for vlan/qinq)"),
                "tag": OPT_INT("VLAN tag (for vlan/qinq)"),
                "vlan-protocol": OPT_STR("VLAN protocol: 802.1q or 802.1ad"),
                "mtu": OPT_INT("MTU"),
                "peers": OPT_STR("VXLAN peers (comma-separated IPs)"),
                "controller": OPT_STR("EVPN controller ID"),
                "vrf-vxlan": OPT_INT("EVPN VRF VXLAN ID"),
                "mac": OPT_STR("Anycast MAC address (for EVPN)"),
                "nodes": OPT_STR("Nodes that apply this zone (empty=all)"),
                "ipam": OPT_STR("IPAM plugin ID"),
                "dns": OPT_STR("DNS plugin ID"),
                "reversedns": OPT_STR("Reverse DNS zone"),
                "dnszone": OPT_STR("DNS zone"),
            },
            "required": ["zone", "type"],
        },
    },
    {
        "name": "update_sdn_zone",
        "description": "Update an SDN zone.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "zone": OPT_STR("Zone ID"),
                "mtu": OPT_INT("MTU"),
                "nodes": OPT_STR("Allowed nodes"),
                "ipam": OPT_STR("IPAM plugin"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["zone"],
        },
    },
    {
        "name": "delete_sdn_zone",
        "description": "Delete an SDN zone.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "zone": OPT_STR("Zone ID"),
            },
            "required": ["zone"],
        },
    },
    # --- VNets ---
    {
        "name": "list_sdn_vnets",
        "description": "List all SDN VNets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pending": OPT_BOOL("Include pending changes"),
                "running": OPT_BOOL("Include running state"),
            },
        },
    },
    {
        "name": "get_sdn_vnet",
        "description": "Get configuration of an SDN VNet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vnet": OPT_STR("VNet ID"),
                "pending": OPT_BOOL("Show pending"),
                "running": OPT_BOOL("Show running"),
            },
            "required": ["vnet"],
        },
    },
    {
        "name": "create_sdn_vnet",
        "description": "Create a new SDN VNet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vnet": OPT_STR("VNet ID"),
                "zone": OPT_STR("Zone this VNet belongs to"),
                "tag": OPT_INT("VLAN/VXLAN tag"),
                "alias": OPT_STR("Alias name"),
                "vlanaware": OPT_BOOL("Allow VLAN-aware guests"),
            },
            "required": ["vnet", "zone"],
        },
    },
    {
        "name": "update_sdn_vnet",
        "description": "Update an SDN VNet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vnet": OPT_STR("VNet ID"),
                "alias": OPT_STR("Alias"),
                "tag": OPT_INT("VLAN/VXLAN tag"),
                "vlanaware": OPT_BOOL("VLAN aware"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["vnet"],
        },
    },
    {
        "name": "delete_sdn_vnet",
        "description": "Delete an SDN VNet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vnet": OPT_STR("VNet ID"),
            },
            "required": ["vnet"],
        },
    },
    # --- Subnets ---
    {
        "name": "list_sdn_subnets",
        "description": "List subnets in an SDN VNet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vnet": OPT_STR("VNet ID"),
                "pending": OPT_BOOL("Include pending"),
                "running": OPT_BOOL("Include running"),
            },
            "required": ["vnet"],
        },
    },
    {
        "name": "create_sdn_subnet",
        "description": "Create a subnet in an SDN VNet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vnet": OPT_STR("VNet ID"),
                "subnet": OPT_STR("CIDR (e.g. 10.0.1.0/24)"),
                "type": OPT_STR("Subnet type (subnet)"),
                "gateway": OPT_STR("Gateway IP"),
                "snat": OPT_BOOL("Enable SNAT"),
                "dhcp-range": OPT_STR("DHCP range (start-end)"),
                "dhcp-dns-server": OPT_STR("DHCP DNS server"),
                "dnszoneprefix": OPT_STR("DNS zone prefix"),
            },
            "required": ["vnet", "subnet", "type"],
        },
    },
    {
        "name": "delete_sdn_subnet",
        "description": "Delete a subnet from an SDN VNet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vnet": OPT_STR("VNet ID"),
                "subnet": OPT_STR("Subnet CIDR"),
            },
            "required": ["vnet", "subnet"],
        },
    },
    # --- Node SDN ---
    {
        "name": "list_node_sdn_zones",
        "description": "List SDN zones visible from a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "list_node_sdn_vnets",
        "description": "List SDN VNets visible from a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    if name == "apply_sdn":
        return await client.put("/cluster/sdn")

    elif name == "list_sdn_zones":
        params = {k: args[k] for k in ("pending", "running", "type") if k in args}
        return await client.get("/cluster/sdn/zones", params or None)

    elif name == "get_sdn_zone":
        params = {k: args[k] for k in ("pending", "running") if k in args}
        return await client.get(f"/cluster/sdn/zones/{args['zone']}", params or None)

    elif name == "create_sdn_zone":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/sdn/zones", data)

    elif name == "update_sdn_zone":
        zone = args["zone"]
        data = {k: v for k, v in args.items() if k != "zone"}
        return await client.put(f"/cluster/sdn/zones/{zone}", data)

    elif name == "delete_sdn_zone":
        return await client.delete(f"/cluster/sdn/zones/{args['zone']}")

    elif name == "list_sdn_vnets":
        params = {k: args[k] for k in ("pending", "running") if k in args}
        return await client.get("/cluster/sdn/vnets", params or None)

    elif name == "get_sdn_vnet":
        params = {k: args[k] for k in ("pending", "running") if k in args}
        return await client.get(f"/cluster/sdn/vnets/{args['vnet']}", params or None)

    elif name == "create_sdn_vnet":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/sdn/vnets", data)

    elif name == "update_sdn_vnet":
        vnet = args["vnet"]
        data = {k: v for k, v in args.items() if k != "vnet"}
        return await client.put(f"/cluster/sdn/vnets/{vnet}", data)

    elif name == "delete_sdn_vnet":
        return await client.delete(f"/cluster/sdn/vnets/{args['vnet']}")

    elif name == "list_sdn_subnets":
        params = {k: args[k] for k in ("pending", "running") if k in args}
        return await client.get(f"/cluster/sdn/vnets/{args['vnet']}/subnets", params or None)

    elif name == "create_sdn_subnet":
        vnet = args["vnet"]
        data = {k: v for k, v in args.items() if k != "vnet"}
        return await client.post(f"/cluster/sdn/vnets/{vnet}/subnets", data)

    elif name == "delete_sdn_subnet":
        from urllib.parse import quote
        subnet = quote(args["subnet"], safe="")
        return await client.delete(f"/cluster/sdn/vnets/{args['vnet']}/subnets/{subnet}")

    elif name == "list_node_sdn_zones":
        return await client.get(f"/nodes/{args['node']}/sdn/zones")

    elif name == "list_node_sdn_vnets":
        return await client.get(f"/nodes/{args['node']}/sdn/vnets")

    raise ValueError(f"Unknown tool: {name}")
