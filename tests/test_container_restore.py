"""restore_container_backup: the restore flag, disk overrides, and protected guests."""

import json
import urllib.parse

import httpx
import pytest

from proxmox_mcp import guards, server
from proxmox_mcp.client import ProxmoxClient
from proxmox_mcp.tools import storage

ARCHIVE = "nas:backup/vzdump-lxc-120-2026_11_01-02_00_00.tar.zst"


@pytest.fixture
def sent(monkeypatch):
    """A real ProxmoxClient over a fake transport: (method, path, form) for every request."""
    requests = []

    def answer(request):
        form = dict(urllib.parse.parse_qsl(request.content.decode())) if request.content else {}
        requests.append((request.method, request.url.path, form))
        return httpx.Response(200, json={"data": "UPID:pve:1:2:3:vzrestore:120:root@pam:"})

    client = ProxmoxClient()
    client.base_url = "https://pve.test:8006/api2/json"
    client.token = "PVEAPIToken=test"
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    monkeypatch.setattr(server, "proxmox", client)
    monkeypatch.setattr(server, "PROTECTED", frozenset({100}))
    return requests


async def call(name, args):
    result = await server.call_tool(name, args)
    return result.is_error, json.loads(result.content[0].text)


async def test_restore_is_marked_as_a_restore(sent):
    failed, body = await call(
        "restore_container_backup",
        {"node": "pve", "vmid": 120, "ostemplate": ARCHIVE, "storage": "local-lvm", "unique": True},
    )
    assert not failed, body
    method, path, form = sent[0]
    assert (method, path) == ("POST", "/api2/json/nodes/pve/lxc")
    # unique is only accepted on a restore, so it failed before restore=1 was sent.
    assert form == {
        "vmid": "120",
        "ostemplate": ARCHIVE,
        "storage": "local-lvm",
        "unique": "1",
        "restore": "1",
    }


async def test_disk_overrides_are_sent_as_given(sent):
    failed, body = await call(
        "restore_container_backup",
        {
            "node": "pve",
            "vmid": 120,
            "ostemplate": ARCHIVE,
            "storage": "local-lvm",
            "rootfs": "16",
            "mp0": "local-lvm:100,mp=/data",
            "mp12": "nas:500,mp=/media,backup=0",
        },
    )
    assert not failed, body
    form = sent[0][2]
    assert form["rootfs"] == "16" and form["restore"] == "1"
    assert form["mp0"] == "local-lvm:100,mp=/data"
    assert form["mp12"] == "nas:500,mp=/media,backup=0"


async def test_mount_points_without_rootfs_are_refused_before_any_request(sent):
    failed, body = await call(
        "restore_container_backup",
        {"node": "pve", "vmid": 120, "ostemplate": ARCHIVE, "mp0": "local-lvm:100,mp=/data"},
    )
    assert failed and "need rootfs" in body["error"]
    assert sent == []


async def test_restoring_over_a_protected_container_is_refused(sent):
    failed, body = await call(
        "restore_container_backup",
        {"node": "pve", "vmid": 100, "ostemplate": ARCHIVE, "force": True},
    )
    assert failed and "protected" in body["error"]
    assert sent == []


async def test_restoring_from_a_protected_guests_backup_is_allowed(sent):
    # Reading guest 100's backup into a new container leaves guest 100 as it is.
    archive = "nas:backup/vzdump-lxc-100-2026_11_01-02_00_00.tar.zst"
    failed, body = await call(
        "restore_container_backup", {"node": "pve", "vmid": 120, "ostemplate": archive}
    )
    assert not failed, body


@pytest.mark.parametrize(
    "name,args",
    [
        # Each would attach (or import) protected guest 100's disk to another guest.
        (
            "restore_container_backup",
            {
                "vmid": 120,
                "ostemplate": ARCHIVE,
                "rootfs": "local-lvm:16",
                "mp0": "local-lvm:vm-100-disk-1,mp=/data",
            },
        ),
        (
            "restore_container_backup",
            {"vmid": 120, "ostemplate": ARCHIVE, "rootfs": "local-zfs:subvol-100-disk-0"},
        ),
        ("set_container_config", {"vmid": 121, "mp0": "local-lvm:vm-100-disk-1,mp=/data"}),
        ("set_vm_config", {"vmid": 130, "scsi1": "local-lvm:vm-100-disk-0"}),
        (
            "set_vm_config",
            {"vmid": 130, "virtio2": "local-lvm:0,import-from=local-lvm:vm-100-disk-0"},
        ),
        ("create_vm", {"vmid": 131, "extra_config": {"efidisk0": "local-lvm:vm-100-disk-2"}}),
    ],
)
def test_disks_of_protected_guests_cant_be_attached(name, args):
    with pytest.raises(PermissionError, match="protected"):
        guards.check(name, {"node": "pve", **args}, frozenset({100}))


@pytest.mark.parametrize(
    "name,args",
    [
        (
            "restore_container_backup",
            {
                "vmid": 120,
                "ostemplate": ARCHIVE,
                "rootfs": "local-lvm:16",
                "mp0": "local-lvm:100,mp=/data",
            },
        ),
        ("set_container_config", {"vmid": 121, "mp0": "local-lvm:vm-101-disk-1,mp=/data"}),
        ("set_vm_config", {"vmid": 130, "scsi0": "local-lvm:vm-130-disk-0,discard=on"}),
        (
            "set_vm_config",
            {"vmid": 130, "description": "copied from vm-100-disk-0"},
        ),  # not a disk input
    ],
)
def test_other_disks_are_allowed(name, args):
    guards.check(name, {"node": "pve", **args}, frozenset({100}))


def test_schema_offers_rootfs_and_mount_points():
    [tool] = [t for t in storage.TOOLS if t["name"] == "restore_container_backup"]
    schema = tool["inputSchema"]
    assert {"rootfs", "mp0", "mp3"} <= set(schema["properties"])
    [pattern] = schema["patternProperties"]
    import re

    assert (
        re.search(pattern, "mp255")
        and not re.search(pattern, "mp256")
        and not re.search(pattern, "mp3")
    )
    assert "force" in tool["description"] and "rootfs" in tool["description"]
