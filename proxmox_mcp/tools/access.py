"""Access control tools: users, groups, roles, ACL, API tokens, TFA, domains, passwords."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731


TOOLS = [
    # --- Users ---
    {
        "name": "list_users",
        "description": "List all users in Proxmox.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "enabled": OPT_BOOL("Filter by enabled state"),
                "full": OPT_BOOL("Include group and token info"),
            },
        },
    },
    {
        "name": "get_user",
        "description": "Get a specific user's configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID (e.g. admin@pam or user@pve)"),
            },
            "required": ["userid"],
        },
    },
    {
        "name": "create_user",
        "description": "Create a new Proxmox user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID (e.g. john@pam)"),
                "password": OPT_STR("Initial password"),
                "email": OPT_STR("Email address"),
                "firstname": OPT_STR("First name"),
                "lastname": OPT_STR("Last name"),
                "comment": OPT_STR("Comment"),
                "groups": OPT_STR("Comma-separated group IDs"),
                "enable": OPT_BOOL("Enable account (default true)"),
                "expire": OPT_INT("Expiry time as Unix timestamp (0 = no expiry)"),
                "keys": OPT_STR("TFA keys"),
            },
            "required": ["userid"],
        },
    },
    {
        "name": "update_user",
        "description": "Update a Proxmox user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID"),
                "email": OPT_STR("Email address"),
                "firstname": OPT_STR("First name"),
                "lastname": OPT_STR("Last name"),
                "comment": OPT_STR("Comment"),
                "groups": OPT_STR("Comma-separated group IDs"),
                "enable": OPT_BOOL("Enable account"),
                "expire": OPT_INT("Expiry time as Unix timestamp"),
                "keys": OPT_STR("TFA keys"),
                "append": OPT_BOOL("Append groups instead of replacing"),
                "delete": OPT_STR("Keys to delete"),
            },
            "required": ["userid"],
        },
    },
    {
        "name": "delete_user",
        "description": "Delete a Proxmox user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID"),
            },
            "required": ["userid"],
        },
    },
    {
        "name": "change_user_password",
        "description": "Change a user's password.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID"),
                "password": OPT_STR("New password"),
                "confirmation-password": OPT_STR("Current admin password (required for non-root)"),
            },
            "required": ["userid", "password"],
        },
    },
    # --- API Tokens ---
    {
        "name": "list_user_tokens",
        "description": "List API tokens for a user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID"),
            },
            "required": ["userid"],
        },
    },
    {
        "name": "get_user_token",
        "description": "Get configuration for a specific API token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID"),
                "tokenid": OPT_STR("Token ID"),
            },
            "required": ["userid", "tokenid"],
        },
    },
    {
        "name": "create_user_token",
        "description": "Create an API token for a user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID"),
                "tokenid": OPT_STR("Token ID (unique name)"),
                "comment": OPT_STR("Token comment"),
                "expire": OPT_INT("Expiry as Unix timestamp (0 = no expiry)"),
                "privsep": OPT_BOOL("Token has reduced privileges (default true)"),
            },
            "required": ["userid", "tokenid"],
        },
    },
    {
        "name": "update_user_token",
        "description": "Update an API token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID"),
                "tokenid": OPT_STR("Token ID"),
                "comment": OPT_STR("Token comment"),
                "expire": OPT_INT("Expiry as Unix timestamp"),
                "privsep": OPT_BOOL("Token privilege separation"),
                "delete": OPT_STR("Keys to delete"),
            },
            "required": ["userid", "tokenid"],
        },
    },
    {
        "name": "delete_user_token",
        "description": "Delete an API token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID"),
                "tokenid": OPT_STR("Token ID"),
            },
            "required": ["userid", "tokenid"],
        },
    },
    # --- Groups ---
    {
        "name": "list_groups",
        "description": "List all groups.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_group",
        "description": "Get a group's configuration and members.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "groupid": OPT_STR("Group ID"),
            },
            "required": ["groupid"],
        },
    },
    {
        "name": "create_group",
        "description": "Create a new group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "groupid": OPT_STR("Group ID"),
                "comment": OPT_STR("Group comment"),
            },
            "required": ["groupid"],
        },
    },
    {
        "name": "update_group",
        "description": "Update a group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "groupid": OPT_STR("Group ID"),
                "comment": OPT_STR("Group comment"),
            },
            "required": ["groupid"],
        },
    },
    {
        "name": "delete_group",
        "description": "Delete a group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "groupid": OPT_STR("Group ID"),
            },
            "required": ["groupid"],
        },
    },
    # --- Roles ---
    {
        "name": "list_roles",
        "description": "List all roles and their privileges.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_role",
        "description": "Get a role's privileges.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "roleid": OPT_STR("Role ID"),
            },
            "required": ["roleid"],
        },
    },
    {
        "name": "create_role",
        "description": "Create a custom role.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "roleid": OPT_STR("Role ID"),
                "privs": OPT_STR("Comma-separated privileges"),
            },
            "required": ["roleid"],
        },
    },
    {
        "name": "update_role",
        "description": "Update a role's privileges.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "roleid": OPT_STR("Role ID"),
                "privs": OPT_STR("Comma-separated privileges"),
                "append": OPT_BOOL("Append privileges (default replace)"),
            },
            "required": ["roleid"],
        },
    },
    {
        "name": "delete_role",
        "description": "Delete a custom role.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "roleid": OPT_STR("Role ID"),
            },
            "required": ["roleid"],
        },
    },
    # --- ACL ---
    {
        "name": "get_acl",
        "description": "Get the access control list (permissions tree).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "update_acl",
        "description": "Add or remove an ACL entry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": OPT_STR("Path (e.g. / or /vms/100 or /nodes/pve01)"),
                "roles": OPT_STR("Comma-separated role IDs"),
                "users": OPT_STR("Comma-separated user IDs"),
                "groups": OPT_STR("Comma-separated group IDs"),
                "tokens": OPT_STR("Comma-separated API token IDs"),
                "propagate": OPT_BOOL("Propagate permissions to sub-paths"),
                "delete": OPT_BOOL("Delete this ACL entry"),
            },
            "required": ["path", "roles"],
        },
    },
    # --- Auth domains ---
    {
        "name": "list_auth_domains",
        "description": "List all authentication domains/realms.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_auth_domain",
        "description": "Get configuration for an authentication domain.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "realm": OPT_STR("Realm name (e.g. pam, pve, or LDAP realm ID)"),
            },
            "required": ["realm"],
        },
    },
    {
        "name": "create_auth_domain",
        "description": "Create a new authentication domain (LDAP, AD, OpenID).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "realm": OPT_STR("Realm name"),
                "type": OPT_STR("Type: ad, ldap, openid, or pam"),
                "server1": OPT_STR("Primary server"),
                "server2": OPT_STR("Fallback server"),
                "base_dn": OPT_STR("LDAP/AD base DN"),
                "bind_dn": OPT_STR("LDAP/AD bind DN"),
                "password": OPT_STR("Bind password"),
                "user_attr": OPT_STR("LDAP user attribute"),
                "default": OPT_BOOL("Set as default realm"),
                "comment": OPT_STR("Comment"),
                "port": OPT_INT("Server port"),
                "secure": OPT_BOOL("Use SSL/TLS"),
                "tfa": OPT_STR("TFA config"),
                "sync-defaults-options": OPT_STR("Sync defaults"),
                "issuer-url": OPT_STR("OpenID issuer URL"),
                "client-id": OPT_STR("OpenID client ID"),
                "client-key": OPT_STR("OpenID client key"),
                "username-claim": OPT_STR("OpenID username claim"),
            },
            "required": ["realm", "type"],
        },
    },
    {
        "name": "update_auth_domain",
        "description": "Update an authentication domain configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "realm": OPT_STR("Realm name"),
                "comment": OPT_STR("Comment"),
                "default": OPT_BOOL("Set as default realm"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["realm"],
        },
    },
    {
        "name": "delete_auth_domain",
        "description": "Delete an authentication domain.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "realm": OPT_STR("Realm name"),
            },
            "required": ["realm"],
        },
    },
    {
        "name": "sync_auth_domain",
        "description": "Sync users/groups from an LDAP/AD/OpenID realm.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "realm": OPT_STR("Realm name"),
                "dry-run": OPT_BOOL("Perform dry run without making changes"),
                "enable-new": OPT_BOOL("Enable newly synced users"),
                "full": OPT_BOOL("Full sync (remove users not in source)"),
                "purge": OPT_BOOL("Remove users/ACLs not in source"),
                "scope": OPT_STR("Scope: users, groups, or both"),
                "remove-vanished": OPT_STR("What to remove: acl, entry, properties (comma-separated)"),
            },
            "required": ["realm"],
        },
    },
    # --- TFA ---
    {
        "name": "list_tfa",
        "description": "List TFA configurations for all users.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("Filter by user ID (optional)"),
            },
        },
    },
    {
        "name": "get_user_tfa",
        "description": "Get TFA configuration for a specific user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID"),
            },
            "required": ["userid"],
        },
    },
    {
        "name": "add_tfa",
        "description": "Add a TFA entry for a user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID"),
                "type": OPT_STR("TFA type: totp, u2f, webauthn, recovery, or yubico"),
                "description": OPT_STR("Description"),
                "totp": OPT_STR("TOTP secret or URI"),
                "value": OPT_STR("Verification value"),
                "challenge": OPT_STR("Challenge for webauthn/u2f"),
                "password": OPT_STR("Current user password"),
            },
            "required": ["userid", "type"],
        },
    },
    {
        "name": "delete_tfa",
        "description": "Delete a TFA entry for a user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": OPT_STR("User ID"),
                "id": OPT_STR("TFA entry ID"),
                "password": OPT_STR("Current user password"),
            },
            "required": ["userid", "id"],
        },
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    if name == "list_users":
        params = {k: args[k] for k in ("enabled", "full") if k in args}
        return await client.get("/access/users", params or None)

    elif name == "get_user":
        return await client.get(f"/access/users/{args['userid']}")

    elif name == "create_user":
        data = {k: v for k, v in args.items()}
        return await client.post("/access/users", data)

    elif name == "update_user":
        userid = args["userid"]
        data = {k: v for k, v in args.items() if k != "userid"}
        return await client.put(f"/access/users/{userid}", data)

    elif name == "delete_user":
        return await client.delete(f"/access/users/{args['userid']}")

    elif name == "change_user_password":
        data = {k: v for k, v in args.items()}
        return await client.put("/access/password", data)

    elif name == "list_user_tokens":
        return await client.get(f"/access/users/{args['userid']}/token")

    elif name == "get_user_token":
        return await client.get(f"/access/users/{args['userid']}/token/{args['tokenid']}")

    elif name == "create_user_token":
        userid = args["userid"]
        tokenid = args["tokenid"]
        data = {k: v for k, v in args.items() if k not in ("userid", "tokenid")}
        return await client.post(f"/access/users/{userid}/token/{tokenid}", data or None)

    elif name == "update_user_token":
        userid = args["userid"]
        tokenid = args["tokenid"]
        data = {k: v for k, v in args.items() if k not in ("userid", "tokenid")}
        return await client.put(f"/access/users/{userid}/token/{tokenid}", data)

    elif name == "delete_user_token":
        return await client.delete(f"/access/users/{args['userid']}/token/{args['tokenid']}")

    elif name == "list_groups":
        return await client.get("/access/groups")

    elif name == "get_group":
        return await client.get(f"/access/groups/{args['groupid']}")

    elif name == "create_group":
        data = {k: v for k, v in args.items()}
        return await client.post("/access/groups", data)

    elif name == "update_group":
        groupid = args["groupid"]
        data = {k: v for k, v in args.items() if k != "groupid"}
        return await client.put(f"/access/groups/{groupid}", data)

    elif name == "delete_group":
        return await client.delete(f"/access/groups/{args['groupid']}")

    elif name == "list_roles":
        return await client.get("/access/roles")

    elif name == "get_role":
        return await client.get(f"/access/roles/{args['roleid']}")

    elif name == "create_role":
        data = {k: v for k, v in args.items()}
        return await client.post("/access/roles", data)

    elif name == "update_role":
        roleid = args["roleid"]
        data = {k: v for k, v in args.items() if k != "roleid"}
        return await client.put(f"/access/roles/{roleid}", data)

    elif name == "delete_role":
        return await client.delete(f"/access/roles/{args['roleid']}")

    elif name == "get_acl":
        return await client.get("/access/acl")

    elif name == "update_acl":
        data = {k: v for k, v in args.items()}
        return await client.put("/access/acl", data)

    elif name == "list_auth_domains":
        return await client.get("/access/domains")

    elif name == "get_auth_domain":
        return await client.get(f"/access/domains/{args['realm']}")

    elif name == "create_auth_domain":
        data = {k: v for k, v in args.items()}
        return await client.post("/access/domains", data)

    elif name == "update_auth_domain":
        realm = args["realm"]
        data = {k: v for k, v in args.items() if k != "realm"}
        return await client.put(f"/access/domains/{realm}", data)

    elif name == "delete_auth_domain":
        return await client.delete(f"/access/domains/{args['realm']}")

    elif name == "sync_auth_domain":
        realm = args["realm"]
        data = {k: v for k, v in args.items() if k != "realm"}
        return await client.post(f"/access/domains/{realm}/sync", data or None)

    elif name == "list_tfa":
        params = {k: args[k] for k in ("userid",) if k in args}
        return await client.get("/access/tfa", params or None)

    elif name == "get_user_tfa":
        return await client.get(f"/access/tfa/{args['userid']}")

    elif name == "add_tfa":
        userid = args["userid"]
        data = {k: v for k, v in args.items() if k != "userid"}
        return await client.post(f"/access/tfa/{userid}", data)

    elif name == "delete_tfa":
        userid = args["userid"]
        tfa_id = args["id"]
        params = {}
        if "password" in args:
            params["password"] = args["password"]
        return await client.delete(f"/access/tfa/{userid}/{tfa_id}", params or None)

    raise ValueError(f"Unknown tool: {name}")
