#!/usr/bin/env python3
"""Read-only structural analysis for an Amlogic eMMC dump.

The scanner intentionally uses only Python's standard library and never writes
to the image.  It reports boot/container signatures, Android image headers and
filesystems whose superblocks start on MiB boundaries.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import struct
import sys
from pathlib import Path


MIB = 1024 * 1024
SCAN_CHUNK = 32 * MIB
SIGNATURES = {
    b"@AML": "Amlogic signed boot container",
    b"ANDROID!": "Android boot image",
    b"AVB0": "Android Verified Boot metadata",
    b"AVBf": "Android Verified Boot footer",
    b"hsqs": "SquashFS filesystem",
}


def human_size(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}"
        amount /= 1024
    raise AssertionError("unreachable")


def offset_text(value: int) -> str:
    return f"0x{value:010x} ({value / MIB:10.3f} MiB)"


def sha256(path: Path, limit: int | None = None) -> str:
    digest = hashlib.sha256()
    remaining = limit
    with path.open("rb", buffering=0) as stream:
        while remaining is None or remaining > 0:
            size = 8 * MIB if remaining is None else min(8 * MIB, remaining)
            block = stream.read(size)
            if not block:
                break
            digest.update(block)
            if remaining is not None:
                remaining -= len(block)
    return digest.hexdigest()


def is_all_zero(path: Path) -> bool:
    with path.open("rb", buffering=0) as stream:
        while block := stream.read(8 * MIB):
            if any(block):
                return False
    return True


def scan_signatures(path: Path) -> dict[bytes, list[int]]:
    found: dict[bytes, list[int]] = {magic: [] for magic in SIGNATURES}
    overlap = max(map(len, SIGNATURES)) - 1
    tail = b""
    absolute = 0
    with path.open("rb", buffering=0) as stream:
        while block := stream.read(SCAN_CHUNK):
            data = tail + block
            base = absolute - len(tail)
            for magic, offsets in found.items():
                cursor = 0
                while len(offsets) < 128:
                    position = data.find(magic, cursor)
                    if position < 0:
                        break
                    value = base + position
                    if not offsets or value != offsets[-1]:
                        offsets.append(value)
                    cursor = position + 1
            absolute += len(block)
            tail = data[-overlap:]
    return found


def scan_ascii_macs(path: Path) -> dict[str, int]:
    """Return plausible unicast MAC strings and their first image offset."""
    pattern = re.compile(rb"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}(?![0-9A-Fa-f])")
    found: dict[str, int] = {}
    overlap = 32
    tail = b""
    absolute = 0
    with path.open("rb", buffering=0) as stream:
        while block := stream.read(SCAN_CHUNK):
            data = tail + block
            base = absolute - len(tail)
            for match in pattern.finditer(data):
                text = match.group().decode("ascii").lower()
                octets = bytes.fromhex(text.replace(":", ""))
                if octets == b"\0" * 6 or octets == b"\xff" * 6 or octets[0] & 1:
                    continue
                found.setdefault(text, base + match.start())
                if len(found) >= 256:
                    return found
            absolute += len(block)
            tail = data[-overlap:]
    return found


def ext4_at(stream, start: int, image_size: int) -> str | None:
    if start + 2048 > image_size:
        return None
    stream.seek(start + 1024)
    sb = stream.read(1024)
    if len(sb) != 1024 or sb[0x38:0x3A] != b"\x53\xef":
        return None
    blocks_lo = struct.unpack_from("<I", sb, 0x04)[0]
    log_block_size = struct.unpack_from("<I", sb, 0x18)[0]
    blocks_hi = struct.unpack_from("<I", sb, 0x150)[0]
    block_size = 1024 << log_block_size
    blocks = blocks_lo | (blocks_hi << 32)
    label = sb[0x78:0x88].split(b"\0", 1)[0].decode("ascii", "replace")
    return f"ext filesystem label={label!r} size={human_size(blocks * block_size)}"


def f2fs_at(stream, start: int, image_size: int) -> str | None:
    if start + 2048 > image_size:
        return None
    stream.seek(start + 1024)
    sb = stream.read(512)
    if sb[:4] != b"\x10\x20\xf5\xf2":
        return None
    log_block_size = struct.unpack_from("<I", sb, 0x10)[0]
    block_count = struct.unpack_from("<Q", sb, 0x24)[0]
    raw_label = sb[0x7C:0x27C]
    label = raw_label.decode("utf-16-le", "replace").split("\0", 1)[0]
    return (
        f"F2FS filesystem label={label!r} "
        f"size={human_size(block_count << log_block_size)}"
    )


def erofs_at(stream, start: int, image_size: int) -> str | None:
    if start + 2048 > image_size:
        return None
    stream.seek(start + 1024)
    sb = stream.read(128)
    if sb[:4] != b"\xe2\xe1\xf5\xe0":
        return None
    return "EROFS filesystem"


def fat_at(stream, start: int, image_size: int) -> str | None:
    if start + 512 > image_size:
        return None
    stream.seek(start)
    sector = stream.read(512)
    if sector[510:512] != b"\x55\xaa":
        return None
    kind = sector[82:90] if sector[82:90].startswith(b"FAT32") else sector[54:62]
    if not kind.startswith(b"FAT"):
        return None
    label_offset = 71 if kind.startswith(b"FAT32") else 43
    label = sector[label_offset:label_offset + 11].decode("ascii", "replace").strip()
    return f"{kind.decode('ascii', 'replace').strip()} filesystem label={label!r}"


def scan_filesystems(path: Path, alignment: int) -> list[tuple[int, str]]:
    size = path.stat().st_size
    result: list[tuple[int, str]] = []
    probes = (ext4_at, f2fs_at, erofs_at, fat_at)
    occupied = [
        (offset, offset + part_size)
        for _, _, checksum, calculated, entries in parse_mpt_tables(path)
        if checksum == calculated
        for _, offset, part_size, _ in entries
    ]
    with path.open("rb", buffering=0) as stream:
        for start in range(0, size, alignment):
            # Keep real partition starts, but suppress ext backup superblocks
            # and embedded payloads found inside a known MPT partition.
            if any(begin < start < end for begin, end in occupied):
                continue
            for probe in probes:
                description = probe(stream, start, size)
                if description:
                    result.append((start, description))
                    break
    return result


def probe_filesystem(stream, start: int, image_size: int) -> str:
    for probe in (ext4_at, f2fs_at, erofs_at, fat_at):
        description = probe(stream, start, image_size)
        if description:
            return description
    return "raw/unknown"


def parse_mpt_tables(path: Path) -> list[tuple[int, str, int, int, list[tuple[str, int, int, int]]]]:
    """Find sane MPT tables at MiB boundaries in the first 64 MiB."""
    image_size = path.stat().st_size
    tables = []
    with path.open("rb", buffering=0) as stream:
        for table_offset in range(0, min(image_size, 64 * MIB), MIB):
            stream.seek(table_offset)
            header = stream.read(24)
            if len(header) != 24 or header[:4] != b"MPT\0":
                continue
            _, raw_version, count, checksum = struct.unpack("<4s12sII", header)
            if not 1 <= count <= 32:
                continue
            entries_raw = stream.read(count * 40)
            if len(entries_raw) != count * 40:
                continue
            entries = []
            sane = True
            for index in range(count):
                raw_name, size, offset, flags, _ = struct.unpack_from(
                    "<16sQQII", entries_raw, index * 40
                )
                name = raw_name.split(b"\0", 1)[0].decode("ascii", "replace")
                if not name or offset + size > image_size:
                    sane = False
                    break
                entries.append((name, offset, size, flags))
            if not sane:
                continue
            first_words = struct.unpack("<10I", entries_raw[:40])
            calculated = (sum(first_words) * count) & 0xFFFFFFFF
            version = raw_version.split(b"\0", 1)[0].decode("ascii", "replace")
            tables.append((table_offset, version, checksum, calculated, entries))
    return tables


def print_mpt_tables(path: Path) -> None:
    tables = parse_mpt_tables(path)
    print("\nAmlogic MPT partition tables")
    if not tables:
        print("  none detected")
        return
    image_size = path.stat().st_size
    with path.open("rb", buffering=0) as stream:
        for table_offset, version, checksum, calculated, entries in tables:
            state = "valid" if checksum == calculated else "INVALID"
            print(
                f"  table at {offset_text(table_offset)}, version={version}, "
                f"checksum=0x{checksum:08x} ({state})"
            )
            print("    #  name              start MiB    size MiB     end MiB  flags  content")
            for index, (name, offset, size, flags) in enumerate(entries):
                content = probe_filesystem(stream, offset, image_size)
                print(
                    f"    {index:2d} {name:<16} {offset / MIB:10.3f} "
                    f"{size / MIB:11.3f} {(offset + size) / MIB:11.3f} "
                    f"{flags:5d}  {content}"
                )


def print_signature_results(found: dict[bytes, list[int]]) -> None:
    print("\nEmbedded signatures")
    for magic, description in SIGNATURES.items():
        offsets = found[magic]
        if not offsets:
            continue
        print(f"  {description} ({magic!r}):")
        for value in offsets:
            print(f"    {offset_text(value)}")
        if len(offsets) == 128:
            print("    ... result limit reached")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="raw eMMC user-area dump")
    parser.add_argument(
        "--boot-area",
        action="append",
        default=[],
        type=Path,
        help="optional boot0/boot1 dump (repeatable)",
    )
    parser.add_argument(
        "--alignment-mib",
        type=int,
        default=1,
        help="filesystem start alignment to probe (default: 1 MiB)",
    )
    parser.add_argument(
        "--scan-macs",
        action="store_true",
        help="scan the image for plausible colon-separated unicast MAC strings",
    )
    args = parser.parse_args()

    if not args.image.is_file():
        parser.error(f"image not found: {args.image}")
    if args.alignment_mib <= 0:
        parser.error("--alignment-mib must be positive")

    size = args.image.stat().st_size
    print(f"Image: {args.image}")
    print(f"Size:  {size} bytes ({human_size(size)}), {size // 512} sectors")
    print(f"SHA-256 (first 4 MiB): {sha256(args.image, 4 * MIB)}")

    with args.image.open("rb", buffering=0) as stream:
        sector0 = stream.read(512)
        sector1 = stream.read(512)
    print(f"Sector 0: {'all zero' if not any(sector0) else 'contains data'}")
    print(f"GPT header: {'present' if sector1[:8] == b'EFI PART' else 'absent'}")

    for boot in args.boot_area:
        if not boot.is_file():
            parser.error(f"boot area not found: {boot}")
        print(
            f"Boot area: {boot} ({human_size(boot.stat().st_size)}), "
            f"SHA-256={sha256(boot)}, all-zero={'yes' if is_all_zero(boot) else 'no'}"
        )

    print_signature_results(scan_signatures(args.image))
    print_mpt_tables(args.image)

    if args.scan_macs:
        print("\nPlausible ASCII MAC addresses")
        macs = scan_ascii_macs(args.image)
        if not macs:
            print("  none detected")
        for mac, offset in sorted(macs.items(), key=lambda item: item[1]):
            print(f"  {offset_text(offset)}  {mac}")

    print(f"\nFilesystems on {args.alignment_mib} MiB boundaries")
    filesystems = scan_filesystems(args.image, args.alignment_mib * MIB)
    if not filesystems:
        print("  none detected")
    for start, description in filesystems:
        print(f"  {offset_text(start)}  {description}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
