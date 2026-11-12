"""Build small ISO 9660 images with Joliet names, in memory.

The OS deploy tools hand a guest its first-boot settings on a CD: cloud-init reads `user-data`,
`meta-data` and `network-config` from a volume labelled `cidata`, and Windows Setup reads
`autounattend.xml` from any drive. Proxmox's upload API takes ISO images but not cloud-init
snippets, so the server builds the CD itself.

Only what those uses need: one root directory of small files. The primary volume uses ISO 9660
level 2 names (upper case); the Joliet volume keeps the real names (`user-data`), which Linux and
Windows read when it's present.
"""

from __future__ import annotations

import datetime as _dt
import struct

BLOCK = 2048
_SYSTEM_AREA = 16  # blocks before the first volume descriptor


def _both16(n: int) -> bytes:
    return struct.pack("<H", n) + struct.pack(">H", n)


def _both32(n: int) -> bytes:
    return struct.pack("<I", n) + struct.pack(">I", n)


def _blocks(size: int) -> int:
    return max(1, -(-size // BLOCK))


def _record_date(when: _dt.datetime) -> bytes:
    return bytes([when.year - 1900, when.month, when.day, when.hour, when.minute, when.second, 0])


def _volume_date(when: _dt.datetime) -> bytes:
    return when.strftime("%Y%m%d%H%M%S00").encode() + b"\x00"


def _primary_name(name: str) -> bytes:
    """An ISO 9660 level 2 file identifier: upper case, d-characters, with a version."""
    stem, dot, ext = name.upper().rpartition(".")
    if not dot:
        stem, ext = ext, ""
    clean = lambda s: "".join(c if c.isalnum() else "_" for c in s)  # noqa: E731
    stem, ext = clean(stem)[:26], clean(ext)[:3]
    return f"{stem}.{ext};1".encode("ascii")


def _dir_record(ident: bytes, lba: int, size: int, is_dir: bool, when: _dt.datetime) -> bytes:
    length = 33 + len(ident) + (1 if len(ident) % 2 == 0 else 0)
    record = (
        bytes([length, 0])
        + _both32(lba)
        + _both32(size)
        + _record_date(when)
        + bytes([2 if is_dir else 0, 0, 0])
        + _both16(1)
        + bytes([len(ident)])
        + ident
    )
    return record + b"\x00" * (length - len(record))


def _path_table(root_lba: int, big_endian: bool) -> bytes:
    lba = struct.pack(">I" if big_endian else "<I", root_lba)
    parent = struct.pack(">H" if big_endian else "<H", 1)
    return bytes([1, 0]) + lba + parent + b"\x00\x00"  # root: one-byte name 0x00, padded


def _pad(text: str, length: int, joliet: bool) -> bytes:
    if joliet:
        raw = text.encode("utf-16-be")[: length - length % 2]
        padded = raw + " ".encode("utf-16-be") * ((length - len(raw)) // 2)
        return padded.ljust(length, b"\x00")  # an odd-length field ends with one zero byte
    return text.encode("ascii")[:length].ljust(length, b" ")


def _volume_descriptor(
    joliet: bool,
    label: str,
    total_blocks: int,
    path_table_size: int,
    l_table: int,
    m_table: int,
    root_record: bytes,
    when: _dt.datetime,
) -> bytes:
    vd = bytearray(BLOCK)
    vd[0] = 2 if joliet else 1
    vd[1:6] = b"CD001"
    vd[6] = 1
    vd[8:40] = _pad("", 32, joliet)
    vd[40:72] = _pad(label, 32, joliet)
    vd[80:88] = _both32(total_blocks)
    if joliet:
        vd[88:91] = b"%/E"  # UCS-2 level 3
    vd[120:124] = _both16(1)
    vd[124:128] = _both16(1)
    vd[128:132] = _both16(BLOCK)
    vd[132:140] = _both32(path_table_size)
    vd[140:144] = struct.pack("<I", l_table)
    vd[148:152] = struct.pack(">I", m_table)
    vd[156:190] = root_record
    for start, length in ((190, 128), (318, 128), (446, 128), (574, 128)):
        vd[start : start + length] = _pad("", length, joliet)
    for start in (702, 739, 776):
        vd[start : start + 37] = _pad("", 37, joliet)
    stamp = _volume_date(when)
    vd[813:830] = stamp
    vd[830:847] = stamp
    vd[847:864] = b"0" * 16 + b"\x00"
    vd[864:881] = b"0" * 16 + b"\x00"
    vd[881] = 1
    return bytes(vd)


def build(label: str, files: dict[str, bytes], when: _dt.datetime | None = None) -> bytes:
    """An ISO image with `files` in its root directory, labelled `label`."""
    if not files:
        raise ValueError("an ISO needs at least one file")
    when = when or _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    names = sorted(files)

    # Layout: descriptors at 16-18, four path tables, two root directories, then file data.
    l_primary, m_primary, l_joliet, m_joliet = 19, 20, 21, 22
    root_primary, root_joliet = 23, 24
    lba = 25
    extents = {}
    for name in names:
        extents[name] = lba
        lba += _blocks(len(files[name]))
    total = lba

    def directory(joliet: bool, own_lba: int) -> bytes:
        records = [
            _dir_record(b"\x00", own_lba, BLOCK, True, when),
            _dir_record(b"\x01", own_lba, BLOCK, True, when),
        ]
        for name in names:
            ident = name.encode("utf-16-be") if joliet else _primary_name(name)
            records.append(_dir_record(ident, extents[name], len(files[name]), False, when))
        data = b"".join(records)
        if len(data) > BLOCK:
            raise ValueError("too many files for a one-block root directory")
        return data.ljust(BLOCK, b"\x00")

    path_table_size = len(_path_table(0, False))
    image = bytearray(BLOCK * _SYSTEM_AREA)
    image += _volume_descriptor(
        False, label.upper(), total, path_table_size, l_primary, m_primary,
        _dir_record(b"\x00", root_primary, BLOCK, True, when), when,
    )
    image += _volume_descriptor(
        True, label, total, path_table_size, l_joliet, m_joliet,
        _dir_record(b"\x00", root_joliet, BLOCK, True, when), when,
    )
    terminator = bytearray(BLOCK)
    terminator[0], terminator[1:6], terminator[6] = 255, b"CD001", 1
    image += terminator
    for root, big in ((root_primary, False), (root_primary, True), (root_joliet, False), (root_joliet, True)):
        image += _path_table(root, big).ljust(BLOCK, b"\x00")
    image += directory(False, root_primary)
    image += directory(True, root_joliet)
    for name in names:
        data = files[name]
        image += data + b"\x00" * (_blocks(len(data)) * BLOCK - len(data))
    assert len(image) == total * BLOCK
    return bytes(image)


def read(image: bytes) -> tuple[str, dict[str, bytes]]:
    """The Joliet label and root files of an ISO made by build(): for tests and checks."""
    joliet = image[17 * BLOCK : 18 * BLOCK]
    if joliet[0] != 2 or joliet[1:6] != b"CD001":
        raise ValueError("no Joliet volume descriptor")
    label = joliet[40:72].decode("utf-16-be").rstrip()
    root_lba = struct.unpack("<I", joliet[156 + 2 : 156 + 6])[0]
    directory = image[root_lba * BLOCK : (root_lba + 1) * BLOCK]
    files, pos = {}, 0
    while pos < len(directory) and directory[pos]:
        length = directory[pos]
        rec = directory[pos : pos + length]
        name_len = rec[32]
        ident = rec[33 : 33 + name_len]
        if ident not in (b"\x00", b"\x01"):
            lba = struct.unpack("<I", rec[2:6])[0]
            size = struct.unpack("<I", rec[10:14])[0]
            files[ident.decode("utf-16-be")] = image[lba * BLOCK : lba * BLOCK + size]
        pos += length
    return label, files
