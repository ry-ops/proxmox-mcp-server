"""Protected guests: VM and container IDs the server refuses to change.

PROXMOX_PROTECTED_VMIDS lists IDs and ranges, e.g. "100,101,9000-9010". Any write tool aimed at
one of them is refused before a request is sent: power actions, config changes, snapshots,
migration, disk moves, deletion, guest-agent commands, HA changes, and deleting its volumes or
backups. Reads are never blocked. Three writes stay allowed because they leave the guest as it
is: cloning from it (only the new ID is checked), backing it up, and opening a console.

Node-wide and bulk power or migrate actions without an explicit guest list would include
protected guests, so they are refused too. Whole-node shutdown and reboot (node_shutdown)
are not covered.
"""

from __future__ import annotations

import re
from typing import Any

# Writes that do not change the guest named by `vmid`.
_SOURCE_ONLY = {"clone_vm", "clone_container"}  # vmid is the source; newid is checked
_HARMLESS = {"backup_vm", "get_vm_vnc_proxy", "get_vm_spice_proxy"}
# These act on every guest on a node (or every guest) when no list is given.
_ALL_GUESTS_BY_DEFAULT = {
    "node_startall",
    "node_stopall",
    "node_migrateall",
    "bulk_start_guests",
    "bulk_shutdown_guests",
    "bulk_migrate_guests",
}
# Guest IDs inside volume names: vm-100-disk-0, base-9000-disk-0, subvol-101-disk-0,
# and backups such as vzdump-qemu-100-2026_10_30-01_00_00.vma.zst.
_VOLUME_ID = re.compile(r"(?:^|[/:])(?:vm|base|subvol)-(\d+)-|vzdump-(?:qemu|lxc|openvz)-(\d+)-")


def parse_protected(value: str | None) -> frozenset[int]:
    """Turn "100,101,9000-9010" into a set of IDs."""
    ids: set[int] = set()
    for part in (value or "").replace(" ", "").split(","):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not m:
            raise ValueError(f"Invalid PROXMOX_PROTECTED_VMIDS entry: {part!r} (use IDs or ranges like 100-110)")
        lo, hi = int(m[1]), int(m[2] or m[1])
        if hi < lo or hi - lo > 100_000:
            raise ValueError(f"Invalid PROXMOX_PROTECTED_VMIDS range: {part!r}")
        ids.update(range(lo, hi + 1))
    return frozenset(ids)


def _ids(value: Any) -> set[int]:
    """Guest IDs in a value such as 100, "100", "100,101", ["100", 101] or "vm:100"."""
    if value is None or isinstance(value, bool):
        return set()
    items = value if isinstance(value, (list, tuple)) else re.split(r"[,\s;]+", str(value))
    found = set()
    for item in items:
        m = re.fullmatch(r"(?:vm:|ct:)?(\d+)", str(item).strip())
        if m:
            found.add(int(m[1]))
    return found


def targets(name: str, args: dict[str, Any]) -> set[int]:
    """The guest IDs a write tool would change."""
    found: set[int] = set()
    if name not in _SOURCE_ONLY and name not in _HARMLESS:
        found |= _ids(args.get("vmid"))
    found |= _ids(args.get("newid"))
    found |= _ids(args.get("target-vmid"))
    found |= _ids(args.get("vms"))
    found |= _ids(args.get("sid"))
    for m in _VOLUME_ID.finditer(str(args.get("volume", ""))):
        found.add(int(m[1] or m[2]))
    return found


def check(name: str, args: dict[str, Any], protected: frozenset[int]) -> None:
    """Raise PermissionError if a write tool would change a protected guest."""
    if not protected:
        return
    if name in _ALL_GUESTS_BY_DEFAULT and not _ids(args.get("vms")):
        raise PermissionError(
            f"{name} without a 'vms' list would include protected guests "
            f"(PROXMOX_PROTECTED_VMIDS); list the guests explicitly"
        )
    hit = sorted(targets(name, args) & protected)
    if hit:
        raise PermissionError(
            f"Refusing {name}: guest {', '.join(map(str, hit))} is protected (PROXMOX_PROTECTED_VMIDS)"
        )
