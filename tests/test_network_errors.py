"""Network failures reach the client as a message that names the address."""

import json

import httpx
import pytest

from proxmox_mcp import server
from proxmox_mcp.client import ProxmoxClient


def failing_client(error):
    def answer(request):
        raise error

    client = ProxmoxClient()
    client.base_url = "https://10.0.0.5:8006/api2/json"
    client.token = "PVEAPIToken=test"
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    return client


@pytest.mark.parametrize(
    "error,expect",
    [
        (httpx.ConnectTimeout(""), "timed out"),  # httpx gives this one no message
        (httpx.ReadTimeout(""), "timed out"),
        (httpx.ConnectError("[Errno 65] No route to host"), "No route to host"),
        (httpx.ConnectError(""), "ConnectError"),
    ],
)
async def test_tool_errors_name_the_address(monkeypatch, error, expect):
    monkeypatch.setattr(server, "proxmox", failing_client(error))
    result = await server.call_tool("list_nodes", {})
    body = json.loads(result.content[0].text)
    assert result.is_error
    assert (
        "Can't reach Proxmox at https://10.0.0.5:8006" in body["error"] and expect in body["error"]
    )


async def test_password_login_errors_name_the_address():
    client = failing_client(httpx.ConnectTimeout(""))
    client.token = None
    with pytest.raises(ConnectionError, match="timed out"):
        await client._login()


async def test_an_exception_without_a_message_still_says_something(monkeypatch):
    class Silent:
        async def get(self, path, params=None):
            raise RuntimeError()

    monkeypatch.setattr(server, "proxmox", Silent())
    body = json.loads((await server.call_tool("list_nodes", {})).content[0].text)
    assert body["error"] == "RuntimeError"
