# 分步骤补丁

这些补丁面向 LibreELEC `libreelec-12.2` 源码仓库，必须按编号顺序应用：

1. `0001-mibox4-device-tree-rtl8723ds.patch`：加入 Mi Box 4 Device Tree、
   RTL8723DS 固件选择和内核配置；
2. `0002-mibox4-soc-efuse-wifi-mac.patch`：通过 NVMEM 读取 SoC eFuse 中的
   WLAN MAC，并在 Realtek eFuse MAC 无效时交给 rtw88 使用；
3. `0003-mibox4-emmctool-safe-install.patch`：加入保留原厂签名启动链的
   eMMC 安装流程及安装前备份。

```bash
git apply --whitespace=nowarn /path/to/Patches/0001-mibox4-device-tree-rtl8723ds.patch
git apply --whitespace=nowarn /path/to/Patches/0002-mibox4-soc-efuse-wifi-mac.patch
git apply /path/to/Patches/0003-mibox4-emmctool-safe-install.patch
```

它们与仓库根目录的 `LibreELEC-12.2-MiBox4-complete.patch` 等价；请只选择
其中一种方式，不要重复应用。
