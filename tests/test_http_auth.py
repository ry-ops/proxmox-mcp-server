"""Bearer-auth gate for HTTP transport. Run: pytest tests/test_http_auth.py"""

import pytest

from proxmox_mcp import server


def _hdr(value: str) -> list[tuple[bytes, bytes]]:
    return [(b"authorization", value.encode())]


def test_no_token_allows_all(monkeypatch):
    monkeypatch.setattr(server, "MCP_AUTH_TOKEN", "")
    assert server._authorized([]) is True
    assert server._authorized(_hdr("Bearer anything")) is True


def test_token_required_and_matched(monkeypatch):
    monkeypatch.setattr(server, "MCP_AUTH_TOKEN", "s3cret")
    assert server._authorized(_hdr("Bearer s3cret")) is True
    assert server._authorized(_hdr("Bearer wrong")) is False
    assert server._authorized(_hdr("s3cret")) is False  # missing "Bearer "
    assert server._authorized([]) is False


def test_loopback_without_token_allowed(monkeypatch):
    monkeypatch.setattr(server, "MCP_AUTH_TOKEN", "")
    for host in ("127.0.0.1", "::1", "localhost"):
        monkeypatch.setattr(server, "MCP_HOST", host)
        server._check_http_config()


def test_non_loopback_requires_token(monkeypatch):
    monkeypatch.setattr(server, "MCP_HOST", "0.0.0.0")
    monkeypatch.setattr(server, "MCP_AUTH_TOKEN", "")
    with pytest.raises(ValueError):
        server._check_http_config()
    monkeypatch.setattr(server, "MCP_AUTH_TOKEN", "s3cret")
    server._check_http_config()


if __name__ == "__main__":
    import sys

    class _MP:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)

    test_no_token_allows_all(_MP())
    test_token_required_and_matched(_MP())
    test_loopback_without_token_allowed(_MP())
    test_non_loopback_requires_token(_MP())
    print("ok")
    sys.exit(0)
