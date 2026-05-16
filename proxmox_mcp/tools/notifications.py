"""Notification tools: endpoints (gotify, sendmail, smtp, webhook), matchers, targets."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731


TOOLS = [
    # --- Targets (read-only view of all endpoints) ---
    {
        "name": "list_notification_targets",
        "description": "List all notification targets (combined view of all endpoint types).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # --- Gotify endpoints ---
    {
        "name": "list_gotify_endpoints",
        "description": "List Gotify notification endpoints.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_gotify_endpoint",
        "description": "Get a Gotify endpoint configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": OPT_STR("Endpoint name")},
            "required": ["name"],
        },
    },
    {
        "name": "create_gotify_endpoint",
        "description": "Create a Gotify notification endpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Endpoint name"),
                "server": OPT_STR("Gotify server URL"),
                "token": OPT_STR("Gotify application token"),
                "comment": OPT_STR("Comment"),
                "disable": OPT_BOOL("Disable endpoint"),
            },
            "required": ["name", "server", "token"],
        },
    },
    {
        "name": "update_gotify_endpoint",
        "description": "Update a Gotify endpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Endpoint name"),
                "server": OPT_STR("Gotify server URL"),
                "token": OPT_STR("Gotify token"),
                "comment": OPT_STR("Comment"),
                "disable": OPT_BOOL("Disable endpoint"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["name"],
        },
    },
    {
        "name": "delete_gotify_endpoint",
        "description": "Delete a Gotify endpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": OPT_STR("Endpoint name")},
            "required": ["name"],
        },
    },
    # --- Sendmail endpoints ---
    {
        "name": "list_sendmail_endpoints",
        "description": "List sendmail notification endpoints.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_sendmail_endpoint",
        "description": "Get a sendmail endpoint configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": OPT_STR("Endpoint name")},
            "required": ["name"],
        },
    },
    {
        "name": "create_sendmail_endpoint",
        "description": "Create a sendmail notification endpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Endpoint name"),
                "mailto": OPT_STR("Recipient email (comma-separated)"),
                "mailto-user": OPT_STR("Send to these Proxmox user emails (comma-separated user IDs)"),
                "from-address": OPT_STR("From address override"),
                "author": OPT_STR("Author name"),
                "comment": OPT_STR("Comment"),
                "disable": OPT_BOOL("Disable endpoint"),
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_sendmail_endpoint",
        "description": "Update a sendmail endpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Endpoint name"),
                "mailto": OPT_STR("Recipient email"),
                "mailto-user": OPT_STR("Proxmox user IDs"),
                "from-address": OPT_STR("From address"),
                "author": OPT_STR("Author"),
                "comment": OPT_STR("Comment"),
                "disable": OPT_BOOL("Disable"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["name"],
        },
    },
    {
        "name": "delete_sendmail_endpoint",
        "description": "Delete a sendmail endpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": OPT_STR("Endpoint name")},
            "required": ["name"],
        },
    },
    # --- SMTP endpoints ---
    {
        "name": "list_smtp_endpoints",
        "description": "List SMTP notification endpoints.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_smtp_endpoint",
        "description": "Create an SMTP notification endpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Endpoint name"),
                "server": OPT_STR("SMTP server hostname"),
                "port": OPT_INT("SMTP port"),
                "mailto": OPT_STR("Recipient email addresses (comma-separated)"),
                "mailto-user": OPT_STR("Proxmox user IDs"),
                "from-address": OPT_STR("From address"),
                "author": OPT_STR("Author name"),
                "mode": OPT_STR("TLS mode: insecure, starttls, or tls"),
                "username": OPT_STR("SMTP username"),
                "password": OPT_STR("SMTP password"),
                "comment": OPT_STR("Comment"),
                "disable": OPT_BOOL("Disable endpoint"),
            },
            "required": ["name", "server", "from-address"],
        },
    },
    {
        "name": "delete_smtp_endpoint",
        "description": "Delete an SMTP endpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": OPT_STR("Endpoint name")},
            "required": ["name"],
        },
    },
    # --- Webhook endpoints ---
    {
        "name": "list_webhook_endpoints",
        "description": "List webhook notification endpoints.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_webhook_endpoint",
        "description": "Create a webhook notification endpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Endpoint name"),
                "url": OPT_STR("Webhook URL"),
                "method": OPT_STR("HTTP method: POST, PUT, or GET"),
                "secret": OPT_STR("Secret for HMAC signature"),
                "header": OPT_STR("HTTP headers (key: value, newline-separated)"),
                "body": OPT_STR("Request body template"),
                "comment": OPT_STR("Comment"),
                "disable": OPT_BOOL("Disable endpoint"),
            },
            "required": ["name", "url", "method"],
        },
    },
    {
        "name": "delete_webhook_endpoint",
        "description": "Delete a webhook endpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": OPT_STR("Endpoint name")},
            "required": ["name"],
        },
    },
    # --- Matchers ---
    {
        "name": "list_notification_matchers",
        "description": "List notification matchers (routing rules).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_notification_matcher",
        "description": "Get a notification matcher configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": OPT_STR("Matcher name")},
            "required": ["name"],
        },
    },
    {
        "name": "create_notification_matcher",
        "description": "Create a notification matcher.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Matcher name"),
                "target": OPT_STR("Notification target(s) (comma-separated endpoint names)"),
                "match-field": OPT_STR("Field match rules (e.g. type=vzdump)"),
                "match-severity": OPT_STR("Severity match: info, notice, warning, error, unknown"),
                "match-calendar": OPT_STR("Calendar match (time range)"),
                "invert-match": OPT_BOOL("Invert match logic"),
                "comment": OPT_STR("Comment"),
                "disable": OPT_BOOL("Disable matcher"),
                "mode": OPT_STR("Match mode: all or any"),
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_notification_matcher",
        "description": "Update a notification matcher.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": OPT_STR("Matcher name"),
                "target": OPT_STR("Notification targets"),
                "match-field": OPT_STR("Field match rules"),
                "match-severity": OPT_STR("Severity match"),
                "disable": OPT_BOOL("Disable"),
                "delete": OPT_STR("Keys to delete"),
                "digest": OPT_STR("Config digest"),
            },
            "required": ["name"],
        },
    },
    {
        "name": "delete_notification_matcher",
        "description": "Delete a notification matcher.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": OPT_STR("Matcher name")},
            "required": ["name"],
        },
    },
    {
        "name": "list_notification_matcher_fields",
        "description": "List available notification matcher field names (e.g. type, hostname, job-id).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    base = "/cluster/notifications"

    if name == "list_notification_targets":
        return await client.get(f"{base}/targets")

    elif name == "list_gotify_endpoints":
        return await client.get(f"{base}/endpoints/gotify")

    elif name == "get_gotify_endpoint":
        return await client.get(f"{base}/endpoints/gotify/{args['name']}")

    elif name == "create_gotify_endpoint":
        data = {k: v for k, v in args.items()}
        return await client.post(f"{base}/endpoints/gotify", data)

    elif name == "update_gotify_endpoint":
        ep_name = args["name"]
        data = {k: v for k, v in args.items() if k != "name"}
        return await client.put(f"{base}/endpoints/gotify/{ep_name}", data)

    elif name == "delete_gotify_endpoint":
        return await client.delete(f"{base}/endpoints/gotify/{args['name']}")

    elif name == "list_sendmail_endpoints":
        return await client.get(f"{base}/endpoints/sendmail")

    elif name == "get_sendmail_endpoint":
        return await client.get(f"{base}/endpoints/sendmail/{args['name']}")

    elif name == "create_sendmail_endpoint":
        data = {k: v for k, v in args.items()}
        return await client.post(f"{base}/endpoints/sendmail", data)

    elif name == "update_sendmail_endpoint":
        ep_name = args["name"]
        data = {k: v for k, v in args.items() if k != "name"}
        return await client.put(f"{base}/endpoints/sendmail/{ep_name}", data)

    elif name == "delete_sendmail_endpoint":
        return await client.delete(f"{base}/endpoints/sendmail/{args['name']}")

    elif name == "list_smtp_endpoints":
        return await client.get(f"{base}/endpoints/smtp")

    elif name == "create_smtp_endpoint":
        data = {k: v for k, v in args.items()}
        return await client.post(f"{base}/endpoints/smtp", data)

    elif name == "delete_smtp_endpoint":
        return await client.delete(f"{base}/endpoints/smtp/{args['name']}")

    elif name == "list_webhook_endpoints":
        return await client.get(f"{base}/endpoints/webhook")

    elif name == "create_webhook_endpoint":
        data = {k: v for k, v in args.items()}
        return await client.post(f"{base}/endpoints/webhook", data)

    elif name == "delete_webhook_endpoint":
        return await client.delete(f"{base}/endpoints/webhook/{args['name']}")

    elif name == "list_notification_matchers":
        return await client.get(f"{base}/matchers")

    elif name == "get_notification_matcher":
        return await client.get(f"{base}/matchers/{args['name']}")

    elif name == "create_notification_matcher":
        data = {k: v for k, v in args.items()}
        return await client.post(f"{base}/matchers", data)

    elif name == "update_notification_matcher":
        matcher_name = args["name"]
        data = {k: v for k, v in args.items() if k != "name"}
        return await client.put(f"{base}/matchers/{matcher_name}", data)

    elif name == "delete_notification_matcher":
        return await client.delete(f"{base}/matchers/{args['name']}")

    elif name == "list_notification_matcher_fields":
        return await client.get(f"{base}/matcher-fields")

    raise ValueError(f"Unknown tool: {name}")
