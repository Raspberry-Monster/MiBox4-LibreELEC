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

Linux and U-Boot use the same standalone Mi Box 4 board description instead
of inheriting the P23x/Q20x/P271 board DTSI. The U-Boot overlay disables the
soldered SDIO Wi-Fi bus so eMMC remains the only MMC boot target and marks the
eMMC and AO UART for U-Boot use.
It also disables UART_A so the RTL8723DS Bluetooth transport and its control
GPIOs remain exclusively under Linux ownership.
Physical UART access requires soldering and is not required or assumed for
validation. LibreELEC loads its separate copy of the board DTB for Linux,
where Wi-Fi and other supported peripherals are enabled.

The U-Boot control DTS reproduces Xiaomi BL33's `gpio set gpioao_4 1` with an
active-high GPIOAO_4 hog. On verified hardware a cold boot left register
`0xc8100024` at `0xbfff3fff`; driving that line high changes it to
`0xbfff3fef` and powers both HDMI and the USB hub. `CONFIG_GPIO_HOG` applies
the state during normal U-Boot driver-model initialization; no early-init
hook or board-specific register write is used.

Xiaomi BL33 also executes `gpio set gpiox_6 1`. The U-Boot overlay owns
GPIOX_6 with an output-high GPIO hog. The Linux DTB remains separate and
represents the same line as an active-high `gpio-leds` power LED.

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
