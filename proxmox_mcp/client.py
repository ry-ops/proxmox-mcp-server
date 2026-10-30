"""Proxmox VE API client with token and password auth."""

from __future__ import annotations

import asyncio
import os
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
PROXMOX_READ_ONLY = os.getenv("PROXMOX_READ_ONLY", "false").lower() == "true"

# Proxmox tickets (password auth) expire after 2 hours. Log in again well before that.
TICKET_LIFETIME = 90 * 60


def _validate_config() -> None:
    if not PROXMOX_HOST or not PROXMOX_USER:
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
        self.client = httpx.AsyncClient(verify=PROXMOX_VERIFY_SSL, timeout=30.0)
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
        response = await self.client.post(
            f"{self.base_url}/access/ticket",
            data={"username": PROXMOX_USER, "password": PROXMOX_PASSWORD},
        )
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
    ) -> Any:
        if PROXMOX_READ_ONLY and method != "GET":
            raise PermissionError(
                f"Read-only mode (PROXMOX_READ_ONLY): refusing {method} {path}"
            )
        if method not in ("GET", "POST", "PUT", "DELETE"):
            raise ValueError(f"Unsupported method: {method}")
        url = f"{self.base_url}{path}"
        if data is not None:
            # Proxmox API rejects true/false; it requires 1/0.
            data = {k: int(v) if isinstance(v, bool) else v for k, v in data.items()}
        if self.ticket and time.monotonic() - self.ticket_issued > TICKET_LIFETIME:
            await self._renew_ticket(self.ticket)
        ticket = self.ticket
        response = await self._send(method, url, data)
        if response.status_code == 401 and ticket:
            # The ticket expired or was revoked early: log in once more and retry.
            await self._renew_ticket(ticket)
            response = await self._send(method, url, data)
        if response.is_error:
            raise _api_error(response)
        return response.json()

    async def _send(
        self, method: str, url: str, data: dict[str, Any] | None
    ) -> httpx.Response:
        headers = self._headers(method)
        if method == "GET":
            response = await self.client.get(url, headers=headers, params=data)
        elif method == "POST":
            response = await self.client.post(url, headers=headers, data=data)
        elif method == "PUT":
            response = await self.client.put(url, headers=headers, data=data)
        else:
            response = await self.client.delete(url, headers=headers, params=data)
        return response

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", path, params)

    async def post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        return await self.request("POST", path, data)

    async def put(self, path: str, data: dict[str, Any] | None = None) -> Any:
        return await self.request("PUT", path, data)

    async def delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request("DELETE", path, params)

    async def close(self) -> None:
        await self.client.aclose()
