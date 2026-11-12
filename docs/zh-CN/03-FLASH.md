作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0

# 03 · 刷写 —— TB323FU 刷写、校验与回退

| 字段 | 内容 |
|---|---|
| 状态 | 2026-11-12 —— 下文 EDL（9008）直写路线即产出「首启 PASS + 连续 3 次重启回归 PASS」的路线；fastbootd 路线保留为历史备选 |
| 适用设备 | 联想拯救者 Y700 五代，型号 **TB323FU**，槽位 `_b`，bootloader 已解锁 |
| 范围 | 各写入通道的真实能力、当前刷写集（分区 / LUN / LBA / 大小 / 镜像 / SHA-256）、分步路线、写后校验、回原厂锚点、红线、故障处置 |
| 证据来源 | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md`；`out/2026-11-11-los24-bootfix/F0-FLASH-BUNDLE.md`；`out/2026-11-11-los24-bootfix/FLASH-CHECKLIST.md`；`out/2026-11-11-los24-bootfix/F0-ACCEPTANCE-CHECKLIST.md`；`out/2026-11-11-los24-bootfix/MORNING-RUNBOOK.md`；`out/2026-11-10-los24-logdump/RESTORE-RUNBOOK.md`；`out/2026-11-10-los24-logdump/LOS24-PLAYBOOK-CONSOLIDATED.md`（§3.1–§3.6）；`refs/readback-full/` |

> **先读这段。** 本文档记录的是在一台实机上做过并验证过的操作。刷写可能变砖、清空 `/data`，或用错包触发反回滚。写任何分区之前：确认分区与 LUN、核对镜像 SHA-256、明确回退锚点。**永远不要相信 EDL 的 `SUCCESS`**——写入的唯一证据是回读哈希或内容指纹。

## 1. 写入通道能力矩阵（本机实测）

| 通道 | LUN0 | LUN4 | 说明 / 证据 |
|---|---|---|---|
| Bootloader fastboot（`is-userspace=no`） | 只读 | 只读 | 仅 `getvar` / `reboot` / `reboot recovery`；`flash` 返回 `remote: 'unknown command'`；`oem edl` 同样 unknown |
| fastbootd（`is-userspace=yes`） | `super` 与逻辑分区 | `vbmeta_b`、`init_boot_b` 等 | 从可启动系统或 recovery 用 `adb reboot fastboot` / `fastboot reboot fastboot` 进入；自动 sparse 传输，13 GB 约 20 s 级 |
| recovery `dd` | Yes | | 可写任意物理/逻辑分区，路径 `/dev/block/by-name/*`；已用 SHA-256 回读验证 |
| EDL + `fh_loader`（2026-11-10 起写法） | Yes | | 需 `--zlpawarehost=1`，XML 带 `label` / `partofsingleimage=false` / `readbackverify=false`；写后回读比对 |
| EDL 旧写法（无 `--zlpawarehost`、裸 LBA） | 部分 | 假成功 | `ERROR: invalid gpt entry number 128` 之后仍打印 `{All Finished Successfully}`——不要用 |
| EDL 读 | 有假成功史 | 有假成功史 | 只能作为辅助，需两次独立回读 / 内容指纹互证 |
| GeekFlashTool（全量包） | Yes | | 历史上唯一「一键回原厂」通道；曾写坏 LUN0 备份 GPT（5 扇区 bug） |
| `adb reboot edl`（软 EDL） | No | | 进入的是不应答 Sahara 的 9008；写入被静默丢弃 |

**单工具铁律：** 同一时刻只允许一个主机工具占用 9008 端口；GUI 工具占住 COM3 时必须关闭并重新插拔进 EDL。每次进入 EDL 只允许一次 Sahara/programmer 握手。

## 2. 当前刷写集（最后一次写入：2026-11-12 20:24–20:26，EDL 直写）

所有 LBA 均为 4 KiB 扇区。`GPT = refs/readback-full/gpt_main0.bin / gpt_main4.bin`。LP 分区物理 LBA = `super` 起始 LBA 8968 + `offset/4096`（两个独立来源一致，独立 LP 解析确认 7 个 `_b` 逻辑分区全部为单 extent 线性映射）。

| 分区 | LUN | 物理 LBA | 扇区数 | 大小（B） | 刷入内容 | SHA-256 |
|---|---|---|---|---|---|---|
| `system_b` | 0 | 620062 | 2,498,804 | 10,235,101,184 | 在 `system_raw_nologdump.raw` 之上的 **9 块 / 36 KiB 补丁**（块 0,1,3,30,53,62069,65536,79494,81367；删除 `logdump.sh` + `logdump.rc`，并含 policy 扇区） | raw `b6ca50f5…`；块数据 `2e563f37…`；块清单 `f21ccc7f…` |
| `system_ext_b` | 0 | 3122496 | 137,444 | 562,970,624 | `system_ext_f0diag.img`（去 SetupWizard + aera-provision + logcat→rawdump） | `e1addc29…` |
| `vendor_b` | 0 | 3259940 | 537,797 | 2,202,816,512 | `vendor_b_full_stock.img`（原厂 vendor 字节） | `08caa9a6…` |
| `vendor_boot_b` | 4 | 672238 | 24,576 | 100,663,296 | `vendor_boot_diag2.img`（first-stage fstab 去 avb flags + `no_fail`；`androidboot.selinux=permissive` + `printk.devkmsg=on`） | `40623569…` |
| `init_boot_b` | 4 | 722990 | 2,048 | 8,388,608 | `init_boot_logging13.img`（kmsg→logdump 捕获） | `baf1133d…` |
| `vbmeta_system_b` | 0 | 5251864 | 16 | 65,536 | `vbmeta_system_v10.img`（与 logging13 配对；verity-off，system digest 不被校验） | `2b52e26b…` |
| `misc` | 0 | 8456 | 256 | 1,048,576 | **未写**（实测 BCB 为空；reset 前无需清） | — |
| `/data`、`/metadata` | — | — | — | — | 由用户在 stock recovery 点 **Factory data reset** 真正格式化（Windows 上 `fastboot -w` 只擦不格式化） | — |

未改动分区：`boot_b`、`dtbo_b`、`recovery_b`、`vbmeta_b`（E12 testkey 根）、GPT、`super` LP 头、`media` 及其它所有分区。

被修补件的完整文档：

| 件 | 完整 SHA-256 |
|---|---|
| `system_raw_nologdump.raw`（10,235,101,184 B） | `b6ca50f586a80584473c97d44e75f7f3013dd50a17f6f56ef1c47c69b5c709ba` |
| `system_b_changed_blocks.bin`（36,864 B） | `2e563f37a786f6644fe087a8cbcabc2afbc94d7ce7798499e01be78c533bd5f3` |
| `blocks.tsv`（375 B） | `f21ccc7f73019c6b48cd3aec4c61ad12060980b0f4b3744d28da7953c9c660fa` |
| `flash-system-blocks.py`（9,990 B） | `b1c47db6cddf65b40b95f6628fe91094e5c9a4a45293deab3a8229bbd931fd13` |
| `vendor_b_full_stock.img`（2,202,816,512 B） | `08caa9a653332bc2e86063f4dd7f545b7760cc83524a68713b6df1eea6897957` |
| `vendor_boot_diag2.img`（100,663,296 B） | `406235697d5df9a95a5425b6ddeed26413cda11da41a88c5612317909345f969` |
| `init_boot_logging13.img`（8,388,608 B） | `baf1133d9699240dd64b069d5792a7b21348121d1b16d53f14b405d8c5ff0c78` |
| `vbmeta_system_v10.img`（65,536 B） | `2b52e26b9c1bc8f15562d5e22a1fc2eced0d5721a432e15846ee26901fce4afc` |
| `system_raw_fixed.raw`（F0 前 system；含 logdump，仅作回退） | `1e7ec2d126d2889340578182b78121af7b39dbd1bc2165f39852cf4453673ff8` |
| `vbmeta_system_v8.img`（F0 前配对签名） | `bfd496d922e66d9cc547769d8eb4846d41ce46a52d23e0245a5d4499f98fe2f7` |
| `init_boot_logging10.img`（F0 前配对 init_boot） | `4511a32e…` |

## 3. 路线 A（推荐，已验证）：EDL / 9008 直写

### 3.1 前置条件

| 项 | 值 |
|---|---|
| 设备模式 | 9008 / EDL（`Qualcomm HS-USB QDLoader 9008`，历史为 COM3） |
| 工具链 | `fh_loader.exe`（SHA-256 前缀 `22507A0B…C5DBA`）、`QSaharaServer.exe`（`F1274519…C838DBD`）、programmer `devprg_legion-y700-5-2.0.11.043`（联想专用，8 个文件） |
| 端口 | `\\.\COM3`（以设备管理器实际为准） |
| 电量 | > 30%；整个流程保持连线 |
| 纪律 | 保持 Firehose 连接（不 reset）直到全部写完，最后只发一次 `power reset` |

### 3.2 第 1 步 —— 只读预检

```powershell
python edl-precheck.py
```

写盘前完成的检查：

- GPT LUN0/LUN4 与原厂 `refs/readback-full` 镜像比对（预期 MATCH）；当前槽位状态；
- `misc` 的 BCB（boot control block）内容（预期为空）；
- 把 9 个目标 `system_b` 块分类为 `OLD` / `NEW`（F0 前预期 8 OLD + 1 NEW）；
- 记录在役 `init_boot_b` / `vbmeta_system_b` 的 SHA-256（便于追溯）。

**预检后不要 reset**——写盘步骤复用该 Firehose 连接。

### 3.3 第 2 步 —— 写 9 块 / 36 KiB system 补丁

```powershell
python flash-system-blocks.py --no-reset
```

- 块号：`0, 1, 3, 30, 53, 62069, 65536, 79494, 81367`（每块 4 KiB，共 36,864 B）；
- 目标 LBA（LUN0，4 KiB LBA = 620062 + 块号）：`620062, 620063, 620065, 620092, 620115, 682131, 685598, 699556, 701429`（共 8 段）；
- 脚本校验 `blocks.tsv` 严格升序/唯一、块数据恰为 9 × 4096 B、所有 LBA 落在 `system_b` extent 内；
- 写后回读 first / middle / last 并逐字节比对，只有打印 `ALL OK` 才算成功。

为什么用块补丁而不是写 10 GiB：该修复恰好只改 9 块（36 KiB），EDL 传输以秒计，且长时间传输中断不会破坏未触碰区域。

### 3.4 第 3 步 —— 写其余五个分区

```powershell
python edl-write-f0.py --no-reset
```

在同一条 Firehose 连接中写入，并逐件做 head/tail 回读（小分区做全量回读）：

| 顺序 | 分区 | 大小 | LUN |
|---|---|---|---|
| 1 | `vendor_b` | 2.05 GiB | 0 |
| 2 | `system_ext_b` | 537 MiB | 0 |
| 3 | `vendor_boot_b` | 96 MiB | 4 |
| 4 | `init_boot_b` | 8 MiB | 4 |
| 5 | `vbmeta_system_b` | 64 KiB | 0 |

LUN4 分区的 EDL XML 必须带 `label=`、`partofsingleimage="false"`、`readbackverify="false"`、`sparse="false"`、`SECTOR_SIZE_IN_BYTES="4096"`，命令行必须带 `--zlpawarehost=1`；镜像必须位于 `--search_path` 内且以 basename 引用。

### 3.5 第 4 步 —— 写后校验（必须）

```powershell
python edl-dump-system-blocks.py --no-reset     # 期望 NEW 9/9
python edl-write-f0.py --verify-only            # 逐分区回读比对
```

验收判据是**内容相等**，不是 Firehose 的 `SUCCESS` 行。已验收的那次：9 块全部 `NEW`，每个写入分区回读 `ALL OK`，并且几何分别用 `restore-map.tsv` 与 `regions.json` 独立复算，零差异。

### 3.6 第 5 步 —— 复位与首启

1. `power reset`（fh_loader `<power value="reset"/>`；已验收那次 9008 设备在数秒内消失，设备落入 **stock recovery**——这是预期行为，因为旧 `/metadata` 已被旧 `logdump` 写坏）。
2. **用户在设备上点一次「Factory data reset」。** 这会真正格式化 `/data` + `/metadata`（由 stock recovery 执行格式化；Windows platform-tools 的 `fastboot -w` 只擦除）。
3. 设备重启，约 1 分钟后 MTP 枚举、adb 上线；预期首启 3–6 分钟进桌面（无 SetupWizard，因为已从 `system_ext` 删除向导并强制 provision）。

### 3.7 第 6 步 —— 验收

```powershell
f0-postboot-verify.ps1 -RebootTest 3
```

PASS 判据（必须全部满足）：

- 首启与之后 3 次重启循环中 adb 均在线且 `sys.boot_completed=1`；
- `init.svc.bootanim=stopped`；
- `/metadata` 已挂载（`sda10` f2fs）、`/data` 已挂载（`dm-49` f2fs，inlinecrypt）；
- `ro.crypto.state=encrypted`、`ro.crypto.type=file`；
- `init_user0` 只出现 1 条正常 `fscrypt_init_user0`；`init_user0_failed` / `Failed to create /metadata` / `mount_all --late` 命中为 0；
- 设备上 `logdump.sh` / `logdump.rc` 不存在；
- 脚本打印 `RESULT: PASS` 且 exit code 0。

已验收那次的时间线（本地时间）：

| 时间 | 事件 |
|---|---|
| 20:11 | 确认设备处于 9008（COM3） |
| 20:17 | EDL 只读预检：GPT MATCH、BCB 空、9 块 = 8 OLD + 1 NEW；在役 `init_boot_b=logging10`、`vbmeta_system_b=v8` |
| 20:24:36 | 写入 9 块补丁 + 回读 MATCH |
| 20:24:40–20:24:53 | 写入 5 个分区 + 回读 ALL OK（vendor 2.05 GiB / 8.3 s） |
| 20:28:16 | 写后复核：9 块 = **NEW 9/9** |
| 20:28:34 | `power reset` |
| 20:29:17 | 落 stock recovery（计划内） |
| ~20:29:5x | 用户点 **Factory data reset** |
| 20:30:22 | MTP 枚举 |
| 20:35:00 | **首启 PASS**：adb 在线、`boot_completed=1` |
| 20:37:51–20:39:27 | **3/3 重启回归 PASS**（`RESULT: PASS`，exit 0） |

## 4. 路线 B（历史备选）：fastbootd 全量写入

2026-11-11 用该路线首次达成开机；在 EDL 不可用、且设备能进 fastbootd 时作为备选保留。

```powershell
fastboot devices
fastboot reboot fastboot          # 进入 fastbootd（用户态 fastboot）
fastboot getvar is-userspace      # 期望：yes
fastboot getvar current-slot      # 期望：b

fastboot flash system_b system_raw_nologdump.raw     # 10 GiB，镜像必须精确等于 extent 长度
fastboot flash vendor_b vendor_b_full_stock.img
fastboot flash vendor_boot_b vendor_boot_diag2.img
fastboot flash init_boot_b init_boot_logging13.img
fastboot flash vbmeta_system_b vbmeta_system_v10.img
fastboot flash system_ext_b system_ext_f0diag.img
fastboot -w
fastboot reboot
```

说明：

- fastbootd 会按镜像 footer 自动 resize 逻辑分区（组内余量充足）；10 GiB 镜像必须**精确**等于逻辑分区大小，即 10,235,101,184 B。
- `fastboot flash super` 拒绝 sparse 镜像；若确需刷 `super`，必须是 raw。
- `fastboot -w` 之后，本机首启仍可能落到 stock recovery 的工厂重置界面（视 metadata 状态而定，可能是计划内也可能是意外）；点一次「Factory data reset」是受支持的格式化方式。
- 若 10 GiB 传输失败/超时，改用路线 A 的 36 KiB 块补丁，不要重复写 10 GiB。

2026-11-11 的单变量基线（保留参考）：首次 LineageOS 开机前设备上为 `boot_b 2731d62c…`、`vendor_boot_b 9349137d…`、`init_boot_b 6ac4a4e8…`（logging4 包装器）、`vbmeta_b 7ed20919…`、`vbmeta_system_b 784ac7d3…`（旧 los4），以及 `super_v7.img`（`5779a9a5…`）配 `vbmeta_system_v7.img`（`6b11d5e4…`）。

## 5. 路线 C —— 全量回原厂（R12 集）

原厂启动链要求恰好这一组（由原厂 `vbmeta_b` 与 `vbmeta_system_b` 解析得出）：

| # | 分区 | LUN | LBA（4 KiB） | 扇区数 | 字节数 | 原厂文件 | SHA-256 | 通道 |
|---|---|---|---|---|---|---|---|---|
| 1 | `super`（内含全部 7 个 LP） | 0 | 8968 | 5,242,880 | 21,474,836,480 | `super.img` | `78e54bd36dc1d6971d338ffb49670c6809cad36ca16f6004d0b281af331cf4e5` | EDL |
| 2 | `vbmeta_system_b` | 0 | 5251864 | 16 | 65,536 | `vbmeta_system_b.img` | `493448e6…0399b` | EDL |
| 3 | `dataext_b` | 0 | 5530408 | 131,072 | 536,870,912 | `dataext_b.img` | `e231c8c7…ac86fb` | EDL |
| 4 | `vbmeta_b` | 4 | 513634 | 16 | 65,536 | `vbmeta_b.img` | `ae4ebd619bb57c0d4f50e6619d1a5937bc805b8eaff90f83becdf2631dbf54d7` | EDL |
| 5 | `boot_b` | 4 | 489006 | 24,576 | 100,663,296 | `boot_b.img` | `2731d62ca182c811ed51e4c4e33fe22da4191218569499cdb7debf793c072bec` | EDL |
| 6 | `dtbo_b` | 4 | 513650 | 18,432 | 75,497,472 | `dtbo_b.img` | `6cdc8d3b…239db49` | EDL |
| 7 | `vendor_boot_b` | 4 | 672238 | 24,576 | 100,663,296 | `vendor_boot_b.img` | `9349137dc262ab61508014275b623f4d39e5b14bc55c77082848d63a28f381b2` | EDL |
| 8 | `recovery_b` | 4 | 696878 | 25,600 | 104,857,600 | `recovery_b.img` | `a3b34a80…62acea0` | EDL |
| 9 | `init_boot_b`（vbmeta_system hash） | 4 | 722990 | 2,048 | 8,388,608 | `init_boot_b.img` | `a31072c0b26f5df8581e2f23e9a39cb8476c00b2b9f251c701db433141653e68` | EDL |
| 10 | `pvmfw_b`（vbmeta_system hash） | 4 | 725054 | 256 | 1,048,576 | `pvmfw_b.img` | `d24b59dc…affc98` | EDL |
| 11 | `metadata`（可选，**默认不写**） | 0 | 5251880 | 16,384 | 67,108,864 | `metadata.img` | `7c043a52…f292ba4c` | EDL |
| 12 | `misc`（可选，**默认不写**） | 0 | 8456 | 256 | 1,048,576 | `misc.img` | `5c90f3ad…7a25fe` | EDL |

- 原厂 `super` SHA-256：`78e54bd3…cf4e5`；其前 64 KiB SHA-256 = `fc0163625355ffd46479d9a6c671187a3879954d43cb3c2cf46407dc3b68c573`（内容修补后 LP 元数据不变）。
- `metadata` / `misc` 为可选：原厂 `metadata` 是 2026-10-06 的快照，可能与当前 `/data` 冲突；`misc` 当前 BCB 为空，写它不会改变槽位选择。
- **不要**单独写 `devinfo`、`efisp`、`uefivarstore`、`logfs`、`secdata`、`frp`、`keystore`、`modemst1/2`、`fsg`、`fsc`；它们承载持久解锁/槽位状态，且已证实与回读集逐字节相同。
- GeekFlashTool 全量回写是最后兜底通道（24.71 GiB；跳过 `USRDATA,userdata,last_parti,rawdump`）；全量恢复后须清一次数据（`Reason: init_user0_failed` 属预期且正常）。

## 6. 校验与「假成功」陷阱

1. **EDL `SUCCESS` 不是证据。** 本机历史陷阱：（a）带 `label=` 的 `program` 查表失败，`fh_loader` 仍打印 `{All Finished Successfully}`；（b）镜像不在 `--search_path` 时连 program 都不发仍打印 SUCCESS；（c）旧写法会被 LUN4 GPT 解析拒绝。
2. **EDL 读也会假成功。** 曾出现 8 个不同分区读回同一段伪随机流，`misc` 读回以 `<response…>` 响应头开头。回读件一律以 SHA-256/大小/内容指纹判定；可疑时重读或换通道。
3. **`super` 回读头部判据**（不全量哈希 20 GiB 时）：偏移 0x1000 的 u32 = `0x616C4467`（LP geometry magic），偏移 0x3000/0x13000/0x23000 之一的 u32 = `0x414C5030`（LP metadata header）。随机/全零/`<response` 字节说明写入未落地。
4. **块补丁预检状态：** `OLD` → 可写；`NEW` → 已修复，跳过；`MIXED` → 上次写入中断，重跑路线 A 的块步骤；`OTHER` → 基线与预期不符，不要写块补丁，改用全量路线或先恢复基线。
5. **写前几何交叉核对：** `restore-map.tsv` 与 `regions.json` 对每个 LP 物理 LBA 必须一致；独立 LP 解析应确认每个 `_b` 分区为单 extent 线性。
6. **逐分区 SHA-256 记录：** 本文档或 `01-DEVICE-FACTS.md` 列出了所有本轮刷写镜像与锚点的哈希；刷写前在主机上跑 `Get-FileHash -Algorithm SHA256`。

## 7. 回退锚点

| 锚点 | 文件 | SHA-256 |
|---|---|---|
| 原厂全量回读（156 文件 / 24.71 GiB） | `refs/readback-full/` | 已核 156/156 |
| 原厂 `super` | `refs/readback-full/super.img` | `78e54bd36dc1d6971d338ffb49670c6809cad36ca16f6004d0b281af331cf4e5` |
| 原厂 `vbmeta_b` | `refs/readback-full/vbmeta_b.img` | `ae4ebd619bb57c0d4f50e6619d1a5937bc805b8eaff90f83becdf2631dbf54d7` |
| 原厂 `boot_b` | `refs/readback-full/boot_b.img` | `2731d62ca182c811ed51e4c4e33fe22da4191218569499cdb7debf793c072bec` |
| 原厂 `vendor_boot_b` | `refs/readback-full/vendor_boot_b.img` | `9349137dc262ab61508014275b623f4d39e5b14bc55c77082848d63a28f381b2` |
| 原厂 `init_boot_b` | `refs/readback-full/init_boot_b.img` | `a31072c0b26f5df8581e2f23e9a39cb8476c00b2b9f251c701db433141653e68` |
| F0 前可开机基线（system） | `system_raw_fixed.raw` | `1e7ec2d1…` |
| F0 前配对签名 | `vbmeta_system_v8.img` | `bfd496d9…` |
| F0 前配对 init_boot | `init_boot_logging10.img` | `4511a32e…` |
| 修复后 `super`（内容修补基线） | `super_v7.img` | `5779a9a5e73ddcdecea245fc65ad8cc9e398de4a1ab889d8656e8f3b335823bf` |
| F0 目标 raw system（恢复 verity 用） | `system_raw_nologdump.raw`（重签形态 `29ad60fb…`，root digest `9103aeb9…`） | `b6ca50f5…` |
| 未来 verity-on 签名 | `vbmeta_system_f0_v11.img` | `66e20599…` |

恢复到 F0 前可开机状态 = `system_raw_fixed.raw` + `vendor_b_full_stock` + `vendor_boot_diag2` + `init_boot_logging10` + `vbmeta_system_v8`。

## 8. 诊断态与发布态

2026-11-12 已验收的刷写集刻意保持**诊断态**：

| 项 | 当前诊断值 | 发布要求 |
|---|---|---|
| SELinux | permissive | enforcing |
| dm-verity | off（`vendor_boot_diag2` 已去 avb flags） | on，且使用 avb-enabled 的 `vendor_boot` |
| 根 `vbmeta_b` | E12 testkey | 解锁设备上可继续沿用 testkey 形态，但需重新审计 |
| `init_boot_b` | logging13（持续 kmsg 捕获） | 原厂或干净 init_boot |
| `system_ext_b` | 去 SetupWizard、自动 provision、logcat→rawdump | 接近原厂的 user 构建 |
| `system_b` | 已删 logdump（**保留**）+ policy 扇区补丁（product/system_ext 为 LOS 时惰性） | 保留 logdump 删除；开启 verity 前回退 policy 扇区 |
| `/metadata` | 修复后已格式化 | 正常 |

verity-on 收尾配方：换回 avb-enabled `vendor_boot`；对 `system` 重新计算 hashtree 并重建 `vbmeta_system`（`vbmeta_system_f0_v11.img`，`66e20599…`，root digest `9103aeb9…`，raw SHA-256 `29ad60fb…`）；回退 policy 扇区补丁；把 `init_boot` 换回原厂/干净镜像；最后把 SELinux 切到 enforcing。

## 9. 红线

1. **不要**写 bootloader 区（`xbl`/`abl`/`tz`/`uefi`/`hyp`/`aop`/`cpucp`/`devcfg`/`qupfw`/`shrm`/`imagefv`/`keymaster`/`modem`/`dsp`/`bluetooth`/TME/`dcp`/`soccp`/`pdp`/`spuservice`/…），除非确认 bootloader 版本完全一致且必须整体回退（仅 GeekFlashTool）。
2. **不要**写 GPT，除非证实 GPT 损坏，且此时主/备成对写。
3. **不要**写 A 槽逻辑分区——本机只有 `_b` LP 分区。
4. **不要**相信 EDL `SUCCESS`；以回读哈希/内容比对为准。
5. 一次 9008 连接 = 一个主机工具。
6. **不要**手工改 LP 元数据，**不要** resize 逻辑分区。
7. **不要**单独恢复 `devinfo`/`efisp`/`uefivarstore`/`logfs`/`secdata`。
8. **不要**用旧 EDL 写法（无 `--zlpawarehost=1`、无 `partofsingleimage`、裸 LBA）写任何分区。
9. **不要**刷更旧的 bootloader，也**不要**用「降级到 A16」救砖。
10. **不要**中断 `super` 写入；主机 SHA-256 校验不通过不得刷写。

## 10. 故障处置

| 现象 | 含义 | 处置 |
|---|---|---|
| `target not stable` / 端口打开 > 3 s | Sahara/programmer 状态卡 | 重发 programmer；仍不行则拔插 USB 重进 EDL |
| `SAHARA_NAK_HASH_TABLE_AUTH_FAILURE` | programmer / XBL 版本不匹配或状态机死 | 重进 9008；确认 `devprg_legion-y700-5-2.0.11.043` |
| `{All Finished Successfully}` 但回读不符 | 假成功 | 检查 `--zlpawarehost=1`、XML 字段、`search_path`；重写该分区 |
| `Not a valid GPT signature` / `invalid gpt entry` | 旧写法 / 裸 LBA 被拒 | 换 `fh-write-*.xml` + `--zlpawarehost=1` 写法 |
| 回读全零或以 `<?xml` 开头 | 假读 | 重读；连续两次失败换通道；以设备行为判据 |
| 写 `super` 时掉线 | 镜像不完整 | 重进 EDL，**从头重写整个** `super` |
| 卡第一屏 / USB 一直不枚举 | 内容/挂载失败 | 核对刷写集是否完整（尤其 `super`、`vbmeta_system`、`dataext`）；见 `05`–`08` |
| 约 8 秒内落 BL fastboot | 启动链/AVB 或早期 init 致命失败 | 核对 `vbmeta_b`/`vbmeta_system_b`/GPT 状态；「8 秒」**不能**一律归因签名 |
| 能开机但无法解密 `/data` / 反复重启 | `/data` 与新系统不匹配 | recovery **Format Data**（唯一受支持的清数据方式） |
| 9008 不出现 | USB/电源状态 | 长按电源 10 s，然后按住音量+（及音量-）插长边接口 |
| 连续多个分区失败 | EDL 通道不稳 | 停止 EDL，改用 GeekFlashTool 全量恢复；不要留下半写状态 |

## 11. 证据来源

| 主题 | 证据 |
|---|---|
| 已验收 EDL 操作、刷写集、时间线、验收 | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md`（§1–§3、§8） |
| F0 整包、预检状态、块补丁、两条路线 | `out/2026-11-11-los24-bootfix/F0-FLASH-BUNDLE.md`；`FLASH-CHECKLIST.md`；`F0-ACCEPTANCE-CHECKLIST.md`；`MORNING-RUNBOOK.md` |
| 通道矩阵、假成功陷阱、R12 恢复集、LBA 速查 | `out/2026-11-10-los24-logdump/RESTORE-RUNBOOK.md`（§0–§4、§8、附录 B）；`LOS24-PLAYBOOK-CONSOLIDATED.md` §3.2–§3.6 |
| 分区/LUN 几何 | `01-DEVICE-FACTS.md` §3；`restore-map.tsv` |
| 回退锚点 / 原厂哈希 | `refs/readback-full/`；`RESTORE-RUNBOOK.md` §3 |
| 诊断态收尾 | `03` §8；`out/2026-11-11-los24-bootfix/F0-SIDE-EFFECT-AUDIT.md` |
