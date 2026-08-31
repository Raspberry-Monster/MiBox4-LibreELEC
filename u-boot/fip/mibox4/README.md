# Mi Box 4 FIP inputs

This directory mirrors the standard file names used by
LibreELEC/amlogic-boot-fip for the GXL firmware image package:

- `bl2.sign`, `bl30.enc`, `bl31.enc`: Xiaomi's original signed/encrypted
  early stages, retained byte-for-byte and used by the production FIP.
- `bl33.enc`: the original vendor BL33 wrapper, retained as a reference.
  The build replaces this slot with an encoded Mainline U-Boot BL33.
- `bl2.bin`, `bl30.bin`, `bl31.bin`, `bl33.bin`: decoded inspection copies.
- `fip`, `fip.enc`: extracted FIP metadata/payload references.
- `SHA256SUMS`: hashes of every input.

The Makefile intentionally calls P212's existing `aml_encrypt_gxl` binary.
That binary is reused only as the GXL FIP packaging tool; Mi Box 4 keeps its
own defconfig, device tree and board implementation, and does not reuse P212
U-Boot board code.

The files are copied from `bootloader/mibox4-stock/extracted`. The LibreELEC
board Makefile follows the `LibreELEC/amlogic-boot-fip` interface and emits a
complete `u-boot.bin`/`u-boot.bin.sd.bin` boot container. The extracted stage
files must never be written to eMMC individually.
