"""The tool registry: names, schemas, read/write labels, toolsets and read-only filtering."""

import asyncio

import pytest

from proxmox_mcp import registry

ALL, HANDLERS = registry.build(list(registry.TOOLSETS), read_only=False)
DUMMY = {"string": "x", "integer": 1, "number": 1, "boolean": True, "array": [], "object": {}}


class RecordingClient:
    """Stands in for ProxmoxClient and records which HTTP methods a tool sends."""

    def __init__(self) -> None:
        self.methods: set[str] = set()

    async def request(self, method, path, data=None):
        self.methods.add(method)
        return {"data": []}

    async def get(self, path, params=None):
        return await self.request("GET", path, params)

    async def post(self, path, data=None):
        return await self.request("POST", path, data)

    async def put(self, path, data=None):
        return await self.request("PUT", path, data)

    async def delete(self, path, params=None):
        return await self.request("DELETE", path, params)


def test_names_are_unique():
    names = [t.name for t in ALL]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("tool", ALL, ids=lambda t: t.name)
def test_schema_is_well_formed(tool):
    schema = tool.inputSchema
    assert schema["type"] == "object"
    props = schema.get("properties", {})
    missing = set(schema.get("required", [])) - set(props)
    assert not missing, f"required but not in properties: {missing}"
    assert tool.description.strip()


@pytest.mark.parametrize("tool", ALL, ids=lambda t: t.name)
async def test_read_only_label_matches_http_methods(tool):
    """A tool labelled read-only must only GET; any other tool must send a write."""
    props = tool.inputSchema.get("properties", {})
    args = {k: DUMMY[props[k].get("type", "string")] for k in tool.inputSchema.get("required", [])}
    client = RecordingClient()
    try:
        await asyncio.wait_for(HANDLERS[tool.name].handle(tool.name, args, client), 2)
    except ValueError:
        # The deploy_* tools validate their inputs before calling the API.
        assert not client.methods and not registry.is_read_only(tool.name)
        return
    assert client.methods, f"{tool.name} sent no request"
    assert (client.methods == {"GET"}) == registry.is_read_only(tool.name), client.methods


def test_annotations():
    by_name = {t.name: t.annotations for t in ALL}
    assert by_name["list_vms"].readOnlyHint is True
    assert by_name["list_vms"].destructiveHint is False
    assert by_name["start_vm"].readOnlyHint is False
    assert by_name["start_vm"].destructiveHint is False
    for name in ("delete_vm", "wipe_disk", "rollback_vm_snapshot", "vm_agent_exec"):
        assert by_name[name].readOnlyHint is False
        assert by_name[name].destructiveHint is True


@pytest.mark.parametrize("value", [None, "", "all", " ALL ", "qemu,all"])
def test_all_toolsets_by_default(value):
    assert registry.parse_toolsets(value) == list(registry.TOOLSETS)


def test_toolsets_keep_registry_order_and_accept_aliases():
    assert registry.parse_toolsets("storage, vms ,containers,qemu") == ["qemu", "lxc", "storage"]


def test_unknown_toolset_is_an_error():
    with pytest.raises(ValueError, match="Unknown PROXMOX_TOOLSETS value.*qmeu"):
        registry.parse_toolsets("qemu,qmeu")


def test_toolsets_limit_tools():
    tools, handlers = registry.build(["pools"], read_only=False)
    assert {t.name for t in tools} == {d["name"] for d in registry.TOOLSETS["pools"].TOOLS}
    assert set(handlers) == {t.name for t in tools}


def test_read_only_mode_hides_writes():
    tools, handlers = registry.build(list(registry.TOOLSETS), read_only=True)
    assert tools
    assert all(t.annotations.readOnlyHint for t in tools)
    assert "list_vms" in handlers and "delete_vm" not in handlers
    assert len(tools) == sum(registry.is_read_only(t.name) for t in ALL)


def test_agent_card_matches_registry():
    """agent-card.json lists every tool once, with the same labels, and the package version."""
    import json
    import re
    from pathlib import Path

    root = Path(__file__).parent.parent
    card = json.loads((root / "agent-card.json").read_text())
    caps = {c["name"]: c for s in card["skills"] for c in s["capabilities"]}
    assert set(caps) == {t.name for t in ALL}
    for t in ALL:
        assert caps[t.name]["read_only"] == t.annotations.readOnlyHint, t.name
        assert caps[t.name]["destructive"] == t.annotations.destructiveHint, t.name
    version = re.search(r'^version = "(.+)"', (root / "pyproject.toml").read_text(), re.M)[1]
    assert card["version"] == version
