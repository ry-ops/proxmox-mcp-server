"""Write a raw disk stream as a qcow2 (version 2) file holding only its non-zero clusters.

Kali's cloud image is a sparse 25 GiB raw disk with about 1 GiB of data, inside a .tar.xz that
Proxmox can't import. Repacked as qcow2, only the data travels to Proxmox; empty clusters read as
zeros. No compression, snapshots or backing files: just L1/L2 tables and refcounts.
"""

from __future__ import annotations

import struct
from typing import IO

CLUSTER_BITS = 16
CLUSTER = 1 << CLUSTER_BITS  # 64 KiB, qemu's default
_L2_ENTRIES = CLUSTER // 8
_REFCOUNTS_PER_BLOCK = CLUSTER // 2  # 16-bit refcounts
_COPIED = 1 << 63  # "refcount is exactly one" flag on L1/L2 entries
_ZERO = bytes(CLUSTER)


def _ceil(a: int, b: int) -> int:
    return -(-a // b)


def write(src: IO[bytes], virtual_size: int, out: IO[bytes]) -> dict[str, int]:
    """Read `virtual_size` bytes from `src` and write them to `out` (seekable) as qcow2.

    Returns the number of data clusters written and the file size.
    """
    if virtual_size <= 0:
        raise ValueError("virtual_size must be positive")
    clusters = _ceil(virtual_size, CLUSTER)
    l1_size = _ceil(clusters, _L2_ENTRIES)
    l1_clusters = _ceil(l1_size * 8, CLUSTER)

    # Cluster 0 is the header, then the L1 table; data clusters follow as they're found.
    out.seek(0)
    out.write(bytes(CLUSTER * (1 + l1_clusters)))
    next_free = 1 + l1_clusters
    l2: dict[int, list[int]] = {}
    data_clusters = 0
    for index in range(clusters):
        chunk = src.read(CLUSTER)
        if len(chunk) < CLUSTER:
            if index < clusters - 1 or len(chunk) < min(CLUSTER, virtual_size - index * CLUSTER):
                raise ValueError("source ended before virtual_size")
            chunk = chunk.ljust(CLUSTER, b"\x00")
        if chunk == _ZERO:
            continue
        out.write(chunk)
        table = l2.setdefault(index // _L2_ENTRIES, [0] * _L2_ENTRIES)
        table[index % _L2_ENTRIES] = (next_free * CLUSTER) | _COPIED
        next_free += 1
        data_clusters += 1

    # L2 tables after the data.
    l1 = [0] * l1_size
    for l1_index in sorted(l2):
        out.write(struct.pack(f">{_L2_ENTRIES}Q", *l2[l1_index]))
        l1[l1_index] = (next_free * CLUSTER) | _COPIED
        next_free += 1

    # Refcount table and blocks last: they must count themselves too.
    blocks = table_clusters = 1
    while True:
        total = next_free + table_clusters + blocks
        need_blocks = _ceil(total, _REFCOUNTS_PER_BLOCK)
        need_table = _ceil(need_blocks * 8, CLUSTER)
        if (need_blocks, need_table) == (blocks, table_clusters):
            break
        blocks, table_clusters = need_blocks, need_table
    table_offset = next_free * CLUSTER
    first_block = next_free + table_clusters
    total = next_free + table_clusters + blocks
    table = [(first_block + i) * CLUSTER for i in range(blocks)]
    out.write(struct.pack(f">{len(table)}Q", *table).ljust(table_clusters * CLUSTER, b"\x00"))
    refcounts = struct.pack(">H", 1) * total
    out.write(refcounts.ljust(blocks * CLUSTER, b"\x00"))

    # Now the L1 table and the header.
    out.seek(CLUSTER)
    out.write(struct.pack(f">{l1_size}Q", *l1))
    out.seek(0)
    out.write(
        struct.pack(
            ">4sIQIIQIIQQIIQ",
            b"QFI\xfb",
            2,  # version
            0, 0,  # no backing file
            CLUSTER_BITS,
            virtual_size,
            0,  # no encryption
            l1_size,
            CLUSTER,  # L1 table offset
            table_offset,
            table_clusters,
            0, 0,  # no snapshots
        )
    )
    out.seek(0, 2)
    return {"data_clusters": data_clusters, "file_size": out.tell()}


def read_cluster(f: IO[bytes], index: int) -> bytes:
    """One cluster of the virtual disk, for tests and checks."""
    f.seek(0)
    head = f.read(72)
    magic, version, _, _, bits, size, _, l1_size, l1_offset = struct.unpack(">4sIQIIQIIQ", head[:48])
    assert magic == b"QFI\xfb" and version == 2 and bits == CLUSTER_BITS
    l1_index, l2_index = divmod(index, _L2_ENTRIES)
    f.seek(l1_offset + 8 * l1_index)
    l2_offset = struct.unpack(">Q", f.read(8))[0] & ~_COPIED
    if not l2_offset:
        return _ZERO
    f.seek(l2_offset + 8 * l2_index)
    data_offset = struct.unpack(">Q", f.read(8))[0] & ~_COPIED
    if not data_offset:
        return _ZERO
    f.seek(data_offset)
    return f.read(CLUSTER)
