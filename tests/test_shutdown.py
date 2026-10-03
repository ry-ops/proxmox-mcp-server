"""The HTTP client is closed in the event loop that used it, not a new one."""

import asyncio
import contextlib

from proxmox_mcp import server


class FakeClient:
    def __init__(self):
        self.loops = {}

    async def authenticate(self):
        self.loops["authenticate"] = asyncio.get_running_loop()

    async def close(self):
        self.loops["close"] = asyncio.get_running_loop()


@contextlib.asynccontextmanager
async def fake_stdio_server():
    yield None, None


async def fake_app_run(*args, **kwargs):
    pass


def test_client_closed_in_same_event_loop(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(server, "proxmox", fake)
    monkeypatch.setattr(server, "_validate_config", lambda: None)
    monkeypatch.setattr(server.mcp.server.stdio, "stdio_server", fake_stdio_server)
    monkeypatch.setattr(server.app, "run", fake_app_run)

    server.run()

    assert fake.loops["close"] is fake.loops["authenticate"]
