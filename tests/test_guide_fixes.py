"""Fixes from the Proxmox VE 9 admin guide review: options the API takes, scans, Ceph pools."""

import urllib.parse

import httpx
import pytest

from proxmox_mcp import registry, server
from proxmox_mcp.client import ProxmoxClient


@pytest.fixture
def sent(monkeypatch):
    """A real ProxmoxClient over a fake transport: (method, path, query, form) for every request."""
    requests = []

    def answer(request):
        form = dict(urllib.parse.parse_qsl(request.content.decode())) if request.content else {}
        requests.append((request.method, request.url.path.removeprefix("/api2/json"), dict(request.url.params), form))
        return httpx.Response(200, json={"data": None})

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


ALL, _ = registry.build(list(registry.TOOLSETS), read_only=False)


def schema(tool):
    return next(t for t in ALL if t.name == tool).input_schema["properties"]


# --- set_cluster_options ---


async def test_cluster_options_take_the_migration_property(sent):
    failed, body = await call("set_cluster_options", {"migration": "type=insecure,network=10.10.0.0/24"})
    assert not failed, body
    assert sent == [("PUT", "/cluster/options", {}, {"migration": "type=insecure,network=10.10.0.0/24"})]


async def test_old_migration_inputs_become_the_migration_property(sent):
    failed, body = await call("set_cluster_options", {"migration_type": "secure", "migration_cidr": "10.10.0.0/24"})
    assert not failed, body
    assert sent[0][3] == {"migration": "type=secure,network=10.10.0.0/24"}


def test_cluster_options_schema_lists_what_the_api_takes():
    props = schema("set_cluster_options")
    assert "migration_cidr" not in props and "migration_type" not in props
    for key in ("migration", "replication", "crs", "ha", "fencing", "token-policy", "user-tag-access",
                "consent-text", "webauthn", "u2f", "bwlimit", "mac_prefix", "http_proxy", "console", "location"):
        assert key in props, key


# --- get_ceph_pool ---


async def test_ceph_pool_reads_its_status(sent):
    failed, body = await call("get_ceph_pool", {"node": "pve", "name": "rbd"})
    assert not failed, body
    assert sent == [("GET", "/nodes/pve/ceph/pool/rbd/status", {}, {})]


# --- get_node_scan ---


async def test_nfs_scan_sends_the_server(sent):
    failed, body = await call("get_node_scan", {"node": "pve", "type": "nfs", "server": "nas.lan"})
    assert not failed, body
    assert sent == [("GET", "/nodes/pve/scan/nfs", {"server": "nas.lan"}, {})]


async def test_pbs_scan_sends_credentials_and_fingerprint(sent):
    args = {"node": "pve", "type": "pbs", "server": "pbs.lan", "username": "backup@pbs!mcp",
            "password": "s3cret", "fingerprint": "aa:bb", "portal": "ignored"}
    failed, body = await call("get_node_scan", args)
    assert not failed, body
    assert sent[0][2] == {"server": "pbs.lan", "username": "backup@pbs!mcp", "password": "s3cret", "fingerprint": "aa:bb"}


async def test_scan_names_what_is_missing(sent):
    failed, body = await call("get_node_scan", {"node": "pve", "type": "iscsi"})
    assert failed and "portal" in body
    assert sent == []


@pytest.mark.parametrize("scan", ["dir", "glusterfs", "../access"])
async def test_scan_refuses_unknown_types(sent, scan):
    failed, _ = await call("get_node_scan", {"node": "pve", "type": scan})
    assert failed
    assert sent == []


# --- options that were passed through but missing from schemas, or dropped by handlers ---


@pytest.mark.parametrize("tool, path", [
    ("resume_vm", "/nodes/pve/qemu/120/status/resume"),
    ("start_vm", "/nodes/pve/qemu/120/status/start"),
])
async def test_time_sync_override_reaches_proxmox(sent, tool, path):
    failed, body = await call(tool, {"node": "pve", "vmid": 120, "sync-time-on-resume": True})
    assert not failed, body
    assert sent[0][1] == path and sent[0][3] == {"sync-time-on-resume": "1"}


async def test_rollback_keeps_start_and_time_sync(sent):
    args = {"node": "pve", "vmid": 120, "snapname": "pre", "start": True, "sync-time-on-resume": False}
    failed, body = await call("rollback_vm_snapshot", args)
    assert not failed, body
    assert sent[0][3] == {"start": "1", "sync-time-on-resume": "0"}


async def test_container_env_list_is_sent_nul_separated(sent):
    args = {"node": "pve", "vmid": 130, "ostemplate": "local:vztmpl/nginx.tar", "entrypoint": "/docker-entrypoint.sh nginx",
            "env": ["A=1", "B=two"]}
    failed, body = await call("create_container", args)
    assert not failed, body
    assert sent[0][3]["env"] == "A=1\x00B=two"
    assert sent[0][3]["entrypoint"] == "/docker-entrypoint.sh nginx"


@pytest.mark.parametrize("tool, key", [
    ("migrate_vm", "with-conntrack-state"),
    ("create_notification_matcher", "expression"),
    ("update_notification_matcher", "expression"),
    ("create_backup_job", "fleecing"),
    ("update_backup_job", "pbs-change-detection-mode"),
    ("backup_vm", "fleecing"),
    ("update_user_token", "regenerate"),
    ("set_node_firewall_options", "nftables"),
    ("add_ha_resource", "failback"),
    ("update_ha_resource", "failback"),
    ("create_ceph_pool", "erasure-coding"),
    ("restore_vm_backup", "allow-identity-mismatch"),
    ("restore_container_backup", "allow-identity-mismatch"),
])
def test_schema_lists_the_option(tool, key):
    assert key in schema(tool)


@pytest.mark.parametrize("tool", [
    "add_cluster_firewall_rule", "add_node_firewall_rule", "add_vm_firewall_rule", "add_container_firewall_rule",
])
def test_firewall_rules_mention_forward(tool):
    assert "forward" in schema(tool)["type"]["description"]
