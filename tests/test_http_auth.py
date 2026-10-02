"""Bearer-auth gate for HTTP transport. Run: pytest tests/test_http_auth.py"""

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


if __name__ == "__main__":
    import sys

    class _MP:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)

    test_no_token_allows_all(_MP())
    test_token_required_and_matched(_MP())
    print("ok")
    sys.exit(0)
