"""Resource pool tools: list, create, update, delete, get members."""

from __future__ import annotations

from typing import Any

from ..client import ProxmoxClient

OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731


TOOLS = [
    {
        "name": "list_pools",
        "description": "List all resource pools.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_pool",
        "description": "Get a resource pool and its members.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "poolid": OPT_STR("Pool ID"),
                "type": OPT_STR("Filter members by type: qemu or lxc"),
            },
            "required": ["poolid"],
        },
    },
    {
        "name": "create_pool",
        "description": "Create a new resource pool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "poolid": OPT_STR("Pool ID"),
                "comment": OPT_STR("Pool description"),
            },
            "required": ["poolid"],
        },
    },
    {
        "name": "update_pool",
        "description": "Update a resource pool (add/remove members or update comment).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "poolid": OPT_STR("Pool ID"),
                "comment": OPT_STR("Pool description"),
                "vms": OPT_STR("Comma-separated VMIDs to add/remove"),
                "storage": OPT_STR("Comma-separated storage IDs to add/remove"),
                "delete": OPT_BOOL("Remove listed VMs/storages from pool instead of adding"),
                "allow-move": OPT_BOOL("Allow moving VMs to this pool from another pool"),
            },
            "required": ["poolid"],
        },
    },
    {
        "name": "delete_pool",
        "description": "Delete a resource pool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "poolid": OPT_STR("Pool ID"),
            },
            "required": ["poolid"],
        },
    },
]


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    if name == "list_pools":
        return await client.get("/pools")

    elif name == "get_pool":
        params = {k: args[k] for k in ("type",) if k in args}
        return await client.get(f"/pools/{args['poolid']}", params or None)

    elif name == "create_pool":
        data = {k: v for k, v in args.items()}
        return await client.post("/pools", data)

    elif name == "update_pool":
        poolid = args["poolid"]
        data = {k: v for k, v in args.items() if k != "poolid"}
        return await client.put(f"/pools/{poolid}", data)

    elif name == "delete_pool":
        return await client.delete(f"/pools/{args['poolid']}")

    raise ValueError(f"Unknown tool: {name}")
