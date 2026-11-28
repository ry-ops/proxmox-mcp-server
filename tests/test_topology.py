"""get_cluster_topology: one graph of hosts, interfaces, bridges, guests and storage."""

import httpx
import pytest

from proxmox_mcp import server, topology
from proxmox_mcp.client import ProxmoxClient

DATA = {
    "/cluster/status": [
        {"type": "cluster", "name": "lab", "quorate": 1, "nodes": 2},
        {"type": "node", "name": "pve1", "ip": "10.0.0.11"},
        {"type": "node", "name": "pve2", "ip": "10.0.0.12"},
    ],
    "/cluster/resources": [
        {"type": "node", "node": "pve1", "status": "online", "maxcpu": 8, "maxmem": 34359738368},
        {"type": "node", "node": "pve2", "status": "offline"},
        {
            "type": "qemu",
            "node": "pve1",
            "vmid": 100,
            "name": "fw",
            "status": "running",
            "tags": "edge",
        },
        {"type": "lxc", "node": "pve1", "vmid": 101, "name": "dns", "status": "stopped"},
        {"type": "qemu", "node": "pve1", "vmid": 102, "name": "app", "status": "running"},
        {
            "type": "storage",
            "node": "pve1",
            "storage": "local-lvm",
            "status": "available",
            "disk": 1,
            "maxdisk": 10,
        },
        {"type": "storage", "node": "pve1", "storage": "ceph", "status": "available"},
    ],
    "/storage": [
        {"storage": "local-lvm", "type": "lvmthin"},
        {"storage": "ceph", "type": "rbd", "shared": 1},
    ],
    "/cluster/sdn/vnets": [{"vnet": "web", "zone": "evpn1", "tag": 1000}],
    "/cluster/ha/resources": [{"sid": "vm:100"}],
    "/nodes/pve1/network": [
        {"iface": "eno1", "type": "eth", "active": 1},
        {"iface": "eno2", "type": "eth", "active": 1},
        {
            "iface": "bond0",
            "type": "bond",
            "slaves": "eno1 eno2",
            "bond_mode": "802.3ad",
            "active": 1,
        },
        {
            "iface": "vmbr0",
            "type": "bridge",
            "bridge_ports": "bond0",
            "bridge_vlan_aware": 1,
            "cidr": "10.0.0.11/24",
            "active": 1,
        },
        {"iface": "vmbr0.20", "type": "vlan", "cidr": "10.0.20.11/24", "active": 1},
    ],
    "/nodes/pve1/qemu/100/config": {
        "ostype": "l26",
        "net0": "virtio=BC:24:11:00:00:01,bridge=vmbr0,tag=10,firewall=1",
        "net1": "e1000=BC:24:11:00:00:02,bridge=vmbr0,tag=20,link_down=1",
        "scsi0": "local-lvm:vm-100-disk-0,iothread=1,size=32G",
        "ide2": "local:iso/x.iso,media=cdrom",
        "efidisk0": "local-lvm:vm-100-disk-1,efitype=4m,size=4M",
    },
    "/nodes/pve1/lxc/101/config": {
        "ostype": "debian",
        "net0": "name=eth0,bridge=vmbr0,hwaddr=BC:24:11:00:00:03,ip=10.0.0.53/24,gw=10.0.0.1,type=veth",
        "rootfs": "ceph:vm-101-disk-0,size=8G",
        "mp0": "/srv/data,mp=/data",
    },
    "/nodes/pve1/qemu/102/config": {
        "net0": "virtio=BC:24:11:00:00:04,bridge=web",
        "scsi0": "ceph:vm-102-disk-0,size=16G",
    },
}


@pytest.fixture
def requests(monkeypatch):
    seen = []

    def answer(request):
        path = request.url.raw_path.decode().split("?")[0].removeprefix("/api2/json")
        seen.append((request.method, path))
        if path in DATA:
            return httpx.Response(200, json={"data": DATA[path]})
        return httpx.Response(501, json={"data": None})

    client = ProxmoxClient()
    client.base_url = "https://pve.test:8006/api2/json"
    client.token = "PVEAPIToken=test"
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    monkeypatch.setattr(server, "proxmox", client)
    return seen


async def call(args=None):
    import json

    result = await server.call_tool("get_cluster_topology", args or {})
    assert not result.is_error, result.content[0].text
    return json.loads(result.content[0].text)


def edge(graph, source, target, kind):
    return [
        e
        for e in graph["edges"]
        if e["source"] == source and e["target"] == target and e["kind"] == kind
    ]


async def test_reads_only_and_skips_offline_nodes(requests):
    await call()
    assert {m for m, _ in requests} == {"GET"}
    assert not any(p.startswith("/nodes/pve2") for _, p in requests)


async def test_graph_wires_hosts_bonds_bridges_and_vlans(requests):
    g = await call()
    assert g["summary"] == {
        "cluster": "lab",
        "hosts": 2,
        "guests": 3,
        "bridges": 1,
        "storage": 2,
        "vnets": 1,
        "vlans": [10, 20],
    }
    assert edge(g, "cluster/lab", "node/pve1", "member")
    assert edge(g, "bridge/pve1/vmbr0", "iface/pve1/bond0", "port")
    assert edge(g, "iface/pve1/bond0", "iface/pve1/eno1", "bond_member")
    assert edge(g, "bridge/pve1/vmbr0", "iface/pve1/vmbr0.20", "vlan")[0]["vlan"] == 20
    bridge = next(n for n in g["nodes"] if n["id"] == "bridge/pve1/vmbr0")
    assert bridge["vlan_aware"] is True and bridge["cidr"] == "10.0.0.11/24"


async def test_guest_nics_disks_and_ha(requests):
    g = await call()
    fw = next(n for n in g["nodes"] if n["id"] == "qemu/100")
    assert fw["ha"] is True and fw["tags"] == "edge"
    assert [d["disk"] for d in fw["disks"]] == ["efidisk0", "scsi0"]  # the CD-ROM is not a disk
    nics = edge(g, "qemu/100", "bridge/pve1/vmbr0", "nic")
    assert [(e["nic"], e["vlan"], e["mac"]) for e in nics] == [
        ("net0", 10, "bc:24:11:00:00:01"),
        ("net1", 20, "bc:24:11:00:00:02"),
    ]
    assert nics[0]["firewall"] is True and nics[1]["link_down"] is True
    assert [e["size"] for e in edge(g, "qemu/100", "storage/pve1/local-lvm", "disk")] == [
        "4M",
        "32G",
    ]
    dns = next(n for n in g["nodes"] if n["id"] == "lxc/101")
    assert dns["nics"][0]["ip"] == "10.0.0.53/24" and dns["nics"][0]["name"] == "eth0"
    assert [d["disk"] for d in dns["disks"]] == ["rootfs"]  # a bind mount has no storage
    assert edge(g, "lxc/101", "storage/ceph", "disk")  # shared storage has one cluster-wide id


async def test_guest_on_an_sdn_vnet_links_to_the_vnet(requests):
    g = await call()
    assert edge(g, "qemu/102", "vnet/web", "nic")
    assert next(n for n in g["nodes"] if n["id"] == "vnet/web")["vlan"] == 1000


async def test_filters(requests):
    g = await call({"include_stopped": False, "include_storage": False})
    ids = {n["id"] for n in g["nodes"]}
    assert "lxc/101" not in ids and not any(i.startswith("storage/") for i in ids)
    assert not any(e["kind"] == "disk" for e in g["edges"])
    g = await call({"node": "pve2"})
    assert g["summary"]["hosts"] == 1 and g["summary"]["guests"] == 0


async def test_missing_sdn_and_ha_are_not_errors(requests, monkeypatch):
    monkeypatch.delitem(DATA, "/cluster/sdn/vnets")
    monkeypatch.delitem(DATA, "/cluster/ha/resources")
    g = await call()
    assert g["summary"]["vnets"] == 0
    assert edge(g, "qemu/102", "bridge/pve1/web", "nic") == []  # dangling edges are dropped


async def test_mermaid(requests):
    out = await call({"format": "mermaid"})
    m = out["mermaid"]
    assert m.startswith("flowchart TB")
    assert 'subgraph node_pve1_box["pve1"]' in m
    assert "qemu_100 -->|VLAN 10| bridge_pve1_vmbr0" in m
    assert "lxc_101 -->|untagged| bridge_pve1_vmbr0" in m
    assert out["summary"]["guests"] == 3


def test_nic_and_disk_parsers():
    nic = topology.parse_guest_nic(
        "net0", "virtio=AA:BB:CC:DD:EE:FF,bridge=vmbr1,tag=145,trunks=10;20", "qemu"
    )
    assert nic == {
        "nic": "net0",
        "bridge": "vmbr1",
        "mac": "aa:bb:cc:dd:ee:ff",
        "model": "virtio",
        "vlan": 145,
        "trunks": "10;20",
    }
    assert topology.parse_guest_disk("ide2", "none,media=cdrom") is None
    assert topology.parse_guest_disk("scsi1", "/dev/disk/by-id/nvme-x,size=1T") is None
    assert topology.parse_guest_disk("unused0", "local-lvm:vm-100-disk-9") == {
        "disk": "unused0",
        "storage": "local-lvm",
        "volume": "vm-100-disk-9",
    }
