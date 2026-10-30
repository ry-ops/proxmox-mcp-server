"""Password-auth tickets expire after 2 hours; the client logs in again instead of failing."""

import asyncio

import httpx
import pytest

from proxmox_mcp import client as client_mod


@pytest.fixture
def pve(monkeypatch):
    """A fake Proxmox that issues numbered tickets and accepts only those still listed as valid."""
    state = {"logins": 0, "valid": set(), "calls": []}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/access/ticket"):
            state["logins"] += 1
            ticket = f"T{state['logins']}"
            state["valid"] = {ticket}
            return httpx.Response(
                200, json={"data": {"ticket": ticket, "CSRFPreventionToken": "csrf"}}
            )
        cookie = request.headers.get("cookie", "")
        state["calls"].append(cookie)
        if cookie.removeprefix("PVEAuthCookie=") not in state["valid"]:
            return httpx.Response(401, json={"data": None})
        return httpx.Response(200, json={"data": "ok"})

    for name, value in {
        "PROXMOX_HOST": "pve.test",
        "PROXMOX_USER": "root@pam",
        "PROXMOX_PASSWORD": "pw",
        "PROXMOX_TOKEN_NAME": "",
        "PROXMOX_TOKEN_VALUE": "",
        "PROXMOX_READ_ONLY": False,
    }.items():
        monkeypatch.setattr(client_mod, name, value)
    c = client_mod.ProxmoxClient()
    c.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return c, state


async def test_renews_before_the_ticket_expires(pve):
    c, state = pve
    await c.authenticate()
    c.ticket_issued -= client_mod.TICKET_LIFETIME + 1
    assert (await c.get("/nodes"))["data"] == "ok"
    assert state["logins"] == 2
    assert state["calls"] == ["PVEAuthCookie=T2"]


async def test_retries_once_after_a_401(pve):
    c, state = pve
    await c.authenticate()
    state["valid"] = set()  # revoked or expired early on the server
    assert (await c.post("/nodes/pve/qemu/100/status/start"))["data"] == "ok"
    assert state["logins"] == 2
    assert state["calls"] == ["PVEAuthCookie=T1", "PVEAuthCookie=T2"]


async def test_gives_up_after_one_retry(pve, monkeypatch):
    c, state = pve
    await c.authenticate()
    real_login = c._login

    async def login_that_never_works():
        await real_login()
        state["valid"] = set()

    monkeypatch.setattr(c, "_login", login_that_never_works)
    state["valid"] = set()
    with pytest.raises(httpx.HTTPStatusError, match="401"):
        await c.get("/nodes")
    assert len(state["calls"]) == 2


async def test_concurrent_requests_share_one_renewal(pve):
    c, state = pve
    await c.authenticate()
    c.ticket_issued -= client_mod.TICKET_LIFETIME + 1
    await asyncio.gather(*(c.get("/nodes") for _ in range(5)))
    assert state["logins"] == 2


async def test_token_auth_never_logs_in(pve, monkeypatch):
    c, state = pve
    monkeypatch.setattr(client_mod, "PROXMOX_TOKEN_NAME", "t")
    monkeypatch.setattr(client_mod, "PROXMOX_TOKEN_VALUE", "v")
    await c.authenticate()
    with pytest.raises(httpx.HTTPStatusError, match="401"):
        await c.get("/nodes")  # the fake rejects tokens; a token 401 is not retried
    assert state["logins"] == 0
