作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0 (original text)

# 11 — 报错目录（Lenovo Legion Y700 五代 TB323FU / LineageOS 24）

| 项 | 值 |
|---|---|
| 文档状态 | 2026-11-12；下列条目全部来自本设备 2026-11-07 → 2026-11-12 的点亮过程实测，或引自原厂固件二进制的错误常量/字符串；无一条为编造 |
| 适用设备 | Lenovo Legion Y700 五代 **TB323FU**（SM8850P，canoe/kaanapali），已解锁，当前槽位 B，`super` 20 GiB / 4 KiB 扇区，virtual A/B |
| 用途 | 把一行原始日志变成“诊断 + 处置”。这是本仓库最常用的文档：设备开不了机 / 刷写没生效 / 捕获是空的，先查这里 |
| 阅读顺序 | 在 §2–§6 找到原文，然后跑 §7 对应命令。若同一行出现在与预期不同的启动上下文里，先按 §6 的捕获健康度规则排除假证据 |
| 相关文档 | [05 · 根因：/vendor ELOOP](05-ROOTCAUSE-VENDOR-SYMLINK.md)、[06 · 根因：logdump/metadata](06-ROOTCAUSE-LOGDUMP-METADATA.md)、[07 · FBE / init_user0](07-FBE-INIT-USER0.md)、[08 · SELinux](08-SELINUX-POLICY.md)、[09 · AVB 信任链](09-AVB-CHAIN-NOTES.md)、[10 · 调试通道](10-DEBUG-CHANNELS.md)、[12 · 实验台账](12-EXPERIMENT-LOG.md) |
| 证据原则 | 原文引自在役日志；变量位置沿用来源报告的占位符（`N`、`<mp>`、`<pid N>`）。没有字面报错文本、只是一项检查失败的条目标 **（判据）**。未闭环项标 **待验证** |

> **路径约定**：`<PROJECT_ROOT>` = 项目证据目录，`<WORKSPACE>` = 工程临时工作区，`<USER_HOME>` = Windows 用户目录，`<SN-REDACTED>` = 设备序列号，`<MAC>` = 任意 MAC 地址。

---

## 1. 来源索引

下表文件均相对 `<PROJECT_ROOT>`；除特别说明外都在 `out/2026-11-11-los24-bootfix/` 下。

| 引用 | 文件 |
|---|---|
| [S1] | `out/2026-11-11-los24-bootfix/VERIFY-REPORT.md` |
| [S2] | `out/2026-11-11-los24-bootfix/BOOT-DOCTOR-REVIEW.md` |
| [S3] | `out/2026-11-11-los24-bootfix/REBUILD-ZYGOTE-TIMELINE.md` |
| [S4] | `out/2026-11-11-los24-bootfix/SESSION-20261112-FBE-ROOTCAUSE-LOG.md`（2026-11-12 FBE 根因实验记录） |
| [S5] | `out/2026-11-11-los24-bootfix/INIT_USER0-ANALYSIS.md` |
| [S6] | `out/2026-11-11-los24-bootfix/SYSTEM_SERVER_CRASH-HYPOTHESES.md` |
| [S7] | `out/2026-11-11-los24-bootfix/ADB-ROOT-ANALYSIS.md` |
| [S8] | `out/2026-11-11-los24-bootfix/SELINUX-COMPILE-ANALYSIS.md` |
| [S9] | `out/2026-11-11-los24-bootfix/SYSTEM-LOGDUMP-REMOVAL-REPORT.md` |
| [S10] | `out/2026-11-11-los24-bootfix/ROOTCAUSE-LOGDUMP-METADATA.md` |
| [S11] | `out/2026-11-11-los24-bootfix/NEXT-ROUND-TEST-PLAN.md` |
| [S12] | `out/2026-11-11-los24-bootfix/SESSION-ADDENDUM-20261112-F0.md` |
| [S13] | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` |
| [S14] | `out/2026-11-11-los24-bootfix/F0-SIDE-EFFECT-AUDIT.md` |
| [S15] | `out/2026-11-11-los24-bootfix/SYSTEMEXT-LOGCAT3-REPORT.md` |
| [S16] | `out/2026-11-11-los24-bootfix/SCRIPT-BUG-AUDIT.md` |
| [S17] | `out/2026-11-11-los24-bootfix/BOOTFIX-FACTS.md` |
| [S18] | `out/2026-11-10-los24-logdump/FACTS-SESSIONS.md` |
| [S19] | `out/2026-11-10-los24-logdump/RECOVERY-PLAYBOOK.md` |
| [S20] | `out/2026-11-10-los24-logdump/LOS24-PLAYBOOK-CONSOLIDATED.md` |
| [S21] | `out/2026-11-11-los24-bootfix/FLASH-CHECKLIST.md` |
| [S22] | `out/2026-11-11-los24-bootfix/F0-FLASH-BUNDLE.md` |
| [S23] | `reports/BOOT-SUCCESS-20261111.md`（位于 `<WORKSPACE>/reports/`） |
| [S24] | `out/2026-11-11-los24-bootfix/INITLOG13-BUILD-REPORT.md` |
| [S25] | `out/2026-11-11-los24-bootfix/INITLOG12-BUILD-REPORT.md` |
| [S26] | `out/2026-11-11-los24-bootfix/SYSTEMEXT-LOGCAT2-REPORT.md` |
| [S27] | `out/2026-11-11-los24-bootfix/ZYGOTE-CRASH-ANALYSIS.md` |
| [S28] | `out/2026-11-11-los24-bootfix/IMAGE-FIX-REPORT.md` |
| [S29] | `out/2026-11-11-los24-bootfix/VENDORBOOT-DIAG2-REPORT.md` |
| [S30] | `out/2026-11-11-los24-bootfix/VENDORBOOT-NOFAIL-REPORT.md` |

---

## 2. A 类 —— AVB / 首阶段挂载

| ID | 报错原文 | 含义 | 处置 | 来源 |
|---|---|---|---|---|
| AVB-01 | `init: [libfs_avb] Device path not found: /dev/block/by-name/vbmeta_b` | 首阶段 fstab 要求对 `vbmeta_b` 做 AVB，但 1 s 的 `WaitForFile` 窗口内 `/dev/block/by-name/vbmeta_b` 不可用。典型原因：当前 `vendor_boot` **不是**去 avb 的诊断变体，或 GPT/by-name 非原厂 | 确认所刷 `vendor_boot` 的 SHA-256 是 `vendor_boot_diag2`（`40623569…`）或其它去 avb 变体；核对原厂 GPT；重新抓取 | [S3] §4.2，[S4] §2，[S2] §1 |
| AVB-02 | `Failed to mount required partitions early` | first-stage init 的 `DoFirstStageMount()` 返回 false；PID1 abort → 内核 panic/重启。该原文通常在落盘前被吞掉 | 当作“首阶段挂载失败”；从相邻行（`libfs_avb`、`Failed to mount <mp>`、`ELOOP`）定位分区；检查 fstab/vbmeta/GPT | [S1] §1 F2，[S2] §1 阶段 0 |
| AVB-03 | `os.open   /vendor          => 40 ELOOP Too many levels of symbolic links`（`realpath /vendor`、`os.stat /vendor`、`/system/vendor` 同理） | LOS `system` 根目录的 `/vendor → /system/vendor` 与 `/system/vendor → /vendor` 互指成环；`fs_mgr_create_canonical_mount_point("/vendor")` 失败，而 `/vendor` 是必需挂载 → 首阶段 FATAL | 重建 `system` raw：`/vendor` 改成真实目录（0755）、补 `/dataext` 目录；`/system/vendor → /vendor` 保留；重算 hashtree 并重签 | [S1] §1.3 F4，[S28] §（根因） |
| AVB-04 | `Failed to mount /system` | `TrySwitchSystemAsRoot()` 挂不上 `/system`；首阶段致命 | 核对 `system` 内容与 `vbmeta_system` digest；确认所刷启动件（avb 开/关）与整套配置匹配 | [S2] §1 阶段 0，[S1] §1 F2 |
| AVB-05 | `[libfs_avb] Failed to load vbmeta` / `Failed to setup verity`（模式，分区名可变） | 该分区的 AVB/verity 初始化失败；随后挂载失败（只有 `no_fail` 才会被忽略） | 检查 vbmeta 分区内容与描述符配对；解锁态只容忍签名类错误，不容忍元数据损坏 | [S2] §1 阶段 0 |
| AVB-06 | `ERROR_INVALID_METADATA`（libavb 错误常量） | 某个 chained vbmeta/分区没有合法 AVB 元数据（例如 `recovery_b` 被换成与原链无关的镜像）。该错误**不会**因解锁/permissive 被容忍；`AvbHandle::Open()` 可能返回 null，首阶段死在同一点 | 回读 `recovery_b` 并与原厂 `a3b34a80…` 比对；不一致就恢复原厂 recovery | [S1] §4.2，[S20] §2.2 N2 |
| AVB-07 | `ERROR_VERIFICATION` / `PUBLIC_KEY_REJECTED`（libavb 错误常量） | 签名/哈希校验错误。bootloader 解锁时 ABL/`fs_avb` 按其 permissive 处理（`IsAvbPermissive()`），所以用 testkey 或改过内容时属预期现象 | 本身不是行动项；不要靠“锁回 bootloader”去掩盖。用 `ro.boot.verifiedbootstate` 确认启动状态 | [S1] §1 F6.5，[S20] §2.2 N2 |
| AVB-08 | `Failed to mount <mp>, ignoring mount for no_fail partition`（INFO） | 首阶段挂载失败但 fstab 条目带 `no_fail`，失败被忽略、继续启动 | 仅诊断变体如此；绝不能把“没有 fatal”当成“挂载成功”。应查正向证据 `EXT4-fs (dm-…) … mounted filesystem` | [S6] §5 Q1，[S30] §（说明） |
| AVB-09 | `Failed to boot into userspace fastboot; one or more components might be unbootable.` | 槽位被标 unbootable 或启动链损坏，bootloader 拒绝启动 fastbootd | 先修槽位属性/内容（整对写原厂 GPT + 已知可开机刷写集），不要反复重试 `fastboot reboot fastboot` | [S18] §9 CANNOT 3 |
| AVB-10 | `Your device is corrupt` | 用户可见 corrupt 屏；ABL/AVB 拒绝启动，和/或槽位 unbootable → recovery/清数据提示 | 不要下意识清数据；先读 GPT 槽位属性与当前 vbmeta/信任链；用 EDL 恢复 | [S23] §4，[S20] §3.2 |
| AVB-11 | `Reset unbootable slots failed enter fastboot mode` / `No bootable slots found enter fastboot mode` | 原厂 ABL 镜像内的字符串：ABL 无法重置/证明可启动槽位，进入 fastboot | 成对写回原厂 GPT 主备表，重查 `slot-unbootable:b`；再验证已知可开机刷写集 | [S19] §1.1（ABL 二进制字符串） |

---

## 3. B 类 —— `/metadata`、FBE 与 `init_user0`

| ID | 报错原文 | 含义 | 处置 | 来源 |
|---|---|---|---|---|
| FBE-01 | `vold: Failed to create /metadata/vold: Read-only file system` | `/metadata` 未挂载，目录落在只读 root 上。本项目根因：LOS `system` 自带 `logdump.sh`，每次启动裸写 `metadata` 分区并毁掉 f2fs 超级块 | 查 F2FS 挂载行（见 §7）；从 `system` 中删掉 `logdump.sh`/`logdump.rc`（F0）；factory reset 一次让 recovery 真正格式化 metadata | [S11] §（链），[S12] §（证据），[S10] |
| FBE-02 | `vold: read_key failed in mountFstab` | 读 metadata-encryption/FBE key 失败；几乎总是 FBE-01（metadata 未挂载）的下游症状 | 先修 metadata 挂载；再谈 checkpoint/wrappedkey 变体 | [S3] §6 残留链，[S12] |
| FBE-03 | `cryptfs encryptFstab Failed` | metadata key 读取失败后的 FBE fstab 设置失败（vold 侧日志行） | 同 FBE-02 | [S12] §（链），[S10] |
| FBE-04 | 6–8 s 段出现 `make_f2fs` **（判据）** | `/data` 因 `formattable` + 加密状态中断被二次格式化——是 metadata 链的症状，不是独立 bug | 以 FBE-01/02/03 为根因，不要追 `make_f2fs` | [S2] §1 阶段 1a |
| FBE-05 | `init: Command 'mount_all /vendor/etc/fstab.qcom --late' … failed: queue_fs_event() failed: Invalid code: -1` | 第二阶段 `mount_all --late` 失败 → `on post-fs-data` 不会执行 | 查 `mount_all` 失败原因（通常是 metadata/data）；在该行之前核对 `/metadata`、`/data` 挂载 | [S10]，[S2] §1 阶段 1a，[S12] |
| FBE-06 | `cutils: Failed to mkdir(/data/misc/vold/user_keys): No such file or directory` / `vold: Failed to prepare /data/misc/vold/user_keys` | `post-fs-data` 没跑，`/data/misc` 从未创建 | 当作 FBE-05 的后果；先修挂载链 | [S2] §1 阶段 1b |
| FBE-07 | `vdc: Command: cryptfs init_user0 Failed: Status(-8, EX_SERVICE_SPECIFIC): '0: '` | `init_user0` 直接失败；init 随即 `reboot_into_recovery --reason=init_user0_failed` | 用 init_boot 包装器抓完整链（FBE-01→07），不要只看最后一行 | [S10]，[S2] §1 阶段 1b，[S6] §5 |
| FBE-08 | `init: vdc call failed with error code: 25` / `vdc terminated by exit(25)` | `vdc cryptfs init_user0` 调用返回非零 | 同 FBE-07 | [S2] §1 阶段 1b |
| FBE-09 | `Can't load Android system. Your data may be corrupt.` + `Reason: init_user0_failed` | init 主动 `reboot_into_recovery(--prompt_and_wipe_data --reason=init_user0_failed)` 后 recovery 显示的提示 | reason 字符串是关键：指向 FBE，不指向 dm-verity/ABL。应修 metadata/FBE 链，而不是反复清数据 | [S5] §1.6，[S4] §1 |
| FBE-10 | **上一次**启动残留日志区里的 `init: [libfs_avb] Device path not found: /dev/block/by-name/vbmeta_b` | 若不按 `ctl.snap_len` 切分 `misc` 日志，很容易把上一次启动的失败链误认为本次 | 分析前按 `ctl.snap_len` 切分；7 s 失败件的 `snap_len` 之后混着上一启动的 init_user0 链 | [S3] §（snap_len），[S2] §2 G11 |

---

## 4. C 类 —— 用户态、system_server、adb 与 SELinux

| ID | 报错原文 | 含义 | 处置 | 来源 |
|---|---|---|---|---|
| USR-01 | `init: Service 'zygote' (pid N) received SIGKILL` | zygote 被杀；该行**不**说明谁杀的 | 搜 `Exit zygote because system server`、crash buffer 的 `FATAL EXCEPTION`、OOM/lmkd、watchdog；抓 logcat | [S27] §（收尸），[S4] §1 |
| USR-02 | `init: Sending SIGKILL to service 'zygote' (pid N) process group...` | init 在 zygote 收到 SIGKILL **之后**清理残留进程组；不是原始杀因 | 永远不要读成“init 先杀了 zygote”；与 USR-01 的先后顺序对照 | [S2] §1 阶段 2，[S3] §（结论） |
| USR-03 | `init: processing action (sys.init.updatable_crashing=1) from (/system/etc/init/flags_health_check.rc:10)` / `flags_health_check UPDATABLE_CRASHING` | 第 4+ 次崩溃后的级联，症状而非根因 | 记录下来，然后找序列里的第一次崩溃 | [S2] §1 阶段 2，[S4] §1 |
| USR-04 | `Exit zygote because system server (pid N) has terminated` | `system_server` 死亡的直接指纹（zygote 的 SIGCHLD handler）。**只出现在 logcat**，不在 kmsg | 抓 logcat（rawdump）或 crash buffer；这是 system_server 层失败的关键行 | [S2] §1 阶段 2 |
| USR-05 | `*** FATAL EXCEPTION IN SYSTEM PROCESS` | logcat crash buffer 中 `system_server` 的 Java 崩溃栈顶 | 读该行下面的栈；按 VINTF/HAL vs keystore/keymint vs 其它分类 | [S2] §1 阶段 2，[S6] §6 |
| USR-06 | `WATCHDOG KILLING SYSTEM PROCESS` | `system_server` 被 watchdog 杀掉 | 在 logcat 里抓 watchdog 栈；通常需要更长捕获窗口 | [S2] §1 阶段 2 |
| USR-07 | `Signature mismatch on system package com.motorola.android.providers.settings for shared user android.uid.system/1000` | LOS `system`（testkey）与原厂 `product`/`system_ext`（联想签名）混装导致签名冲突；`system_server` 崩溃 | `product`、`system_ext` 换成同一批 LOS 构建件，再清一次 data；三个用户态分区必须同批次 | [S23] §1–§2，[S20] §6.1 |
| USR-08 | `logcat: Invalid -v 'pid'` | logcat 格式参数非法，进程退出，捕获为空 | 用 `-v threadtime`（可加 `,usec`）；不要用 `-v pid` | [S4] §5，[S2] §1 阶段 4 |
| USR-09 | `exec logcat -G 16M -b all -v threadtime` 只留下头、没有日志行 **（判据）** | `logcat -G` 只设置 buffer 大小，随后立即 `return EXIT_SUCCESS`（`system/logging/logcat/logcat.cpp:1165`），根本不会进入读循环 | 拆成两步：`logcat -b all -G 16M >/dev/null 2>&1`，再 `exec logcat -b all -v threadtime` | [S15] §（bug），[S16] §1.1 |
| USR-10 | `avc: denied { execute_no_trans } ... path="/system/bin/logdump.sh"` | 本次启动的 `system` 仍在尝试执行旧 `logdump.sh` → F0 修复未生效 | 核对所刷镜像里 `/system/bin/logdump.sh`、`/system/etc/init/logdump.rc` 不存在；重刷 F0 system | [S2] §1 阶段 4 |
| USR-11 | `avc: denied ... permissive=1`（实测数量：一次完整 logcat 3,541 条；其中 `/dev/block/logdump` 在 logcat 94 条、dmesg 7 条） | permissive 模式下的 SELinux 拒绝：记录但不执行，因此不致命。`/dev/block/logdump` 的拒绝正是 `initlog13` 写 logdump 的预期行为 | 诊断态属正常；转 enforcing 后要补/核 `logdump` 分区 label 与 allow 规则 | [S13] §9，[S14] §4 #13 |
| USR-12 | `adb shell` 报 `FAIL closed`，但 `adb devices` 能看到 transport | transport 在、shell 服务被拒；最可能是主机密钥授权丢失（`fastboot -w`/factory reset 清掉 `/data/misc/adb/adb_keys`，且 `ro.adb.secure=1`） | 在设备上重新授权 USB 调试（或确认 `adb devices` 显示 `unauthorized`）；`adb_root.rc` 是被动服务，**不是**原因 | [S7] §0/§3，[S17] §（adb） |
| USR-13 | `device unauthorized` | 主机公钥不在 `/data/misc/adb/adb_keys` 中 | 在设备上点允许 RSA 指纹，或重新加入主机 key；除短时诊断外不要削弱 `ro.adb.secure` | [S7] §3 |
| USR-14 | `Opening SELinux policy from monolithic file /sepolicy` / `First stage mount skipped (recovery mode)` | 这是 **recovery** 引导：首阶段挂载被跳过，使用 recovery ramdisk 的 monolithic `/sepolicy`。不是正常 LOS 启动路径 | 识别并排除；先修回退原因（BCB/槽位/内容），再重抓。不要用这种日志诊断 ROM | [S7] §7.1/§7.3 |
| USR-15 | `DM_DEV_STATUS` ioctl 失败 `ENXIO` → `Could not update logical partition` | recovery 模式的兜底逻辑里，`MountMissingSystemPartitions()` 试图重映射 `system_ext`/`product`，但它们的 dm-linear 设备从未创建（首阶段没跑） | 同 USR-14：这是 recovery 引导的产物 | [S7] §7.2 |
| USR-16 | `Failed to resolve typeattributeset statement at /system_ext/.../system_ext_sepolicy.cil:2` → `Failed to compile cildb: -2`（secilc rc=254） | 运行时 SELinux 策略编译失败：原厂 `product`/`system_ext` 策略引用了 LOS 平台策略未定义的 OEM 独有 type（如 `mediaserverwrapper`） | 用同批 LOS `product` + `system_ext`（已验证 rc=0），或走预编译策略路线；补 stub type 不可行 | [S8] §（矩阵 A/E/F） |

---

## 5. D 类 —— 刷写工具链（EDL / fastboot / GPT）

| ID | 报错原文 | 含义 | 处置 | 来源 |
|---|---|---|---|---|
| FLS-01 | `invalid gpt entry number 128`（其后仍打印 SUCCESS） | 旧式 fh_loader 写 LUN4 失败却报成功（假成功） | 改用新 XML 写法（`--zlpawarehost=1`、`partofsingleimage`/`readbackverify`、真实分区 label），写后回读并算哈希 | [S20] §2.2 N9，[S19] §1.3 |
| FLS-02 | `Not a valid GPT signature`（一次软 EDL 尝试里出现 8 次） | 写入发到了软 EDL（`adb reboot edl`）会话并被静默丢弃；8 个错误 = 什么都没写进去 | 绝不在软 EDL 刷写；只能冷进 9008（关机 + 音量+ + 长边 USB） | [S18] §4.2，[S19] §2 |
| FLS-03 | `{ERROR: Something failed during patching}` / `<response value="NAK" .../>` | 本机 programmer 对 Firehose `patch` 命令回 NAK | 不要用 patch；用 `program` 写整扇区/整分区 | [S19] §1.3 |
| FLS-04 | `target not stable` | EDL 会话不稳定：端口 ~10 s 才开、programmer 上传或读取失败、设备反复进出 crashdump | 重新冷进 EDL，用工具包“读取信息”重置会话，再重试一次；不要无限循环 | [S18] §4.2，[S20] §4.3 |
| FLS-05 | `Sahara protocol error` | 软 EDL 或 9008 会话不健康 | 冷进 EDL + 重置会话 | [S4] §5 |
| FLS-06 | `AdbWriteEndpointSync failed: 超时121`（timeout 121） | 从 bootloader fastboot 进 fastbootd 超时；设备停在 bootloader fastboot | 不要从只读的 bootloader fastboot 进 fastbootd；用 recovery 的 adb 或冷 EDL | [S17] §（历史） |
| FLS-07 | `remote: 'unknown command'`（针对 `flash`、`set_active`、`oem edl`） | 本机 bootloader fastboot 是只读的 | 用 fastbootd（物理+逻辑分区写、`set_active`）或 EDL；BL fastboot 只有 `getvar`/`reboot`/`reboot recovery` | [S18] §9 CANNOT 1，[S4] §5 |
| FLS-08 | fastbootd 刷 `vendor_b`/`vbmeta_system_b` 时报 `unknown partition` | fastbootd 分区名不带 `_b` 后缀 | 用短名：`vendor`、`vendor_boot`、`system_ext`、`init_boot`、`vbmeta_system`…… | [S4] §5，[S11] §（坑） |
| FLS-09 | `Erase successful, but not automatically formatting. File system type raw not supported.` | 本机 Windows platform-tools 的 `fastboot -w` 只会**擦除**（没有 host 端 `mke2fs`/`make_f2fs`），`metadata`/`userdata` 没有被格式化 | 用原厂 recovery 的 “Factory data reset”（真正执行 `make_f2fs`），或显式验证过的 `fastboot format`；之后重启 | [S16] §1.1，[S6] §5（fastboot -w） |
| FLS-10 | `Invalid sparse file format at header magic` | 通过 bootloader fastboot 发送了 sparse 镜像 | `super`/大镜像走 fastbootd（sparse 传输可用），或 EDL 写 raw | [S18] §4.3 |
| FLS-11 | EDL 写/回读 SHA 与期望值不一致（清单要求 `MATCH`）**（判据）** | 写入没落地，或读取是假成功/半截传输 | 重写，再回读首/中/尾（大分区）或整片（小分区）比对 SHA-256；不一致绝不继续 | [S21] §3，[S13] §2 |
| FLS-12 | GPT 备表与主表/参考文件不一致，差几个字节（实测：entries attr `0x77→0x6F` + 头 CRC，共 9 字节）**（判据）** | ABL 或工具单独重提交了一份；两侧 unbootable 位都为 0，故不阻断，但主备已非逐字节一致 | 把原厂 GPT 主备当一对写回；只不一致时也重写两份并重新回读 | [S20] §7 U6，[S19] §问题 2 步骤 2 |

---

## 6. E 类 —— 捕获健康度 / 日志卫生

| ID | 报错原文 | 含义 | 处置 | 来源 |
|---|---|---|---|---|
| CAP-01 | `logcat: Invalid -v 'pid'`（同 USR-08） | 捕获在启动时即死亡；目标分区只有头 | 修脚本（`-v threadtime`）并重抓 | [S4] §5，[S2] §1 阶段 4 |
| CAP-02 | 只有头、没有内容，例如仅 `==== AERA_LOGCAT_BEGIN uptime=… ====` **（判据）** | `CAPTURE-FAILED`：捕获服务起来了但流从未运行 | 查服务命令行（USR-08/USR-09）；修好重刷 | [S2] §1 阶段 4 |
| CAP-03 | 目标分区全零（例如 64 MiB 全 0x00）**（判据）** | `CAPTURE-NOT-RUN`：捕获服务完全没执行 | 启动在服务起来之前就死了，或读错了分区；先确认启动阶段 | [S2] §1 阶段 4，[S2] §0 |
| CAP-04 | `metadata` dump 里出现 `==== LOGDUMP3 mode=once ... uptime=... ====` / `AERA_DMESG` | `PRE-F0-DIAG`：F0 前的 `logdump.sh` 曾活跃（它写 `metadata`）。metadata 快照来自**过去**的启动，不是本次启动的阶段日志 | 只能作为“F0 尚未生效”的证据；不要用它判断本次启动 | [S2] §1 阶段 4，[S10] |
| CAP-05 | `init: 305/718 output lines suppressed` / `init: 718 output lines suppressed` | 内核 `printk` 在生产端被限流丢行；`printk.devkmsg=on` 只改善 `devkmsg` 读路径，不等于关闭 `printk_ratelimit` | 在 `/proc` 挂载后写 `printk_ratelimit=0` 与 `printk_ratelimit_burst=9999`（提议的包装器步骤，**待验证**）；条件允许时加大 `log_buf_len` | [S23] §5，[S7] §7.4 |
| CAP-06 | `misc` 日志区里两次启动的记录被拼在一起 **（判据）** | `initlog12`/`initlog13` 写的是环形/流式区；不按 `ctl.snap_len`（IL12）或最后一个 `==== INITLOG13` 头切分，就会把上一启动的旧记录混进时间线 | 分析前按控制块长度/最后一个头切分 | [S3] §（snap_len），[S2] §2 G11 |
| CAP-07 | `Failed to mount /dataext` | 第二阶段 `/dataext` 挂载失败（通常因为 `dataext_b` 内容与 root vbmeta 的 hashtree 不符）；不致命但数据扩展异常 | 回读 `dataext_b` 并与原厂比对；不要把它当启动阻断项 | [S1] §4.3 |

---

## 7. 判据命令（查表前后都跑）

### 7.1 启动状态与槽位

```bash
adb devices -l                                  # device / unauthorized / recovery
adb shell getprop sys.boot_completed            # "1" = 已启动完成
adb shell getprop init.svc.bootanim             # 成功判据要求 "stopped"
adb shell getprop ro.boot.verifiedbootstate     # orange = 解锁（诊断态）
fastboot getvar current-slot
fastboot getvar slot-unbootable:b               # 必须 "no"
fastboot getvar is-userspace                    # yes = fastbootd
```

### 7.2 首阶段 / AVB

```bash
grep -aE "init first stage started|Failed to mount required partitions|libfs_avb|ELOOP|Failed to mount" logdump.bin
grep -aE "EXT4-fs \(dm-|Opening SELinux policy|Compiling SELinux policy" logdump.bin
grep -aE "silently ignoring|no_fail" logdump.bin           # 仅诊断 fstab
```

**首阶段成功判据：** 至少 7 行 `EXT4-fs (dm-…) … mounted filesystem`，随后出现 `Opening SELinux policy`（或 `Compiling SELinux policy`）。出现 `libfs_avb` 且没有 `EXT4-fs` 块 = 死在首阶段。

### 7.3 metadata / FBE / init_user0

```bash
grep -aE "F2FS-fs \(sda10\)|Failed to create /metadata/vold|read_key failed|encryptFstab" logdump.bin
grep -aE "init_user0|user_keys|mount_all /vendor/etc/fstab.qcom|queue_fs_event|vdc call failed" logdump.bin
adb shell cat /proc/mounts | grep -E "metadata|userdata"   # 仅当 adb 可用
```

**metadata 成功判据：** 本次启动段里存在 `F2FS-fs (sda10): Mounted with checkpoint version = …`。原厂 GPT 下 `sda10 = metadata`、`sda14 = userdata`。

### 7.4 system_server / 用户态

```bash
grep -aE "starting service 'zygote'|received SIGKILL|Sending SIGKILL|updatable_crashing" logdump.bin
grep -aE "Exit zygote because system server|FATAL EXCEPTION IN SYSTEM PROCESS|WATCHDOG KILLING" rawdump.bin
adb logcat -b all -d | grep -E "Boot completed|init_user0|FATAL EXCEPTION"
```

**成功判据：** `sys.boot_completed=1` **且** `init.svc.bootanim=stopped`。只有一张 UI 截图不算判据。

### 7.5 捕获

```bash
python3 boot-doctor-reviewed.py <dump.bin> --tag <label> --out <outdir>
python3 boot-doctor-reviewed.py <evidence_dir> --out <outdir>     # 每个文件单独裁决，不混启动
python3 - <<'PY'
import struct
d=open("misc_fetched.bin","rb").read(); o=0x80000
print(d[o+4:o+8], struct.unpack_from("<I",d,o+8)[0], struct.unpack_from("<I",d,o+24)[0])
PY
```

### 7.6 镜像（离线）

```bash
avbtool info_image   --image <partition_image>      # footer 参数、root digest
avbtool verify_image --image <partition_image> --key testkey_rsa4096.pem
certutil -hashfile <image> SHA256                   # Windows
Get-FileHash <image> -Algorithm SHA256              # PowerShell
```

---

## 8. 决策树（开机后 60 秒内）

```
设备表现？
├─ 8–12 s 落 bootloader fastboot
│   ├─ 查 slot-unbootable:b / GPT attr（FLS、AVB-11）
│   ├─ 查 vbmeta 链与描述符（AVB-06/07），以及 init_boot 是否 OEM/链兼容
│   └─ 若只剩 BL fastboot 通道（FLS-07）→ 冷 EDL
├─ 卡第一屏 / UI 前循环重启
│   ├─ 捕获：init_boot 包装器 → misc/logdump；查 AVB-01..08 / FBE-01..06
│   └─ 若出现 `libfs_avb` → 是 vendor_boot 变体或 GPT 问题，不是内容问题
├─ 到 UI 但无 adb / adb FAIL closed
│   └─ 先按 USR-12/13 查授权，再断言 ROM bug
└─ 到用户态后循环死
    └─ logcat 链：USR-01/02 → USR-04/05/06；先确认捕获健康度 CAP-01..06
```

---

## 9. 证据质量说明

1. 上表中若干行是**下游症状**（FBE-02…06、USR-02/03）。列出它们是因为它们才是人最先看到的行；“处置”列始终指向真正的根因。
2. **（判据）**条目没有单条字面报错，只描述一项检查失败。不要把它们当成“设备打印了这句”。
3. 字符串拼写取自来源文件；`<mp>`、`N`、`<pid N>` 是来源报告的占位符。
4. 有两项未闭环：(a) 某次 2.7 s 启动中 ABL 回退 recovery 的确切触发（当时 BCB 为空）；(b) `printk_ratelimit=0` 是否能完全阻止生产端丢行。二者均标 **待验证**。
5. 若观察到新行，请按以下格式补录：(i) 原文，(ii) 启动阶段，(iii) 刷写集，(iv) 证据捕获文件。**没有实测过的行不要补。**
