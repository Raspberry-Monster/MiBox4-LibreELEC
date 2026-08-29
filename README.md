# MiBox4-LibreELEC

This repository contains LibreELEC 12.2 support for Xiaomi Mi Box 4
(MDZ-21-AA), including the board device tree, RTL8723DS/eFuse MAC support,
and a production Mainline U-Boot FIP integration.

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
command-line marker is used. The custom EMMCTool installer checks that
property, backs up the original boot areas, preserves the Xiaomi firmware
stages inside the newly assembled FIP, and writes the FIP through the same
split-sector layout used by `mkimage_uboot`.

See [bootloader/mibox4-stock/](bootloader/mibox4-stock/) for the extracted
vendor source, [u-boot/fip/mibox4/](u-boot/fip/mibox4/) for the standard FIP
input names, [u-boot/](u-boot/) for the DTS/defconfig overlay, and
[How_To_Install_LibreELEC.md](How_To_Install_LibreELEC.md) for recovery and
installation details. The extracted stage files must never be flashed
individually.

**Disclaimer:** This repository is provided without any warranty. Use it at your own risk.

Licensed under the **GNU General Public License v2.0 (GPL-2.0)**.
