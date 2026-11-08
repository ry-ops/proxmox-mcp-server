"""Tool arguments can't move a request to a different API endpoint."""

import json

import httpx
import pytest

from proxmox_mcp import guards, server
from proxmox_mcp.client import ProxmoxClient


@pytest.fixture
def sent(monkeypatch):
    """A real ProxmoxClient over a fake transport; the list collects every request sent."""
    requests = []
    client = ProxmoxClient()
    client.base_url = "https://pve.test:8006/api2/json"
    client.token = "PVEAPIToken=test"
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: requests.append((r.method, r.url.raw_path.decode()))
            or httpx.Response(200, json={"data": None})
        )
    )
    monkeypatch.setattr(server, "proxmox", client)
    monkeypatch.setattr(server, "PROTECTED", frozenset({100}))
    return requests


async def call(name, args):
    result = await server.call_tool(name, args)
    return result.is_error, json.loads(result.content[0].text)


@pytest.mark.parametrize(
    "name,args,why",
    [
        # Each of these reached guest 100 (protected) before the fix.
        ("stop_vm", {"node": "pve", "vmid": "999/../100"}, "whole number"),
        (
            "update_replication_job",
            {"id": "../../nodes/pve/qemu/100/config", "delete": "net0"},
            "unsafe API path",
        ),
        ("get_vm_config", {"node": "pve/qemu/100/../../../pve", "vmid": 101}, "can't contain '/'"),
        (
            "delete_storage_volume",
            {"node": "pve", "storage": "..", "volume": "x"},
            "unsafe API path",
        ),
    ],
)
async def test_redirecting_arguments_are_refused_before_any_request(sent, name, args, why):
    failed, body = await call(name, args)
    assert failed and why in body["error"]
    assert sent == []


@pytest.mark.parametrize(
    "name,args,path",
    [
        (
            "get_vm_status",
            {"node": "pve", "vmid": "101"},
            "/api2/json/nodes/pve/qemu/101/status/current",
        ),
        (
            "get_vm_status",
            {"node": "pve", "vmid": 101},
            "/api2/json/nodes/pve/qemu/101/status/current",
        ),
        (
            "delete_storage_volume",
            {"node": "pve", "storage": "nas", "volume": "nas:iso/debian.iso"},
            "/api2/json/nodes/pve/storage/nas/content/nas%3Aiso%2Fdebian.iso",
        ),
    ],
)
async def test_ordinary_arguments_still_work(sent, name, args, path):
    failed, body = await call(name, args)
    assert not failed, body
    assert sent[0][1] == path


@pytest.mark.parametrize(
    "path", ["/nodes/pve/../access", "/nodes/./pve", "/..", "/nodes/pve?x=1", "/a#b", "/a\\b"]
)
async def test_client_refuses_unsafe_paths(path):
    client = ProxmoxClient()
    with pytest.raises(PermissionError, match="unsafe API path"):
        await client.get(path)
    await client.close()


@pytest.mark.parametrize("value", [100, "100", " 100 ", 100.0, -1, None])
def test_check_args_accepts_whole_numbers(value):
    guards.check_args("stop_vm", {"vmid": value}, {"properties": {"vmid": {"type": "integer"}}})


@pytest.mark.parametrize("value", ["100/../101", "1e3", "abc", 1.5, True, [100]])
def test_check_args_refuses_other_integers(value):
    with pytest.raises(PermissionError, match="whole number"):
        guards.check_args("stop_vm", {"vmid": value}, {"properties": {"vmid": {"type": "integer"}}})
