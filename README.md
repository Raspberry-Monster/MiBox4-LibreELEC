# MiBox4-LibreELEC

This branch provides LibreELEC 12.2 support for Xiaomi Mi Box 4
(MDZ-21-AA) while retaining Xiaomi's vendor U-Boot boot chain.

The Linux board device tree is synchronized from the latest `uboot` branch
version. It describes the standalone Mi Box 4 hardware, RTL8723DS Wi-Fi,
eFuse MAC cells, HDMI/USB power, analog audio, eMMC, and the absence of an
SD-card slot.

Apply either the one-step patch:

```bash
git apply --whitespace=nowarn LibreELEC-12.2-MiBox4-complete.patch
```

or the two ordered patches documented in [Patches/README.md](Patches/README.md).
Do not mix the two methods.

Build the standard AMLGX generic-box image:

```bash
PROJECT=Amlogic ARCH=aarch64 DEVICE=AMLGX \
  UBOOT_SYSTEM=box make image
```

This branch does not build or install a dedicated Mainline U-Boot/FIP. Xiaomi's
vendor U-Boot starts LibreELEC through the generic box
`aml_autoscript`/`s905_autoscript` flow. Select
`/amlogic/meson-gxlx-mibox4.dtb` in `uEnv.ini` before booting.

EMMCTool is intentionally unmodified. LibreELEC's default generic-box/SBC
safety behavior remains in effect, so this branch does not provide or endorse
an automated eMMC installation path.

See [How_To_Install_LibreELEC.md](How_To_Install_LibreELEC.md) for USB boot
instructions.

**Disclaimer:** This repository is provided without any warranty. Use it at
your own risk.

Licensed under the **GNU General Public License v2.0 (GPL-2.0)**.
