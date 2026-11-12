作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0 (original text)

# 01 · 设备事实 —— 联想拯救者 Y700 五代（TB323FU）

| 字段 | 内容 |
|---|---|
| 状态 | 2026-11-12 —— LineageOS 24.0（Android 17）已能启动到桌面；首启 + 连续 3 次重启回归 PASS |
| 适用设备 | 仅联想拯救者 Y700 五代，型号 **TB323FU**；项目代号 `baldur` / `baldur_prc_wifi` |
| 范围 | 硬件/平台身份、原厂固件基线、分区/LUN 几何、槽位状态、AVB 启动链，以及「设备当前实际刷写内容」基线 |
| 证据来源 | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md`；`CURRENT-STATE.md`（§1/§4/§9）；`out/2026-11-11-los24-bootfix/FLASH-CHECKLIST.md`；`out/2026-11-10-los24-logdump/RESTORE-RUNBOOK.md`；`out/2026-11-10-los24-logdump/restore-map.tsv`；`work/research/B-tb323fu-hardware.md`；`out/2026-11-12-edl-f0/device/postflash-final/getprop-final.txt`；`refs/readback-full/`；设备树 `BoardConfig.mk` |

> **本系列文档约定**
> - 所有 LBA 一律按 **4 KiB 逻辑扇区**（`SECTOR_SIZE_IN_BYTES=4096`）表示，与本机 GPT 及高通 Firehose 工具的取值口径一致。
> - SHA-256 按源日志记录的原样给出；尾部 `…` 表示源记录只保留了前缀。源记录有完整值的，给出完整值。
> - 「待验证」标记：有文档记录但尚未在当前版本上重新实测的数据点。
> - 证据分级：**实测**（有设备日志/属性支撑）、**仅声明**（仅有属性或文档）、**推断**。凡可能被误当成实测的结论，均标注分级。

## 1. 身份信息

| 项 | 值 | 证据 |
|---|---|---|
| 型号 / 设备名 | `TB323FU` | `ro.product.model`、`ro.product.device`（getprop） |
| 市场名 | 联想拯救者 Y700 五代（Lenovo Legion Y700 Gen 5） | 项目记录 |
| 序列号 | `<SN-REDACTED>` | 设备报告（本仓库已脱敏） |
| 项目代号 | `baldur` / `baldur_prc_wifi` | 硬件调研报告 |
| SoC | 高通 **SM8850P**（平台 `canoe`，family `f-canoe`，属 "kaanapali" 平台族），市场名 Snapdragon 8 Elite Gen 5 | `ro.soc.model=SM8850P`、`ro.board.platform=canoe`、`dmesg` cmdline `hqsysfs.pcba_hwid=SM8850P_12+256_11` |
| 内存 / 存储档位 | 12 GB + 256 GB（取自 pcba_hwid 串） | `dmesg` 内核 cmdline |
| CPU ABI | 仅 arm64-v8a（无 32 位用户态）；运行期 CPU variant `oryon` | vendor 属性、`BoardConfig.mk` |
| 内核 | `6.12.69-android16-6-gb133545a642b-ab15507861-4k`（`#1 SMP PREEMPT Wed May 27 17:46:34 UTC 2026`） | `dmesg` 第 2 行 |
| 内核页大小 | 4096 B（`ro.boot.hardware.cpu.pagesize=4096`、`ro.product.page_size=4096`；最大支持 16384） | getprop |
| 槽位结构 | A/B + 独立 recovery 分区，virtual A/B，`super` = 20 GiB，**本机只有 `_b` 逻辑分区** | GPT + LP 元数据 |
| Bootloader 状态 | 已解锁，`verifiedbootstate=orange`，`secure=no` | getprop + fastboot getvar 历史记录 |
| UFS | `1d84000.ufshc`，UFS ICE v4.0.3，MCQ 9 队列 / 8 I/O 队列，队列深度 64 | `dmesg` |

## 2. 原厂固件基线

| 项 | 值 |
|---|---|
| 原厂市场固件 | `ZUXOS_2.5.10.036_ST_261027`（Android 17） |
| 原厂构建标识 | `TB323FU_CN_OPEN_USER_Q00037.0_A17_DF_2.5.02.165_260924`，build 版本 `DF_2.5.02.165_260924_PRC`，incremental `165` |
| Android 版本 / SDK | 17 / 37 |
| 原厂 vendor 指纹 | `Lenovo/TB323FU_PRC/TB323FU:17/CQ2A.260712.001/DF_2.5.02.165_260924_PRC:user/release-keys` |
| 原厂 system 指纹 | `Lenovo/TB323FU_PRC/TB323FU:17/...:user/release-keys`（原厂构建；相关分区已被替换） |
| 原厂内核 | `6.12.69-android16-6-gb133545a642b-ab15507861-4k`（4 KiB 页，KMI `android16-6`） |

### 2.1 本文档系列对应的 LineageOS 构建

| 项 | 值 |
|---|---|
| 构建指纹 | `Lenovo/lineage_TB323FU/TB323FU:17/CP2A.260605.016/eng.root:userdebug/test-keys` |
| LineageOS 版本串 | `24-20261107-UNOFFICIAL-TB323FU` |
| Build ID / 安全补丁 | `CP2A.260605.016` / `2026-11-01` |
| 产品 / 变体 | `lineage_TB323FU` / `userdebug`（test-keys） |
| 目标槽位 | 2026-11-12 验收时为 `_b` 活动 |
| 说明 | `vendor` 分区保持原厂（未改动），因此 `ro.vendor.build.fingerprint` 仍报联想原厂串。这符合「最小内容替换」设计。 |

## 3. 分区 / LUN 几何

设备共暴露 **6 个 UFS LUN**。每个 LUN 的 GPT 均已全量回读（`refs/readback-full/gpt_main0..5.bin`；回读集 156 个文件 / 24.71 GiB，SHA-256 已 156/156 校验通过）。

### 3.1 LUN 概览

| LUN | 分区数 | current_lba | backup_lba | first_usable | last_usable | 容量 |
|---|---|---|---|---|---|---|
| 0 | 14 | 1 | 61390847 | 6 | 61390842 | 234.19 GiB |
| 1 | 9 | 1 | 5119 | 6 | 5114 | 0.02 GiB |
| 2 | 9 | 1 | 5119 | 6 | 5114 | 0.02 GiB |
| 3 | 3 | 1 | 8191 | 6 | 8186 | 0.03 GiB |
| 4 | 99 | 1 | 1048575 | 6 | 1048570 | 4.00 GiB |
| 5 | 6 | 1 | 8191 | 6 | 8186 | 0.03 GiB |

LUN0 承载 `super`、`userdata`、`metadata`、`misc`；LUN1/LUN2 为两个 XBL 槽；LUN3 为 CDT/DDR；**LUN4 承载整条启动链以及全部 `_a`/`_b` 状态分区**；LUN5 为 modem 文件系统区。

### 3.2 LUN0 —— `super` 与 userdata 所在

| 分区 | start_lba | 扇区数 | 字节数 |
|---|---|---|---|
| oemowninfo | 6 | 256 | 1,048,576 |
| ssd | 262 | 2 | 8,192 |
| persist | 264 | 8192 | 33,554,432 |
| misc | 8456 | 256 | 1,048,576 |
| keystore | 8712 | 128 | 524,288 |
| frp | 8840 | 128 | 524,288 |
| **super** | **8968** | **5,242,880** | **21,474,836,480** |
| vbmeta_system_a | 5,251,848 | 16 | 65,536 |
| vbmeta_system_b | 5,251,864 | 16 | 65,536 |
| metadata | 5,251,880 | 16,384 | 67,108,864 |
| rawdump | 5,268,264 | 131,072 | 536,870,912 |
| dataext_a | 5,399,336 | 131,072 | 536,870,912 |
| dataext_b | 5,530,408 | 131,072 | 536,870,912 |
| userdata | 5,661,480 | 55,729,363 | 228,267,470,848 |

### 3.3 LUN4 —— 关键启动链与状态分区

| 分区 | start_lba | 扇区数 | 字节数 | 备注 |
|---|---|---|---|---|
| boot_a / boot_b | 119,078 / 489,006 | 24,576 | 100,663,296 | 内核启动镜像（OEM 签名链） |
| vbmeta_a / vbmeta_b | 143,706 / 513,634 | 16 | 65,536 | 根 vbmeta（原厂为 OEM key；root 时用 testkey E12 形态） |
| dtbo_a / dtbo_b | 143,722 / 513,650 | 18,432 | 75,497,472 | 被根 vbmeta 的 hash 描述符锁定 |
| vendor_boot_a / vendor_boot_b | 302,310 / 672,238 | 24,576 | 100,663,296 | first-stage fstab 位于该 ramdisk 内 |
| recovery_a / recovery_b | 334,630 / 696,878 | 25,600 | 104,857,600 | 独立 recovery 分区 |
| init_boot_a / init_boot_b | 360,742 / 722,990 | 2,048 | 8,388,608 | 通用 ramdisk（A/B OTA 分区） |
| pvmfw_a / pvmfw_b | 362,806 / 725,054 | 256 | 1,048,576 | 受保护 VM 固件；被 vbmeta_system 的 hash 锁定 |
| efisp | 732,182 | 768 | 3,145,728 | 持久状态；**红线，禁止写** |
| devinfo | 732,950 | 1 | 4,096 | 持久状态（`ANDROID-BOOT!` 头）；红线 |
| logfs | 733,207 | 2,048 | 8,388,608 | 持久日志区；红线 |
| logdump | 735,255 | 131,072 | 536,870,912 | 512 MiB 日志分区，诊断 init_boot 使用 |
| uefivarstore | 866,359 | 128 | 524,288 | UEFI 变量存储；红线 |
| secdata | 866,487 | 7 | 28,672 | 持久状态；红线 |
| xbl_sc_logs | 938,766 | 32 | 131,072 | XBL 日志区 |
| dpm | 938,798 | 2 | 8,192 | 持久状态 |

LUN1/LUN2 各承载一套 XBL 槽（`xbl`、`xbl_config`、`multiimgqti`、`multiimgoem`、`apdp`、TME 件）；LUN3 = `ALIGN_TO_128K_1`、`cdt`、`ddr`；LUN5 = `ALIGN_TO_128K_2`、`modemst1`、`modemst2`、`fsg`、`fsc`、`fs_bkup`。完整 147 行映射见 `out/2026-11-10-los24-logdump/restore-map.tsv`。

### 3.4 `super` 布局（原厂；4 KiB 扇区）

| 项 | 值 |
|---|---|
| 物理 `super` | LUN0 @ LBA 8968，21,474,836,480 B（20 GiB），5,242,880 扇区 |
| LP 元数据 | v10.2，`metadata_max=65536`，3 个 slot，4 KiB 逻辑块 |
| 组名 | `qti_dynamic_partitions`（组名不带槽位后缀） |
| 组上限 | 21,470,642,176 B |
| 本机逻辑分区集 | 仅 slot 1（`_b`）：`system`、`system_ext`、`product`、`vendor`、`odm`、`vendor_dlkm`、`system_dlkm` |

原厂逻辑分区尺寸（均等于对应原厂 `.img` 的实际长度）：

| 逻辑分区 | 字节数 |
|---|---|
| system | 10,235,101,184 |
| system_ext | 562,970,624 |
| product | 2,167,775,232 |
| vendor | 2,202,816,512 |
| odm | 334,217,216 |
| vendor_dlkm | 118,259,712 |
| system_dlkm | 14,868,480 |

LUN0 上的物理 LP extent（用于 EDL 直接块写入；已与 `restore-map.tsv` 及独立 LP 解析交叉核对）：

| 逻辑分区 | 物理起始 LBA | 扇区数 | 字节数 |
|---|---|---|---|
| system_b | 620,062 | 2,498,804 | 10,235,101,184 |
| system_ext_b | 3,122,496 | 137,444 | 562,970,624 |
| vendor_b | 3,259,940 | 537,797 | 2,202,816,512 |

> LineageOS 移植未修改原厂 `super` 的 LP 元数据：整个 `super` 只重建/修补逻辑分区区间内部的内容。内容修补后 `super` 前 64 KiB 仍保持原厂 SHA-256 前缀 `fc016362…c573`。

### 3.5 分区表（GPT）锚点

| 对象 | SHA-256 | 说明 |
|---|---|---|
| `gpt_main0`（LUN0 主 GPT） | `162114fe…` | 原厂布局；2026-11-12 EDL 写前/写后均只读复核 |
| `gpt_main4`（LUN4 主 GPT） | `cb20a8b2…c25cc` | `boot_b` 是 GPT entry #53 |
| `gpt_backup4`（LUN4 备份 GPT） | `11892a4f…06ac20` | 主/备必须成对写入 |
| `boot_b` 槽位属性 | GPT entry #53，byte 54 = `0x6F` | `0x6F` = ACTIVE + SUCCESSFUL + 未标记 unbootable；其它 `_b` 分区 = `0x44`；unbootable 态 = `0xEF` |

高通平台的 `AB_FLAG_OFFSET = 48 + 6 = 54`，即 8 字节 GPT 属性字段的 bit 48–55；`ACTIVE=0x04`、`SUCCESSFUL=0x40`、`UNBOOTABLE=0x80`。启动失败会再次置 `0x80`，因此应先完成内容修复，再重复尝试启动。

## 4. 槽位状态与 AVB 链事实

原厂根 `vbmeta_b`（SHA-256 `ae4ebd61…f54d7`，OEM 公钥 sha1 `8fcb864f…`，rollback index 0）声明：

- `chain` → `boot`（RI location 3）、`recovery`（RI location 1）、`vbmeta_system`（RI location 2）；
- `hash` → `dtbo`、`vendor_boot`；
- `hashtree` → `dataext`、`odm`、`system_dlkm`、`vendor`、`vendor_dlkm`。

原厂 `vbmeta_system_b`（SHA-256 `493448e6…0399b`，rollback index `1788566400`，RI location 2）声明：

- `hash` → `init_boot`、`pvmfw`；
- `hashtree` → `product`、`system`、`system_ext`。

本机已确认的实际影响：

1. **仅用户态分区可安全替换**（`system`、`system_ext`、`product`）：每次重建只需按新镜像 footer 的 digest 重签 `vbmeta_system`。
2. `boot` 与 `recovery` 由 **OEM key** 链接，本移植不得替换。
3. `init_boot`、`dtbo`、`vendor_boot` 被根 vbmeta（`dtbo`、`vendor_boot`）或 `vbmeta_system`（`init_boot`）hash 锁定；替换需对应重签。
4. 本机 ABL 接受 **AOSP testkey**（公钥 sha1 `2597c218aae470a130f61162feaae70afd97f011`）作为信任根，即 "E12" 形态：根 vbmeta 用 testkey 签，`chain boot/recovery → OEM`、`chain vbmeta_system → testkey`。chained vbmeta 的 flags **必须为 0**；非 0 会被判为 `ERROR_INVALID_METADATA`。
5. 必需分区上的 dm-verity 不匹配**不会**因为已解锁而被豁免：first-stage 挂载失败后 init 直接 `LOG(FATAL)`。绕过 verity 的唯一开关是根 vbmeta `flags=1/2`，当前诊断刷写集正是这样做的。

## 5. 设备当前实际内容（截至 2026-11-12 20:50）

最后一次写入是 2026-11-12 20:24–20:26 的 **EDL（9008）直写**。逐分区权威表（LUN、物理 LBA、大小、镜像、SHA-256）见 `03-FLASH.md` §3；摘要：

| 分区 | 当前内容 |
|---|---|
| `system_b` | `system_raw_nologdump.raw` + 9 块 / 36 KiB 块补丁（`blocks.tsv`、`system_b_changed_blocks.bin`）；移除 `logdump.sh`/`logdump.rc`，并携带 SELinux policy 扇区补丁 |
| `system_ext_b` | `system_ext_f0diag.img`（去 SetupWizard + 自动 provision + logcat→rawdump） |
| `vendor_b` | `vendor_b_full_stock.img`（原厂 vendor 字节） |
| `vendor_boot_b` | `vendor_boot_diag2.img`（first-stage fstab 去 avb flags + `no_fail`；`androidboot.selinux=permissive` + `printk.devkmsg=on`） |
| `init_boot_b` | `init_boot_logging13.img`（kmsg→logdump 捕获） |
| `vbmeta_system_b` | `vbmeta_system_v10.img`（与 logging13 配对；verity-off，其 system digest 不被校验） |
| `product_b` | LineageOS `product_b`（2026-11-11 22:46 经 fastbootd 写入，此后未动） |
| `vbmeta_b` | E12 testkey 根（`7ed20919…`） |
| `boot_b` / `dtbo_b` / `recovery_b` | 原厂，未动（回退锚点 `boot_b = 2731d62c…`） |
| GPT / misc / super LP 头 | 原厂（`gpt_main0 162114fe…`、`gpt_main4 cb20a8b2…`）；BCB 为空；本轮未写 |

验证状态：首启到达 Launcher，`sys.boot_completed=1`、`init.svc.bootanim=stopped`、`ro.crypto.state=encrypted`（`ro.crypto.type=file`）、`/metadata` 挂载于 `sda10`（f2fs）、`/data` 挂载于 `dm-49`（f2fs，inlinecrypt）；连续 3 次 `adb reboot` 均为 `boot_completed=1`（`RESULT: PASS`，exit 0）。

## 6. 硬件要点

完整功能/HAL 矩阵见 `04-HARDWARE-SUPPORT.md`。要点：

| 子系统 | 事实 |
|---|---|
| 显示 | 物理 1904 × 3040，8.8 英寸，CSOT 面板 + Novatek NT36523N 控制器，双 DSI，30/60/90/120/144/165 Hz，440 dpi，HDR10 / 广色域，圆角屏 |
| 触控 / 笔 | Novatek NVT 电容触控 + 笔输入（SPI，级联，PID 0x609F）；支持联想 Tab Pen Plus 蓝牙笔 |
| 触感 / LED | 双 Awinic AW86937 马达；AW22127 LED 控制器（原厂 dmesg 抓取中曾报 `aw22xxx_fw.bin` 缺失导致 LED 固件加载失败；F0 刷后设备日志显示固件加载成功） |
| NFC | 原厂 dmesg 有 NXP NFC I²C 驱动；但 NFC HAL **未**在 `canoe` SKU manifest 中声明（只在无关的 `alor` manifest 中）→ 实际是否存在**待验证** |
| 音频 | `audiohalservice.qti`、AGM/PAL、Dolby DAX3；vendor 内含 canoe SKU mixer 配置 |
| 相机 | `vendor.qti.camera.provider-service_64`；实际 sensor 型号/数量**待验证** |
| 连接 | QTI WLAN（wlan0、wifi-aware0）、Bluetooth A2DP/LE-Audio、GNSS；`ro.vendor.config.lgsi.device.nettype=wifi` |
| 存储 | UFS 4.x 级控制器；外置 SD 经 `8804000.sdhci`；USB-OTG 存储经 DWC3 |

## 7. 已知注意事项与待验证项

1. **当前刷写集是诊断态，不是发布态**：SELinux permissive、dm-verity off、testkey 根 vbmeta、`init_boot` = logging13、`system_ext` 去向导/自动 provision、`system_b` 带 policy 扇区补丁。收尾配方见 `03-FLASH.md` §8 与各根因文档。
2. **硬件功能尚未实测**——目前只确认 HAL/服务在开机后存在（F1 测试轮待做）。见 `04-HARDWARE-SUPPORT.md`。
3. **`/dataext` 缺失**：当前 LineageOS `system` 镜像根目录没有 `/dataext`（原厂 system-as-root 有）。首轮修复有意未包含；补法需要 `BOARD_ROOT_EXTRA_FOLDERS += dataext` 加 SELinux `file_contexts` 映射。见 `02-BUILD.md` §7。
4. **历史记录偏差（保留以便追溯）**：早期笔记记录 00:35 曾写过 `logging13` + `vbmeta_system_v10`；20:17 只读预检实测设备上为 `logging10` + `v8`。原因未查明，且不影响 F0 结果；F0 写入按计划把两者覆盖为 `logging13` + `v10`。
5. 设备 RTC 运行在 GMT（`persist.sys.timezone=GMT`），屏幕/日志时间比 Asia/Shanghai 早 8 小时。属正常现象，不影响启动。
6. 本机**只有 `_b` 逻辑分区**；当前 `super` LP 元数据中不存在 A 槽逻辑分区。不要尝试刷写 A 槽逻辑分区。
7. 本仓库对序列号与本地路径做脱敏（`<SN-REDACTED>`、`<PROJECT_ROOT>`、`<WORKSPACE>`、`<USER_HOME>`）。

## 8. 证据来源（按章节）

| 章节 | 主要证据 |
|---|---|
| §1 身份 | `out/2026-11-12-edl-f0/device/postflash-final/getprop-final.txt`；`dmesg` 摘录；`work/research/B-tb323fu-hardware.md` §0.2/§4.6 |
| §2 原厂基线 | 硬件调研报告 §0.2/§5.1；`F0-ACCEPTANCE-REPORT.md` §1；刷后 `getprop-final.txt` |
| §3 分区/LUN 几何 | `work/research/B-tb323fu-hardware.md` §2（基于 `refs/readback-full/gpt_main0..5.bin` 的 GPT 复算）；`RESTORE-RUNBOOK.md` §3/附录 B；`F0-ACCEPTANCE-REPORT.md` §2；`restore-map.tsv` |
| §4 槽位状态 / AVB | `RESTORE-RUNBOOK.md` §3；`out/2026-11-10-los24-logdump/LOS24-PLAYBOOK-CONSOLIDATED.md` §3.2/§3.3；`FLASH-CHECKLIST.md` §0 |
| §5 当前刷写集 | `F0-ACCEPTANCE-REPORT.md` §2/§3；`CURRENT-STATE.md` §4/§5 |
| §6 硬件 | `work/research/B-tb323fu-hardware.md` §1/§3/§4；`postflash-final/ps-A.txt`；`postflash-final/logcat-all.txt` |
| §7 注意事项 | `F0-ACCEPTANCE-REPORT.md` §5/§8；`CURRENT-STATE.md` §6；`BUILD-FIX-REPORT.md` §8 |
