# LibreELEC 12.2 分步补丁

这些补丁面向 LibreELEC `libreelec-12.2`，必须按编号顺序应用：

1. `0001-Amlogic-add-Xiaomi-Mi-Box-4-Linux-support.patch`
   - 引入与 `uboot` 分支同步的最新 Mi Box 4 Linux DTS；
   - 注册 DTB、RTL8723DS 固件和内核配置。
2. `0002-wifi-derive-Mi-Box-4-MAC-from-Meson-eFuse.patch`
   - 回移 NVMEM MAC 读取支持；
   - 在 RTL8723DS 模块 eFuse MAC 无效时使用板载 SoC eFuse WLAN MAC。

```bash
git apply --whitespace=nowarn \
  /path/to/Patches/0001-Amlogic-add-Xiaomi-Mi-Box-4-Linux-support.patch
git apply --whitespace=nowarn \
  /path/to/Patches/0002-wifi-derive-Mi-Box-4-MAC-from-Meson-eFuse.patch
```

它们与仓库根目录的 `LibreELEC-12.2-MiBox4-complete.patch` 等价；只能选择
一种应用方式。

本分支不修改 U-Boot/FIP，也不修改 EMMCTool。镜像目标固定为通用
`UBOOT_SYSTEM=box`，由 Xiaomi vendor U-Boot 通过
`aml_autoscript`/`s905_autoscript` 启动。
