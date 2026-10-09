"""deploy_cloud_vms: cloud-image VMs with cloud-init, ready for a cluster."""

from urllib.parse import parse_qs, unquote

import httpx
import pytest

from proxmox_mcp import client as client_mod
from proxmox_mcp.tools import appliances

KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIexample user@host"


def make_client(monkeypatch, handler):
    monkeypatch.setattr(client_mod, "PROXMOX_HOST", "pve.test")
    monkeypatch.setattr(client_mod, "PROXMOX_READ_ONLY", False)
    c = client_mod.ProxmoxClient()
    c.token = "PVEAPIToken=u!t=v"
    c.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return c


class CloudFake:
    """Routes the calls deploy_cloud_vms makes and records them."""

    def __init__(self, existing=()):
        self.calls = []
        self.existing = list(existing)

    def __call__(self, r: httpx.Request) -> httpx.Response:
        path = r.url.path.removeprefix("/api2/json")
        body = {k: v[0] for k, v in parse_qs(r.content.decode()).items()} if r.method in ("POST", "PUT") else None
        self.calls.append((r.method, path, body))
        if path == "/cluster/resources":
            return httpx.Response(200, json={"data": self.existing})
        if path == "/cluster/nextid":
            return httpx.Response(200, json={"data": "130"})
        if "/tasks/" in path:
            return httpx.Response(200, json={"data": {"status": "stopped", "exitstatus": "OK"}})
        if path.endswith("/config"):
            vmid = path.split("/")[-2]
            return httpx.Response(200, json={"data": {"net0": f"virtio=BC:24:11:00:01:{int(vmid) - 100:02X},bridge=vmbr1,tag=145"}})
        if path.endswith("/resize"):
            return httpx.Response(200, json={"data": None})  # synchronous on some versions
        return httpx.Response(200, json={"data": "UPID:pve01:task"})

    def creates(self):
        return [b for m, p, b in self.calls if m == "POST" and p == "/nodes/pve01/qemu"]


async def test_three_static_vms(monkeypatch):
    fake = CloudFake()
    c = make_client(monkeypatch, fake)
    out = await appliances.handle("deploy_cloud_vms", {
        "node": "pve01", "names": ["t-1", "t-2", "t-3"], "image": "local:import/noble.qcow2",
        "ip_addresses": ["10.0.0.21/24", "10.0.0.22/24", "10.0.0.23/24"], "gateway": "10.0.0.1",
        "nameserver": "10.0.0.1", "ssh_public_keys": KEY, "bridge": "vmbr1", "vlan": 145}, c)

    creates = fake.creates()
    assert [b["vmid"] for b in creates] == ["130", "131", "132"]
    first = creates[0]
    assert first["scsi0"] == "local-lvm:0,import-from=local:import/noble.qcow2,discard=on"
    assert first["ide2"] == "local-lvm:cloudinit" and first["agent"] == "enabled=1"
    assert first["net0"] == "virtio,bridge=vmbr1,tag=145"
    assert first["ipconfig0"] == "ip=10.0.0.21/24,gw=10.0.0.1" and first["nameserver"] == "10.0.0.1"
    assert first["ciuser"] == "ubuntu" and unquote(first["sshkeys"]) == KEY and " " not in first["sshkeys"]
    resizes = [(p, b) for m, p, b in fake.calls if m == "PUT"]
    assert resizes[0] == ("/nodes/pve01/qemu/130/resize", {"disk": "scsi0", "size": "20G"})
    starts = [p for m, p, _ in fake.calls if m == "POST" and p.endswith("/status/start")]
    assert len(starts) == 3

    assert [(v["vmid"], v["name"], v["ip"]) for v in out["vms"]] == [
        (130, "t-1", "10.0.0.21"), (131, "t-2", "10.0.0.22"), (132, "t-3", "10.0.0.23")]
    assert out["vms"][0]["mac"] == "bc:24:11:00:01:1e" and "note" not in out


async def test_dhcp_without_start(monkeypatch):
    fake = CloudFake()
    c = make_client(monkeypatch, fake)
    out = await appliances.handle("deploy_cloud_vms", {
        "node": "pve01", "names": ["d-1"], "image": "local:import/noble.qcow2", "ssh_public_keys": KEY,
        "first_vmid": 140, "start": False}, c)
    assert fake.creates()[0]["ipconfig0"] == "ip=dhcp" and fake.creates()[0]["vmid"] == "140"
    assert not any(p.endswith("/status/start") for _, p, _ in fake.calls)
    assert out["vms"][0]["ip"] is None and "DHCP" in out["note"]


@pytest.mark.parametrize("args, match", [
    ({"names": []}, "at least one"),
    ({"names": ["a", "a"]}, "unique"),
    ({"names": ["a"], "ssh_public_keys": ""}, "ssh_public_keys"),
    ({"names": ["a", "b"], "ip_addresses": ["10.0.0.1/24"]}, "1 entries for 2"),
    ({"names": ["a"], "ip_addresses": ["10.0.0.1"]}, "prefix length"),
    ({"names": ["a"], "ip_addresses": ["10.0.0.300/24"]}, "does not appear to be"),
])
async def test_validation_before_any_call(monkeypatch, args, match):
    fake = CloudFake()
    c = make_client(monkeypatch, fake)
    base = {"node": "pve01", "image": "local:import/noble.qcow2", "ssh_public_keys": KEY}
    with pytest.raises(ValueError, match=match):
        await appliances.handle("deploy_cloud_vms", {**base, **args}, c)
    assert fake.calls == []


async def test_refuses_existing_names_and_vmids(monkeypatch):
    fake = CloudFake(existing=[{"vmid": 110, "name": "k3s-master"}, {"vmid": 131, "name": "other"}])
    c = make_client(monkeypatch, fake)
    base = {"node": "pve01", "image": "local:import/noble.qcow2", "ssh_public_keys": KEY}
    with pytest.raises(ValueError, match="already named k3s-master"):
        await appliances.handle("deploy_cloud_vms", {**base, "names": ["k3s-master"]}, c)
    with pytest.raises(ValueError, match="VMIDs 131 are in use"):
        await appliances.handle("deploy_cloud_vms", {**base, "names": ["x-1", "x-2"]}, c)
    assert fake.creates() == []


def test_registered():
    from proxmox_mcp import server
    assert {"deploy_cloud_vms", "deploy_fortigate_vm"} <= {t.name for t in server.ALL_TOOLS}
