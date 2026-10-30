"""MCP resources: read-only views of the cluster a client can attach as context.

Static resources cover the whole cluster; templates take a node and a guest ID. Every one maps
to a single GET, so they work in read-only mode and for every role. Path segments are checked
before use, so a URI can't steer the request elsewhere in the API.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from mcp.types import Resource, ResourceTemplate

from .client import ProxmoxClient

MIME = "application/json"


@dataclass(frozen=True)
class Static:
    uri: str
    name: str
    description: str
    path: str


STATIC = [
    Static(
        "proxmox://cluster/status",
        "Cluster status",
        "Quorum and node membership.",
        "/cluster/status",
    ),
    Static(
        "proxmox://cluster/resources",
        "Cluster resources",
        "Every node, VM, container and storage with live usage.",
        "/cluster/resources",
    ),
    Static(
        "proxmox://cluster/tasks",
        "Recent tasks",
        "Recent tasks across the cluster, with status.",
        "/cluster/tasks",
    ),
    Static("proxmox://nodes", "Nodes", "Nodes with status, CPU, memory and uptime.", "/nodes"),
    Static(
        "proxmox://storage",
        "Storage definitions",
        "Configured storage: type, content and nodes.",
        "/storage",
    ),
]
BY_URI = {s.uri: s for s in STATIC}

_NODE = r"(?P<node>[A-Za-z0-9][A-Za-z0-9.-]{0,62})"
_VMID = r"(?P<vmid>[1-9][0-9]{2,8})"
TEMPLATES: list[tuple[ResourceTemplate, re.Pattern[str], str]] = [
    (
        ResourceTemplate(
            uriTemplate="proxmox://nodes/{node}/status",
            name="Node status",
            description="CPU, memory, load, uptime and versions of one node.",
            mimeType=MIME,
        ),
        re.compile(rf"proxmox://nodes/{_NODE}/status"),
        "/nodes/{node}/status",
    ),
    (
        ResourceTemplate(
            uriTemplate="proxmox://vms/{node}/{vmid}/config",
            name="VM config",
            description="Configuration of one QEMU VM.",
            mimeType=MIME,
        ),
        re.compile(rf"proxmox://vms/{_NODE}/{_VMID}/config"),
        "/nodes/{node}/qemu/{vmid}/config",
    ),
    (
        ResourceTemplate(
            uriTemplate="proxmox://cts/{node}/{vmid}/config",
            name="Container config",
            description="Configuration of one LXC container.",
            mimeType=MIME,
        ),
        re.compile(rf"proxmox://cts/{_NODE}/{_VMID}/config"),
        "/nodes/{node}/lxc/{vmid}/config",
    ),
]


def list_resources() -> list[Resource]:
    return [
        Resource(uri=s.uri, name=s.name, description=s.description, mimeType=MIME) for s in STATIC
    ]


def list_templates() -> list[ResourceTemplate]:
    return [t for t, _, _ in TEMPLATES]


def api_path(uri: str) -> str:
    """The Proxmox API path a resource URI reads. Raises ValueError for unknown URIs."""
    if uri in BY_URI:
        return BY_URI[uri].path
    for _, pattern, path in TEMPLATES:
        m = pattern.fullmatch(uri)
        if m:
            return path.format(**m.groupdict())
    raise ValueError(f"Unknown resource: {uri}")


async def read(client: ProxmoxClient, uri: str) -> str:
    result: Any = await client.get(api_path(uri))
    return json.dumps(result, separators=(",", ":"), ensure_ascii=False, default=str)
