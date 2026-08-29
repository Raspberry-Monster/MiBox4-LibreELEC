# LibreELEC 12.2 补丁

本目录提供两种等价的应用方式，只能选择其中一种，不能在同一源码树中混用。

## 一步补丁

在干净的 LibreELEC `libreelec-12.2` 源码树中执行：

```bash
git apply --whitespace=nowarn \
  /path/to/MiBox4-LibreELEC/Patches/LibreELEC-12.2-MiBox4-all-in-one.patch
```

## 分步补丁

需要逐项审查或调试时，按照 `series/series` 的顺序应用：

```bash
while read -r patch; do
  git apply --whitespace=nowarn \
    "/path/to/MiBox4-LibreELEC/Patches/series/${patch}"
done < /path/to/MiBox4-LibreELEC/Patches/series/series
```

补丁顺序按职责整理如下：

1. `0001`：注册 `mibox4` AMLGX 目标，添加板级 Device Tree、RTL8723DS 固件及内核配置。
2. `0002`：Realtek eFuse 地址无效时，从 Meson SoC eFuse 读取稳定的 WLAN MAC。
3. `0003`：添加 U-Boot v2025.07 DTS、正式 `mibox4_defconfig`，把 Mainline BL33 安装为 `/u-boot.ext`。
4. `0004`：扩展 LibreELEC 的 `amlogic-boot-fip` 包，复制标准命名的原厂阶段并用 Mainline BL33 生成 `u-boot-fip.bin`。
5. `0005`：添加保留原厂早期启动链的 EMMCTool 安装、备份和整盘写入保护。

`u-boot/fip/mibox4/` 保存 `bl2.sign`、`bl30.enc`、`bl31.enc`、`bl33.enc`
等标准输入名及校验值。构建时仅重新封装 Mainline BL33；原厂 BL2/BL30/BL31
保持字节不变。

正式启动仍由原厂启动链通过 `s905_autoscript` chainload 原始
`/u-boot.ext`。生成的 `u-boot-fip.bin` 仅作为构建/恢复参考产物进入 release，
不会写入镜像启动扇区，也不会由 EMMCTool 自动刷入 eMMC。

## 构建

```bash
PROJECT=Amlogic ARCH=aarch64 DEVICE=AMLGX \
  UBOOT_SYSTEM=mibox4 make image
```

成功经过 Mainline BL33 后，内核命令行应包含 `mibox4_bl33=mainline`。
禁止把镜像或 `u-boot-fip.bin` 直接写入 eMMC；应先从 USB 启动，再执行
`emmctool install`。
