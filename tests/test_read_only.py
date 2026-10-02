"""PROXMOX_READ_ONLY blocks every non-GET request before it reaches the network."""

import httpx
import pytest

from proxmox_mcp import client as client_mod


@pytest.fixture
def proxmox(monkeypatch):
    sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.method)
        return httpx.Response(200, json={"data": None})

    monkeypatch.setattr(client_mod, "PROXMOX_HOST", "pve.test")
    c = client_mod.ProxmoxClient()
    c.token = "PVEAPIToken=u!t=v"
    c.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return c, sent


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
async def test_read_only_blocks_writes(monkeypatch, proxmox, method):
    c, sent = proxmox
    monkeypatch.setattr(client_mod, "PROXMOX_READ_ONLY", True)
    with pytest.raises(PermissionError, match="Read-only mode"):
        await c.request(method, "/nodes/pve/qemu/100/status/start")
    assert sent == []


async def test_read_only_allows_get(monkeypatch, proxmox):
    c, sent = proxmox
    monkeypatch.setattr(client_mod, "PROXMOX_READ_ONLY", True)
    await c.get("/nodes")
    assert sent == ["GET"]


async def test_writes_allowed_by_default(monkeypatch, proxmox):
    c, sent = proxmox
    monkeypatch.setattr(client_mod, "PROXMOX_READ_ONLY", False)
    await c.post("/nodes/pve/qemu/100/status/start")
    assert sent == ["POST"]
