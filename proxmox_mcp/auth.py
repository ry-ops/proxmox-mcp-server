"""Who is calling, and what their role lets them do.

stdio has one caller, the client that spawned the server, with full access. The HTTP entrypoint
can give each client its own bearer token and role:

    MCP_AUTH_TOKENS="ops:admin:<token>,grafana:read:<token>,ci:operator:<token>"
    MCP_AUTH_TOKENS_FILE=/run/secrets/mcp-tokens   # one "name role token" per line, # comments

Roles narrow what the server already allows (PROXMOX_TOOLSETS, PROXMOX_READ_ONLY,
PROXMOX_NO_DESTRUCTIVE); they never widen it:

    read      only tools that read
    operator  everything except destructive tools
    admin     everything

MCP_AUTH_TOKEN, a single token, is still accepted as an admin token named "default".
"""

from __future__ import annotations

import hmac
import re
from dataclasses import dataclass
from pathlib import Path

from . import registry

ROLES = ("read", "operator", "admin")


@dataclass(frozen=True)
class Principal:
    name: str
    role: str
    token: str = ""

    def __repr__(self) -> str:  # never print the token
        return f"Principal(name={self.name!r}, role={self.role!r})"


STDIO = Principal("stdio", "admin")
ANONYMOUS = Principal("anonymous", "admin")


def allows(role: str, tool: str) -> bool:
    if role == "admin":
        return True
    if role == "operator":
        return not registry.is_destructive(tool)
    return registry.is_read_only(tool)


def _entry(name: str, role: str, token: str, where: str) -> Principal:
    if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,64}", name):
        raise ValueError(f"{where}: token name {name!r} must be 1-64 letters, digits or _.@-")
    if role not in ROLES:
        raise ValueError(f"{where}: role {role!r} for {name!r} must be one of {', '.join(ROLES)}")
    if len(token) < 16:
        raise ValueError(f"{where}: the token for {name!r} must be at least 16 characters")
    return Principal(name, role, token)


def load_principals(
    tokens: str | None = None, tokens_file: str | None = None, legacy_token: str | None = None
) -> list[Principal]:
    """Parse every configured token. Raises ValueError on a malformed or duplicate entry."""
    found: list[Principal] = []
    if legacy_token:
        found.append(Principal("default", "admin", legacy_token))
    for i, item in enumerate((tokens or "").split(","), 1):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":", 2)
        if len(parts) != 3:
            raise ValueError(f"MCP_AUTH_TOKENS entry {i}: use name:role:token")
        found.append(_entry(parts[0], parts[1], parts[2], where=f"MCP_AUTH_TOKENS entry {i}"))
    if tokens_file:
        for n, line in enumerate(Path(tokens_file).read_text().splitlines(), 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 3:
                raise ValueError(f"{tokens_file}:{n}: use 'name role token'")
            found.append(_entry(parts[0], parts[1], parts[2], where=f"{tokens_file}:{n}"))
    names = [p.name for p in found]
    tokens_seen = [p.token for p in found]
    if len(set(names)) != len(names):
        raise ValueError(f"Duplicate token name in: {', '.join(sorted(names))}")
    if len(set(tokens_seen)) != len(tokens_seen):
        raise ValueError("Two token entries share the same token value")
    return found


def authenticate(authorization: bytes, principals: list[Principal]) -> Principal | None:
    """The principal whose token matches `Authorization: Bearer <token>`, checked in constant time."""
    match = None
    for p in principals:  # compare against every token, so timing doesn't reveal which matched
        if hmac.compare_digest(authorization, f"Bearer {p.token}".encode()):
            match = p
    return match
