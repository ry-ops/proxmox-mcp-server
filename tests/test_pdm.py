"""Proxmox Datacenter Manager toolset: spec, routing, input checks, guards, waits, client."""

import json
import re
from pathlib import Path

import httpx
import pytest

from proxmox_mcp import guards, pdm_client, registry, server
from proxmox_mcp.tools import pdm

ROOT = Path(__file__).parent.parent
PVE_UPID = "UPID:pve01:0003A1B2:01C9D3E4:6720F0A1:qmstart:104:root@pam!pdm:"
REMOTE_UPID = "pve01!" + PVE_UPID
PDM_UPID = "UPID:localhost:00001234:0000ABCD:00000001:6720F0A1:refresh-remote-updates::root@pam:"


# --- the spec ---


def roadmap_tools(phase):
    text = (ROOT / "ROADMAP.md").read_text()
    section = re.search(rf"#### Phase {phase}: [^\n]+\n\n([^\n]+)", text)[1]
    return set(re.findall(r"`(pdm_[a-z_]+)`", section))


def test_spec_matches_the_roadmap():
    spec = json.loads((ROOT / "proxmox_mcp/tools/pdm_spec.json").read_text())
    phase1 = {t["name"] for t in spec["tools"] if t["phase"] == "1"}
    phase2 = {t["name"] for t in spec["tools"] if t["phase"] == "2"}
    assert phase1 == roadmap_tools(1) and phase2 == roadmap_tools(2)
    assert len(pdm.NAMES) == 89 and spec["endpoint_count"] == 327


@pytest.mark.parametrize("tool", pdm.TOOLS, ids=lambda t: t["name"])
def test_every_path_input_is_required(tool):
    spec = pdm._TOOLS[tool["name"]]
    for ep in spec["endpoints"]:
        for name in re.findall(r"\{([^}]+)\}", ep["path"]):
            assert name in tool["inputSchema"]["required"], (tool["name"], name)
        assert set(ep["params"]) <= set(tool["inputSchema"]["properties"])


def test_safety_classes():
    assert registry.is_read_only("pdm_list_resources")
    assert not registry.is_read_only("pdm_pve_start_guest")
    assert not registry.is_destructive("pdm_pve_start_guest")
    for name in ("pdm_pve_stop_guest", "pdm_pve_rollback_snapshot", "pdm_pve_remote_migrate_guest"):
        assert registry.is_destructive(name)
    assert {"pdm_pve_start_guest", "pdm_refresh_updates"} <= registry.WAITABLE


# --- routing and input checks ---


def test_type_picks_the_endpoint():
    assert pdm.request_of(
        "pdm_pve_start_guest", {"remote": "pve01", "vmid": 101, "type": "qemu"}
    ) == (
        "POST",
        "/pve/remotes/pve01/qemu/101/start",
        {},
    )
    method, path, _ = pdm.request_of(
        "pdm_pve_start_guest", {"remote": "pve01", "vmid": 101, "type": "lxc"}
    )
    assert path == "/pve/remotes/pve01/lxc/101/start"


def test_section_picks_the_endpoint():
    _, path, _ = pdm.request_of(
        "pdm_ceph_cluster",
        {"cluster": "5d8e1c3a-7b2f-4e6d-9a1c-3f0b2e4d6a8c", "section": "osd-tree"},
    )
    assert path == "/ceph/clusters/5d8e1c3a-7b2f-4e6d-9a1c-3f0b2e4d6a8c/osd-tree"
    _, path, _ = pdm.request_of("pdm_sdn_list", {"section": "vnets"})
    assert path == "/sdn/vnets"


def test_inputs_split_into_path_and_query():
    method, path, rest = pdm.request_of(
        "pdm_pve_node_apt_changelog", {"remote": "pve01", "node": "pve01", "name": "pve-manager"}
    )
    assert (method, path, rest) == (
        "GET",
        "/pve/remotes/pve01/nodes/pve01/apt/changelog",
        {"name": "pve-manager"},
    )


def test_type_specific_inputs_reach_only_their_endpoint():
    args = {
        "remote": "pve01",
        "vmid": 101,
        "target": "pve02",
        "target-storage": ["local:local"],
        "target-bridge": ["vmbr0:vmbr0"],
        "restart": True,
    }
    _, _, lxc = pdm.request_of("pdm_pve_remote_migrate_guest", {**args, "type": "lxc"})
    _, _, qemu = pdm.request_of("pdm_pve_remote_migrate_guest", {**args, "type": "qemu"})
    assert lxc["restart"] is True and "restart" not in qemu


@pytest.mark.parametrize(
    "name,args,error",
    [
        ("pdm_pve_start_guest", {"remote": "pve01", "vmid": 101}, "missing type"),
        ("pdm_pve_start_guest", {"remote": "pve01", "vmid": 101, "type": "vm"}, "choose type"),
        ("pdm_list_remotes", {"verbose": True}, "unknown input"),
        ("pdm_pve_list_nodes", {"remote": "../access"}, "isn't a valid PDM remote"),
        (
            "pdm_pve_node_status",
            {"remote": "pve01", "node": "pve01/../x"},
            "isn't a valid PDM node",
        ),
        ("pdm_pve_list_nodes", {"remote": "x"}, "isn't a valid PDM remote"),  # PDM wants 2-32 chars
        ("pdm_pve_start_guest", {"remote": "pve01", "vmid": 0, "type": "qemu"}, "out of range"),
    ],
)
def test_bad_inputs_are_refused(name, args, error):
    with pytest.raises(ValueError, match=error):
        pdm.request_of(name, args)


def test_path_inputs_stay_in_their_segment():
    # This datastore input has no PDM pattern; a "/" is encoded, so it can't add path segments.
    _, path, _ = pdm.request_of(
        "pdm_pbs_list_namespaces", {"remote": "pbs1", "datastore": "s/../../x"}
    )
    assert path == "/pbs/remotes/pbs1/datastore/s%2F..%2F..%2Fx/namespaces"


# --- protected guests ---


def test_parse_pdm_protected():
    assert guards.parse_pdm_protected("pve01:104, pve01:105,*:9000-9001") == {
        "pve01": {104, 105},
        "*": {9000, 9001},
    }
    for bad in ("104", "pve01:", ":104", "pve01:abc", "pve/01:104"):
        with pytest.raises(ValueError, match="PDM_PROTECTED_GUESTS"):
            guards.parse_pdm_protected(bad)


PROTECTED = guards.parse_pdm_protected("pve01:104,*:9000")


@pytest.mark.parametrize(
    "name,args",
    [
        ("pdm_pve_stop_guest", {"remote": "pve01", "vmid": 104, "type": "qemu"}),
        (
            "pdm_pve_rollback_snapshot",
            {"remote": "pve01", "vmid": 104, "type": "qemu", "snapname": "s"},
        ),
        ("pdm_pve_start_guest", {"remote": "pve02", "vmid": 9000, "type": "qemu"}),  # wildcard
        # Migrating onto a protected guest ID on the target remote.
        (
            "pdm_pve_remote_migrate_guest",
            {"remote": "pve02", "vmid": 7, "target": "pve01", "target-vmid": 104},
        ),
        ("pdm_pve_remote_migrate_guest", {"remote": "pve02", "vmid": 104, "target": "pve01"}),
        ("pdm_pve_stop_task", {"remote": "pve01", "upid": REMOTE_UPID}),  # a task of guest 104
    ],
)
def test_protected_guests_are_refused(name, args):
    with pytest.raises(PermissionError, match="PDM_PROTECTED_GUESTS"):
        guards.check_pdm(name, args, PROTECTED)


@pytest.mark.parametrize(
    "name,args",
    [
        ("pdm_pve_stop_guest", {"remote": "pve02", "vmid": 104, "type": "qemu"}),  # other remote
        ("pdm_pve_stop_guest", {"remote": "pve01", "vmid": 105, "type": "qemu"}),
        ("pdm_stop_task", {"node": "localhost", "upid": PDM_UPID}),
    ],
)
def test_other_guests_are_allowed(name, args):
    guards.check_pdm(name, args, PROTECTED)


def test_upid_worker_id_in_both_formats():
    assert guards.pdm_targets("pdm_pve_stop_task", {"remote": "pve01", "upid": PVE_UPID}) == {
        ("pve01", 104)
    }
    pbs = "UPID:pbs1:00001234:0000ABCD:00000002:6720F0A1:backup:205:root@pam:"
    assert guards.pdm_targets("pdm_pbs_stop_task", {"remote": "pbs1", "upid": pbs}) == {
        ("pbs1", 205)
    }


# --- toolset selection ---


def test_select_toolsets():
    sets, core = server.select_toolsets(None, pve=True, pdm=False)
    assert "pdm" not in sets and "qemu" in sets and core
    sets, core = server.select_toolsets(None, pve=True, pdm=True)
    assert "pdm" in sets and "qemu" in sets and core
    sets, core = server.select_toolsets(None, pve=False, pdm=True)
    assert sets == ["pdm"] and not core
    with pytest.raises(ValueError, match="PDM_HOST"):
        server.select_toolsets("pdm", pve=True, pdm=False)
    with pytest.raises(ValueError, match="PROXMOX_HOST"):
        server.select_toolsets("qemu,pdm", pve=False, pdm=True)


# --- through the server ---


class FakePdm:
    def __init__(self):
        self.calls = []

    async def request(self, method, path, params=None, body=None):
        self.calls.append((method, path, params, body))
        if path.endswith("/start"):
            return {"data": REMOTE_UPID}
        if path.endswith("/status") and "/tasks/" in path:
            return {"data": {"status": "stopped", "exitstatus": "OK"}}
        return {"data": [{"remote": "pve01"}]}

    async def get(self, path, params=None):
        return await self.request("GET", path, params)


@pytest.fixture
def with_pdm(monkeypatch):
    tools, handlers = registry.build(["pdm"], read_only=False, core=False)
    fake = FakePdm()
    monkeypatch.setattr(server, "ALL_TOOLS", tools)
    monkeypatch.setattr(server, "TOOL_MODULE", handlers)
    monkeypatch.setattr(server, "SCHEMAS", {t.name: t.input_schema for t in tools})
    monkeypatch.setattr(server, "pdm", fake)
    monkeypatch.setattr(server, "PDM_PROTECTED", guards.parse_pdm_protected("pve01:104"))
    return fake


async def call(name, args):
    result = await server.call_tool(name, args)
    return result.is_error, json.loads(result.content[0].text)


async def test_read_goes_to_pdm(with_pdm):
    failed, body = await call("pdm_list_remotes", {})
    assert not failed and body == {"data": [{"remote": "pve01"}]}
    assert with_pdm.calls == [("GET", "/remotes/remote", {}, None)]


async def test_action_waits_on_the_remote_task(with_pdm):
    failed, body = await call(
        "pdm_pve_start_guest", {"remote": "pve01", "vmid": 101, "type": "qemu", "wait": True}
    )
    assert not failed and body["task"]["ok"] is True and body["task"]["node"] == "pve01"
    status_path = with_pdm.calls[1][1]
    assert status_path == f"/pve/remotes/pve01/tasks/{REMOTE_UPID}/status"


async def test_protected_guest_refused_before_any_request(with_pdm):
    failed, body = await call(
        "pdm_pve_stop_guest", {"remote": "pve01", "vmid": 104, "type": "qemu"}
    )
    assert failed and "protected" in body["error"]
    assert with_pdm.calls == []


async def test_pve_protected_vmids_dont_apply_to_pdm(with_pdm, monkeypatch):
    monkeypatch.setattr(server, "PROTECTED", frozenset({101}))
    failed, _ = await call("pdm_pve_start_guest", {"remote": "pve01", "vmid": 101, "type": "qemu"})
    assert not failed


async def test_status_wait_follows_the_task(with_pdm):
    failed, body = await call(
        "pdm_pve_task_status", {"remote": "pve01", "upid": REMOTE_UPID, "wait": True}
    )
    assert not failed and body["data"]["status"] == "stopped"
    assert all("wait" not in (c[2] or {}) for c in with_pdm.calls)


# --- the client ---


def make_client(monkeypatch, answer):
    monkeypatch.setattr(pdm_client, "PDM_TOKEN_ID", "root@pam!proxmox-mcp")
    monkeypatch.setattr(pdm_client, "PDM_TOKEN_SECRET", "s3cret-value")
    c = pdm_client.PdmClient()
    c.base_url = "https://pdm.test:8443/api2/json"
    c.client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    return c


async def test_client_sends_the_token_and_json(monkeypatch):
    seen = []
    c = make_client(
        monkeypatch, lambda r: seen.append(r) or httpx.Response(200, json={"data": "ok"})
    )
    await c.request(
        "POST", "/pve/remotes/pve01/qemu/101/snapshot", body={"snapname": "s1", "vmstate": True}
    )
    await c.request("GET", "/remotes/tasks/list", params={"running": True})
    assert seen[0].headers["authorization"] == "PDMAPIToken=root@pam!proxmox-mcp:s3cret-value"
    assert json.loads(seen[0].content) == {"snapname": "s1", "vmstate": True}
    assert seen[1].url.params["running"] == "true"


async def test_client_refuses_unsafe_paths_and_reads_only(monkeypatch):
    c = make_client(monkeypatch, lambda r: httpx.Response(200, json={}))
    with pytest.raises(PermissionError, match="unsafe API path"):
        await c.request("GET", "/pve/remotes/../access")
    monkeypatch.setattr(pdm_client, "PROXMOX_READ_ONLY", True)
    with pytest.raises(PermissionError, match="Read-only"):
        await c.request("POST", "/remotes/updates/refresh")


async def test_client_network_errors_name_pdm(monkeypatch):
    def answer(request):
        raise httpx.ConnectTimeout("")

    c = make_client(monkeypatch, answer)
    with pytest.raises(
        ConnectionError, match=r"Datacenter Manager at https://pdm.test:8443: timed out.*PDM_HOST"
    ):
        await c.get("/version")


def test_config_errors(monkeypatch):
    monkeypatch.setattr(pdm_client, "PDM_HOST", "pdm.test")
    monkeypatch.setattr(pdm_client, "PDM_TOKEN_ID", "proxmox-mcp")
    monkeypatch.setattr(pdm_client, "PDM_TOKEN_SECRET", "")
    errors = pdm_client.config_errors()
    assert any("user@realm!name" in e for e in errors) and any("SECRET" in e for e in errors)


# --- TLS: pinning PDM's own certificate, which names `pdm` but not the address used ---


@pytest.fixture(scope="module")
def pdm_server(tmp_path_factory):
    """An HTTPS server on 127.0.0.1 with a self-signed, non-CA certificate naming only `pdm`,
    like Datacenter Manager's own api.pem."""
    import datetime
    import http.server
    import ssl
    import threading

    x509 = pytest.importorskip("cryptography.x509")
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    tmp = tmp_path_factory.mktemp("pdm-tls")
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "pdm.localdomain")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("pdm")]), critical=False)
        .sign(key, hashes.SHA256())
    )
    (tmp / "api.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (tmp / "key.pem").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = b'{"data": {"version": "1.1.9"}}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(tmp / "api.pem", tmp / "key.pem")
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield tmp / "api.pem", httpd.server_address[1]
    httpd.shutdown()


def pinned_client(monkeypatch, pem, port, tls_name):
    monkeypatch.setattr(pdm_client, "PDM_HOST", "127.0.0.1")
    monkeypatch.setattr(pdm_client, "PDM_CA_BUNDLE", str(pem))
    monkeypatch.setattr(pdm_client, "PDM_TLS_NAME", tls_name)
    monkeypatch.setattr(pdm_client, "PDM_TOKEN_ID", "root@pam!t")
    monkeypatch.setattr(pdm_client, "PDM_TOKEN_SECRET", "s")
    c = pdm_client.PdmClient()
    c.base_url = f"https://127.0.0.1:{port}/api2/json"
    return c


async def test_pinned_certificate_with_tls_name(pdm_server, monkeypatch):
    pem, port = pdm_server
    c = pinned_client(monkeypatch, pem, port, "pdm")
    assert (await c.get("/version"))["data"]["version"] == "1.1.9"
    await c.close()


async def test_pinned_certificate_without_tls_name_says_what_to_set(pdm_server, monkeypatch):
    pem, port = pdm_server
    c = pinned_client(monkeypatch, pem, port, "")
    with pytest.raises(ConnectionError, match="set PDM_TLS_NAME"):
        await c.get("/version")
    await c.close()


async def test_pinned_certificate_rejects_a_wrong_name(pdm_server, monkeypatch):
    pem, port = pdm_server
    c = pinned_client(monkeypatch, pem, port, "evil.example")
    with pytest.raises(ConnectionError, match="CERTIFICATE_VERIFY_FAILED"):
        await c.get("/version")
    await c.close()


@pytest.mark.parametrize(
    "given",
    [PVE_UPID, "pve01!" + PVE_UPID, "pve:pve01!" + PVE_UPID],  # list_tasks, PDM, list_remote_tasks
)
def test_task_tools_take_every_task_id_form(given):
    _, path, _ = pdm.request_of("pdm_pve_task_status", {"remote": "pve01", "upid": given})
    assert path == f"/pve/remotes/pve01/tasks/pve01!{PVE_UPID}/status"


def test_required_inputs_with_a_default_are_filled_in():
    # PDM requires guest config's `state` but documents a default ("pending"); callers may skip it.
    args = {"remote": "pve01", "type": "qemu", "vmid": 108}
    assert "state" not in pdm._TOOLS["pdm_pve_guest_config"]["inputSchema"]["required"]
    assert pdm.request_of("pdm_pve_guest_config", args)[2] == {"state": "pending"}
    assert pdm.request_of("pdm_pve_guest_config", {**args, "state": "active"})[2] == {
        "state": "active"
    }


def test_superuser_only_tools_say_so():
    # PDM 1.1 declares no access rule on these endpoints, so only root@pam with a password may
    # call them; API tokens get 403 (confirmed against PDM 1.1.9). Their descriptions say so.
    flagged = {n for n, t in pdm._TOOLS.items() if t["superuser_only"]}
    assert flagged == {
        "pdm_pve_list_remotes",
        "pdm_pbs_list_remotes",
        "pdm_metric_collection_status",
        "pdm_collect_metrics",
        "pdm_get_remote_rrddata",
        "pdm_pve_sdn_vnet_mac_vrf",
        "pdm_pve_sdn_zone_ip_vrf",
    }
    for t in pdm.TOOLS:
        assert ("root@pam" in t["description"]) == (t["name"] in flagged), t["name"]
