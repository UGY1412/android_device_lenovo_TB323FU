作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0

# 07 — FBE / `init_user0` 机制、双 fstab 规则与 A–F 实验设计

| 项 | 值 |
|---|---|
| 状态 | 2026-11-12 — 机制已闭环；A–F 矩阵作为设计/记录保留。"重启必 `init_user0_failed`"后来定位为 `logdump.sh` 写坏 metadata（doc 06），不是 FBE 密钥路径；修复后的刷写集在 FBE 完全开启下可首启并可反复重启 |
| 适用设备 | Lenovo Legion Y700 五代 **TB323FU**，SN `<SN-REDACTED>`，SM8850P（canoe / kaanapali），A/B，4 KiB 页，super 20 GiB，unlocked（`vbs=orange`），B 槽 active |
| 适用对象 | LineageOS 24.0（Android 17）bring-up：`/data` 开启 FBE（原厂 fstab 为 `fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized+wrappedkey_v0`）、原厂 `vendor_b` + `vendor_boot_b` |
| 证据来源 | `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\INIT_USER0-ANALYSIS.md`、`…\PLAINFBE-REPORT.md`、`…\VENDOR-CHECKPOINT-OFF-REPORT.md`、`…\VENDOR-FSTAB-MOD-REPORT.md`、`…\NEXT-ROUND-TEST-PLAN.md`、`…\SESSION-20261112-FBE-ROOTCAUSE-LOG.md`；`<PROJECT_ROOT>\out\2026-11-12-edl-f0\F0-ACCEPTANCE-REPORT.md` |

---

## 1. 背景

修好 `/vendor` 符号链接环（doc 05）之后，移植在**刚擦除的 `/data`** 上可以进入 LineageOS 欢迎界面，但正常重启就落回原厂 recovery：

```
Can't load Android system. Your data may be corrupt. …
Reason: init_user0_failed
```

当时的假设是：FBE（文件级加密）的"解封/装载"路径在重启时失败，而"创建"路径在首启时成功。于是设计了下面的 A–F 矩阵，逐一隔离 FBE 的各个特性（checkpoint、wrapped key、metadata 加密、inlinecrypt、纯 v2 软件密钥、彻底关 FBE），看哪一个导致失败。

**事后结论：** 从上一启动残留的 `misc` 日志里恢复出的证据显示，`/metadata` 根本没有挂载（`vold: Failed to create /metadata/vold: Read-only file system`）；真正原因是调试脚本 `logdump.sh` 每次启动 `dd` 写坏 `/metadata`（doc 06）。把它删掉、并让 recovery 真正格式化一次 metadata 之后，FBE 端到端正常：最终验收为 `ro.crypto.state=encrypted`、`ro.crypto.type=file`、`ro.crypto.metadata.enabled=true`、`vold.post_fs_data_done=1`、`sys.user.0.ce_available=true`、`/data` f2fs `inlinecrypt`，且连续 3 次重启 PASS。因此 A–F 矩阵现在的价值是：(a) 准确描述本机 FBE 语义；(b) 记录已经排除了什么——它不再是解决"重启必挂"的必需步骤。

## 2. `init_user0` 失败机制（源码级）

1. `system/core/rootdir/init.rc:1086` — `on post-fs-data`（块从 `:707` 开始；`/data` 已挂载；vold 在 `:602` 启动；keystore/keymaster early-boot 已结束）中的 builtin `init_user0`。
2. `system/core/init/builtins.cpp:1190-1192` — `do_init_user0()` → `ExecVdcRebootOnFailure("init_user0")`。
3. `builtins.cpp:1151-1177` — `ExecVdcRebootOnFailure()`：
   - 以临时 oneshot service 执行 `exec /system/bin/vdc --wait cryptfs init_user0`；
   - 失败时：`reboot_reason = vdc_arg + "_failed"`；若 `IsFbeEnabled() && !IsGsiRunning()` → `reboot_into_recovery({"--prompt_and_wipe_data", "--reason=<reason>"})`，并打日志 `"... Rebooting into recovery, reason: init_user0_failed"`；
   - **若 FBE 未启用，只打 `"Failure (reboot suppressed)"`，不会跳 recovery**——这是 bring-up 阶段"关 FBE"方案的安全垫。
4. `system/vold/vdc.cpp:163-164` — `cryptfs init_user0` → `vold->initUser0()`；`system/vold/VoldNativeService.cpp:631-635` → `fscrypt_init_user0()`。
5. `system/vold/FsCrypt.cpp:655-690` — `fscrypt_init_user0()`：
   - 若 `IsFbeEnabled()`：创建 `/data/misc/vold/user_keys/{de,ce}`，缺失时 `create_de_key(0)`/`create_ce_key(0)`，再 `load_all_de_keys()`；
   - `prepare_special_dirs()`：创建 `/data/data`、bind mount 到 `/data/user/0`、处理 `/data/media/obb`；
   - `fscrypt_prepare_user_storage("", 0, STORAGE_FLAG_DE)`；
   - 成功置 `fscrypt_init_user0_done = true`（由 `vold main.cpp:315/324` 使用；注释写明：基础 FBE 初始化失败 → boot will fail）。
   - 密钥的包裹/解包走 **KeyMint/Keymaster + keystore2**；metadata 加密的密钥目录由 fstab 的 `keydirectory=` 指定为 `/metadata/vold/metadata_encryption`。
6. recovery 文案：`bootable/recovery/recovery.cpp:301-314` `prompt_and_wipe_data()` 的标题 "Can't load Android system …" + `"Reason: " + device->GetReason()`；reason 来自 init 的 `reboot_into_recovery(--reason=…)`（经 misc/BCB 传递）。所以用户看到的 `Reason: init_user0_failed` 是 init 传入的，不是 dm-verity/ABL 生成的。

## 3. 为什么有两份 fstab——且必须同时改

`/data` 的描述存在于**两个不同 fstab**，二者作用于栈的不同层：

1. **首阶段** — `vendor_boot` ramdisk 内的 `first_stage_ramdisk/fstab.qcom`（7,374 B；设备回读 `vendor_boot_b` sha256 `9349137dc262ab61508014275b623f4d39e5b14bc55c77082848d63a28f381b2` = 原厂）。`fs_mgr` 从这里读表并设置 `ro.crypto.type`（`system/fs/fs_mgr/fs_mgr.cpp:1174`）；`IsFbeEnabled()` 就是判断 `ro.crypto.type == "file"`（`builtins.cpp:1125-1127`），`ro.crypto.state` 由 init 依据 `mount_all`/`installkey` 设置（`builtins.cpp:582/597`）。
2. **第二阶段** — 原厂 `vendor_b` 分区内的 `/vendor/etc/fstab.qcom`（inode 1034，7,374 B，mode 0644，label `u:object_r:vendor_configs_file:s0`，sha256 `4524469bf2480b1deb8f3f17545d6ac8588a220223609104f6340356d263e7b6`）。原厂 vendor 的 `init.qcom.rc` 执行 `mount_all /vendor/etc/fstab.qcom`（`--early`/`--late`），**vold 也从这份文件解析 `fileencryption`/`keydirectory`/`metadata_encryption`**。

影响：

- **只改 `vendor_boot` 首阶段 fstab 不够**：首阶段可能设出了（或没设出）`ro.crypto.type=file`，但第二阶段 `mount_all` 仍按原厂 `/data` flags 执行，vold 也仍看到原厂 FBE 参数。
- **只 `fastboot -w` 也关不掉 FBE**：不删 fstab flags，重新格式化出来的 `/data` 仍然带加密，`init_user0` 照跑。
- 改原厂 `/vendor/etc/fstab.qcom` 位于 `vendor_b`（`super` 内逻辑分区），必须重建 `vendor_b`、重算 vendor AVB hashtree，**并重签 root `vbmeta_b` 里的 vendor hashtree descriptor**（原厂 vendor descriptor：partition `vendor`、salt `4b41bf18…`、root digest `cd1f240f…`、algorithm `NONE`、image size 2,167,975,936 B）——否则 verity-on 启动会 EIO。

原厂 `/data` 行（原文，来自 `/vendor/etc/fstab.qcom` 第 53 行）：
```
/dev/block/bootdevice/by-name/userdata  /data  f2fs  noatime,nosuid,nodev,discard,reserve_root=32768,resgid=1065,fsync_mode=nobarrier,inlinecrypt  latemount,wait,check,formattable,fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized+wrappedkey_v0,keydirectory=/metadata/vold/metadata_encryption,metadata_encryption=aes-256-xts:wrappedkey_v0,quota,reservedsize=128M,sysfs_path=/sys/devices/platform/soc/1d84000.ufshc,checkpoint=fs
```

## 4. FBE flag 语义

- `fileencryption=…:v1` / `:v2` 选择的是 **fscrypt policy 版本**，不是 wrapped-key 模式。
- 密钥类型由 flag 决定：`wrappedkey_v0` → `kHwWrappedV0`，`wrappedkey` → `kHwWrapped`，两者都没有 → `kRaw`（软件密钥），见 `system/vold/KeyUtil.cpp:303-320`。
- `inlinecrypt_optimized` 对应 IV_INO_LBLK_32 / 32-DUN 优化（`FsCrypt.cpp:335-341`），去掉是安全的。
- 因此"纯 v2 + 软件密钥"（E 组）是内核支持的组合，作为实验是合理的。

## 5. 候选失败原因（按设计时的可能性排序）

| 排序 | 假设 | 源码/机制依据 | 判别判据 |
|---|---|---|---|
| 1 | `checkpoint=fs` + 频繁 EDL 复位/断电 → vold checkpoint restore 失败 | `vold/Checkpoint.cpp:84-152`（restore 依赖 metadata + keymaster 快照）；`init.rc` `on post-fs-data` 第一句就是 `vdc checkpoint prepareCheckpoint`（`:710`） | logcat 里 `vold`/`checkpoint` 报错；`/metadata/vold/checkpoint`；`persist.vold.dont_commit_checkpoint` |
| 2 | `/data` 与 `/metadata` 的 FBE 状态不一致（一边被清、另一边没清） | `keydirectory=/metadata/vold/metadata_encryption` 在 `/metadata`，DE/CE 密钥在 `/data`；任一边被清都会解包失败 | `/data/misc/vold/user_keys`、`/metadata/vold/metadata_encryption` 是否存在；`ro.crypto.*` |
| 3 | LOS `vold`/`keystore2` ↔ 原厂 `KeyMint`/gatekeeper HAL（AIDL 版本混搭）导致 `create/load_*_key` 失败 | bring-up 是 LOS `system`（vold/keystore2）+ 原厂 `vendor`（KeyMint/onekeymint/gatekeeper），FBE 依赖这些 HAL | logcat 里 `keystore2`/`keymaster`/`vold` 报错 |
| 4 | 误判：把 FBE 与 dm-verity/ABL 混淆 | recovery 文案走的是 `prompt_and_wipe_data`，不是 verity corrupt | 已排除 |

四种失败最终都以 `init_user0` 非 0 退出收尾，且 reason 只带名字，离线无法区分；必须拿到一次正常 boot 的 logcat。

## 6. A–F 实验矩阵（设计）

每组规则：**两份 fstab 做同样修改**，然后清 `/data` + `/metadata`，再分别测**首启**与**重启**。镜像均离线用 `debugfs` 只改 fstab 单行、`e2fsck -fn` clean、全树 diff 仅该文件。

| 组 | 改动（两份 fstab） | 镜像 | 状态 / 已观测结果 |
|---|---|---|---|
| **A** | `/data` flags **只删** `checkpoint=fs`（其余 FBE flags 全保留） | `vendor_b_checkpoint_off.img`（`4d93028e4577657cba251bbad0db62994965da71fb10bf25bd48d42e81209291`；fstab 7,374→7,360 B，只删 `checkpoint=fs`）；`vendor_boot_diag6.img`（`e15ab973…`，首阶段同样改动） | 曾做**不干净**的部分测试（2026-11-12 00:30–00:40）：`vendor_b_checkpoint_off` + `vendor_boot_diag2`，**36–47 s 进 recovery，reason `init_user0_failed`**，但首阶段 fstab 仍带 `checkpoint=fs`。`vendor_boot_diag6` 已构建并校验 SHA，但在 F0 根因出现前**未上机（待验证）**。 |
| **B** | 同 A + 额外强制清 `/data`+`/metadata` | 同 A | 未执行（被 F0 根因取代）。 |
| **C** | **只删** `wrappedkey_v0`（保留 `v2+inlinecrypt_optimized+metadata_encryption+checkpoint`） | `vendor_b_nokw.img`（`cc2e446c…`）；`vendor_boot_diag7.img`（`6162b02f…`） | 已完成离线构建与校验；**未上机**（被 F0 取代）。若测试，判别点：若在**创建**阶段就失败，说明 stock KeyMint 不认新格式。 |
| **D** | 删 `metadata_encryption=` + `keydirectory=`（保留 checkpoint 及其余） | `vendor_b_nometa.img` + `vendor_boot_diag8.img`（计划，未构建） | 未构建（被 F0 取代）。分析预期：若假设成立，失败会发生在**挂载**阶段而非 `init_user0`。 |
| **E** | **纯 v2 软件密钥**：去掉挂载选项 `inlinecrypt`；`fileencryption` 缩短为 `aes-256-xts:aes-256-cts:v2`；去掉 `keydirectory=`、`metadata_encryption=`、`checkpoint=fs` | `vendor_b_plainfbe.img`（`1cf8ff58993d7ca19af8e1cfb7c310523c2e74fb545d627a891c993fd55edb36`；fstab 7,374→7,218 B）；`vendor_boot_diag5.img`（`2a2f42d0450a0fcfc89bef6b12339366ccc0f5d0942eaf650141e02edbc44509`；首阶段同改，bootconfig 与 diag2 相同 `f6302812…`，AVB footer 重算 → 新 digest `6f7ab065…`） | **2026-11-12 00:59–01:10 实测**：卡开机动画 >280 s，USB 全程不枚举（PnP 空、280 s 内无 adb），用户确认"还是卡开机动画"。FBE 保持开启且已过 `init_user0`。结论：FBE 开 + 软件密钥仍不能进桌面；症状与 FBE-off 相同 ⇒ 卡动画的根因不是加密方式。之后设备电量耗尽关机。 |
| **F** | **关 FBE**（去挂载选项 `inlinecrypt` + flags `fileencryption`、`keydirectory`、`metadata_encryption`、`checkpoint`） | `vendor_b_raw_mod.img`（`18cebcb3aaa2afbbf3b598861ce1a5d3ea7cbf12f9b6cd8eb823921156c87eff`；fstab 7,374→7,176 B）；`vendor_boot_diag4.img`（`5572278678a697dd64b7f14327d64b3dd2414e60f3c5564d8cb6c11ec15267b6`） | **2026-11-11 23:50–00:20 实测**：首次越过 `init_user0` → 进入 LineageOS 开机动画但一直卡住；USB 全程不枚举。kmsg：`init: starting service 'zygote'` 之后反复 `init: Service 'zygote' (pid N) received SIGKILL`；`init: processing action (sys.init.updatable_crashing=1)` + `flags_health_check UPDATABLE_CRASHING`；`init: Control message: Could not find 'aidl/android.system.net.netd.INetd/default'`；117 s 处 `UCSI ... usb = 0` / `nvt_charger: USB plug out`（用户拔线去 EDL）⇒ "USB 不枚举"部分是被拔线；logcat 未抓到。 |

### 6.1 改变方向的前置发现（A0）

在读 `misc_20261112_005239.bin` 的 **STALE 区**（按 `ctl.snap_len` 切分，避免把上一启动的日志混进来）时，出现了决定性的链条：`/metadata` **没有挂载**（`vold: Failed to create /metadata/vold: Read-only file system`，且没有 `F2FS-fs (sda10)` 行），而一次已知成功启动恰好有该行。由此确定判据：**每次启动都要看 kmsg 里有没有 `F2FS-fs (sda10)`**（`sda10` = metadata）。顺着这条线索最终定位到 `logdump.sh` 的每启动写入（doc 06）——A–F 矩阵的前提（FBE 密钥/checkpoint 损坏）是错的。

### 6.2 E/F 结果仍然说明什么

- **F（关 FBE）证明**：FBE 关掉后设备可以过 `init_user0` 并进入开机动画——即卡动画不是 `/data` 加密路径造成的；而 `init_user0` 回 recovery 是由**数据/metadata 状态**造成的，不是仅由加密 flag 造成。
- **卡动画本身是另一个缺陷**：`zygote`/`system_server` 反复被杀/崩溃，`sys.boot_completed` 永远不置位。`received SIGKILL` 不说明发送者（`sigchld_handler.cpp:100-119`）；若是 init 主动杀，会另有 `Sending SIGKILL to … process group`（`service.cpp:283-295`），因此候选是 OOM/lmkd、`crash_dump`/watchdog，或 init 在 Reap 后清理进程组。`init.zygote64.rc` 的 `critical window=off` 使 `ParseCritical` 提前返回（`service_parser.cpp:120-143`），所以第 4 次崩溃后 zygote 走 "updatable_crashing" 分支（`service.cpp:381-425`）——只重置 aconfig flags 并由 apexd `WaitForBootStatus`（仅存在 staged session 才回滚重启）——与观测到的 `flags_health_check UPDATABLE_CRASHING` 吻合。捕获窗内没有 lmkd/OOM/crash_dump/tombstone 命中（但有 1,138 个 seq 缺口），原始杀因仍未闭环。
- **E 与 F 都出现"USB 不枚举"**：F 中部分是用户 117 s 拔线（UCSI `usb = 0`）造成的。后续测试必须全程保持插线。

## 7. 将来做 FBE 实验时的安全约束

1. 同一组改动**同时改两份 fstab**，并对两份镜像分别验证（`debugfs cat` 看 fstab、`e2fsck -fn`、全树 diff 仅 fstab）。
2. `/data` 与 `/metadata` 都要清（本机 Windows 上 `fastboot -w` 只 erase；真正格式化要靠 recovery 的"Factory data reset"或能格式化的工具）。
3. 改 `/vendor/etc/fstab.qcom` 会改变 vendor AVB digest；verity-on 时必须重签 root `vbmeta_b` 的 vendor hashtree descriptor。本轮产出的 FBE-off / plain-FBE 镜像 AVB 尾部是旧的，因此只能在 verity-off + unlocked 下使用。
4. 测试期间保持 SELinux permissive（bring-up 现状）：否则策略 denial 可能掩盖或叠加 fstab 的效果。
5. 不要把 FBE-off 的 `/data` 与 FBE-on 的 fstab 混用（反之亦然）：半加密状态会引入新的失败。
6. 记录每次启动：所刷镜像 SHA、是否 `fastboot -w`、首启结果、重启结果、kmsg/logcat 证据。

## 8. 未验证 / 下一步

1. A、B、C、D 都没有做过干净的单变量真机测试：`vendor_boot_diag6`（A）、`vendor_boot_diag7`（C）已构建并离线校验但未刷；D 从未构建。鉴于 F0 已移除真实原因，这是可接受的；矩阵只作为将来出现 FBE 问题时的参考保留。
2. 卡动画阶段 `zygote`/`system_server` 被杀的原因仍未闭环（需要 logdump 分区的全量 kmsg + `logcat -b crash` + `/data/tombstones`）。
3. 最终 F0 刷写集在 FBE 全开下已验证可用（`ro.crypto.*=encrypted/file`、`vold.post_fs_data_done=1`）：验收集用的是**原厂** `vendor_b` 与 `vendor_boot_diag2`，即 FBE flags 全部回到原厂值——验收集中不再保留任何 FBE workaround。
4. 若要恢复 verity-on/enforcing，需要干净的 `vendor_b`/`vendor_boot` 加 v11 verity 配方（见 doc 06 §5.3 / doc 08）。

## 9. 证据索引

| 路径 | 内容 |
|---|---|
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\INIT_USER0-ANALYSIS.md` | `init_user0` 源码链、双 fstab 说明、最小 FBE-off 配方、候选排序 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\VENDOR-FSTAB-MOD-REPORT.md` | FBE-off vendor_b 修改（fstab 第 53 行，7,374→7,176 B）、自检、AVB caveat |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\PLAINFBE-REPORT.md` | 纯 v2/软件密钥镜像（vendor fstab 7,374→7,218 B；diag5）、离线校验、digest |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\VENDOR-CHECKPOINT-OFF-REPORT.md` | 只删 checkpoint 的镜像、行级 diff、回退包清单 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\NEXT-ROUND-TEST-PLAN.md` | A–F 矩阵、每次启动的判据（`F2FS-fs (sda10)`）、踩坑清单 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SESSION-20261112-FBE-ROOTCAUSE-LOG.md` | 23:00–01:10 实验归档、FBE-off/plain-FBE/checkpoint 结果、zygote 被杀证据 |
| `<PROJECT_ROOT>\out\2026-11-12-edl-f0\F0-ACCEPTANCE-REPORT.md` | FBE 完全开启、无 workaround 的最终状态 |
