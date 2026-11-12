# TB323FU — LineageOS 24 设备树

作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017

联想拯救者 Y700 五代（**TB323FU，SM8850P / kaanapali**）平板的非官方
**LineageOS 24（Android 17）** 设备树。

本仓库完整记录并自动化了**从零移植到首次开机**的全过程：设备配置、构建修复、
first-stage 挂载排查、安全启动（AVB）处理、EDL/fastbootd 刷写流程，以及让
LineageOS 在本机启动所需的全部根因调查。

英文说明见 [README.md](README.md)。

## 当前状态（2026-11-12）

| 项 | 状态 |
|---|---|
| 构建（LineageOS 24.0，`lineage_TB323FU-cp2a-userdebug`） | ✅ 可构建，镜像已校验 |
| 首次开机 | ✅ 可进入 LineageOS 桌面 |
| 重启稳定性 | ✅ 连续 3 次重启全部通过（`sys.boot_completed=1`） |
| /data 文件级加密（FBE） | ✅ `ro.crypto.state=encrypted`、`type=file` |
| 硬件功能 | ⚠️ 部分未验证，见 [04-HARDWARE-SUPPORT](docs/zh-CN/04-HARDWARE-SUPPORT.md) |
| 当前构建形态 | ⚠️ 调试/bring-up 态（SELinux permissive、dm-verity off、test-keys、详细启动日志） |

这是**移植底座**，不是发布版 ROM；刷机前请先读文档。

## 设备

| 项 | 值 |
|---|---|
| 机型 | Lenovo Legion Y700 Gen5（TB323FU） |
| 平台 | 高通 SM8850P / kaanapali（`canoe`） |
| 分区 | A/B + 独立 recovery，virtual A/B，4 KiB 页，super 20 GiB |
| 屏幕 | 1904×3040 竖屏，120 Hz |
| 原厂基线 | 联想 A17（`TB323FU_CN_OPEN_USER_Q00037.0_A17_ZUXOS_2.5.10.036_ST_261027`） |
| 解锁 | bootloader 已解锁（orange），B 槽激活 |

完整分区/LUN 表与刷写几何见 [docs/zh-CN/01-DEVICE-FACTS.md](docs/zh-CN/01-DEVICE-FACTS.md)。

## 构建快速开始

要求：Linux（WSL2 Ubuntu 24.04 可用）、约 60 GiB 源码 + 150 GiB 输出空间、
`repo`、JDK，以及 LineageOS 24.0 manifest。

```bash
# 1) 同步 LineageOS 24.0
repo init -u https://github.com/LineageOS/android -b lineage-24.0 --git-lfs --no-repo-verify
repo sync -c -j"$(nproc)"

# 2) 放置本设备树
mkdir -p device/lenovo
git clone https://github.com/UGY1412/android_device_lenovo_TB323FU device/lenovo/TB323FU

# 3) 从“你自己的原厂固件”提取 proprietary blobs
cd device/lenovo/TB323FU && ./extract-files.py /path/to/your/dump

# 4) 编译
source build/envsetup.sh
lunch lineage_TB323FU-cp2a-userdebug
mka systemimage
```

使用原厂 6.12 GKI 内核（本仓库不含内核源码；请从自己的固件提取）。构建细节、
坑与已知构建错误见 [docs/zh-CN/02-BUILD.md](docs/zh-CN/02-BUILD.md)。

> 本仓库**刻意不含任何二进制**：`prebuilt/Image`（内核）与 `prebuilts/dtbo.img`
> 均已排除，获取方法见 [02-BUILD](docs/zh-CN/02-BUILD.md)。

## 刷写快速开始

设备必须已解锁。两条路线：

- **EDL（9008）**：设备无法正常进入系统时首选（`docs/zh-CN/03-FLASH.md` §EDL）。
- **fastbootd**：设备还能进 recovery/fastbootd 时使用（`...§fastbootd`）。

两条路线都必须：**解锁 bootloader** + **做一次 Factory data reset**（清掉旧
metadata 损坏）。不要刷半套镜像；每个分区的期望 SHA-256 都在文档里。

## 文档索引（中英双语）

完整索引：[docs/README.md](docs/README.md)

12 篇主题：设备事实 / 构建 / 刷写 / 硬件矩阵 / `/vendor` 自指环根因 /
logdump 写坏 metadata 根因 / FBE 与 `init_user0` / SELinux 策略 / AVB 链 /
无 pstore 调试通道 / 错误目录 / 实验台账。

如果设备卡第一屏或反复重启，先读 05、06、11 三篇。

## 工具

`tools/` 是 bring-up 期间使用的参考脚本（EDL 刷 F0 镜像、system 块级补丁、
super 拼包、启动日志分类）。路径已脱敏为 `<PROJECT_ROOT>` / `<WORKSPACE>`
占位符，使用前必须按本机路径修改；说明见 [tools/README.md](tools/README.md)。

## 相关仓库

- 橙狐 / TWRP recovery 树：[android_device_lenovo_TB323FU-orangefox](https://github.com/UGY1412/android_device_lenovo_TB323FU-orangefox)
- AERA Recovery 树：[android_device_lenovo_TB323FU-aera](https://github.com/UGY1412/android_device_lenovo_TB323FU-aera)

## 致谢

所有被使用/参考的上游项目见 [CREDITS.md](CREDITS.md)（AOSP、LineageOS、
TWRP/TeamWin、TWRP-Test、polygraphene、OrangeFox、AERA、isrgish、
aweiyry/lenovo-ota-tool、DeepSeek V4.1 Flash 1017）。合规与归属政策见
[docs/COMPLIANCE.md](docs/COMPLIANCE.md)。

## 许可

原创文件：Apache-2.0（见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)）；三方文件
保留各自原有通知；不分发任何专有二进制。

## 免责声明

本项目按 **“AS IS”** 提供，不附带任何明示或暗示担保。刷机、解锁或修改设备
可能导致数据丢失、设备无法启动或加密数据无法访问；是否使用、如何备份由你自行
决定并承担全部责任。维护者不对任何损坏或后果负责。

本项目为非官方社区项目；Lenovo、Legion、Qualcomm、Snapdragon、Android、
LineageOS、TeamWin、OrangeFox、AERA 等商标归各自所有者，本项目与它们无隶属
或被认可关系。
