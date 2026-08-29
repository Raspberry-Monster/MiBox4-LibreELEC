# Mi Box 4 Mainline U-Boot overlay

These files target U-Boot `v2025.07`, the version used by LibreELEC 12.2.

- Copy `configs/mibox4_defconfig` to U-Boot's `configs/` directory.
- Copy `dts/meson-gxlx-mibox4.dts` to
  `dts/upstream/src/arm64/amlogic/`.
- Copy `dts/meson-gxlx-mibox4-u-boot.dtsi` to `arch/arm/dts/`.

LibreELEC appends its common Amlogic options to the defconfig, including
`CONFIG_EFI_LOADER=n`, compression commands, and `CONFIG_BOOTDELAY=0`.

The dedicated config deliberately does not enable `CONFIG_MISC_INIT_R`.
The shared P212 board implementation reads Ethernet/serial eFuse fields at
P212-specific offsets which do not match the Mi Box 4 layout. The resulting
U-Boot uses `CONFIG_ENV_IS_NOWHERE=y`, so it does not persist an environment
over Xiaomi's vendor `env` partition.

Only the eMMC, USB host, and AO UART paths needed during early bring-up are
enabled in the U-Boot control DT. The UART nodes are retained as build-time
debug support, but physical UART access requires soldering on the Mi Box 4 and
is not required or assumed for validation. LibreELEC loads its separate kernel
DTB for Linux, where Wi-Fi and other peripherals remain enabled.

For a standalone build with an AArch64 cross-toolchain:

```sh
make CROSS_COMPILE=aarch64-linux-gnu- mibox4_defconfig
make CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)"
```

The validated compiler output is `u-boot.bin` (BL33). The production
LibreELEC target passes it to `amlogic-boot-fip`, combines it with Xiaomi's
signed BL2/BL30/BL31 stages, and installs the resulting
`u-boot.bin.sd.bin` through LibreELEC's standard bootloader image path.

The [fip/mibox4/](fip/mibox4/) directory contains the Xiaomi stages under the
standard names expected by `LibreELEC/amlogic-boot-fip`: `bl2.sign`,
`bl30.enc`, `bl31.enc`, and the original `bl33.enc`, plus decoded references,
FIP metadata and `SHA256SUMS`. LibreELEC patch `0004` copies these files into
the package and encodes the freshly built Mainline BL33. The image boots this
full FIP directly; it does not contain or chainload `/u-boot.ext`.

When booting Linux, U-Boot v2025.07 adds its standard `u-boot,version`
property below `/chosen`. Runtime checks should read that device-tree property
instead of adding a board-specific kernel command-line argument.
