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

## Analog mute GPIO trace

The vendor DTB describes the sound-card mute as
`mute_gpio-gpios = <&gpio 0x15 0>` together with `mute_inv`. The GXL
peripheral GPIO ABI starts GPIOH after GPIOZ_0..15, so linear ID `0x15`
(decimal 21) is GPIOH_5. This is not a BL33-global GPIO number: Xiaomi's
vendor BL33 contains an older, different bank-number table. Its decoded bank
descriptor at file offset `0xbc8d0` nevertheless identifies the GPIOH bank
and register bit base 20, but that legacy table exposes only GPIOH_0..3.
Linux's GXL bank definition exposes GPIOH_0..9 with the same bit base, so
GPIOH_5 is register bit 25. This is why a BL33 numeric GPIO ID must not be
used to interpret the vendor kernel's `0x15` specifier.

The decoded BL33 contains startup commands for GPIOX_9, GPIOX_6, and
GPIOAO_4 at offsets `0xaa2ce`, `0xaa2ef`, and `0xaa302`. It contains no
command that drives GPIOH_5, so Linux must own the analog mute line. The GXL
GPIO registers provide a non-invasive hardware check: bit 25 (`0x02000000`)
of `0xc883443c` is output-enable (zero means output), `0xc8834440` is output
level, and `0xc8834444` is input level. Read them before, during, and after
analog playback:

```text
devmem 0xc883443c 32
devmem 0xc8834440 32
devmem 0xc8834444 32
```

With the Mainline `simple-audio-amplifier` route active, GPIOH_5 should go
high only while the AV line-output DAPM path is powered. Confirm the same
low/high transition at the mute transistor or amplifier enable pin with a
meter or oscilloscope. Do not write the whole GPIO registers with `mw` or
`devmem`; they contain unrelated GPIO lines.
