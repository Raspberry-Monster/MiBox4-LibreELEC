# MiBox4-LibreELEC

This repository contains device tree and LibreELEC 12.2 patches for the
Xiaomi Mi Box 4 (MDZ-21-AA). Apply
[`LibreELEC-12.2-MiBox4-complete.patch`](LibreELEC-12.2-MiBox4-complete.patch)
for a one-step integration, or use the ordered patches in [`Patches/`](Patches/)
for development and review.

The original DTB/DTS files were extracted from the stock firmware with the assistance of Codex.

The adapted device tree adds internal eMMC, Bluetooth, and RTL8723DS Wi-Fi
support. The kernel patch reads the stable WLAN MAC address from the Meson SoC
eFuse through NVMEM when the RTL8723DS eFuse address is invalid. The custom
EMMCTool installer preserves the signed vendor boot chain instead of writing a
generic image over it.

See [EMMC_ANALYSIS.md](EMMC_ANALYSIS.md) for the dump layout, patch choices,
build steps, MAC design, installation procedure, and recovery limits.

**Disclaimer:** This repository is provided without any warranty. Use it at your own risk.

Licensed under the **GNU General Public License v2.0 (GPL-2.0)**.
