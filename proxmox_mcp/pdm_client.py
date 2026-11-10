"""Proxmox Datacenter Manager (PDM) API client, for the `pdm` toolset.

    PDM_HOST           PDM hostname or IP. Set, the `pdm` toolset loads.
    PDM_PORT           API port (default: 8443)
    PDM_TOKEN_ID       API token ID, user@realm!name (e.g. root@pam!proxmox-mcp)
    PDM_TOKEN_SECRET   API token secret
    PDM_CA_BUNDLE      File with PDM's certificate (or the CA that signed it) to verify against
    PDM_TLS_NAME       Name to check the certificate against when PDM_HOST is an IP it doesn't
                       name. PDM's self-signed certificate names `pdm` and `localhost`, not its IP.
    PDM_VERIFY_SSL     Verify against the system's trusted CAs instead (default: false)

PDM tokens get their permissions from ACL entries on the token itself (Configuration ->
Access Control -> Permissions in PDM's UI).
"""

from __future__ import annotations

import os
import ssl
import sys
from typing import Any

import httpx

from .client import _UNSAFE_PATH, PROXMOX_READ_ONLY, _api_error, _network_error, ca_context

PDM_HOST = os.getenv("PDM_HOST", "")
PDM_PORT = os.getenv("PDM_PORT", "8443")
PDM_TOKEN_ID = os.getenv("PDM_TOKEN_ID", "")
PDM_TOKEN_SECRET = os.getenv("PDM_TOKEN_SECRET", "")
PDM_CA_BUNDLE = os.getenv("PDM_CA_BUNDLE", "")
PDM_VERIFY_SSL = os.getenv("PDM_VERIFY_SSL", "false").lower() == "true"
PDM_TLS_NAME = os.getenv("PDM_TLS_NAME", "")

# The Authorization scheme PDM's API expects for tokens: PDMAPIToken=user@realm!name:secret.
TOKEN_SCHEME = "PDMAPIToken"


def configured() -> bool:
    return bool(PDM_HOST)


def config_errors() -> list[str]:
    """What's wrong with the PDM settings, if PDM_HOST is set."""
    if not PDM_HOST:
        return []
    errors = []
    if not PDM_TOKEN_ID or "!" not in PDM_TOKEN_ID or "@" not in PDM_TOKEN_ID.split("!")[0]:
        errors.append("PDM_TOKEN_ID must be an API token ID: user@realm!name")
    if not PDM_TOKEN_SECRET:
        errors.append("PDM_TOKEN_SECRET must be set")
    return errors


def tls_verify() -> ssl.SSLContext | bool:
    if PDM_CA_BUNDLE:
        return ca_context(PDM_CA_BUNDLE, "PDM_CA_BUNDLE")
    return PDM_VERIFY_SSL


def tls_warning() -> str | None:
    if not PDM_HOST or PDM_CA_BUNDLE or PDM_VERIFY_SSL:
        return None
    return (
        "Warning: the Datacenter Manager TLS certificate is not verified, so anyone on the "
        "network path can read the API token. Set PDM_CA_BUNDLE to a copy of PDM's certificate "
        "(/etc/proxmox-datacenter-manager/auth/api.pem on the PDM host), or PDM_VERIFY_SSL=true "
        "for a publicly trusted certificate."
    )


class PdmClient:
    """Requests against PDM's /api2/json, with token auth and the same path safety as the
    Proxmox VE client."""

    def __init__(self) -> None:
        self.base_url = f"https://{PDM_HOST}:{PDM_PORT}/api2/json"
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        # Created on first use, so a server without PDM settings never loads a CA bundle.
        if self._client is None:
            self._client = httpx.AsyncClient(verify=tls_verify(), timeout=60.0)
        return self._client

    @client.setter
    def client(self, value: httpx.AsyncClient) -> None:
        self._client = value

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"{TOKEN_SCHEME}={PDM_TOKEN_ID}:{PDM_TOKEN_SECRET}"}

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        if PROXMOX_READ_ONLY and method != "GET":
            raise PermissionError(f"Read-only mode (PROXMOX_READ_ONLY): refusing {method} {path}")
        if _UNSAFE_PATH.search(path):
            raise PermissionError(f"Refusing {method} {path!r}: unsafe API path")
        if method not in ("GET", "POST", "PUT", "DELETE"):
            raise ValueError(f"Unsupported method: {method}")
        if params:
            # PDM reads booleans in query strings as true/false.
            params = {k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()}
        try:
            response = await self.client.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(),
                params=params or None,
                json=body if body else None,
                # Check the certificate against this name while connecting to PDM_HOST.
                extensions={"sni_hostname": PDM_TLS_NAME} if PDM_TLS_NAME else None,
            )
        except httpx.TransportError as e:
            error = _network_error(e, self.base_url, "Proxmox Datacenter Manager", "PDM")
            if "mismatch" in str(e) and not PDM_TLS_NAME:
                error = ConnectionError(
                    f"{error} PDM's certificate doesn't name {PDM_HOST}: set PDM_TLS_NAME to a "
                    "name it does (PDM's own certificate names pdm and localhost)."
                )
            raise error from e
        if response.is_error:
            raise _api_error(response)
        return response.json()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


def startup_errors() -> None:
    """Print PDM setting problems and exit, like the Proxmox VE checks do."""
    errors = config_errors()
    if errors:
        for e in errors:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
