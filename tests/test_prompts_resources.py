"""MCP prompts and resources."""

import json
import re

import pytest
from pydantic import AnyUrl

from proxmox_mcp import prompts, registry, resources, server

ALL, _ = registry.build(list(registry.TOOLSETS), read_only=False)
TOOL_NAMES = {t.name for t in ALL}
FULL_ARGS = {"vmid": "120", "change": "add 4 GB of memory", "hours": "6", "threshold_percent": "90"}


@pytest.mark.parametrize("spec", prompts.SPECS, ids=lambda s: s.name)
def test_prompts_only_name_real_tools(spec):
    text = prompts.get_prompt(spec.name, FULL_ARGS).messages[0].content.text
    named = set(re.findall(r"`([a-z]+(?:_[a-z]+)+)`", text))
    assert named, "a prompt should point at tools"
    assert named <= TOOL_NAMES, named - TOOL_NAMES


def test_prompt_arguments_are_used_and_required():
    text = prompts.get_prompt("safe_change", {"vmid": "120", "change": "add 4 GB of memory"}).messages[0].content.text
    assert "guest 120: add 4 GB of memory" in text
    assert "above 90%" in prompts.get_prompt("capacity_report", {"threshold_percent": "90"}).messages[0].content.text
    assert "above 80%" in prompts.get_prompt("capacity_report", None).messages[0].content.text
    with pytest.raises(ValueError, match="needs: vmid, change"):
        prompts.get_prompt("safe_change", {})
    with pytest.raises(ValueError, match="Unknown prompt"):
        prompts.get_prompt("rm_rf", {})


def test_list_prompts():
    listed = {p.name: p for p in prompts.list_prompts()}
    assert set(listed) == {s.name for s in prompts.SPECS}
    assert [a.name for a in listed["decommission_guest"].arguments if a.required] == ["vmid"]


@pytest.mark.parametrize(
    "uri,path",
    [
        ("proxmox://cluster/resources", "/cluster/resources"),
        ("proxmox://nodes", "/nodes"),
        ("proxmox://nodes/pve-1.lan/status", "/nodes/pve-1.lan/status"),
        ("proxmox://vms/pve1/120/config", "/nodes/pve1/qemu/120/config"),
        ("proxmox://cts/pve1/210/config", "/nodes/pve1/lxc/210/config"),
    ],
)
def test_resource_paths(uri, path):
    assert resources.api_path(uri) == path


@pytest.mark.parametrize(
    "uri",
    [
        "proxmox://vms/pve1/120/../../../access/users/config",
        "proxmox://nodes/../access/status",
        "proxmox://vms/pve1/12/config",
        "proxmox://vms/pve1/abc/config",
        "proxmox://nodes/pve%2F..%2Faccess/status",
        "proxmox://cluster/secrets",
    ],
)
def test_resource_paths_reject_anything_else(uri):
    with pytest.raises(ValueError, match="Unknown resource"):
        resources.api_path(uri)


class FakeProxmox:
    def __init__(self):
        self.calls = []

    async def get(self, path, params=None):
        self.calls.append(path)
        return {"data": [{"node": "pve1", "status": "online"}]}


async def test_read_resource_through_server(monkeypatch):
    fake = FakeProxmox()
    monkeypatch.setattr(server, "proxmox", fake)
    [content] = await server.read_resource(AnyUrl("proxmox://nodes"))
    assert content.mime_type == "application/json"
    assert json.loads(content.content) == {"data": [{"node": "pve1", "status": "online"}]}
    assert fake.calls == ["/nodes"]
