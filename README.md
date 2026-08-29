# MiBox4-LibreELEC

This repository contains LibreELEC 12.2 support for Xiaomi Mi Box 4
(MDZ-21-AA), including the board device tree, RTL8723DS/eFuse MAC support,
and a production Mainline U-Boot BL33 integration.

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

The target builds U-Boot v2025.07 with the dedicated `mibox4_defconfig` and
packages its raw `u-boot.bin` as `/u-boot.ext`. It also extends LibreELEC's
`amlogic-boot-fip` package with the standard Mi Box 4 vendor-stage inputs and
generates `u-boot-fip.bin` as a release/reference artifact. Xiaomi's original
BL2/BL30/BL31 and vendor `s905_autoscript` remain the production early boot
chain; they chainload Mainline BL33 from the selected USB or eMMC boot
partition. Mainline U-Boot scans USB first and then eMMC, while using
`CONFIG_ENV_IS_NOWHERE` so Xiaomi's persistent environment is never modified.

The image fixes `meson-gxlx-mibox4.dtb` in `uEnv.ini` and `extlinux.conf`, and
marks a successful Mainline BL33 boot with `mibox4_bl33=mainline`. The custom
EMMCTool installer requires that marker and `/flash/u-boot.ext`, backs up the
original boot-chain area, preserves Xiaomi's early stages, and only then
migrates the running image to eMMC. Never write the image directly to eMMC.

See [bootloader/mibox4-stock/](bootloader/mibox4-stock/) for the extracted
vendor source, [u-boot/fip/mibox4/](u-boot/fip/mibox4/) for the standard FIP
input names, [u-boot/](u-boot/) for the DTS/defconfig overlay, and
[EMMC_ANALYSIS.md](EMMC_ANALYSIS.md) for layout, recovery, and installation
details. Neither the extracted stages nor `u-boot-fip.bin` are installed into
the eMMC boot area automatically.

**Disclaimer:** This repository is provided without any warranty. Use it at your own risk.

Licensed under the **GNU General Public License v2.0 (GPL-2.0)**.
