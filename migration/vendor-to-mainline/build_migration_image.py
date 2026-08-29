#!/usr/bin/env python3
"""Build a Vendor-U-Boot-to-Mainline migration image from a Mi Box 4 image."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
from pathlib import Path
import re
import shutil
import struct
import time
import uuid
import zlib

try:
    from pyfatfs.PyFatFS import PyFatFS
except ImportError as exc:
    raise SystemExit(
        "pyfatfs is required: python -m pip install pyfatfs==1.1.0"
    ) from exc


SECTOR_SIZE = 512
UIMAGE_MAGIC = 0x27051956
IH_OS_LINUX = 5
IH_ARCH_ARM64 = 22
IH_TYPE_SCRIPT = 6
IH_COMP_NONE = 0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def decompress_image(source: Path, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".partial")
    temporary.unlink(missing_ok=True)
    try:
        with gzip.open(source, "rb") as compressed, temporary.open("wb") as raw:
            shutil.copyfileobj(compressed, raw, length=8 * 1024 * 1024)
            raw.flush()
            os.fsync(raw.fileno())
        temporary.replace(destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def read_partitions(image: Path) -> list[tuple[int, int, int]]:
    with image.open("rb") as stream:
        mbr = stream.read(SECTOR_SIZE)
    if len(mbr) != SECTOR_SIZE or mbr[510:512] != b"\x55\xaa":
        raise ValueError("image does not contain a valid MBR")

    partitions = []
    for index in range(4):
        entry = mbr[446 + index * 16 : 462 + index * 16]
        part_type = entry[4]
        start_lba, sectors = struct.unpack_from("<II", entry, 8)
        if part_type and sectors:
            partitions.append((part_type, start_lba, sectors))
    if len(partitions) < 2:
        raise ValueError("expected BOOT and DISK partitions")
    return partitions


def fat_uuid(image: Path, offset: int) -> str:
    with image.open("rb") as stream:
        stream.seek(offset)
        boot_sector = stream.read(SECTOR_SIZE)
    if boot_sector[82:90] == b"FAT32   ":
        serial_offset = 67
    elif boot_sector[54:62].startswith(b"FAT"):
        serial_offset = 39
    else:
        raise ValueError("first partition is not a recognised FAT filesystem")
    serial = struct.unpack_from("<I", boot_sector, serial_offset)[0]
    return f"{serial >> 16:04X}-{serial & 0xFFFF:04X}"


def ext_uuid(image: Path, offset: int) -> str:
    with image.open("rb") as stream:
        stream.seek(offset + 1024)
        superblock = stream.read(1024)
    if superblock[0x38:0x3A] != b"\x53\xef":
        raise ValueError("second partition is not an ext filesystem")
    return str(uuid.UUID(bytes=superblock[0x68:0x78]))


def make_legacy_script(source: bytes, name: str) -> bytes:
    # IH_TYPE_SCRIPT prepends a big-endian component-size table terminated by 0.
    payload = struct.pack(">II", len(source), 0) + source
    data_crc = zlib.crc32(payload) & 0xFFFFFFFF
    encoded_name = name.encode("ascii")[:32].ljust(32, b"\0")
    header = struct.pack(
        ">7I4B32s",
        UIMAGE_MAGIC,
        0,
        int(time.time()),
        len(payload),
        0,
        0,
        data_crc,
        IH_OS_LINUX,
        IH_ARCH_ARM64,
        IH_TYPE_SCRIPT,
        IH_COMP_NONE,
        encoded_name,
    )
    header_crc = zlib.crc32(header) & 0xFFFFFFFF
    header = header[:4] + struct.pack(">I", header_crc) + header[8:]
    return header + payload


def replace_file(filesystem: PyFatFS, path: str, data: bytes) -> None:
    if filesystem.exists(path):
        filesystem.remove(path)
    filesystem.writebytes(path, data)


def replace_file_from_path(filesystem: PyFatFS, path: str, source: Path) -> None:
    if filesystem.exists(path):
        filesystem.remove(path)
    with source.open("rb") as input_stream, filesystem.openbin(path, "w") as output_stream:
        shutil.copyfileobj(input_stream, output_stream, length=8 * 1024 * 1024)


def installer_script(
    image_size: int, raw_image_sha256: str, payload_sha256: str
) -> bytes:
    sectors = (image_size + SECTOR_SIZE - 1) // SECTOR_SIZE
    script = f"""#!/bin/sh
set -o pipefail

fail() {{
  echo "error: $*"
  exit 1
}}

[ "$(dtname)" = "xiaomi,mibox4" ] || fail "this is not a Mi Box 4"
[ -f /flash/MIBOX4_VENDOR_MIGRATION ] || fail "migration marker is missing"
[ -f /flash/mibox4-install.img.gz ] || fail "installation payload is missing"

FLASH_PART=$(awk '$2 == "/flash" {{ print $1; exit }}' /proc/mounts)
case "${{FLASH_PART}}" in
  /dev/sd*[0-9]) SOURCE_DISK=$(echo "${{FLASH_PART}}" | sed 's/[0-9]*$//') ;;
  /dev/mmcblk*p[0-9]) SOURCE_DISK=${{FLASH_PART%p*}} ;;
  *) fail "could not identify the external migration disk from ${{FLASH_PART}}" ;;
esac

EMMC=$(find /dev -name 'mmcblk*rpmb' | sed 's/rpmb$//' | head -n 1)
[ -b "${{EMMC}}" ] || fail "eMMC was not detected"
[ "${{SOURCE_DISK}}" != "${{EMMC}}" ] || fail "the system is running from eMMC"

IMAGE_BYTES={image_size}
IMAGE_SECTORS={sectors}
RAW_IMAGE_SHA256={raw_image_sha256}
PAYLOAD_SHA256={payload_sha256}
PAYLOAD=/flash/mibox4-install.img.gz
EMMC_NAME=${{EMMC##*/}}
EMMC_SECTORS=$(cat "/sys/class/block/${{EMMC_NAME}}/size" 2>/dev/null)
case "${{EMMC_SECTORS}}" in
  ''|*[!0-9]*) fail "could not determine eMMC size" ;;
esac
[ "${{EMMC_SECTORS}}" -ge "${{IMAGE_SECTORS}}" ] || fail "eMMC is too small"

echo "info: verifying the embedded installation image"
ACTUAL_PAYLOAD_SHA256=$(sha256sum "${{PAYLOAD}}" | awk '{{ print $1 }}')
[ "${{ACTUAL_PAYLOAD_SHA256}}" = "${{PAYLOAD_SHA256}}" ] || \
  fail "installation payload SHA-256 mismatch"
gzip -t "${{PAYLOAD}}" || fail "installation payload gzip test failed"

AVAILABLE_KIB=$(df -Pk /storage | awk 'NR == 2 {{ print $4 }}')
[ -n "${{AVAILABLE_KIB}}" ] || fail "could not determine /storage free space"
[ "${{AVAILABLE_KIB}}" -ge 614400 ] || fail "/storage needs 600 MiB free"

echo
echo "WARNING: Android, the vendor MPT and all eMMC user data will be erased."
echo "The first 512 MiB and boot0/boot1 will be backed up to USB /storage."
echo "Target image SHA-256: ${{RAW_IMAGE_SHA256}}"
echo "Type MIBOX4-MIGRATE to continue:"
read -r answer
[ "${{answer}}" = "MIBOX4-MIGRATE" ] || fail "migration cancelled"

stamp=$(date +%Y%m%d-%H%M%S)
prefix="/storage/mibox4-vendor-migration-${{stamp}}"
echo "info: backing up the first 512 MiB"
dd if="${{EMMC}}" bs=1M count=512 | gzip > "${{prefix}}-first512M.img.gz" || \
  fail "user-area backup failed"
for area in boot0 boot1; do
  device="${{EMMC}}${{area}}"
  if [ -b "${{device}}" ]; then
    echo "info: backing up ${{device}}"
    dd if="${{device}}" | gzip > "${{prefix}}-${{area}}.img.gz" || \
      fail "${{area}} backup failed"
  fi
done
sync

for mounted in $(awk -v dev="${{EMMC}}" '$1 ~ "^" dev {{ print $1 }}' /proc/mounts); do
  umount "${{mounted}}" || fail "could not unmount ${{mounted}}"
done

echo "info: writing ${{IMAGE_BYTES}} bytes from the embedded image to ${{EMMC}}"
gzip -dc "${{PAYLOAD}}" | dd of="${{EMMC}}" bs=4M || \
  fail "eMMC image write failed"
sync

WRITTEN_MAGIC=$(dd if="${{EMMC}}" bs=1 skip=528 count=4 2>/dev/null)
[ "${{WRITTEN_MAGIC}}" = "@AML" ] || fail "written FIP verification failed"
echo "info: verifying the complete eMMC image"
WRITTEN_SHA256=$(dd if="${{EMMC}}" bs=512 count="${{IMAGE_SECTORS}}" 2>/dev/null | \
  sha256sum | awk '{{ print $1 }}')
[ "${{WRITTEN_SHA256}}" = "${{RAW_IMAGE_SHA256}}" ] || \
  fail "written image SHA-256 mismatch"

echo
echo "info: migration completed"
echo "info: backups use prefix ${{prefix}}"
echo "info: run poweroff, remove the USB drive, then cold power-cycle"
"""
    return script.encode("utf-8")


def patch_boot_files(image: Path, source: Path, scripts_dir: Path) -> dict[str, str]:
    partitions = read_partitions(image)
    _, boot_lba, boot_sectors = partitions[0]
    _, disk_lba, _ = partitions[1]
    boot_offset = boot_lba * SECTOR_SIZE
    disk_offset = disk_lba * SECTOR_SIZE

    with image.open("rb") as stream:
        stream.seek(0x210)
        if stream.read(4) != b"@AML":
            raise ValueError("source image does not contain an Amlogic FIP at 0x210")

    boot_id = fat_uuid(image, boot_offset)
    disk_id = ext_uuid(image, disk_offset)
    raw_image_digest = sha256(image)
    payload_digest = sha256(source)

    filesystem = PyFatFS(str(image), offset=boot_offset, preserve_case=True)
    try:
        required = ["KERNEL", "EXTLINUX/extlinux.conf", "AMLOGIC/meson-gxlx-mibox4.dtb"]
        missing = [path for path in required if not filesystem.exists(path)]
        if missing:
            root_entries = ", ".join(filesystem.listdir("/"))
            extlinux_entries = ", ".join(filesystem.listdir("/EXTLINUX"))
            amlogic_entries = ", ".join(filesystem.listdir("/AMLOGIC"))
            raise ValueError(
                f"BOOT partition is missing: {', '.join(missing)}; "
                f"root contains: {root_entries}; EXTLINUX contains: "
                f"{extlinux_entries}; AMLOGIC contains: {amlogic_entries}"
            )

        extlinux = filesystem.readtext("EXTLINUX/extlinux.conf")
        fdt_match = re.search(r"(?m)^\s*FDT\s+(\S+)\s*$", extlinux)
        append_match = re.search(r"(?m)^\s*APPEND\s+(.+?)\s*$", extlinux)
        if not fdt_match or not append_match:
            raise ValueError("could not parse extlinux.conf")
        bootargs = re.sub(r"\bboot=\S+", f"boot=UUID={boot_id}", append_match.group(1))
        bootargs = re.sub(r"\bdisk=\S+", f"disk=UUID={disk_id}", bootargs)
        uenv = f"dtb_name={fdt_match.group(1)}\nbootargs={bootargs}\n".encode("ascii")

        added: dict[str, bytes] = {
            "uEnv.ini": uenv,
            "aml_autoscript": make_legacy_script(
                (scripts_dir / "aml_autoscript.src").read_bytes(), "MiBox4 migration env"
            ),
            "s905_autoscript": make_legacy_script(
                (scripts_dir / "s905_autoscript.src").read_bytes(), "MiBox4 migration boot"
            ),
            "install-to-emmc.sh": installer_script(
                image.stat().st_size, raw_image_digest, payload_digest
            ),
            "MIBOX4_VENDOR_MIGRATION": (
                "Vendor U-Boot migration bridge for Mi Box 4\n"
                f"BOOT_UUID={boot_id}\nDISK_UUID={disk_id}\n"
            ).encode("ascii"),
        }
        for path, data in added.items():
            replace_file(filesystem, path, data)
        replace_file_from_path(filesystem, "mibox4-install.img.gz", source)
        return {
            "boot_uuid": boot_id,
            "disk_uuid": disk_id,
            "boot_lba": str(boot_lba),
            "boot_sectors": str(boot_sectors),
            "raw_image_sha256": raw_image_digest,
            "payload_sha256": payload_digest,
            **{f"sha256_{name}": hashlib.sha256(data).hexdigest() for name, data in added.items()},
        }
    finally:
        filesystem.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="source Mi Box 4 .img.gz")
    parser.add_argument("output", type=Path, help="output migration .img")
    parser.add_argument("--force", action="store_true", help="overwrite an existing output")
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_file():
        parser.error(f"source image not found: {source}")
    if output.exists() and not args.force:
        parser.error(f"output already exists: {output} (use --force)")
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"Decompressing {source} -> {output}")
    decompress_image(source, output)
    try:
        metadata = patch_boot_files(
            output, source, Path(__file__).resolve().parent / "scripts"
        )
        output_hash = sha256(output)
        manifest = output.with_suffix(output.suffix + ".manifest.txt")
        lines = [
            f"source={source}",
            f"source_sha256={sha256(source)}",
            f"output={output}",
            f"output_bytes={output.stat().st_size}",
            f"output_sha256={output_hash}",
            *(f"{key}={value}" for key, value in sorted(metadata.items())),
        ]
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    except BaseException:
        output.unlink(missing_ok=True)
        raise

    print(f"Created: {output}")
    print(f"SHA-256: {output_hash}")
    print(f"Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
