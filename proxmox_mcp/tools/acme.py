"""ACME/TLS certificate tools: accounts, plugins, certificates, node certs."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

NODE = {"type": "string", "description": "Node name (e.g. pve01)"}
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731


TOOLS = [
    # --- ACME accounts ---
    {
        "name": "list_acme_accounts",
        "description": "List registered ACME accounts.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_acme_account",
        "description": "Get details of an ACME account.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Account name (default 'default')"),
            },
            "required": ["name"],
        },
    },
    {
        "name": "register_acme_account",
        "description": "Register a new ACME account (Let's Encrypt).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Account name"),
                "contact": OPT_STR("Email address for registration"),
                "directory": OPT_STR("ACME directory URL (default Let's Encrypt)"),
                "tos_url": OPT_STR("Terms of service URL to accept"),
            },
            "required": ["contact"],
        },
    },
    {
        "name": "deregister_acme_account",
        "description": "Deregister an ACME account.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Account name"),
            },
            "required": ["name"],
        },
    },
    # --- ACME plugins ---
    {
        "name": "list_acme_plugins",
        "description": "List ACME challenge plugins.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": OPT_STR("Filter by type: dns or standalone"),
            },
        },
    },
    {
        "name": "get_acme_plugin",
        "description": "Get an ACME plugin configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Plugin ID"),
            },
            "required": ["id"],
        },
    },
    {
        "name": "create_acme_plugin",
        "description": "Create an ACME DNS challenge plugin.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Plugin ID"),
                "type": OPT_STR("Plugin type: dns or standalone"),
                "api": OPT_STR("DNS provider API (e.g. cloudflare, route53, hetzner)"),
                "data": OPT_STR("API credentials as key=value pairs (newline-separated)"),
                "disable": OPT_BOOL("Disable this plugin"),
                "validation-delay": OPT_STR("Validation delay in seconds"),
            },
            "required": ["id", "type"],
        },
    },
    {
        "name": "update_acme_plugin",
        "description": "Update an ACME plugin.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Plugin ID"),
                "data": OPT_STR("API credentials"),
                "disable": OPT_BOOL("Disable plugin"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["id"],
        },
    },
    {
        "name": "delete_acme_plugin",
        "description": "Delete an ACME plugin.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": OPT_STR("Plugin ID"),
            },
            "required": ["id"],
        },
    },
    # --- Node certificates ---
    {
        "name": "get_node_certificates",
        "description": "Get certificate info for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "order_node_acme_cert",
        "description": "Order or renew an ACME certificate for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "force": OPT_BOOL("Force renewal even if not expiring"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "revoke_node_acme_cert",
        "description": "Revoke the ACME certificate for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {"node": NODE},
            "required": ["node"],
        },
    },
    {
        "name": "upload_node_custom_cert",
        "description": "Upload a custom TLS certificate for a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "certificates": OPT_STR("PEM-encoded certificate chain"),
                "key": OPT_STR("PEM-encoded private key"),
                "force": OPT_BOOL("Overwrite existing certificate"),
                "restart": OPT_BOOL("Restart services after upload"),
            },
            "required": ["node", "certificates"],
        },
    },
    {
        "name": "delete_node_custom_cert",
        "description": "Delete the custom TLS certificate for a node (reverts to self-signed).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "restart": OPT_BOOL("Restart services after deletion"),
            },
            "required": ["node"],
        },
    },
    # --- ACME metadata / directories ---
    {
        "name": "list_acme_directories",
        "description": "List available ACME directory URLs (Let's Encrypt, staging, etc.).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_acme_tos",
        "description": "Get the Terms of Service URL for an ACME directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "directory": OPT_STR("ACME directory URL"),
            },
        },
    },
    {
        "name": "list_acme_challenge_schemas",
        "description": "List available ACME DNS challenge schemas (supported DNS providers).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    if name == "list_acme_accounts":
        return await client.get("/cluster/acme/account")

    elif name == "get_acme_account":
        return await client.get(f"/cluster/acme/account/{args['name']}")

    elif name == "register_acme_account":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/acme/account", data)

    elif name == "deregister_acme_account":
        return await client.delete(f"/cluster/acme/account/{args['name']}")

    elif name == "list_acme_plugins":
        params = {k: args[k] for k in ("type",) if k in args}
        return await client.get("/cluster/acme/plugins", params or None)

    elif name == "get_acme_plugin":
        return await client.get(f"/cluster/acme/plugins/{args['id']}")

    elif name == "create_acme_plugin":
        data = {k: v for k, v in args.items()}
        return await client.post("/cluster/acme/plugins", data)

    elif name == "update_acme_plugin":
        plugin_id = args["id"]
        data = {k: v for k, v in args.items() if k != "id"}
        return await client.put(f"/cluster/acme/plugins/{plugin_id}", data)

    elif name == "delete_acme_plugin":
        return await client.delete(f"/cluster/acme/plugins/{args['id']}")

    elif name == "get_node_certificates":
        return await client.get(f"/nodes/{args['node']}/certificates/info")

    elif name == "order_node_acme_cert":
        data = {}
        if "force" in args:
            data["force"] = args["force"]
        return await client.post(f"/nodes/{args['node']}/certificates/acme/certificate", data or None)

    elif name == "revoke_node_acme_cert":
        return await client.delete(f"/nodes/{args['node']}/certificates/acme/certificate")

    elif name == "upload_node_custom_cert":
        node = args["node"]
        data = {k: v for k, v in args.items() if k != "node"}
        return await client.post(f"/nodes/{node}/certificates/custom", data)

    elif name == "delete_node_custom_cert":
        params = {}
        if "restart" in args:
            params["restart"] = args["restart"]
        return await client.delete(f"/nodes/{args['node']}/certificates/custom", params or None)

    elif name == "list_acme_directories":
        return await client.get("/cluster/acme/directories")

    elif name == "get_acme_tos":
        params = {k: args[k] for k in ("directory",) if k in args}
        return await client.get("/cluster/acme/tos", params or None)

    elif name == "list_acme_challenge_schemas":
        return await client.get("/cluster/acme/challenge-schema")

    raise ValueError(f"Unknown tool: {name}")
