# How to Boot LibreELEC on Mi Box 4

The dedicated `-mibox4.img.gz` image contains a complete Amlogic FIP in its
raw boot sectors. It combines Xiaomi's signed BL2/BL30/BL31 stages with the
Mainline U-Boot v2025.07 BL33 and boots it directly. The old
`s905_autoscript` → `/u-boot.ext` chainload path is not used.

## Before deployment

Installing to eMMC replaces Android system/data and the active user-area boot
container. Keep all of the following on separate storage before proceeding:

- a complete stock eMMC user-area dump;
- the original eMMC `boot0` and `boot1` dumps;
- a tested Amlogic recovery/USB-burning procedure.

The previous `adb shell reboot update` instructions depended on the removed
vendor-U-Boot chainload path. Use a recovery or external boot method capable
of starting the full FIP image. Do not assume a stock vendor U-Boot autoscript
can load this image.

## Verify a direct Mainline U-Boot boot

After booting the dedicated image, verify the board, U-Boot handoff and source
devices:

```bash
dtname
tr -d '\0' < /sys/firmware/devicetree/base/chosen/u-boot,version; echo
findmnt /flash
findmnt /storage
lsblk -o NAME,TRAN,SIZE,FSTYPE,LABEL,MOUNTPOINTS
```

`dtname` must print `xiaomi,mibox4`, and `u-boot,version` must begin with
`2025.07`. Both mounts must be on the intended external boot device before an
eMMC installation.

## Install to eMMC

Over SSH, inspect the target and start the guarded installer:

```bash
emmctool info
emmctool install
# short form: emmctool x
```

Confirm by typing uppercase `MIBOX4`. The installer then:

1. validates `/chosen/u-boot,version`, the Mi Box 4 DTB and packaged FIP;
2. checks the original `@AML` container, MPT and eMMC capacity;
3. backs up the first 512 MiB plus `boot0` and `boot1` to USB `/storage`;
4. recreates the BOOT/DISK partitions while restoring preserved metadata;
5. writes `u-boot.bin.sd.bin` using LibreELEC's split-sector layout;
6. copies the running LibreELEC boot files and fixes the extlinux labels.

After completion, shut down, remove the external boot device, and cold power
cycle. If the box does not start, stop and restore the saved user-area and
boot-area images with the prepared external recovery workflow.

Never flash `bl2.sign`, `bl30.enc`, `bl31.enc`, or `bl33.enc` individually.
