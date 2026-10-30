"""The MCP protocol handlers, driven in-process by the SDK client in both protocol eras."""

import json

import pytest
from mcp import Client

from proxmox_mcp import server

UPID = "UPID:pve:0003A1B2:01C9D3E4:6720F0A1:qmstart:101:root@pam:"


class FakeProxmox:
    async def get(self, path, params=None):
        if path.endswith("/status") and "/tasks/" in path:
            return {"data": {"status": "stopped", "exitstatus": "OK"}}
        return {"data": [{"node": "pve1"}]}

    async def post(self, path, data=None):
        return {"data": UPID}

    put = post
    delete = post


@pytest.fixture(params=["auto", "legacy"])
def connect(request, monkeypatch):
    """Opens a client in the test's own task (anyio scopes can't cross tasks)."""
    monkeypatch.setattr(server, "proxmox", FakeProxmox())
    monkeypatch.setattr(server, "PROTECTED", frozenset({100}))
    return lambda: Client(server.app, mode=request.param)


async def test_tools(connect):
    async with connect() as client:
        tools = (await client.list_tools()).tools
        assert len(tools) == len(server.ALL_TOOLS)
        by_name = {t.name: t for t in tools}
        assert by_name["delete_vm"].annotations.destructive_hint is True
        assert "wait" in by_name["clone_vm"].input_schema["properties"]


async def test_call_tool_success_and_wait(connect):
    async with connect() as client:
        result = await client.call_tool("start_vm", {"node": "pve", "vmid": 101, "wait": True})
        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["data"] == UPID and payload["task"]["ok"] is True


async def test_call_tool_errors_set_is_error(connect):
    async with connect() as client:
        refused = await client.call_tool("delete_vm", {"node": "pve", "vmid": 100})
        assert refused.is_error is True
        assert "protected" in json.loads(refused.content[0].text)["error"]
        unknown = await client.call_tool("format_all_disks", {})
        assert unknown.is_error is True


async def test_prompts(connect):
    async with connect() as client:
        names = {p.name for p in (await client.list_prompts()).prompts}
        assert "cluster_health_check" in names
        got = await client.get_prompt("safe_change", {"vmid": "120", "change": "add memory"})
        assert "guest 120: add memory" in got.messages[0].content.text


async def test_resources(connect):
    async with connect() as client:
        uris = {str(r.uri) for r in (await client.list_resources()).resources}
        assert "proxmox://cluster/resources" in uris
        templates = {
            t.uri_template for t in (await client.list_resource_templates()).resource_templates
        }
        assert "proxmox://vms/{node}/{vmid}/config" in templates
        read = await client.read_resource("proxmox://nodes")
        assert json.loads(read.contents[0].text) == {"data": [{"node": "pve1"}]}
