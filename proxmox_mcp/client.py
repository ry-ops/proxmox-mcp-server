"""Proxmox VE API client with token and password auth."""

from __future__ import annotations

import asyncio
import os
import re
import ssl
import sys
import time
from typing import Any

import httpx
from dotenv import load_dotenv

# Load .env before reading the settings below; they are read once, at import time.
load_dotenv()

PROXMOX_HOST = os.getenv("PROXMOX_HOST", "")
PROXMOX_PORT = os.getenv("PROXMOX_PORT", "8006")
PROXMOX_USER = os.getenv("PROXMOX_USER", "")
PROXMOX_TOKEN_NAME = os.getenv("PROXMOX_TOKEN_NAME", "")
PROXMOX_TOKEN_VALUE = os.getenv("PROXMOX_TOKEN_VALUE", "")
PROXMOX_PASSWORD = os.getenv("PROXMOX_PASSWORD", "")
PROXMOX_VERIFY_SSL = os.getenv("PROXMOX_VERIFY_SSL", "false").lower() == "true"
# The Proxmox cluster CA (/etc/pve/pve-root-ca.pem on any node). Set, it turns verification on
# against that CA, so nodes with their default self-signed certificates can be verified.
PROXMOX_CA_BUNDLE = os.getenv("PROXMOX_CA_BUNDLE", "")
PROXMOX_READ_ONLY = os.getenv("PROXMOX_READ_ONLY", "false").lower() == "true"

# A "." or ".." segment would let a tool argument move the request to another endpoint
# (httpx resolves them before sending), and "?", "#" or "\\" would change the URL's meaning.
# Tools never build such paths, so refuse them outright.
_UNSAFE_PATH = re.compile(r"(?:^|/)\.{1,2}(?:/|$)|[?#\\]")

# Proxmox tickets (password auth) expire after 2 hours. Log in again well before that.
TICKET_LIFETIME = 90 * 60


def _validate_config() -> None:
    """Check the Proxmox VE settings. Without PROXMOX_HOST there is nothing to check: the
    server may be talking only to Proxmox Datacenter Manager (see server._validate_config)."""
    if not PROXMOX_HOST:
        return
    if not PROXMOX_USER:
        print("Error: PROXMOX_HOST and PROXMOX_USER must be set", file=sys.stderr)
        sys.exit(1)
    use_token = PROXMOX_TOKEN_NAME and PROXMOX_TOKEN_VALUE
    use_password = PROXMOX_PASSWORD
    if not use_token and not use_password:
        print(
            "Error: Either PROXMOX_TOKEN_NAME+PROXMOX_TOKEN_VALUE or PROXMOX_PASSWORD must be set",
            file=sys.stderr,
        )
        sys.exit(1)


def ca_context(ca_bundle: str, setting: str) -> ssl.SSLContext:
    """An SSL context that trusts ca_bundle. A file that can't be loaded stops the server
    rather than falling back to no verification."""
    try:
        ctx = ssl.create_default_context(cafile=ca_bundle)
    except (OSError, ssl.SSLError) as e:
        print(f"Error: {setting}={ca_bundle}: {e}", file=sys.stderr)
        sys.exit(1)
    # Python 3.13+ turns on strict RFC 5280 checks, which reject node certificates that
    # older Proxmox releases issued without an Authority Key Identifier. The chain to this
    # CA and the hostname are still verified.
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    # Accept a self-signed server certificate in the file as the trust anchor (Python 3.13+
    # does this by default), so a Proxmox product's own certificate can be pinned this way.
    ctx.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
    return ctx


def tls_verify() -> ssl.SSLContext | bool:
    """What the client checks the Proxmox certificate against.

    PROXMOX_CA_BUNDLE: that CA file. PROXMOX_VERIFY_SSL=true: the system's trusted CAs.
    Neither: nothing.
    """
    if PROXMOX_CA_BUNDLE:
        return ca_context(PROXMOX_CA_BUNDLE, "PROXMOX_CA_BUNDLE")
    return PROXMOX_VERIFY_SSL


def tls_warning() -> str | None:
    """A startup warning when the Proxmox certificate isn't verified, else None."""
    if not PROXMOX_HOST or PROXMOX_CA_BUNDLE or PROXMOX_VERIFY_SSL:
        return None
    return (
        "Warning: the Proxmox TLS certificate is not verified, so anyone on the network path "
        "can read the API token or password. Set PROXMOX_CA_BUNDLE to the cluster CA "
        "(/etc/pve/pve-root-ca.pem on any node), or PROXMOX_VERIFY_SSL=true for a publicly "
        "trusted certificate."
    )


def _network_error(
    error: httpx.TransportError, base_url: str, product: str = "Proxmox", prefix: str = "PROXMOX"
) -> ConnectionError:
    """A ConnectionError that says which address failed and how.

    httpx's own messages are often empty (a connect timeout has none), which reached clients
    as {"error": ""}.
    """
    where = base_url.removesuffix("/api2/json")
    if isinstance(error, httpx.TimeoutException):
        what = "timed out"
    else:
        what = str(error).strip() or type(error).__name__
    if "CERTIFICATE_VERIFY_FAILED" in what:
        ca = "the cluster CA (/etc/pve/pve-root-ca.pem)" if prefix == "PROXMOX" else "its certificate"
        hint = (
            f"The certificate isn't trusted: set {prefix}_CA_BUNDLE to {ca}, and use a "
            f"{prefix}_HOST the certificate names."
        )
    else:
        hint = (
            f"Check {prefix}_HOST and {prefix}_PORT, and that this machine can route to that "
            "address (a VPN can capture the traffic)."
        )
    return ConnectionError(f"Can't reach {product} at {where}: {what}. {hint}")


def _api_error(response: httpx.Response) -> httpx.HTTPStatusError:
    """An HTTPStatusError that keeps the reason Proxmox gives in the response body.

    Proxmox puts the useful detail there, e.g. {"errors": {"scsi0": "invalid format ..."}}
    for "400 Parameter verification failed", which the status line alone does not show.
    """
    detail = ""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        errors = body.get("errors")
        if isinstance(errors, dict) and errors:
            detail = "; ".join(f"{k}: {str(v).strip()}" for k, v in errors.items())
        elif body.get("message"):
            detail = str(body["message"]).strip()
    elif response.text:
        detail = response.text.strip()[:300]
    message = f"{response.status_code} {response.reason_phrase} for {response.request.method} {response.request.url.path}"
    if detail:
        message += f": {detail}"
    return httpx.HTTPStatusError(message, request=response.request, response=response)


class ProxmoxClient:
    def __init__(self) -> None:
        self.base_url = f"https://{PROXMOX_HOST}:{PROXMOX_PORT}/api2/json"
        self.client = httpx.AsyncClient(verify=tls_verify(), timeout=30.0)
        self.ticket: str | None = None
        self.csrf_token: str | None = None
        self.token: str | None = None
        self.ticket_issued: float = 0.0
        self._login_lock = asyncio.Lock()

    async def authenticate(self) -> None:
        use_token = PROXMOX_TOKEN_NAME and PROXMOX_TOKEN_VALUE
        if use_token:
            self.token = f"PVEAPIToken={PROXMOX_USER}!{PROXMOX_TOKEN_NAME}={PROXMOX_TOKEN_VALUE}"
            print(f"✓ Token auth: {PROXMOX_USER}!{PROXMOX_TOKEN_NAME}", file=sys.stderr)
        else:
            await self._login()
            print(f"✓ Ticket auth: {PROXMOX_USER}", file=sys.stderr)

    async def _login(self) -> None:
        """Get a new ticket with the password."""
        try:
            response = await self.client.post(
                f"{self.base_url}/access/ticket",
                data={"username": PROXMOX_USER, "password": PROXMOX_PASSWORD},
            )
        except httpx.TransportError as e:
            raise _network_error(e, self.base_url) from e
        if response.is_error:
            raise _api_error(response)
        data = response.json()["data"]
        self.ticket = data["ticket"]
        self.csrf_token = data["CSRFPreventionToken"]
        self.ticket_issued = time.monotonic()

    async def _renew_ticket(self, stale: str | None) -> None:
        """Log in again, unless a concurrent request already replaced the `stale` ticket."""
        async with self._login_lock:
            if self.ticket == stale:
                await self._login()

    def _headers(self, method: str) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = self.token
        elif self.ticket:
            headers["Cookie"] = f"PVEAuthCookie={self.ticket}"
            if method != "GET":
                headers["CSRFPreventionToken"] = self.csrf_token or ""
        return headers

    async def request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        """files (multipart uploads) and timeout are for POSTs such as storage uploads."""
        if PROXMOX_READ_ONLY and method != "GET":
            raise PermissionError(
                f"Read-only mode (PROXMOX_READ_ONLY): refusing {method} {path}"
            )
        if _UNSAFE_PATH.search(path):
            raise PermissionError(f"Refusing {method} {path!r}: unsafe API path")
        if method not in ("GET", "POST", "PUT", "DELETE"):
            raise ValueError(f"Unsupported method: {method}")
        url = f"{self.base_url}{path}"
        if data is not None:
            # Proxmox API rejects true/false; it requires 1/0.
            data = {k: int(v) if isinstance(v, bool) else v for k, v in data.items()}
        if self.ticket and time.monotonic() - self.ticket_issued > TICKET_LIFETIME:
            await self._renew_ticket(self.ticket)
        ticket = self.ticket
        response = await self._send(method, url, data, files, timeout)
        if response.status_code == 401 and ticket:
            # The ticket expired or was revoked early: log in once more and retry.
            await self._renew_ticket(ticket)
            for spec in (files or {}).values():
                if hasattr(spec[1], "seek"):
                    spec[1].seek(0)  # send the upload again from the start
            response = await self._send(method, url, data, files, timeout)
        if response.is_error:
            raise _api_error(response)
        return response.json()

    async def _send(
        self,
        method: str,
        url: str,
        data: dict[str, Any] | None,
        files: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        headers = self._headers(method)
        extra: dict[str, Any] = {}
        if timeout is not None:
            extra["timeout"] = timeout
        try:
            if method == "GET":
                response = await self.client.get(url, headers=headers, params=data)
            elif method == "POST":
                response = await self.client.post(url, headers=headers, data=data, files=files, **extra)
            elif method == "PUT":
                response = await self.client.put(url, headers=headers, data=data)
            else:
                response = await self.client.delete(url, headers=headers, params=data)
        except httpx.TransportError as e:
            raise _network_error(e, self.base_url) from e
        return response

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", path, params)

    async def upload(
        self, node: str, storage: str, content: str, filename: str, fileobj: Any, timeout: float = 3600
    ) -> Any:
        """Upload a file to a storage (content: iso, vztmpl or import). Returns the task."""
        return await self.request(
            "POST",
            f"/nodes/{node}/storage/{storage}/upload",
            {"content": content},
            files={"filename": (filename, fileobj, "application/octet-stream")},
            timeout=timeout,
        )

    async def post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        return await self.request("POST", path, data)

    async def put(self, path: str, data: dict[str, Any] | None = None) -> Any:
        return await self.request("PUT", path, data)

    async def delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request("DELETE", path, params)

    async def close(self) -> None:
        await self.client.aclose()
