# How to Boot LibreELEC on Mi Box 4

## Requirements

You will need:

- A USB hub with at least two ports
- A USB drive
  - At least 4 GiB if you do not plan to back up the stock system image
  - 16 GiB or larger is recommended
- A working computer with [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) installed
- A brave and calm mind

## Boot LibreELEC from USB

1. Write the LibreELEC image to the USB drive using Rufus or another disk-imaging tool.

   Rufus is the only tool I have tested.

2. After flashing the image, a FAT32 partition should appear.

3. Open `uEnv.ini` on that partition and replace `@@DTB_NAME@@` with `meson-gxlx-mibox4.dtb`.

   The resulting line should look like this:

   ```ini
   dtb_name=/amlogic/meson-gxlx-mibox4.dtb
   ```

4. Connect the USB drive to the USB hub, then connect the hub to the Mi Box 4.

5. Boot the device normally into MIUI TV and enable ADB debugging.

6. From your computer, connect to the Mi Box 4 using:

   ```bash
   adb connect YOUR_BOX_IP_ADDRESS
   ```

7. Once the ADB connection has been established, run:

   ```bash
   adb shell reboot update
   ```

   The Mi Box 4 should then reboot into LibreELEC.

If you only want to run LibreELEC from USB, you are done.

If you want to install LibreELEC to the internal eMMC, continue with the steps below.

## Install LibreELEC to eMMC

> [!WARNING]
> Installing LibreELEC to the internal eMMC may brick your device.
> Back up the original disk image before proceeding.
>
> **Proceed at your own risk.**

Log in to LibreELEC via SSH, then run the following command in the SSH shell:

```bash
emmctool install
```

This installs LibreELEC to the internal eMMC.

After the installation is complete, shut down the device and unplug the USB drive. The Mi Box 4 should then boot LibreELEC directly from its internal eMMC.