"""Audit log: one JSON line for every write tool call, including refused ones.

    PROXMOX_AUDIT_LOG=/var/log/proxmox-mcp/audit.jsonl   # or "stderr"
    PROXMOX_AUDIT_READS=true                             # log reads too (default: false)

Each line has the time (UTC), who called (stdio, or the HTTP token's name) and over which
transport, the tool, its arguments with secrets redacted, the outcome (ok, error or refused),
the error, the task UPID and its result when there is one, and the duration in milliseconds.
The file is opened in append mode for each line, so log rotation needs no signal.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from datetime import datetime, timezone
from typing import Any

AUDIT_LOG = os.getenv("PROXMOX_AUDIT_LOG", "")
AUDIT_READS = os.getenv("PROXMOX_AUDIT_READS", "false").lower() == "true"

_SECRET = re.compile(r"pass|secret|token|private|api[_-]?key|^value$|cipassword", re.I)
_lock = threading.Lock()


def redact(value: Any) -> Any:
    """Copy of `value` with secret-looking fields replaced by "***"."""
    if isinstance(value, dict):
        return {k: "***" if _SECRET.search(str(k)) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def enabled() -> bool:
    return bool(AUDIT_LOG)


def record(entry: dict[str, Any], path: str | None = None) -> None:
    """Append one entry. Never raises: a broken audit log must not break tool calls."""
    target = AUDIT_LOG if path is None else path
    if not target:
        return
    line = json.dumps(
        {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), **entry},
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    try:
        with _lock:
            if target == "stderr":
                print(line, file=sys.stderr, flush=True)
            else:
                with open(target, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
    except OSError as e:
        print(f"Audit log write failed ({target}): {e}", file=sys.stderr)
