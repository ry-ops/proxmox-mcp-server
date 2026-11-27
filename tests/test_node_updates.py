"""Node packages and kernels, APT repositories, subscription, node config, bulk suspend."""

import json
import urllib.parse

import httpx
import pytest

from proxmox_mcp import audit, registry, server
from proxmox_mcp.client import ProxmoxClient

ALL, _ = registry.build(list(registry.TOOLSETS), read_only=False)
BY_NAME = {t.name: t for t in ALL}

VERSIONS = [
    {"Package": "proxmox-ve", "Version": "9.2.0", "RunningKernel": "7.3.5-1-pve", "CurrentState": "Installed"},
    {"Package": "pve-manager", "Version": "9.2.4", "CurrentState": "Installed"},
    {"Package": "proxmox-kernel-helper", "Version": "9.0.4", "CurrentState": "Installed"},
    {"Package": "proxmox-kernel-7.0", "Version": "7.0.14-30", "CurrentState": "Installed"},
    {"Package": "proxmox-kernel-7.0.14-30-pve-signed", "Version": "7.0.14-30", "CurrentState": "Installed"},
    {"Package": "proxmox-kernel-7.3", "Version": "7.3.5-1", "CurrentState": "Installed"},
    {"Package": "proxmox-kernel-7.3.5-1-pve-signed", "Version": "7.3.5-1", "CurrentState": "Installed"},
    {"Package": "proxmox-kernel-6.17.2-1-pve-signed", "Version": "6.17.2-1", "CurrentState": "ConfigFiles"},
]


@pytest.fixture
def sent(monkeypatch):
    """A real ProxmoxClient over a fake transport: (method, path, query, form) per request."""
    requests = []

    def answer(request):
        form = dict(urllib.parse.parse_qsl(request.content.decode())) if request.content else {}
        path = request.url.path.removeprefix("/api2/json")
        requests.append((request.method, path, dict(request.url.params), form))
        data = VERSIONS if path.endswith("/apt/versions") else None
        return httpx.Response(200, json={"data": data})

    client = ProxmoxClient()
    client.base_url = "https://pve.test:8006/api2/json"
    client.token = "PVEAPIToken=test"
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    monkeypatch.setattr(server, "proxmox", client)
    monkeypatch.setattr(server, "PROTECTED", frozenset())
    return requests


async def call(name, args):
    result = await server.call_tool(name, args)
    return result.is_error, result.content[0].text


async def test_kernel_summary(sent):
    failed, body = await call("get_node_kernel", {"node": "pve1"})
    assert not failed, body
    summary = json.loads(body)
    assert summary["running_kernel"] == "7.3.5-1-pve"
    assert summary["running_series"] == "7.3"
    assert summary["installed_series"] == ["7.0", "7.3"]
    # Kernel images only: not the helper, not removed kernels with only config files left.
    assert [p["package"] for p in summary["kernel_packages"]] == [
        "proxmox-kernel-7.0", "proxmox-kernel-7.0.14-30-pve-signed",
        "proxmox-kernel-7.3", "proxmox-kernel-7.3.5-1-pve-signed",
    ]
    assert sent == [("GET", "/nodes/pve1/apt/versions", {}, {})]


def test_kernel_summary_without_data():
    from proxmox_mcp.tools import nodes

    assert nodes._kernel_summary({"data": []}) == {
        "running_kernel": None, "running_series": None, "installed_series": [], "kernel_packages": []}


@pytest.mark.parametrize("tool, args, expected", [
    ("get_node_apt_versions", {"node": "pve1"}, ("GET", "/nodes/pve1/apt/versions", {}, {})),
    ("get_node_apt_history", {"node": "pve1", "package": "proxmox-kernel-7.3", "limit": 5},
     ("GET", "/nodes/pve1/apt/history", {"package": "proxmox-kernel-7.3", "limit": "5"}, {})),
    ("get_node_apt_repositories", {"node": "pve1"}, ("GET", "/nodes/pve1/apt/repositories", {}, {})),
    ("refresh_node_apt_index", {"node": "pve1", "notify": True}, ("POST", "/nodes/pve1/apt/update", {}, {"notify": "1"})),
    ("set_node_apt_repository",
     {"node": "pve1", "path": "/etc/apt/sources.list.d/pve-enterprise.sources", "index": 0, "enabled": False},
     ("POST", "/nodes/pve1/apt/repositories", {},
      {"path": "/etc/apt/sources.list.d/pve-enterprise.sources", "index": "0", "enabled": "0"})),
    ("add_node_apt_repository", {"node": "pve1", "handle": "no-subscription"},
     ("PUT", "/nodes/pve1/apt/repositories", {}, {"handle": "no-subscription"})),
    ("set_node_subscription_key", {"node": "pve1", "key": "pve2c-0123456789"},
     ("PUT", "/nodes/pve1/subscription", {}, {"key": "pve2c-0123456789"})),
    ("refresh_node_subscription", {"node": "pve1", "force": True}, ("POST", "/nodes/pve1/subscription", {}, {"force": "1"})),
    ("delete_node_subscription", {"node": "pve1"}, ("DELETE", "/nodes/pve1/subscription", {}, {})),
    ("get_node_config", {"node": "pve1", "property": "wakeonlan"}, ("GET", "/nodes/pve1/config", {"property": "wakeonlan"}, {})),
    ("set_node_config", {"node": "pve1", "wakeonlan": "mac=aa:bb:cc:dd:ee:ff", "startall-onboot-delay": 30},
     ("PUT", "/nodes/pve1/config", {}, {"wakeonlan": "mac=aa:bb:cc:dd:ee:ff", "startall-onboot-delay": "30"})),
    ("node_suspendall", {"node": "pve1", "vms": "200,201"}, ("POST", "/nodes/pve1/suspendall", {}, {"vms": "200,201"})),
    ("bulk_suspend_guests", {"vms": "200,201", "to-disk": True},
     ("POST", "/cluster/bulk-action/guest/suspend", {}, {"vms": "200,201", "to-disk": "1"})),
])
async def test_requests(sent, tool, args, expected):
    failed, body = await call(tool, args)
    assert not failed, body
    assert sent == [expected]


@pytest.mark.parametrize("tool, args", [
    ("node_suspendall", {"node": "pve1"}),
    ("bulk_suspend_guests", {}),
])
async def test_suspending_everything_needs_a_list_while_guests_are_protected(sent, monkeypatch, tool, args):
    monkeypatch.setattr(server, "PROTECTED", frozenset({100}))
    failed, body = await call(tool, args)
    assert failed and "vms" in body
    assert sent == []


def test_subscription_key_is_redacted_in_the_audit_log():
    assert audit.redact({"node": "pve1", "key": "pve2c-0123456789"}, "set_node_subscription_key") == {
        "node": "pve1", "key": "***"}


def test_safety_classes():
    for tool in ("get_node_kernel", "get_node_apt_versions", "get_node_apt_history", "get_node_apt_repositories"):
        assert BY_NAME[tool].annotations.read_only_hint is True, tool
    assert BY_NAME["delete_node_subscription"].annotations.destructive_hint is True
    for tool in ("refresh_node_apt_index", "set_node_apt_repository", "add_node_apt_repository", "set_node_config",
                 "node_suspendall", "bulk_suspend_guests"):
        assert BY_NAME[tool].annotations.read_only_hint is False, tool
        assert BY_NAME[tool].annotations.destructive_hint is False, tool


def test_index_refresh_and_bulk_suspend_can_wait():
    assert "wait" in BY_NAME["refresh_node_apt_index"].input_schema["properties"]
    assert "wait" in BY_NAME["bulk_suspend_guests"].input_schema["properties"]
