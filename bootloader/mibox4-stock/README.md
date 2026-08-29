# Extracted Xiaomi Mi Box 4 boot chain

Source: `mibox4-stock-boot0.img`, copied from the read-only backup at
`D:\Projects\MiBox4 Stock Image Backup`.

The original 4 MiB boot0 image contains a zero sector followed by the GXL boot
container. `bootloader-sector1.bin` is the same image with the first 512-byte
sector removed for `gxlimg -e`.

`extracted/` contains both the original wrapped stages and decoded inspection
copies:

- `bl2.sign` / `bl2.bin`: DDR/early board initialization and BL21 payload.
- `bl30.enc` / `bl30.bin`: SCP system-management firmware and BL301 payload.
- `bl31.enc` / `bl31.bin`: ARM Trusted Firmware.
- `bl33.enc` / `bl33.bin`: Xiaomi vendor U-Boot.
- `fip.enc` / `fip`: encrypted and decoded FIP metadata extracted by gxlimg.

The encoded files are the authoritative inputs for repacking. Do not rebuild
BL2, BL30, or BL31 from the decoded inspection copies.

