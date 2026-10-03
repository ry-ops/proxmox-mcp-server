"""Error details from the API, fixed storage/qemu tools, and deploy_fortigate_vm."""

import json
from urllib.parse import parse_qs

import httpx
import pytest

from proxmox_mcp import client as client_mod
from proxmox_mcp.tools import appliances, qemu, storage


def make_client(monkeypatch, handler):
    monkeypatch.setattr(client_mod, "PROXMOX_HOST", "pve.test")
    monkeypatch.setattr(client_mod, "PROXMOX_READ_ONLY", False)
    c = client_mod.ProxmoxClient()
    c.token = "PVEAPIToken=u!t=v"
    c.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return c


def form(request: httpx.Request) -> dict:
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


async def test_error_includes_proxmox_reason(monkeypatch):
    c = make_client(monkeypatch, lambda r: httpx.Response(
        400, json={"data": None, "errors": {"scsi0": "invalid format - import-from: volume does not exist"}}))
    with pytest.raises(httpx.HTTPStatusError, match="scsi0: invalid format - import-from"):
        await c.post("/nodes/pve01/qemu", {"vmid": 1})


async def test_error_falls_back_to_message(monkeypatch):
    c = make_client(monkeypatch, lambda r: httpx.Response(403, json={"data": None, "message": "Permission check failed\n"}))
    with pytest.raises(httpx.HTTPStatusError, match="403 Forbidden for POST /api2/json/x: Permission check failed"):
        await c.post("/x")


async def test_download_url_uses_hyphenated_params(monkeypatch):
    seen = []
    c = make_client(monkeypatch, lambda r: seen.append(r) or httpx.Response(200, json={"data": "UPID:x"}))
    await storage.handle("download_url_to_storage", {"node": "pve01", "storage": "local", "url": "https://x/a.qcow2",
                         "content": "import", "filename": "a.qcow2", "checksum": "abc",
                         "checksum_algorithm": "sha256", "verify_certificates": False}, c)
    body = form(seen[0])
    assert body["checksum-algorithm"] == "sha256" and body["verify-certificates"] == "0"
    assert "checksum_algorithm" not in body and body["content"] == "import"


async def test_import_vm_disk_uses_import_from(monkeypatch):
    seen = []
    c = make_client(monkeypatch, lambda r: seen.append(r) or httpx.Response(200, json={"data": "UPID:x"}))
    await qemu.handle("import_vm_disk", {"node": "pve01", "vmid": 120, "source": "local:import/fw.qcow2",
                      "storage": "local-lvm", "disk": "scsi1", "options": "discard=on"}, c)
    assert seen[0].url.path == "/api2/json/nodes/pve01/qemu/120/config"
    assert form(seen[0]) == {"scsi1": "local-lvm:0,import-from=local:import/fw.qcow2,discard=on"}


async def test_create_vm_extra_config_merged(monkeypatch):
    seen = []
    c = make_client(monkeypatch, lambda r: seen.append(r) or httpx.Response(200, json={"data": "UPID:x"}))
    await qemu.handle("create_vm", {"node": "pve01", "vmid": 120, "net1": "virtio,bridge=vmbr1,tag=150",
                      "extra_config": {"net4": "virtio,bridge=vmbr2", "ciuser": "ubuntu"}}, c)
    body = form(seen[0])
    assert body["net1"] == "virtio,bridge=vmbr1,tag=150" and body["net4"] == "virtio,bridge=vmbr2"
    assert body["ciuser"] == "ubuntu" and "extra_config" not in body and "node" not in body


class DeployFake:
    """Routes the calls deploy_fortigate_vm makes and records them."""

    def __init__(self):
        self.calls = []

    def __call__(self, r: httpx.Request) -> httpx.Response:
        path = r.url.path.removeprefix("/api2/json")
        self.calls.append((r.method, path, form(r) if r.method == "POST" else None))
        if path == "/cluster/nextid":
            return httpx.Response(200, json={"data": "121"})
        if path.endswith("/status") and "/tasks/" in path:
            return httpx.Response(200, json={"data": {"status": "stopped", "exitstatus": "OK"}})
        if path.endswith("/config"):
            return httpx.Response(200, json={"data": {
                "net0": "virtio=BC:24:11:00:00:01,bridge=vmbr1,tag=145",
                "net1": "virtio=BC:24:11:00:00:02,bridge=vmbr1,tag=150"}})
        return httpx.Response(200, json={"data": "UPID:pve01:task"})


async def test_deploy_fortigate_vm_from_url(monkeypatch):
    fake = DeployFake()
    c = make_client(monkeypatch, fake)
    out = await appliances.handle("deploy_fortigate_vm", {
        "node": "pve01", "image_url": "http://mac:8765/fortios.qcow2", "wan_bridge": "vmbr1", "wan_vlan": 145,
        "lan_bridge": "vmbr1", "lan_vlan": 150, "log_disk_gb": 8}, c)
    posts = [(p, b) for m, p, b in fake.calls if m == "POST"]
    assert posts[0] == ("/nodes/pve01/storage/local/download-url",
                        {"url": "http://mac:8765/fortios.qcow2", "content": "import", "filename": "fortios.qcow2"})
    create = posts[1][1]
    assert posts[1][0] == "/nodes/pve01/qemu" and create["vmid"] == "121"
    assert create["scsi0"] == "local-lvm:0,import-from=local:import/fortios.qcow2"
    assert create["net0"] == "virtio,bridge=vmbr1,tag=145" and create["net1"] == "virtio,bridge=vmbr1,tag=150"
    assert create["cores"] == "1" and create["memory"] == "2048" and create["scsi1"] == "local-lvm:8"
    assert posts[2][0] == "/nodes/pve01/qemu/121/status/start"
    assert out["ports"] == [
        {"port": "port1", "nic": "net0", "mac": "bc:24:11:00:00:01", "bridge": "vmbr1", "vlan": 145},
        {"port": "port2", "nic": "net1", "mac": "bc:24:11:00:00:02", "bridge": "vmbr1", "vlan": 150}]
    assert "warnings" not in out


async def test_deploy_fortigate_vm_validation_and_warnings(monkeypatch):
    fake = DeployFake()
    c = make_client(monkeypatch, fake)
    with pytest.raises(ValueError, match="exactly one"):
        await appliances.handle("deploy_fortigate_vm", {"node": "pve01"}, c)
    with pytest.raises(ValueError, match="disk image"):
        await appliances.handle("deploy_fortigate_vm", {"node": "pve01", "image_url": "https://x/FGT_VM64_KVM.out.kvm.zip"}, c)
    assert fake.calls == []
    out = await appliances.handle("deploy_fortigate_vm", {
        "node": "pve01", "image": "local:import/fortios.qcow2", "cores": 2, "memory": 4096,
        "lan_bridge": "vmbr1", "extra_nics": ["vmbr1:160", "vmbr2"], "start": False}, c)
    assert len(out["warnings"]) == 2
    assert not any(p.endswith("/status/start") for _, p, _ in fake.calls)


async def test_wait_task_raises_on_failure(monkeypatch):
    c = make_client(monkeypatch, lambda r: httpx.Response(200, json={"data": {"status": "stopped", "exitstatus": "import failed"}}))
    with pytest.raises(RuntimeError, match="import failed"):
        await appliances.wait_task(c, "pve01", "UPID:x")


def test_tool_count():
    from proxmox_mcp import server
    assert "deploy_fortigate_vm" in {t.name for t in server.ALL_TOOLS}
    assert json.dumps(appliances.TOOLS)  # schema is JSON-serialisable
