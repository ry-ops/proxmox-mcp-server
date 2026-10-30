"""Per-token roles over HTTP, and the audit log."""

import json

import pytest
from starlette.testclient import TestClient

from proxmox_mcp import audit, auth, server, server_http

ADMIN = "a" * 32
READER = "r" * 32
OPERATOR = "o" * 32
UPID = "UPID:pve:0003A1B2:01C9D3E4:6720F0A1:qmstart:101:root@pam:"
ACCEPT = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


# --- token parsing ---


def test_load_principals_from_env_file_and_legacy(tmp_path):
    f = tmp_path / "tokens"
    f.write_text(f"# comment\ngrafana read {READER}\n\n")
    ps = auth.load_principals(f"ci:operator:{OPERATOR}", str(f), ADMIN)
    assert [(p.name, p.role) for p in ps] == [("default", "admin"), ("ci", "operator"), ("grafana", "read")]
    assert READER not in repr(ps)


@pytest.mark.parametrize(
    "tokens,match",
    [
        ("ci:operator", "name:role:token"),
        (f"ci:root:{ADMIN}", "role 'root'"),
        ("ci:admin:short", "at least 16"),
        (f"bad name:admin:{ADMIN}", "token name"),
        (f"a:admin:{ADMIN},a:read:{READER}", "Duplicate token name"),
        (f"a:admin:{ADMIN},b:read:{ADMIN}", "same token value"),
    ],
)
def test_bad_token_config(tokens, match):
    with pytest.raises(ValueError, match=match):
        auth.load_principals(tokens)


def test_authenticate():
    ps = auth.load_principals(f"ops:admin:{ADMIN},grafana:read:{READER}")
    assert auth.authenticate(f"Bearer {READER}".encode(), ps).name == "grafana"
    assert auth.authenticate(b"Bearer nope", ps) is None
    assert auth.authenticate(READER.encode(), ps) is None


def test_roles():
    assert auth.allows("read", "list_vms") and not auth.allows("read", "start_vm")
    assert auth.allows("operator", "start_vm") and not auth.allows("operator", "delete_vm")
    assert auth.allows("admin", "delete_vm")


# --- audit ---


def test_redact():
    args = {"userid": "bob@pve", "password": "x", "ci": {"cipassword": "y"}, "list": [{"api_key": "z"}]}
    assert audit.redact(args) == {"userid": "bob@pve", "password": "***", "ci": {"cipassword": "***"}, "list": [{"api_key": "***"}]}


def test_record_appends_json_lines(tmp_path):
    path = tmp_path / "audit.jsonl"
    audit.record({"tool": "start_vm"}, str(path))
    audit.record({"tool": "stop_vm"}, str(path))
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert [entry["tool"] for entry in lines] == ["start_vm", "stop_vm"]
    assert lines[0]["ts"].endswith("+00:00")


def test_record_never_raises(tmp_path, capsys):
    audit.record({"tool": "x"}, str(tmp_path / "missing-dir" / "audit.jsonl"))
    assert "Audit log write failed" in capsys.readouterr().err


# --- through the server ---


class FakeProxmox:
    def __init__(self):
        self.calls = []

    async def authenticate(self):
        pass

    async def close(self):
        pass

    async def get(self, path, params=None):
        self.calls.append(("GET", path))
        return {"data": []}

    async def post(self, path, data=None):
        self.calls.append(("POST", path))
        return {"data": UPID}

    put = post
    delete = post


@pytest.fixture
def env(monkeypatch, tmp_path):
    fake = FakeProxmox()
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr(server, "proxmox", fake)
    monkeypatch.setattr(server_http, "proxmox", fake)
    monkeypatch.setattr(server, "PROTECTED", frozenset({100}))
    monkeypatch.setattr(audit, "AUDIT_LOG", str(log))
    monkeypatch.setattr(audit, "AUDIT_READS", False)
    return fake, log


def audit_lines(log):
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


async def test_stdio_calls_are_audited(env):
    fake, log = env
    await server.call_tool("start_vm", {"node": "pve", "vmid": 101})
    await server.call_tool("delete_vm", {"node": "pve", "vmid": 100})  # protected
    await server.call_tool("list_vms", {"node": "pve"})  # a read: not logged
    ok, refused = audit_lines(log)
    assert ok["who"] == "stdio" and ok["outcome"] == "ok" and ok["upid"] == UPID
    assert refused["outcome"] == "refused" and "protected" in refused["error"]
    assert isinstance(ok["ms"], int)


async def test_reads_are_audited_when_asked(env, monkeypatch):
    fake, log = env
    monkeypatch.setattr(audit, "AUDIT_READS", True)
    await server.call_tool("list_vms", {"node": "pve"})
    assert audit_lines(log)[0]["tool"] == "list_vms"


async def test_audit_redacts_secrets(env):
    fake, log = env
    await server.call_tool("change_user_password", {"userid": "bob@pve", "password": "hunter2hunter2"})
    entry = audit_lines(log)[0]
    assert entry["args"] == {"userid": "bob@pve", "password": "***"}
    assert "hunter2" not in log.read_text()


def session(client, token):
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}},
    }
    h = {**ACCEPT, "Authorization": f"Bearer {token}"}
    r = client.post("/mcp", headers=h, json=init)
    h = {**h, "mcp-session-id": r.headers["mcp-session-id"], "mcp-protocol-version": "2025-06-18"}
    client.post("/mcp", headers=h, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    return h


def rpc(client, h, method, params=None, id_=2):
    r = client.post("/mcp", headers=h, json={"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}})
    data = [line[5:] for line in r.text.splitlines() if line.startswith("data:")]
    return json.loads(data[-1]) if data else r.json()


def test_roles_over_http(env):
    fake, log = env
    principals = auth.load_principals(f"ops:admin:{ADMIN},grafana:read:{READER},ci:operator:{OPERATOR}")
    with TestClient(server_http.build_asgi_app("0.0.0.0", principals=principals)) as client:
        counts = {}
        for name, token in (("ops", ADMIN), ("grafana", READER), ("ci", OPERATOR)):
            h = session(client, token)
            tools = {t["name"] for t in rpc(client, h, "tools/list")["result"]["tools"]}
            counts[name] = tools
        assert counts["ops"] == {t.name for t in server.ALL_TOOLS}
        assert counts["grafana"] == {t.name for t in server.ALL_TOOLS if auth.allows("read", t.name)}
        assert "start_vm" in counts["ci"] and "delete_vm" not in counts["ci"]

        h = session(client, READER)
        result = rpc(client, h, "tools/call", {"name": "start_vm", "arguments": {"node": "pve", "vmid": 101}})
        assert "not allowed for grafana (role: read)" in result["result"]["content"][0]["text"]
        assert ("POST", "/nodes/pve/qemu/101/status/start") not in fake.calls

        h = session(client, OPERATOR)
        rpc(client, h, "tools/call", {"name": "start_vm", "arguments": {"node": "pve", "vmid": 101}})
    entries = audit_lines(log)
    assert [(e["who"], e["via"], e["outcome"]) for e in entries] == [("grafana", "http", "refused"), ("ci", "http", "ok")]
