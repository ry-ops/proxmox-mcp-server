"""wait / wait_for_task, protected guests, and compact output."""

import json

import pytest

from proxmox_mcp import guards, server, tasks

UPID = "UPID:pve2:0003A1B2:01C9D3E4:6720F0A1:qmclone:9000:root@pam:"


class FakeProxmox:
    """Answers task status from a script of states, and records every request."""

    def __init__(self, states=(), log=()):
        self.states = list(states) or [{"status": "stopped", "exitstatus": "OK"}]
        self.log = [{"n": i, "t": line} for i, line in enumerate(log, 1)]
        self.calls = []

    async def get(self, path, params=None):
        self.calls.append(("GET", path))
        if path.endswith("/status"):
            return {"data": self.states.pop(0) if len(self.states) > 1 else self.states[0]}
        if path.endswith("/log"):
            return {"data": self.log}
        return {"data": []}

    async def post(self, path, data=None):
        self.calls.append(("POST", path))
        return {"data": UPID}

    put = post
    delete = post


# --- tasks ---


def test_upid_node():
    assert tasks.upid_node(UPID) == "pve2"
    with pytest.raises(ValueError, match="Not a Proxmox task ID"):
        tasks.upid_node("pve2:1234")


async def test_wait_reports_success():
    fake = FakeProxmox([{"status": "running"}, {"status": "stopped", "exitstatus": "OK"}])
    result = await tasks.wait(fake, UPID, timeout=5, poll=0.01)
    assert result == {"upid": UPID, "node": "pve2", "status": "stopped", "exitstatus": "OK", "ok": True}
    assert fake.calls[0] == ("GET", f"/nodes/pve2/tasks/{UPID}/status")


async def test_wait_reports_failure_with_log_tail():
    log = [f"line {i}" for i in range(30)] + ["TASK ERROR: storage 'nvme' does not exist"]
    fake = FakeProxmox([{"status": "stopped", "exitstatus": "storage 'nvme' does not exist"}], log)
    result = await tasks.wait(fake, UPID, timeout=5, poll=0.01)
    assert result["ok"] is False
    assert len(result["log_tail"]) == tasks.LOG_TAIL
    assert result["log_tail"][-1].startswith("TASK ERROR")


async def test_wait_returns_running_on_timeout():
    fake = FakeProxmox([{"status": "running"}])
    result = await tasks.wait(fake, UPID, timeout=0.05, poll=0.01)
    assert result["status"] == "running" and result["ok"] is None
    assert "wait_for_task" in result["note"]


# --- protected guests ---


def test_parse_protected():
    assert guards.parse_protected("100, 101,9000-9002") == {100, 101, 9000, 9001, 9002}
    assert guards.parse_protected("") == frozenset()
    for bad in ("abc", "10-5", "100-"):
        with pytest.raises(ValueError, match="PROXMOX_PROTECTED_VMIDS"):
            guards.parse_protected(bad)


@pytest.mark.parametrize(
    "name,args",
    [
        ("stop_vm", {"node": "pve", "vmid": 100}),
        ("delete_container", {"node": "pve", "vmid": "100"}),
        ("vm_agent_exec", {"node": "pve", "vmid": 100, "command": ["id"]}),
        ("clone_vm", {"node": "pve", "vmid": 9000, "newid": 100}),
        ("move_vm_disk", {"node": "pve", "vmid": 5, "disk": "scsi0", "target-vmid": 100}),
        ("bulk_shutdown_guests", {"vms": "200,100"}),
        ("node_stopall", {"node": "pve", "vms": "100"}),
        ("delete_ha_resource", {"sid": "vm:100"}),
        ("delete_storage_volume", {"node": "pve", "storage": "local-lvm", "volume": "local-lvm:vm-100-disk-0"}),
        ("delete_storage_volume", {"node": "pve", "storage": "nas", "volume": "nas:backup/vzdump-qemu-100-2026_10_30-01_00_00.vma.zst"}),
    ],
)
def test_protected_guest_is_refused(name, args):
    with pytest.raises(PermissionError, match="protected"):
        guards.check(name, args, frozenset({100}))


@pytest.mark.parametrize(
    "name,args",
    [
        ("stop_vm", {"node": "pve", "vmid": 101}),
        ("clone_vm", {"node": "pve", "vmid": 100, "newid": 123}),  # cloning from it is fine
        ("backup_vm", {"node": "pve", "vmid": 100}),
        ("get_vm_vnc_proxy", {"node": "pve", "vmid": 100}),
        ("delete_storage_volume", {"node": "pve", "storage": "local-lvm", "volume": "local-lvm:vm-1001-disk-0"}),
        ("bulk_start_guests", {"vms": "101,102"}),
    ],
)
def test_other_guests_are_allowed(name, args):
    guards.check(name, args, frozenset({100}))


def test_node_wide_actions_need_a_list_when_guests_are_protected():
    with pytest.raises(PermissionError, match="without a 'vms' list"):
        guards.check("node_stopall", {"node": "pve"}, frozenset({100}))
    guards.check("node_stopall", {"node": "pve"}, frozenset())  # no protection, no limit


# --- through the server ---


async def call(name, args):
    result = await server.call_tool(name, args)
    [content] = result.content
    assert result.is_error == ("error" in json.loads(content.text))
    return content.text


@pytest.fixture
def fake(monkeypatch):
    f = FakeProxmox()
    monkeypatch.setattr(server, "proxmox", f)
    monkeypatch.setattr(server, "PROTECTED", frozenset())
    return f


async def test_wait_flag_returns_task_outcome(fake):
    text = await call("clone_vm", {"node": "pve2", "vmid": 9000, "newid": 123, "wait": True})
    result = json.loads(text)
    assert result["data"] == UPID
    assert result["task"]["ok"] is True
    assert ("GET", f"/nodes/pve2/tasks/{UPID}/status") in fake.calls


async def test_without_wait_returns_the_upid_only(fake):
    result = json.loads(await call("clone_vm", {"node": "pve2", "vmid": 9000, "newid": 123}))
    assert result == {"data": UPID}
    assert all(method == "POST" for method, _ in fake.calls)


async def test_wait_for_task_tool(fake):
    result = json.loads(await call("wait_for_task", {"upid": UPID, "timeout": 5}))
    assert result["status"] == "stopped" and result["ok"] is True


async def test_server_refuses_protected_guest_before_any_request(fake, monkeypatch):
    monkeypatch.setattr(server, "PROTECTED", frozenset({100}))
    result = json.loads(await call("delete_vm", {"node": "pve", "vmid": 100}))
    assert "protected" in result["error"]
    assert fake.calls == []


async def test_reads_ignore_protection(fake, monkeypatch):
    monkeypatch.setattr(server, "PROTECTED", frozenset({100}))
    result = json.loads(await call("get_vm_status", {"node": "pve", "vmid": 100}))
    assert "error" not in result


async def test_output_is_compact(fake):
    text = await call("list_pools", {})
    assert text == '{"data":[]}'
