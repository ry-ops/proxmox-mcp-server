"""Cluster and node firewall tools: rules, aliases, IPsets, security groups, options, logs."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731
NODE = {"type": "string", "description": "Node name (e.g. pve01)"}


TOOLS = [
    # --- Cluster firewall rules ---
    {
        "name": "list_cluster_firewall_rules",
        "description": "List all cluster-level firewall rules.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "add_cluster_firewall_rule",
        "description": "Add a cluster-level firewall rule.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": OPT_STR("in or out"),
                "action": OPT_STR("ACCEPT, DROP, or REJECT"),
                "proto": OPT_STR("Protocol: tcp, udp, icmp, etc."),
                "dport": OPT_STR("Destination port or range"),
                "sport": OPT_STR("Source port"),
                "source": OPT_STR("Source address or CIDR"),
                "dest": OPT_STR("Destination address or CIDR"),
                "macro": OPT_STR("Macro name (e.g. SSH, HTTP, HTTPS)"),
                "comment": OPT_STR("Rule comment"),
                "enable": OPT_INT("Enable: 1 or 0"),
                "pos": OPT_INT("Insert at position"),
            },
            "required": ["type", "action"],
        },
    },
    {
        "name": "update_cluster_firewall_rule",
        "description": "Update a cluster-level firewall rule.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pos": OPT_INT("Rule position"),
                "type": OPT_STR("in or out"),
                "action": OPT_STR("ACCEPT, DROP, or REJECT"),
                "proto": OPT_STR("Protocol"),
                "dport": OPT_STR("Destination port"),
                "source": OPT_STR("Source"),
                "dest": OPT_STR("Destination"),
                "enable": OPT_INT("Enable: 1 or 0"),
                "comment": OPT_STR("Comment"),
                "digest": OPT_STR("Config digest"),
                "moveto": OPT_INT("Move to this position"),
                "delete": OPT_STR("Keys to delete"),
            },
            "required": ["pos"],
        },
    },
    {
        "name": "delete_cluster_firewall_rule",
        "description": "Delete a cluster-level firewall rule.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pos": OPT_INT("Rule position"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["pos"],
        },
    },
    {
        "name": "get_cluster_firewall_options",
        "description": "Get cluster firewall options.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_cluster_firewall_options",
        "description": "Set cluster firewall options.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "enable": OPT_INT("Enable firewall: 1 or 0"),
                "policy_in": OPT_STR("Default inbound policy: ACCEPT, DROP, or REJECT"),
                "policy_out": OPT_STR("Default outbound policy: ACCEPT, DROP, or REJECT"),
                "log_ratelimit": OPT_STR("Log rate limit (e.g. enable=1,burst=5,rate=1/second)"),
                "ebtables": OPT_BOOL("Enable ebtables bridge filtering"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
        },
    },
    # --- Security groups ---
    {
        "name": "list_firewall_groups",
        "description": "List all firewall security groups.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_firewall_group",
        "description": "Create a firewall security group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group": OPT_STR("Security group name"),
                "comment": OPT_STR("Comment"),
                "rename": OPT_STR("Rename from this old name"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["group"],
        },
    },
    {
        "name": "delete_firewall_group",
        "description": "Delete a firewall security group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group": OPT_STR("Security group name"),
            },
            "required": ["group"],
        },
    },
    {
        "name": "list_firewall_group_rules",
        "description": "List rules inside a firewall security group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group": OPT_STR("Security group name"),
            },
            "required": ["group"],
        },
    },
    {
        "name": "add_firewall_group_rule",
        "description": "Add a rule to a firewall security group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group": OPT_STR("Security group name"),
                "type": OPT_STR("in or out"),
                "action": OPT_STR("ACCEPT, DROP, or REJECT"),
                "proto": OPT_STR("Protocol"),
                "dport": OPT_STR("Destination port"),
                "source": OPT_STR("Source"),
                "dest": OPT_STR("Destination"),
                "comment": OPT_STR("Comment"),
                "enable": OPT_INT("Enable: 1 or 0"),
                "pos": OPT_INT("Insert position"),
            },
            "required": ["group", "type", "action"],
        },
    },
    {
        "name": "delete_firewall_group_rule",
        "description": "Delete a rule from a firewall security group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group": OPT_STR("Security group name"),
                "pos": OPT_INT("Rule position"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["group", "pos"],
        },
    },
    # --- Aliases ---
    {
        "name": "list_firewall_aliases",
        "description": "List all firewall aliases (named IPs/CIDRs).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_firewall_alias",
        "description": "Create a firewall alias.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Alias name"),
                "cidr": OPT_STR("IP or CIDR (e.g. 10.0.0.0/8)"),
                "comment": OPT_STR("Comment"),
            },
            "required": ["name", "cidr"],
        },
    },
    {
        "name": "update_firewall_alias",
        "description": "Update a firewall alias.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Alias name"),
                "cidr": OPT_STR("New IP or CIDR"),
                "comment": OPT_STR("Comment"),
                "rename": OPT_STR("New alias name"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["name"],
        },
    },
    {
        "name": "delete_firewall_alias",
        "description": "Delete a firewall alias.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Alias name"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["name"],
        },
    },
    # --- IPsets ---
    {
        "name": "list_firewall_ipsets",
        "description": "List all firewall IPsets.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_firewall_ipset",
        "description": "Create a firewall IPset.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("IPset name"),
                "comment": OPT_STR("Comment"),
                "rename": OPT_STR("Rename from old name"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["name"],
        },
    },
    {
        "name": "delete_firewall_ipset",
        "description": "Delete a firewall IPset.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("IPset name"),
                "force": OPT_BOOL("Force deletion even if used"),
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_firewall_ipset_entries",
        "description": "List IPs in a firewall IPset.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("IPset name"),
            },
            "required": ["name"],
        },
    },
    {
        "name": "add_firewall_ipset_entry",
        "description": "Add an IP/CIDR to a firewall IPset.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("IPset name"),
                "cidr": OPT_STR("IP or CIDR to add"),
                "comment": OPT_STR("Comment"),
                "nomatch": OPT_BOOL("Negate this entry"),
            },
            "required": ["name", "cidr"],
        },
    },
    {
        "name": "delete_firewall_ipset_entry",
        "description": "Remove an IP/CIDR from a firewall IPset.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("IPset name"),
                "cidr": OPT_STR("IP or CIDR to remove"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["name", "cidr"],
        },
    },
    # --- Node firewall ---
    {
        "name": "list_node_firewall_rules",
        "description": "List firewall rules for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "add_node_firewall_rule",
        "description": "Add a firewall rule to a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "type": OPT_STR("in or out"),
                "action": OPT_STR("ACCEPT, DROP, or REJECT"),
                "proto": OPT_STR("Protocol"),
                "dport": OPT_STR("Destination port"),
                "source": OPT_STR("Source"),
                "dest": OPT_STR("Destination"),
                "comment": OPT_STR("Comment"),
                "enable": OPT_INT("Enable: 1 or 0"),
                "pos": OPT_INT("Insert position"),
            },
            "required": ["node", "type", "action"],
        },
    },
    {
        "name": "delete_node_firewall_rule",
        "description": "Delete a firewall rule from a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "pos": OPT_INT("Rule position"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["node", "pos"],
        },
    },
    {
        "name": "get_node_firewall_options",
        "description": "Get firewall options for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "set_node_firewall_options",
        "description": "Set firewall options for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "enable": OPT_INT("Enable firewall: 1 or 0"),
                "log_level_in": OPT_STR("Log level for inbound"),
                "log_level_out": OPT_STR("Log level for outbound"),
                "tcp_flags_log_level": OPT_STR("Log level for TCP flags"),
                "smurf_log_level": OPT_STR("Log level for smurf attacks"),
                "nosmurfs": OPT_BOOL("Block smurf attacks"),
                "tcpflags": OPT_BOOL("Filter illegal TCP flags"),
                "nf_conntrack_max": OPT_INT("Max connection tracking entries"),
                "nf_conntrack_tcp_timeout_established": OPT_INT("TCP connection tracking timeout"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_node_firewall_log",
        "description": "Get firewall log for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "limit": OPT_INT("Max entries"),
                "start": OPT_INT("Start offset"),
                "since": OPT_INT("Show entries since Unix timestamp"),
                "until": OPT_INT("Show entries until Unix timestamp"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "get_cluster_firewall_log",
        "description": "Get cluster-level firewall log.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": OPT_INT("Max entries"),
                "start": OPT_INT("Start offset"),
                "since": OPT_INT("Show entries since Unix timestamp"),
                "until": OPT_INT("Show entries until Unix timestamp"),
            },
        },
    },
    {
        "name": "list_firewall_macros",
        "description": "List available firewall macros (e.g. SSH, HTTP, Ping).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_firewall_refs",
        "description": "List firewall rule references (aliases and IPsets).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": OPT_STR("Filter by type: alias or ipset"),
            },
        },
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    if name == "list_cluster_firewall_rules":
        return await client.get("/cluster/firewall/rules")

    elif name == "add_cluster_firewall_rule":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/firewall/rules", data)

    elif name == "update_cluster_firewall_rule":
        pos = args["pos"]
        data = {k: v for k, v in args.items() if k != "pos"}
        return await client.put(f"/cluster/firewall/rules/{pos}", data)

    elif name == "delete_cluster_firewall_rule":
        params = {k: args[k] for k in ("digest",) if k in args}
        return await client.delete(f"/cluster/firewall/rules/{args['pos']}", params or None)

    elif name == "get_cluster_firewall_options":
        return await client.get("/cluster/firewall/options")

    elif name == "set_cluster_firewall_options":
        data = {k: v for k, v in args.items()}
        return await client.put("/cluster/firewall/options", data)

    elif name == "list_firewall_groups":
        return await client.get("/cluster/firewall/groups")

    elif name == "create_firewall_group":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/firewall/groups", data)

    elif name == "delete_firewall_group":
        return await client.delete(f"/cluster/firewall/groups/{args['group']}")

    elif name == "list_firewall_group_rules":
        return await client.get(f"/cluster/firewall/groups/{args['group']}")

    elif name == "add_firewall_group_rule":
        group = args["group"]
        data = {k: v for k, v in args.items() if k != "group"}
        return await client.post(f"/cluster/firewall/groups/{group}", data)

    elif name == "delete_firewall_group_rule":
        params = {k: args[k] for k in ("digest",) if k in args}
        return await client.delete(f"/cluster/firewall/groups/{args['group']}/{args['pos']}", params or None)

    elif name == "list_firewall_aliases":
        return await client.get("/cluster/firewall/aliases")

    elif name == "create_firewall_alias":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/firewall/aliases", data)

    elif name == "update_firewall_alias":
        name_val = args["name"]
        data = {k: v for k, v in args.items() if k != "name"}
        return await client.put(f"/cluster/firewall/aliases/{name_val}", data)

    elif name == "delete_firewall_alias":
        params = {k: args[k] for k in ("digest",) if k in args}
        return await client.delete(f"/cluster/firewall/aliases/{args['name']}", params or None)

    elif name == "list_firewall_ipsets":
        return await client.get("/cluster/firewall/ipset")

    elif name == "create_firewall_ipset":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/firewall/ipset", data)

    elif name == "delete_firewall_ipset":
        params = {k: args[k] for k in ("force",) if k in args}
        return await client.delete(f"/cluster/firewall/ipset/{args['name']}", params or None)

    elif name == "list_firewall_ipset_entries":
        return await client.get(f"/cluster/firewall/ipset/{args['name']}")

    elif name == "add_firewall_ipset_entry":
        ipset_name = args["name"]
        data = {k: v for k, v in args.items() if k != "name"}
        return await client.post(f"/cluster/firewall/ipset/{ipset_name}", data)

    elif name == "delete_firewall_ipset_entry":
        from urllib.parse import quote
        cidr = quote(args["cidr"], safe="")
        params = {k: args[k] for k in ("digest",) if k in args}
        return await client.delete(f"/cluster/firewall/ipset/{args['name']}/{cidr}", params or None)

    elif name == "list_node_firewall_rules":
        return await client.get(f"/nodes/{args['node']}/firewall/rules")

    elif name == "add_node_firewall_rule":
        node = args["node"]
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(f"/nodes/{node}/firewall/rules", data)

    elif name == "delete_node_firewall_rule":
        params = {k: args[k] for k in ("digest",) if k in args}
        return await client.delete(f"/nodes/{args['node']}/firewall/rules/{args['pos']}", params or None)

    elif name == "get_node_firewall_options":
        return await client.get(f"/nodes/{args['node']}/firewall/options")

    elif name == "set_node_firewall_options":
        node = args["node"]
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.put(f"/nodes/{node}/firewall/options", data)

    elif name == "get_node_firewall_log":
        node = args["node"]
        params = {k: args[k] for k in ("limit", "start", "since", "until") if k in args}
        return await client.get(f"/nodes/{node}/firewall/log", params or None)

    elif name == "get_cluster_firewall_log":
        params = {k: args[k] for k in ("limit", "start", "since", "until") if k in args}
        return await client.get("/cluster/firewall/log", params or None)

    elif name == "list_firewall_macros":
        return await client.get("/cluster/firewall/macros")

    elif name == "list_firewall_refs":
        params = {k: args[k] for k in ("type",) if k in args}
        return await client.get("/cluster/firewall/refs", params or None)

    raise ValueError(f"Unknown tool: {name}")
