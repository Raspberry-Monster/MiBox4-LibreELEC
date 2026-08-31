# Mi Box 4 GXL FIP packaging using Xiaomi's signed early-stage wrappers.

O ?= .
TMP ?= .
BL33 ?=
# Reuse the GXL packaging tool shipped in amlogic-boot-fip's P212 directory;
# keeping it in place avoids duplicating or relocating an upstream asset.
AMLICRYPT ?= ../p212/aml_encrypt_gxl
QEMU_LD_PREFIX ?= /usr/x86_64-linux-gnu/

UNAME_M := $(shell uname -m)
ifneq ($(UNAME_M),x86_64)
QEMU := qemu-x86_64 -L $(QEMU_LD_PREFIX)
endif

.PHONY: all clean distclean
.NOTPARALLEL: ${TMP}/bl33.bin.enc ${O}/u-boot.bin

all: ${O}/u-boot.bin

${TMP}/bl33.bin.enc: ${BL33}
	${QEMU} ${AMLICRYPT} --bl3enc --input ${BL33} --output $@

${O}/u-boot.bin: bl2.sign bl30.enc bl31.enc ${TMP}/bl33.bin.enc
	${QEMU} ${AMLICRYPT} --bootmk --output $@ \
		--bl2 bl2.sign --bl30 bl30.enc --bl31 bl31.enc \
		--bl33 ${TMP}/bl33.bin.enc
	test -f ${O}/u-boot.bin.sd.bin
	dd if=${O}/u-boot.bin of=${O}/u-boot.bin.usb.tpl skip=49152 bs=1
	dd if=${O}/u-boot.bin of=${O}/u-boot.bin.usb.bl2 bs=49152 count=1

clean:
	rm -f ${TMP}/bl33.bin.enc

distclean: clean
	rm -f ${O}/u-boot.bin ${O}/u-boot.bin.sd.bin
	rm -f ${O}/u-boot.bin.usb.bl2 ${O}/u-boot.bin.usb.tpl
