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

补丁职责如下：

1. `0001`：添加 Linux 板级 Device Tree、RTL8723DS 固件及内核配置。
2. `0002`：Realtek eFuse 地址无效时，从 Meson SoC eFuse 读取稳定的 WLAN MAC。
3. `0003`：添加 U-Boot v2025.07 板级代码、DTS 和 `mibox4_defconfig`。
4. `0004`：扩展 `amlogic-boot-fip`，使用原厂签名 BL2/BL30/BL31 和 Mainline BL33 构建完整 `u-boot.bin.sd.bin`。
5. `0005`：注册 `mibox4` 构建目标，并接入 LibreELEC 原生 `mkimage_uboot` 镜像路径。
6. `0006`：将 `xiaomi,mibox4` 加入 EMMCTool 支持的板型检查。

`u-boot/fip/mibox4/` 保存原厂包装阶段和校验值。构建时重新封装 Mainline
BL33，生成的完整 FIP 由 LibreELEC 标准 `mkimage_uboot` 写入镜像启动扇区。
镜像中不再包含 `/u-boot.ext`，也不再通过原厂 U-Boot chainload BL33。

U-Boot 会使用标准 FDT fixup 在 Linux 设备树的 `/chosen` 节点中写入
`u-boot,version`，可在写入 eMMC 前用于人工确认当前启动链；不再添加
`mibox4_bl33=mainline` 内核命令行参数，也不维护 Mi Box 4 专用安装流程。

## 构建

```bash
PROJECT=Amlogic ARCH=aarch64 DEVICE=AMLGX \
  UBOOT_SYSTEM=mibox4 make image
```

完整 FIP 会修改设备启动容器。部署前必须保留可用的整盘、boot0 和 boot1
备份，并准备外部恢复方法。
