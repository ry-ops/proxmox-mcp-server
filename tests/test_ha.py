"""HA rules, HA-aware migrate and relocate, maintenance mode, arm and disarm."""

import urllib.parse

import httpx
import pytest

from proxmox_mcp import registry, server
from proxmox_mcp.client import ProxmoxClient

ALL, _ = registry.build(list(registry.TOOLSETS), read_only=False)
BY_NAME = {t.name: t for t in ALL}


@pytest.fixture
def sent(monkeypatch):
    """A real ProxmoxClient over a fake transport: (method, raw path, query, form) per request."""
    requests = []

    def answer(request):
        form = dict(urllib.parse.parse_qsl(request.content.decode())) if request.content else {}
        path = request.url.raw_path.decode().split("?")[0].removeprefix("/api2/json")
        requests.append((request.method, path, dict(request.url.params), form))
        return httpx.Response(200, json={"data": None})

    client = ProxmoxClient()
    client.base_url = "https://pve.test:8006/api2/json"
    client.token = "PVEAPIToken=test"
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    monkeypatch.setattr(server, "proxmox", client)
    monkeypatch.setattr(server, "PROTECTED", frozenset({100}))
    return requests


async def call(name, args):
    result = await server.call_tool(name, args)
    return result.is_error, result.content[0].text


# --- rules ---


async def test_node_affinity_rule_is_sent_as_given(sent):
    args = {"rule": "db-on-fast", "type": "node-affinity", "resources": "vm:200,vm:201",
            "nodes": "pve1:2,pve2:1", "strict": True, "comment": "NVMe nodes"}
    failed, body = await call("create_ha_rule", args)
    assert not failed, body
    assert sent == [("POST", "/cluster/ha/rules", {}, {
        "rule": "db-on-fast", "type": "node-affinity", "resources": "vm:200,vm:201",
        "nodes": "pve1:2,pve2:1", "strict": "1", "comment": "NVMe nodes"})]


async def test_resource_affinity_rule_keeps_guests_apart(sent):
    args = {"rule": "keep-apart", "type": "resource-affinity", "resources": "vm:200,vm:201", "affinity": "negative"}
    failed, body = await call("create_ha_rule", args)
    assert not failed, body
    assert sent[0][3]["affinity"] == "negative"


@pytest.mark.parametrize("args, says", [
    ({"type": "resource-affinity", "resources": "vm:200,vm:201"}, "affinity"),
    ({"type": "resource-affinity", "resources": "vm:200,vm:201", "affinity": "positive", "nodes": "pve1"}, "node-affinity"),
    ({"type": "node-affinity", "resources": "vm:200"}, "nodes"),
])
async def test_rule_mix_ups_are_explained(sent, args, says):
    failed, body = await call("create_ha_rule", {"rule": "r1", **args})
    assert failed and says in body
    assert sent == []


async def test_rule_update_and_delete_use_the_rule_path(sent):
    assert not (await call("update_ha_rule", {"rule": "r1", "type": "node-affinity", "disable": True}))[0]
    assert not (await call("delete_ha_rule", {"rule": "r1"}))[0]
    assert [(m, p) for m, p, _, _ in sent] == [("PUT", "/cluster/ha/rules/r1"), ("DELETE", "/cluster/ha/rules/r1")]
    assert sent[0][3] == {"type": "node-affinity", "disable": "1"}


async def test_rules_list_filters(sent):
    assert not (await call("list_ha_rules", {"type": "resource-affinity", "resource": "vm:200"}))[0]
    assert sent == [("GET", "/cluster/ha/rules", {"type": "resource-affinity", "resource": "vm:200"}, {})]


@pytest.mark.parametrize("tool, args", [
    ("get_ha_rule", {"rule": "r1/../../access"}),
    ("delete_ha_rule", {"rule": "../nodes"}),
    ("get_ha_resource", {"sid": "200/../../access"}),
    ("migrate_ha_resource", {"sid": "vm:200/../x", "node": "pve2"}),
])
async def test_ids_cannot_change_the_path(sent, tool, args):
    failed, _ = await call(tool, args)
    assert failed
    assert sent == []


async def test_rule_naming_a_protected_guest_is_refused(sent):
    args = {"rule": "pin", "type": "node-affinity", "resources": "vm:200,vm:100", "nodes": "pve1", "strict": True}
    failed, body = await call("create_ha_rule", args)
    assert failed and "protected" in body
    assert sent == []


# --- moving HA guests ---


async def test_migrate_goes_through_the_ha_manager(sent):
    failed, body = await call("migrate_ha_resource", {"sid": "vm:200", "node": "pve2", "with-conntrack-state": True})
    assert not failed, body
    assert sent == [("POST", "/cluster/ha/resources/vm:200/migrate", {}, {"node": "pve2", "with-conntrack-state": "1"})]


async def test_relocate(sent):
    assert not (await call("relocate_ha_resource", {"sid": "ct:201", "node": "pve3"}))[0]
    assert sent == [("POST", "/cluster/ha/resources/ct:201/relocate", {}, {"node": "pve3"})]


async def test_moving_a_protected_guest_is_refused(sent):
    failed, body = await call("migrate_ha_resource", {"sid": "vm:100", "node": "pve2"})
    assert failed and "protected" in body
    assert sent == []


async def test_removing_a_resource_can_purge_its_rules(sent):
    assert not (await call("delete_ha_resource", {"sid": "vm:200", "purge": True}))[0]
    assert sent == [("DELETE", "/cluster/ha/resources/vm:200", {"purge": "1"}, {})]


# --- maintenance, arm and disarm ---


async def test_maintenance_mode(sent):
    assert not (await call("set_node_maintenance", {"node": "pve1", "maintenance-mode": "enable"}))[0]
    assert sent == [("PUT", "/nodes/pve1/maintenance", {}, {"maintenance-mode": "enable"})]


async def test_disarm_and_arm(sent):
    assert not (await call("disarm_ha", {"resource-mode": "freeze"}))[0]
    assert not (await call("arm_ha", {}))[0]
    assert sent == [
        ("POST", "/cluster/ha/status/disarm-ha", {}, {"resource-mode": "freeze"}),
        ("POST", "/cluster/ha/status/arm-ha", {}, {}),
    ]


async def test_manager_status(sent):
    assert not (await call("get_ha_manager_status", {}))[0]
    assert sent == [("GET", "/cluster/ha/status/manager_status", {}, {})]


@pytest.mark.parametrize("tool, destructive", [
    ("relocate_ha_resource", True),
    ("set_node_maintenance", True),
    ("disarm_ha", True),
    ("delete_ha_rule", True),
    ("migrate_ha_resource", False),
    ("arm_ha", False),
    ("create_ha_rule", False),
    ("update_ha_rule", False),
])
def test_safety_classes(tool, destructive):
    assert BY_NAME[tool].annotations.destructive_hint is destructive
    assert BY_NAME[tool].annotations.read_only_hint is False


@pytest.mark.parametrize("tool", ["list_ha_rules", "get_ha_rule", "get_ha_manager_status"])
def test_reads(tool):
    assert BY_NAME[tool].annotations.read_only_hint is True
