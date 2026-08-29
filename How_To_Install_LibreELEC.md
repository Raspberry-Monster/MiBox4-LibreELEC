# How to Boot LibreELEC on Mi Box 4

You will need the dedicated `-mibox4.img.gz` image (not the generic AMLGX
`-box.img.gz`), a USB drive and hub, and Android Platform Tools.

## Boot from USB

1. Write the dedicated image to USB with Rufus, LibreELEC USB-SD Creator, or
   another disk-imaging tool.
2. Do not edit `uEnv.ini`. The image already contains
   `dtb_name=/amlogic/meson-gxlx-mibox4.dtb`, the Mainline BL33
   `/u-boot.ext`, and the vendor autoscripts.
3. Connect the USB drive through the hub, enable ADB debugging in Android, and
   run:

   ```bash
   adb connect YOUR_BOX_IP_ADDRESS
   adb shell reboot update
   ```

4. After reboot, verify that the formal chain completed:

   ```bash
   grep -o 'mibox4_bl33=mainline' /proc/cmdline
   findmnt /flash
   findmnt /storage
   lsblk -o NAME,TRAN,SIZE,FSTYPE,LABEL,MOUNTPOINTS
   ```

   Both mounts must be on the USB device. The vendor BL2/BL30/BL31 and
   `s905_autoscript` are still the early stages; Mainline U-Boot is BL33.

## Install to eMMC

> Installing to eMMC destroys Android system/data and can brick the device.
> Keep a complete stock dump and the generated backup on separate storage.

Never use `emmctool write` and never write the image or a FIP directly to eMMC.
The production installer preserves the vendor boot container and environment.
The build may publish `u-boot-fip.bin` as a diagnostic/recovery artifact; it
is not `/u-boot.ext`, is not copied into the boot filesystem, and must not be
flashed by this installation procedure.

Boot the USB image, confirm the marker and mounts above, then over SSH run:

```bash
dtname
emmctool info
emmctool install
# short form: emmctool x
```

Confirm by typing uppercase `MIBOX4`. The installer requires
`dtname=xiaomi,mibox4`, `/flash/u-boot.ext`, and
`mibox4_bl33=mainline`; it backs up the first 512 MiB plus eMMC boot areas,
preserves the vendor chain, creates `BOOT`/`DISK`, and copies the running
image. After completion, shut down, remove USB, and cold-power-cycle.

If anything fails, restore the saved first-512-MiB and boot0/boot1 backups with
an external recovery workflow. Do not experiment on the live eMMC boot area.
