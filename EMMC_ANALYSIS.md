# 小米盒子 4 eMMC 分析与安装说明

本文针对 Xiaomi Mi Box 4（MDZ-21-AA）和 LibreELEC `libreelec-12.2`
分支。结论来自仓库中的整盘、`boot0` 和 `boot1` dump；分析过程只读，未向
dump 写入数据。

## Dump 结论

- eMMC 用户区大小为 `7,818,182,656` 字节（约 7.28 GiB）。
- 第 0 扇区全零，没有 GPT；签名 Amlogic 启动容器从用户区 `0x200`
  开始，`@AML` 位于 `0x210`。
- `boot0`、`boot1` 均为 4 MiB，内容非空；两者与用户区开头 4 MiB 的
  SHA-256 相同。
- 4 MiB 位置存在校验正确的 Amlogic MPT，版本 `01.00.00`，校验值
  `0x91151330`。
- Android 日志中的 `ro.boot.wifimac` 是固定值，说明原厂 Bootloader
  能从 SoC eFuse 读取板载 WLAN 地址。eMMC dump 只包含日志里的副本，
  并不包含 SoC eFuse 本体。

MPT 分区如下：

| # | 名称 | 起点 MiB | 大小 MiB | 内容 |
|---:|---|---:|---:|---|
| 0 | bootloader | 0 | 4 | Amlogic 签名启动链 |
| 1 | reserved | 4 | 8 | MPT/保留区 |
| 2 | cache | 12 | 256 | ext4 |
| 3 | env | 268 | 4 | Bootloader 环境 |
| 4 | logo | 272 | 3 | 启动画面 |
| 5 | encrypt | 275 | 1 | 厂商数据 |
| 6 | recovery | 276 | 32 | Android boot image |
| 7 | tee | 308 | 8 | TEE |
| 8 | crypt | 316 | 32 | 厂商数据 |
| 9 | misc | 348 | 32 | Android misc |
| 10 | boot | 380 | 20 | Android boot image |
| 11 | system | 400 | 1024 | ext4，内部含 squashfs 数据 |
| 12 | backup | 1424 | 512 | 厂商备份区 |
| 13 | persist | 1936 | 8 | ext4 |
| 14 | panic | 1944 | 4 | 崩溃记录 |
| 15 | data | 1948 | 5508 | ext4 |

因此不能使用原版 `emmctool write` 把通用 box image 从扇区 0 整盘写入；
这样会破坏签名启动容器、MPT、环境和恢复分区，而通用镜像又不包含这台
设备可替换的签名 U-Boot。

可重复运行以下命令验证 dump：

```bash
python3 tools/analyze-emmc-dump.py mibox4-stock-emmc.img \
  --boot-area mibox4-stock-boot0.img \
  --boot-area mibox4-stock-boot1.img
```

## LibreELEC 12.2 补丁

在干净的 LibreELEC `libreelec-12.2` checkout 中，二选一应用补丁。

直接集成全部功能：

```bash
git apply --whitespace=nowarn \
  /path/to/MiBox4-LibreELEC/LibreELEC-12.2-MiBox4-complete.patch
```

或者为了逐步审查、调试，按顺序应用 `Patches/` 下的三个小补丁：

```bash
git apply --whitespace=nowarn \
  /path/to/MiBox4-LibreELEC/Patches/0001-mibox4-device-tree-rtl8723ds.patch
git apply --whitespace=nowarn \
  /path/to/MiBox4-LibreELEC/Patches/0002-mibox4-soc-efuse-wifi-mac.patch
git apply \
  /path/to/MiBox4-LibreELEC/Patches/0003-mibox4-emmctool-safe-install.patch
```

两种方式产生相同的 LibreELEC 源码结果，不能在同一个源码树中重复应用。
`0001`、`0002` 会把实际内核补丁放入 12.2 的 AMLGX 补丁目录，`0003`
修改 LibreELEC 的 EMMCTool 脚本。

构建通用 AMLGX box image：

```bash
PROJECT=Amlogic ARCH=aarch64 DEVICE=AMLGX UBOOT_SYSTEM=box make image
```

写入 USB 后，把其 `uEnv.ini` 中的 DTB 设置为：

```text
dtb_name=/amlogic/meson-gxlx-mibox4.dtb
```

## 固定 Wi-Fi MAC 的 Kernel Patch

厂商 DTS 定义了以下 SoC eFuse 布局：

- `mac`：偏移 `0x00`，6 字节；
- `mac_bt`：偏移 `0x06`，6 字节；
- `mac_wifi`：偏移 `0x0c`，6 字节；
- `usid`：偏移 `0x12`，16 字节。

补丁在板级 DTS 中把 `0x0c..0x11` 声明为 NVMEM cell，并用标准
`nvmem-cell-names = "mac-address"` 关联到 RTL8723DS SDIO function。
rtw88 的逻辑为：

1. Realtek 模块自身 eFuse MAC 有效时保持原行为；
2. 无效时调用 `of_get_mac_address()`，从 Device Tree/NVMEM 获取
   SoC eFuse 中的 WLAN MAC；
3. 两者均无效时才生成随机地址。

该方案只读 SoC eFuse，不会烧写 RTL8723DS 的 OTP eFuse。

启动 LibreELEC 后可检查：

```bash
dmesg | grep -E 'rtw88|firmware MAC|efuse MAC'
cat /sys/class/net/wlan0/address
```

得到的地址应与 Android 下 `getprop ro.boot.wifimac` 一致，并在断电重启
后保持不变。

## 安装到 eMMC

已确认 `adb shell reboot update` 能让本机进入外部 USB。第一次从 USB
启动时，LibreELEC 的 `aml_autoscript` 会把扫描 USB/eMMC 的启动命令保存
到原厂 U-Boot 环境；安装前不要清除该环境。

先确认当前确实从 USB 启动，且 DTB 正确：

```bash
dtname
emmctool info
```

`dtname` 必须输出 `xiaomi,mibox4`。然后执行：

```bash
emmctool install
# 或 emmctool x
```

工具要求输入大写 `MIBOX4`，之后会：

1. 检查 `@AML`、MPT、eMMC 容量、Mi Box 4 DTB 和启动脚本；
2. 要求 USB `/storage` 至少有 600 MiB 空间；
3. 备份用户区前 512 MiB、`boot0` 和 `boot1` 到 USB `/storage`；
4. 只让 MBR 使用扇区 0，并恢复扇区 1 到 512 MiB，保持原厂启动链；
5. 从 512 MiB 起创建 512 MiB FAT32 `BOOT`，从 1024 MiB 起创建 ext4
   `DISK`；
6. 复制当前 USB 的 LibreELEC 启动文件并固定 DTB、`BOOT`/`DISK` 标签。

完成后正常关机，拔掉 USB，再彻底断电重启。USB 未拔除时两个介质会有
相同标签，不应据此判断 eMMC 启动是否成功。

## 风险与恢复边界

- 安装会覆盖 Android `system`、`backup`、`persist`、`panic` 和 `data`
  的大部分或全部内容，Android 将不可启动。
- 自动生成的 512 MiB 备份用于保护/恢复启动链，不是完整 Android 备份。
  仓库中的整盘 dump 才是完整恢复源，务必在其他存储介质保留副本。
- 当前验证包括 dump 结构、LibreELEC 12.2 外层补丁应用、Linux 6.16-rc3
  内层补丁顺序和 shell 语法；最终写入及冷启动仍需在实机上验证。
