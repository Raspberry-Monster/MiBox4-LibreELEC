# MiBox4-LibreELEC

This repository contains LibreELEC 12.2 support for Xiaomi Mi Box 4
(MDZ-21-AA), including the board device tree, RTL8723DS/eFuse MAC support,
and a production Mainline U-Boot FIP integration.

The board DTS is independent from the P23x/Q20x/P271 reference-board DTSI.
It reports the hardware as `Xiaomi Mi Box 4 (MDZ-21-AA)`, describes all four
vendor eFuse fields (Ethernet, Bluetooth, WLAN, and USID), and currently
exposes HDMI as the only audio output. Analog/CVBS audio and video are not
enabled.

RTL8723DS Bluetooth wiring is documented in the DTS, but its UART and child
node intentionally remain disabled. The required board-matching Bluetooth
firmware/configuration is not available from upstream `linux-firmware`, so
this repository does not add a private Bluetooth firmware patch to
LibreELEC. Wi-Fi remains enabled and uses `rtw88/rtw8723d_fw.bin`.

The front-panel power LED is GPIOX_6, active high. Mainline U-Boot explicitly
turns it on during `board_init()`, matching Xiaomi BL33, and Linux keeps it on
through the standard `gpio-leds` binding.

For a one-step integration, apply
[Patches/LibreELEC-12.2-MiBox4-all-in-one.patch](Patches/LibreELEC-12.2-MiBox4-all-in-one.patch):

```bash
git apply --whitespace=nowarn \
  Patches/LibreELEC-12.2-MiBox4-all-in-one.patch
```

For review and development, the equivalent ordered patch series is under
[Patches/series/](Patches/series/). Do not mix the two application methods.

The formal image target is `UBOOT_SYSTEM=mibox4`:

```bash
PROJECT=Amlogic ARCH=aarch64 DEVICE=AMLGX \
  UBOOT_SYSTEM=mibox4 make image
```

The target builds U-Boot v2025.07 with the dedicated `mibox4_defconfig`. It
extends LibreELEC's `amlogic-boot-fip` package with Xiaomi's signed
BL2/BL30/BL31 inputs, replaces BL33 with the freshly built Mainline U-Boot,
and produces the standard `u-boot.bin.sd.bin`. LibreELEC's native
`mkimage_uboot` path writes that complete FIP into the image boot sectors.
There is no `/u-boot.ext` and no vendor-U-Boot chainload step. Mainline U-Boot
scans USB first and then eMMC, while using `CONFIG_ENV_IS_NOWHERE` so Xiaomi's
persistent environment is never modified.

The image fixes `meson-gxlx-mibox4.dtb` in `extlinux.conf`. U-Boot's standard
FDT fixup publishes its version as `/chosen/u-boot,version`; no private kernel
command-line marker is used. The resulting image follows LibreELEC's standard
Amlogic SBC disk layout and can be written to eMMC with `emmctool write`.
The EMMCTool patch only adds `xiaomi,mibox4` to the supported-board check.

See [bootloader/mibox4-stock/](bootloader/mibox4-stock/) for the extracted
vendor source, [u-boot/fip/mibox4/](u-boot/fip/mibox4/) for the standard FIP
input names, [u-boot/](u-boot/) for the DTS/defconfig overlay, and
[How_To_Install_LibreELEC.md](How_To_Install_LibreELEC.md) for recovery and
installation details. The extracted stage files must never be flashed
individually.

**Disclaimer:** This repository is provided without any warranty. Use it at your own risk.

Licensed under the **GNU General Public License v2.0 (GPL-2.0)**.
