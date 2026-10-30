"""The streamable-HTTP entrypoint: safe defaults, bearer auth, and the same tools as stdio."""

import json

import pytest
from starlette.testclient import TestClient

from proxmox_mcp import server, server_http

ACCEPT = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}


class FakeProxmox:
    def __init__(self):
        self.calls = []

    async def authenticate(self):
        pass

    async def close(self):
        pass

    async def get(self, path, params=None):
        self.calls.append(path)
        return {"data": [{"poolid": "lab"}]}


@pytest.fixture
def fake_proxmox(monkeypatch):
    fake = FakeProxmox()
    monkeypatch.setattr(server, "proxmox", fake)
    monkeypatch.setattr(server_http, "proxmox", fake)
    return fake


def rpc_result(response):
    """The JSON-RPC message in a streamable-HTTP response (JSON or a one-event SSE stream)."""
    assert response.status_code == 200, response.text
    if response.headers["content-type"].startswith("application/json"):
        return response.json()
    data = [line[5:] for line in response.text.splitlines() if line.startswith("data:")]
    return json.loads(data[-1])


def mcp_session(client, headers):
    r = client.post("/mcp", headers={**ACCEPT, **headers}, json=INIT)
    sid = r.headers["mcp-session-id"]
    assert rpc_result(r)["result"]["serverInfo"]["name"] == "proxmox-mcp-server"
    h = {**ACCEPT, **headers, "mcp-session-id": sid, "mcp-protocol-version": "2025-06-18"}
    client.post("/mcp", headers=h, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    return h


@pytest.mark.parametrize(
    "host,expected",
    [
        ("127.0.0.1", True),
        ("127.0.0.53", True),
        ("localhost", True),
        ("::1", True),
        ("[::1]", True),
        ("0.0.0.0", False),
        ("192.168.1.10", False),
        ("::", False),
        ("pve-mcp.lan", False),
    ],
)
def test_is_loopback(host, expected):
    assert server_http.is_loopback(host) is expected


def test_refuses_network_bind_without_token():
    with pytest.raises(ValueError, match="Refusing to serve on 0.0.0.0"):
        server_http.check_http_config("0.0.0.0", token="", allow_no_auth=False)


@pytest.mark.parametrize(
    "host,token,allow",
    [("127.0.0.1", "", False), ("0.0.0.0", "s3cret", False), ("0.0.0.0", "", True)],
)
def test_allowed_configurations(host, token, allow):
    server_http.check_http_config(host, token=token, allow_no_auth=allow)


def test_token_is_required_when_set(fake_proxmox):
    with TestClient(server_http.build_asgi_app("0.0.0.0", "s3cret")) as client:
        for headers in ({}, {"Authorization": "Bearer wrong"}, {"Authorization": "s3cret"}):
            r = client.post("/mcp", headers={**ACCEPT, **headers}, json=INIT)
            assert r.status_code == 401
            assert r.headers["www-authenticate"].startswith("Bearer")
        assert client.get("/healthz").json() == {"status": "ok"}


def test_tools_over_http(fake_proxmox):
    with TestClient(server_http.build_asgi_app("0.0.0.0", "s3cret")) as client:
        h = mcp_session(client, {"Authorization": "Bearer s3cret"})
        listed = rpc_result(
            client.post("/mcp", headers=h, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        )
        assert {t["name"] for t in listed["result"]["tools"]} == {t.name for t in server.ALL_TOOLS}
        call = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "list_pools", "arguments": {}},
        }
        result = rpc_result(client.post("/mcp", headers=h, json=call))["result"]
        assert json.loads(result["content"][0]["text"]) == {"data": [{"poolid": "lab"}]}
        assert fake_proxmox.calls == ["/pools"]


def test_loopback_rejects_foreign_host_header(fake_proxmox):
    with TestClient(
        server_http.build_asgi_app("127.0.0.1"), base_url="http://127.0.0.1:8811"
    ) as client:
        assert client.post("/mcp", headers=ACCEPT, json=INIT).status_code == 200
        r = client.post("/mcp", headers={**ACCEPT, "Host": "evil.example"}, json=INIT)
        assert r.status_code == 421
