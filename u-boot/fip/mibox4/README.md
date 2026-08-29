# Mi Box 4 FIP inputs

This directory mirrors the standard file names used by
LibreELEC/amlogic-boot-fip for the GXL firmware image package:

- `bl2.sign`, `bl30.enc`, `bl31.enc`: Xiaomi's original signed/encrypted
  early stages, retained byte-for-byte.
- `bl33.enc`: the original vendor BL33 wrapper, retained as a reference.
  The production build replaces this slot with the Mainline BL33 wrapper.
- `bl2.bin`, `bl30.bin`, `bl31.bin`, `bl33.bin`: decoded inspection copies.
- `fip`, `fip.enc`: extracted FIP metadata/payload references.
- `SHA256SUMS`: hashes of every input.

The files are copied from `bootloader/mibox4-stock/extracted`. They are
reference inputs for FIP packaging and must never be written directly to eMMC.

