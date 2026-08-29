# Mi Box 4 Vendor-to-Mainline migration image

This directory builds a one-time USB migration image from a complete Mi Box 4
LibreELEC image. The resulting image retains the full Mainline U-Boot FIP in
the raw disk sectors and adds a temporary Vendor U-Boot boot bridge to the FAT
BOOT partition. It also stores the pristine source image as
`/mibox4-install.img.gz`; this avoids copying a USB `/storage` filesystem after
LibreELEC has expanded it to the USB drive's capacity.

The bridge does not use `u-boot.ext`. Xiaomi's Vendor U-Boot executes
`s905_autoscript`, which loads `KERNEL`, `uEnv.ini`, and the Mi Box 4 DTB
directly from USB. After Linux starts, `/flash/install-to-emmc.sh` verifies and
decompresses that pristine image to eMMC, then verifies the complete written
image.

## Build

Install the image-editing dependency:

```sh
python -m pip install pyfatfs==1.1.0
```

Then run:

```sh
python build_migration_image.py \
  LibreELEC-AMLGX.aarch64-12.2-mibox4.img.gz \
  output/LibreELEC-AMLGX.aarch64-12.2-mibox4-vendor-migration.img
```

Write the resulting `.img` to a USB drive of at least 2 GB with `dd`, Rufus,
or another raw image writer.

## Boot and install

With the USB drive attached, Android users can run `adb shell reboot update`.
An already configured Vendor LibreELEC installation can normally be cold
booted with the USB attached. The first autoscript pass may save the Vendor
U-Boot environment and reboot once before Linux starts.

After USB boot, both mounts must be on the USB device:

```sh
findmnt /flash
findmnt /storage
```

Install the full image to eMMC with:

```sh
sh /flash/install-to-emmc.sh
```

The installer requires the exact confirmation `MIBOX4-MIGRATE`, backs up the
first 512 MiB plus `boot0` and `boot1` to USB `/storage`, then overwrites the
eMMC user area with the migration image. Android, the Vendor MPT, recovery,
and all eMMC user data are destroyed. The eMMC hardware boot partitions are
backed up but are not modified.
