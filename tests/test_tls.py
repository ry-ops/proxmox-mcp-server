"""PROXMOX_CA_BUNDLE, PROXMOX_VERIFY_SSL and the startup warning."""

import datetime
import http.server
import ipaddress
import ssl
import threading

import pytest

from proxmox_mcp import client as client_mod

x509 = pytest.importorskip("cryptography.x509")
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from cryptography.x509.oid import NameOID  # noqa: E402


def _cert(subject, issuer, key, issuer_key, ca, san=None):
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer)]))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
    )
    if ca:
        builder = builder.add_extension(
            x509.KeyUsage(False, False, False, False, False, True, True, False, False),
            critical=True,
        )
    if san:
        builder = builder.add_extension(x509.SubjectAlternativeName(san), critical=False)
    return builder.sign(issuer_key, hashes.SHA256())


@pytest.fixture(scope="module")
def pve(tmp_path_factory):
    """An HTTPS server whose certificate is signed by a throwaway "Proxmox" CA."""
    tmp = tmp_path_factory.mktemp("tls")
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca = _cert(
        "Proxmox Virtual Environment", "Proxmox Virtual Environment", ca_key, ca_key, ca=True
    )
    key = ec.generate_private_key(ec.SECP256R1())
    san = [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    cert = _cert("pve", "Proxmox Virtual Environment", key, ca_key, ca=False, san=san)
    (tmp / "ca.pem").write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    (tmp / "other-ca.pem").write_bytes(
        _cert(
            "Other", "Other", ca_key := ec.generate_private_key(ec.SECP256R1()), ca_key, ca=True
        ).public_bytes(serialization.Encoding.PEM)
    )
    (tmp / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (tmp / "key.pem").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = b'{"data": {"version": "9.2"}}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(tmp / "cert.pem", tmp / "key.pem")
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield tmp, server.server_address[1]
    server.shutdown()


def settings(monkeypatch, ca="", verify=False):
    monkeypatch.setattr(client_mod, "PROXMOX_CA_BUNDLE", ca)
    monkeypatch.setattr(client_mod, "PROXMOX_VERIFY_SSL", verify)


async def get_version(port):
    c = client_mod.ProxmoxClient()
    c.base_url = f"https://127.0.0.1:{port}/api2/json"
    c.token = "PVEAPIToken=test"
    try:
        return await c.get("/version")
    finally:
        await c.close()


async def test_ca_bundle_verifies_a_self_signed_proxmox_certificate(pve, monkeypatch):
    # The test certificates have no Authority Key Identifier, like those older Proxmox
    # releases issued; Python 3.13+'s strict checks would reject them.
    tmp, port = pve
    settings(monkeypatch, ca=str(tmp / "ca.pem"))
    assert (await get_version(port))["data"]["version"] == "9.2"


async def test_ca_bundle_rejects_a_certificate_from_another_ca(pve, monkeypatch):
    tmp, port = pve
    settings(monkeypatch, ca=str(tmp / "other-ca.pem"))
    with pytest.raises(ConnectionError, match="CERTIFICATE_VERIFY_FAILED.*PROXMOX_CA_BUNDLE"):
        await get_version(port)


async def test_verify_ssl_uses_system_cas_which_reject_the_proxmox_ca(pve, monkeypatch):
    _, port = pve
    settings(monkeypatch, verify=True)
    with pytest.raises(ConnectionError, match="CERTIFICATE_VERIFY_FAILED.*PROXMOX_CA_BUNDLE"):
        await get_version(port)


async def test_default_does_not_verify(pve, monkeypatch):
    _, port = pve
    settings(monkeypatch)
    assert (await get_version(port))["data"]["version"] == "9.2"


def test_missing_ca_bundle_stops_the_server(tmp_path, monkeypatch, capsys):
    settings(monkeypatch, ca=str(tmp_path / "missing.pem"))
    with pytest.raises(SystemExit):
        client_mod.tls_verify()
    assert "PROXMOX_CA_BUNDLE" in capsys.readouterr().err


@pytest.mark.parametrize(
    "ca,verify,warns", [("", False, True), ("/ca.pem", False, False), ("", True, False)]
)
def test_warning_only_when_nothing_is_verified(monkeypatch, ca, verify, warns):
    settings(monkeypatch, ca=ca, verify=verify)
    warning = client_mod.tls_warning()
    assert (warning is not None) == warns
    if warns:
        assert "PROXMOX_CA_BUNDLE" in warning


def test_ca_bundle_still_checks_the_hostname(pve, monkeypatch):
    tmp, _ = pve
    settings(monkeypatch, ca=str(tmp / "ca.pem"))
    ctx = client_mod.tls_verify()
    assert ctx.check_hostname is True and ctx.verify_mode == ssl.CERT_REQUIRED
