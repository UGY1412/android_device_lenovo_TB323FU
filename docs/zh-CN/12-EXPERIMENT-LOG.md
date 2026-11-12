作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0 (original text)

# 12 — 实验台账：失败实验与已排除项（TB323FU / LineageOS 24）

| 项 | 值 |
|---|---|
| 文档状态 | 2026-11-12；覆盖 2026-11-07 至 2026-11-12 的全部实验轮次（含与结论相关的前史） |
| 适用设备 | Lenovo Legion Y700 五代 **TB323FU**（SM8850P，canoe/kaanapali），已解锁，当前槽位 B，`super` 20 GiB，4 KiB 扇区，virtual A/B |
| 用途 | **防止重复劳动。** 每条记录精确配置、观测结果，以及结论是已证实、不可用（被污染）还是已被推翻。设计“新实验”前先读这里——大概率已经试过 |
| 证据分级 | **HW** = 真机观察/日志/回读；**IMG** = 离线镜像分析；**DECL** = 仅脚本声明、无回读；**USER** = 用户目视屏幕状态。未闭环项标 **待验证** |
| 配套文档 | `11-ERROR-CATALOG.md`（日志行含义）；`09-AVB-CHAIN-NOTES.md`（链改动为什么成/为什么败）；`10-DEBUG-CHANNELS.md`（怎么抓证据） |
| 相关文档 | [01 · 设备事实](01-DEVICE-FACTS.md)、[03 · 刷写](03-FLASH.md)、[05 · 根因：/vendor ELOOP](05-ROOTCAUSE-VENDOR-SYMLINK.md)、[06 · 根因：logdump/metadata](06-ROOTCAUSE-LOGDUMP-METADATA.md)、[07 · FBE / init_user0](07-FBE-INIT-USER0.md)、[08 · SELinux](08-SELINUX-POLICY.md)、[11 · 报错目录](11-ERROR-CATALOG.md) |

> **路径约定**：`<PROJECT_ROOT>` = 项目证据目录，`<WORKSPACE>` = 工程临时工作区，`<USER_HOME>` = Windows 用户目录，`<SN-REDACTED>` = 设备序列号，`<MAC>` = 任意 MAC 地址。

---

## 1. 如何阅读本台账

- **配置**列 = 本次**意图上唯一**改变的变量。只要同时改了多项，条目会明确标注“多变量”，其结论自动降级。
- **结果**列 = 实际观测（屏幕状态、`adb`、`boot_completed`、recovery、日志证据）。
- **状态** = `CONFIRMED`（真机验证且可复现）、`INCONCLUSIVE`（被其它因素污染）、`SUPERSEDED`（后续实验推翻了当时的结论）、`NOT RUN`（准备了但未执行）。
- 早期轮次（E 编号）在设备状态上反复叠加；很多条目因为当时槽位已 unbootable 而属于 `INCONCLUSIVE`。不要把它们当作干净证据引用。

---

## 2. 实验总台账

### 2.1 2026-11-07 —— 最早的 AVB/链实验（E 系列）

| # | 配置（意图单变量） | 结果 | 结论 / 状态 |
|---|---|---|---|
| E1 | 11-07 08:37；回读原厂启动链 + 自建 `super_b` + `vbmeta_system_b_full`（补 init_boot/pvmfw 描述符）+ testkey root | fastbootd 全部 OKAY（super 18 片，42.19 s）；启动失败回落 bootloader fastboot | 链引用的分区（`pvmfw_b`、`dataext_b`）描述符缺失 → 混合链。**对 AVB 策略 INCONCLUSIVE**，但确立了“描述符完整性”教训 |
| E5 | 11-07（计划）；E1 + 补刷 `pvmfw_b`/`dataext_b` | 未作为干净单变量轮次执行（当时设备正在整机恢复） | **NOT RUN** |
| E6 | 11-07 09:14；LOS `system`/`system_ext`/`product` + full vbmeta 链 + testkey root + 回读 `pvmfw`/`dataext`，`set_active b` | 第一屏后重启循环；不落 fastboot、无 corrupt 屏；四个分区 `e2fsck` clean | LOS 内容问题独立于链存在。**CONFIRMED：故障域是内容而不是刷写方式** |
| E7 | 11-07 09:26；与 E6 相同但 `vbmeta_system` `flags=1`（关 verity） | 仍第一屏后重启循环 | **dm-verity/hashtree 不是原因。** CONFIRMED（推翻 verity 假设） |
| E8 | 11-07 10:35；重签 `system`（补 3 个 VINTF HAL，无 SELinux xattr） | 变为**卡第一屏不重启** | 行为改变；怀疑 footer/描述符不一致。**INCONCLUSIVE** |
| E9 | 11-07 10:59；LOS `system` + 整套原厂 VINTF manifest/matrix（in-place、保 xattr） | 卡第一屏 | **VINTF 不是原因。** CONFIRMED |
| E10 | 11-07；root `flags=1`（社区同款） | 无效：槽位 `unbootable:b=yes`，ABL 未尝试启动 | **INCONCLUSIVE**（不要引用来证明 flags 旁路有效/无效） |
| E11 | 11-07 11:42；原厂 `boot` + permissive + testkey 重签 + `chain boot→testkey` | 12 s 回 fastboot；但当时 `slot-unbootable:b` 已是 yes | **INCONCLUSIVE**（被污染）。“干净槽位下 `boot→testkey` 是否可用”从未做过 |
| **E12** | 11-07 11:56–12:03；**原厂内容** + testkey root（`chain boot/recovery→OEM`、`chain vbmeta_system→testkey`）+ testkey `vbmeta_system` | **能开机：`sys.boot_completed=1`，原厂指纹** | **CONFIRMED：设备接受 AOSP-testkey root + testkey vbmeta_system + 原厂内容。** 这是整个点亮过程最决定性的实验 |
| E13 | 11-07 12:02；LOS `system`（原厂 VINTF）+ `vbmeta_system_v4` + 已验证的 E12 链 | 仍卡第一屏 | **VINTF 假设彻底排除；失败在 LOS 用户态内容。** CONFIRMED |
| G0 | 11-08；LOS 三件套 + panic 注入 `vendor_boot`（`panic=10 … pstore.backend=efi`）+ patched root，目标 EFI pstore | 被 `slot-unbootable:b` 阻断；ABL 从未尝试启动 | **NOT RUN**（日志通道未借该路线验证） |

### 2.2 2026-11-09 → 2026-11-10 —— 完整刷写与包装器实验

| # | 配置 | 结果 | 结论 / 状态 |
|---|---|---|---|
| F1 | 11-09 20:09–20:20；B 槽完整刷写：`boot→vendor_boot→dtbo→init_boot→recovery→vbmeta→vbmeta_system→super`（sparse 40/40，54.9 s）+ `set_active b` | 校验全过、内核启动，卡在系统启动阶段（不再 20 s 被打回） | 刷写方式正确；剩余失败在早期用户态。**CONFIRMED** |
| E-LOS1 | 11-10 21:38–21:47；`super_test5`（原厂 super 仅替换 `system_b`）+ `vbmeta_system_full5` + 原厂启动链；EDL 写 + reset | 重启循环 → EDL | 循环不是诊断包装器引入；“干净”的 LOS 首启同样循环。**CONFIRMED** |
| E-LOS2 | 11-10 22:03–22:42；包装器 vB（`init_boot_new`，open 正确、无 sleep）+ `full6`；后换 vC（`initlog`，`O_RDONLY / O_WRONLY` bug + `sleep(90)`） | 22:06 无 beacon；用户观察“先停 ~90 s 再反复重启”；22:42 回读全成功但 `misc` 仍无 beacon | 包装器能执行（90 s 停顿与 `sleep` 吻合），但 `/init` 时刻 UFS 块设备尚不存在（模块探测 ~1.16 s），且 open 标志错误。**机制 CONFIRMED；该包装器不可用** |
| E-LOS3 | 11-10 23:26 → 11-11 00:53；① restore-stock 15 分区；② 00:03 EDL 重写原厂 GPT → 设备恢复可开机；③ `init_boot_logging`（**kernel_size=1**）+ `vbmeta_system_los`；④ `logging2`（**kernel_size=0**）+ `los2`；⑤ 00:53 读 `misc` | ③ 快速重启循环，包装器不执行；④ 卡第一屏；⑤ `misc` @0x80000 = `counter=67 / "IL7" / stage=2` + cmdline | **两条已证实教训：** (a) 自编 `init_boot` 必须 `kernel_size=0`；(b) 包装器必须立即 flush/mark，父进程在 `exec /init.real` 前不能 sleep。`stage=2` 证明包装器执行且找到 `misc`，但流未落盘 |

### 2.3 2026-11-11 —— 开机轮（A/B 组 → 诊断集 → 首次桌面）

| # | 配置 | 结果 | 结论 / 状态 |
|---|---|---|---|
| A 组 | 21:51–21:53；EDL 刷 `super_v7`（已修 `/vendor` 环）+ `vbmeta_system_v7_stockib` + **原厂** `init_boot` | 设备重启一次落在 bootloader 菜单；首阶段仍 ~0.5 s 死 | 只修 `/vendor` 环在该配置下不足以通过首阶段。**观测 CONFIRMED，原因未单变量隔离** |
| B 组 | 22:00；fastbootd 刷 `vbmeta_system_v7` + `init_boot_logging4`（IL9 包装器） | 约 15–18 s 后回 bootloader；`misc` 日志在 ~482 ms 处硬断 | 同样的首阶段死亡；包装器有效（抓到日志）但致命点未落盘。**对根因 INCONCLUSIVE** |
| 诊断集 | 22:18–22:19；EDL 刷原厂 GPT + `vendor_boot_nofail`（13 行 fstab 加 `no_fail`）+ `init_boot_logging10` + `vbmeta_system_v8`；全部回读 MATCH | **22:35 首次进入第二屏**——`dm-7…dm-13` 全部以 dm-verity 挂载成功、`Opening SELinux policy`，随后 `Compiling SELinux policy` | **`/vendor` 修复被证明有效**（首阶段全部真实挂载成功，不是 `no_fail` 吞错）。**CONFIRMED。** 但该集合同时改了多项，因此“哪一项让首阶段通过”没有单变量证明 |
| diag2 | 22:38–22:44；`vendor_boot_diag2`（去全部 `avb=` + `no_fail` + `androidboot.selinux=permissive` + `printk.devkmsg=on`）+ 1 个 4 KiB policy-hash 扇区补丁（LUN0 LBA 701429，扇区 sha `d05ef83d…`）+ EDL 回读 MATCH | 22:39:42 reset → **+18.4 s adb 上线**（首次进 Android 用户态）；`system_server` 因签名冲突崩溃 | 用 policy 扇区绕过 SELinux 现场编译；首次进用户态。**CONFIRMED**（policy 扇区是副作用：`system_b` 整件 SHA 不再等于镜像） |
| LOS 用户态三件 | 22:45:59；fastbootd 刷 LOS `product_b` + LOS `system_ext_b` + `fastboot -w` | 22:48–22:50 **用户目视进入 LineageOS 欢迎界面**（首个开机成功判据）；23:08 该次启动稳定运行 ≥660 s | 签名冲突修复（三个用户态分区都换成 LOS）。**CONFIRMED——首个“能进 UI”里程碑。** 该轮从未直接读到 `sys.boot_completed`（仅目视） |
| system_ext_mod | 23:12–23:13；EDL 刷 `system_ext_mod.img`（删 `adb_root.rc`、加 `ro.setupwizard.mode=DISABLED`、aera-logdump/provision） | 刷入且回读 MATCH；后续启动均未进系统 | 从未在成功启动上验证。**NOT RUN（无干净结果）** |
| 2.7 s 死亡 | 23:16；启动 2.7 s 后死亡并落原厂 recovery | kmsg 显示 `Opening SELinux policy from monolithic file /sepolicy`；`logdump` 前 64 MiB 全 0 | **该次是 recovery 引导**（首阶段挂载被跳过、root 来自 recovery ramdisk）。**不是**修改版 `system_ext` 的问题，也**不是** `no_fail` 吞错。**诊断 CONFIRMED** |
| diag3 | 23:19:24；EDL 刷 `vendor_boot_diag3`（cmdline 加 `printk.devkmsg=on`） | 启动仍落 recovery（+37 s） | 不是修复。**SUPERSEDED**（可开机变体仍是 diag2） |
| BCB 清零 | 23:44:47；冷 EDL 读 `metadata`/`misc`/GPT；`misc` BCB = `boot-recovery`；写 4 KiB 零清 BCB，回读 MATCH，reset | 23:45:05–23:48:10 仍 recovery（`adb = <SN-REDACTED> recovery`） | **清 BCB 不足以恢复系统引导。CONFIRMED**（BCB 是结果而非原因） |

### 2.4 2026-11-12 —— FBE 实验（用户主诉）

调查的用户主诉：*“只有格式化 data 后才能开机；重启又回 recovery 并报 `init_user0_failed`。”*

| # | 配置 | 结果 | 结论 / 状态 |
|---|---|---|---|
| FBE-off | 23:50–00:20；`vendor_b_raw_mod`（原厂 vendor raw：`/data` 行去掉 `fileencryption`/`keydirectory`/`metadata_encryption`/`checkpoint`/`inlinecrypt`）+ `vendor_boot_diag4`（首阶段 fstab 同样去 FBE）+ `fastboot -w` | **首次越过 `init_user0`**：进入 LineageOS 开机动画；随后卡动画数分钟（该轮记录为 >5 min），USB 不枚举 | 关 FBE 可绕过 `init_user0_failed`，但下一个阻塞点立刻出现（zygote/system_server 崩溃循环）。kmsg：反复 `Service 'zygote' (pid N) received SIGKILL`、`sys.init.updatable_crashing=1`。**FBE 旁路 CONFIRMED，但不是修复** |
| FBE-on + 仅去 checkpoint（仅 vendor 侧） | 00:30–00:40；`vendor_b_checkpoint_off`（原厂 vendor 只删 `/data` 行 `checkpoint=fs`）+ `vendor_boot_diag2`（首阶段 fstab 仍保留 checkpoint）+ `fastboot -w` | 36–47 s → recovery，`Reason: init_user0_failed` | **实验不干净**：首阶段 fstab 的 checkpoint 仍在，两处 fstab 必须一致。**INCONCLUSIVE** |
| 2b —— 恢复已知可开机集 | 00:35–00:52；EDL 重刷已知可开机集（`vendor_b_full_stock`、`system_ext_raw`、`init_boot_logging10`、`vbmeta_system_v8` + 清零 userdata/metadata 头） | 仍 47 s → recovery；再写原厂 GPT + 清 BCB → 仍 39 s → recovery | **教训：** EDL 裸清零 `userdata`/`metadata` 超级块**不等价于** `fastboot -w`/recovery 清数据流程；多次裸清后“首启进欢迎界面”状态无法复现。**流程教训 CONFIRMED** |
| 7 s 死亡 | 00:44；读 `misc`（`IL12`）：`counter=1247 ticks=700 uptime=7s snaps=2`；最后一条 init 记录 `init: [libfs_avb] Device path not found: /dev/block/by-name/vbmeta_b`（6.50 s） | 启动约 7 s 后死亡，死在首阶段 | 该次启动的首阶段 fstab 仍带 AVB 标志（或当时 GPT 非原厂——原厂 GPT 直到 00:56 才重写）。**机制 CONFIRMED**；具体变体配置未记录（教训） |
| #3 —— 纯 v2 软件密钥 FBE | 00:59–01:10；`vendor_b_plainfbe`（FBE 保持开启，不 wrappedkey/不 metadata 加密/不 checkpoint/不 inlinecrypt；`:v2`）+ `vendor_boot_diag5` + `fastboot -w` | 卡开机动画 >280 s，USB 不枚举；用户确认“还是卡开机动画” | “卡动画”的根因**不是**加密方式。**CONFIRMED 排除**（与 FBE-off 症状相同） |

### 2.5 2026-11-12 —— 真凶（logdump 写坏 `metadata`）与 F0 验证

| # | 配置 | 结果 | 结论 / 状态 |
|---|---|---|---|
| 根因 | 离线镜像证据：LOS `system` 自带 `/system/bin/logdump.sh` + `/system/etc/init/logdump.rc`；rc 在 `early-init`/`init`/`post-fs-data`/`boot` 执行 `logdump.sh once 0 / 8 / 16 / 24`，脚本执行 `dd … of=/dev/block/by-name/metadata bs=4096 seek=$((OFF_MB*256)) conv=fsync` | `once 0` **每次启动**覆盖 metadata 的 f2fs 超级块：factory reset 后首启正常 → 该次启动即写坏 metadata → **下次**重启挂不上 metadata → vold/FBE 链失败 → `init_user0_failed` → recovery 要求清数据 → 循环 | **用户主诉真凶 CONFIRMED。** 失败链从上一启动的残留日志区逐行还原（`Failed to create /metadata/vold` → `read_key failed` → `encryptFstab Failed` → `make_f2fs` → `queue_fs_event` → `user_keys` 缺失 → `vdc cryptfs init_user0 Failed`） |
| F0 组件 | 从 `system` 删除 `logdump.sh` + `logdump.rc`（变化 9 块 / 36 KiB：块 0,1,3,30,53,62069,65536,79494,81367）+ 保留 policy 扇区（块 81367，当前刷写集下惰性） | `system_raw_nologdump.raw` sha `b6ca50f5…`，9 块差异与 `blocks.tsv` 完全一致；`e2fsck -fn` clean | **离线性 CONFIRMED** |
| F0 真机验证 | 20:24 EDL 直写 F0 六件（9 块 system 补丁 + `system_ext_f0diag` + `vendor_b_full_stock` + `vendor_boot_diag2` + `init_boot_logging13` + `vbmeta_system_v10`），回读 ALL OK；`power reset`；落原厂 recovery（预期，旧 metadata 已坏）→ 用户 factory data reset → 20:35 `sys.boot_completed=1` → 3/3 重启回归 PASS | 无 `init_user0_failed`；`/metadata`（sda10 f2fs）与 `/data`（dm-49 f2fs inlinecrypt）正常挂载；`logdump.sh/rc` 已不存在；adb 在线 | **CONFIRMED——用户可见 bug 已修复。** 验收：`f0-postboot-verify.ps1 -RebootTest 3` → `RESULT: PASS`（exit 0） |
| verity 恢复准备 | 重算 system hashtree（`system_verity.raw`，sha `29ad60fb…`，新 root digest `9103aeb9…`）+ `vbmeta_system_f0_v11`（sha `66e20599…`）+ 启用 AVB 的 `vendor_boot` | 离线 `avbtool verify_image` staged 校验全 PASS | **尚未真机执行**——F0 刷写集下不要开 verity |
| `fastboot fetch` 可用性 | 准备捕获时发现：platform-tools 37 在 fastbootd 支持 `fastboot fetch <partition> <file>` | 可免冷 EDL 取 `misc`/`logdump`/`metadata` | **命令存在 CONFIRMED**；512 MiB 整片 fetch 未端到端跑完（**待验证**） |

---

## 3. 已排除 / 已推翻的假设（不要再试）

| 假设 | 状态 | 证据 |
|---|---|---|
| “自签 `vbmeta` 必死（8 s 落 fastboot）” | **已推翻** | E12：AOSP testkey root + testkey `vbmeta_system` + 原厂内容 → `sys.boot_completed=1`。只有**自造的非 testkey 密钥**必败。见 `09-AVB-CHAIN-NOTES.md` §5 |
| “8 s 落 fastboot 是 AVB 拒绝签名造成的” | **作为单一原因已推翻** | `init_boot`/`dtbo`/`vendor_boot` 的 footer 全是 `Algorithm: NONE`（根本没签名）；8 s 与 AOSP init 遇致命错误后 `sleep(5)` + 重启到 bootloader 的路径吻合。成因多重：混合链/漏描述符、非 OEM `init_boot`、槽位 unbootable |
| “关掉 dm-verity（`vbmeta_system flags=1`）能修好第一屏失败” | **已推翻** | E7：关 verity 后仍重启循环 |
| “VINTF manifest/matrix 不匹配是第一屏失败原因” | **已推翻** | E9、E13 换整套原厂 VINTF 仍卡 |
| “SELinux 拒绝是阻塞点” | **（在该阶段）已推翻** | 真正问题是运行时 `secilc` 因原厂 `product`/`system_ext` 策略引用 OEM 独有 type 而 rc=254；换 LOS 用户态三件后 rc=0 |
| “清 data 能修复重启问题” | **作为修复已推翻** | 只能撑到当前这次启动再次写坏 `metadata`（F0 根因）。这是只有一次启动寿命的绕过手段 |
| “`fastboot -w` 会格式化 `/data` 与 `/metadata`” | **在 Windows 上已推翻** | 没有 host 端 `mke2fs`/`make_f2fs` 的 platform-tools 只擦除，并打印 `Erase successful, but not automatically formatting. File system type raw not supported.` |
| “擦/写 `devinfo`/`efisp`/`uefivarstore` 能清 `slot-unbootable`” | **已推翻** | 这些分区与出厂逐字节一致；槽位状态在 GPT 属性（LUN4 `boot_b` entry #53，attr byte 54）。擦它们毫无作用 |
| “`slot-unbootable` 存在 `misc` / RPMB / `persist`” | **按原文表述已推翻** | `misc` 内没有 AOSP bootloader-control 的 `BCAB` magic；这些分区全盘比对均与出厂一致；真正生效的修复是整对写回原厂 GPT |
| “`vendor_boot` 不能改，否则 AVB 会拒绝” | **已推翻** | 解锁态 ABL 容忍 hash 不符（`State: Unlocked, AvbSlotVerify returned …, continue boot`）；只观测到 orange + 第一屏失败，没有 8 s 落 fastboot |
| “`no_fail` 让启动成功” | **作为根因已推翻** | 22:35 日志显示 `dm-7…dm-13` 是真实挂载的文件系统（不是被吞的失败）。真正的修复是 `/vendor` 符号环修复；22:18 集合同时改了多项，`no_fail` 的贡献未被隔离 |
| “出现 `dm-N` 就证明 AVB 校验通过” | **已推翻** | 即使 `kVerificationError`，dm-verity 表仍会创建；真正校验推迟到读块（不符则 EIO） |
| “自编 `init_boot` 用 1 字节 kernel 可行” | **已推翻** | `kernel_size=1` → 快速重启循环，包装器不执行；必须 `kernel_size=0` |
| “包装器可以先 sleep/等块设备再 `exec /init.real`” | **已推翻** | UFS 模块探测需要真 init 继续跑（~1.16 s）；父进程 sleep 会卡住启动，子进程永远等不到设备 |
| “`system_ext` 服务可以抓早期启动日志” | **对早期阶段已推翻** | `class core`/`post-fs-data` 起得比崩溃晚；捕获全部错过。应使用 `init_boot` 包装器 |
| “`pstore`/`ramoops`/`last_kmsg`/`logfs` 能提供失败启动日志” | **已推翻** | 无 ramoops DT 节点（`dtb_size=0`，reserved-memory 查找全 -1）；VT/FB 关闭；EFI pstore 无记录（失败非 panic 型）；`logfs` 被清零后 FAT 损坏 |
| “`adb_root.rc` 重启 `adbd` 导致 `adb shell FAIL closed`” | **已推翻** | 源码分析：`adb_root` 是被动 AIDL 服务；清 data 后未授权才是真正原因 |
| “recovery 引导的日志可以用来诊断 ROM” | **已推翻** | recovery 模式跳过首阶段挂载并使用 monolithic `/sepolicy`；在那里 2.7 s 死亡是预期结果 |
| “上一轮的 `vbmeta_system` 仍匹配当前 `system`” | **已推翻** | 内容一变 system 描述符就失效；verity-on 下旧配对直接 dm-verity EIO。见 `09-AVB-CHAIN-NOTES.md` §9 |
| “重刷 `init_boot` 后，`dataext_b`/`pvmfw_b`/`recovery_b` 可以按原厂假设” | **假设未验证** | 开机修复轮从未回读其内容。`recovery_b` 换成非原厂 recovery 会让 `AvbHandle::Open()` 失败（`ERROR_INVALID_METADATA`） |
| “清 BCB 能恢复系统引导” | **已推翻** | 清 BCB 后设备仍进 recovery（23:45–23:48） |
| “LOS 用户态失败是 VINTF/AVB 问题” | **已被取代** | 首阶段失败是文件系统拓扑 bug（`/vendor` 符号环）；用户态失败是签名冲突（OEM 与 LOS 用户态混装）。两者均已复现并修复 |

---

## 4. 失败配置清单（不要再重复）

每一行都是试过且**没有**进桌面的配置。除非在测一个新单变量，否则复现它们只会浪费设备轮次。

| 配置（关键件 + sha 前缀） | 观测结果 | 失败原因 |
|---|---|---|
| `super_test5` + `vbmeta_system_full5` + 原厂链 | 重启循环 → EDL | `system` 里仍有 `/vendor` 符号环 |
| `super_b` + `vbmeta_system_b_full` + testkey root（E1） | 回落 bootloader fastboot | 描述符引用了未刷的 `pvmfw_b`/`dataext_b` |
| LOS 内容 + 原厂 `vbmeta_system`（E12 前） | 第一屏后循环 / 卡 | 内容与描述符不匹配 |
| `vbmeta_system` `flags=1`（E7） | 同样循环 | verity 不是原因 |
| 整套换原厂 VINTF（E9/E13） | 卡第一屏 | VINTF 不是原因 |
| `init_boot_new`/`init_boot_dbg*`（1 字节 kernel） | 重启循环，包装器不执行 | `kernel_size` 必须为 0 |
| 包装器在 `exec` 前 `sleep(90)` | 停 90 s 后循环，无持久日志 | 父进程必须立即 exec；轮询/写入交给子进程 |
| `vendor_b_raw_mod`（关 FBE） | 卡开机动画、无 USB | 下一个阻塞点（system_server/zygote）出现 |
| 只刷 `vendor_b_checkpoint_off` | 仍 `init_user0_failed` | 实验不干净：首阶段 fstab 仍带 `checkpoint=fs` |
| `vendor_b_plainfbe`（v2 软件密钥） | 卡开机动画 | 加密方式不是卡动画的原因 |
| `system_ext_mod`（删 adb_root.rc、`ro.setupwizard.mode=DISABLED`） | 未在干净启动上验证 | 该属性在本树无运行时消费者；可靠绕过是删向导 APK |
| `system_ext_logcat` / `diag3` 捕获服务 | 空 logdump / 只有头 | `logcat -v pid` 非法；`class core` 起得太晚 |
| 把 `vendor_boot_diag3/4/5` 当启动修复件 | recovery 或卡住 | 不是根因；只是诊断变体 |
| 从 bootloader fastboot `fastboot reboot fastboot` | `AdbWriteEndpointSync failed: 超时121` | 槽位 unbootable 时 BL fastboot 进不了 fastbootd |
| EDL 裸清零 `userdata`/`metadata` 超级块 | 无法复现“首启进欢迎界面”状态 | 裸清零 ≠ recovery wipe/format；`wiped` 标志/格式化路径才是关键 |
| 原厂 GPT + 清 BCB 当开机修复 | 仍 recovery | BCB 是结果；内容/FBE 链才是原因 |
| 只加 `ro.setupwizard.mode=DISABLED` 关向导 | 无效 | 该属性无消费者；需删 `LineageSetupWizard` 目录并置 `device_provisioned`/`user_setup_complete` |
| 删 `adb_root.rc` 想修 adb | 授权问题无变化 | 被动服务；真正丢的是 `/data/misc/adb/adb_keys` |

---

## 5. 最费时间的流程坑（非技术）

1. **相信过期文档。** 早于最新刷写集的结论反复出错（“自签 vbmeta 必死”“从未开机”“/data 已排除”）。行动前必须重读当前状态 + 最新证据目录。
2. **开机轮缺单变量纪律。** 22:18 诊断集同时改了 GPT、`vendor_boot` 标志、`init_boot` 包装器与 `vbmeta_system`。它证明了 `/vendor` 修复有效，但无法隔离“no_fail vs GPT vs 去 avb”。后续每轮只改一项。
3. **没有逐次记录镜像 SHA。** 7 s 死亡无法归因到具体 `vendor_boot` 变体，因为只记了文件名没有 SHA-256。每次启动前记录所有已刷分区的 SHA。
4. **混用不同启动的日志。** `misc` 环形/快照区跨启动看起来是连续的。分析前按 `ctl.snap_len`（IL12）或最后一个 `INITLOG13` 头切分。
5. **相信刷写工具的“成功”。** EDL 对失败的 LUN4 写也报成功；每次写必须回读算哈希。
6. **静默失效的捕获脚本。** `logcat -v pid`（非法）与 `logcat -G`（设完即退）都产生“只有头”的捕获，被误当成“没有崩溃”。
7. **把 recovery 引导当成 ROM 失败。** recovery 引导跳过首阶段；当正常启动分析会得出错误结论。
8. **诊断写进 `metadata`。** F0 前的捕获脚本裸写 `metadata`，制造了它本该诊断的 `init_user0_failed` 循环。
9. **不干净的数据状态操作。** EDL 擦超级块不等于 recovery 格式化；“factory reset 后首启”状态无法用这种方式复现。
10. **工具/会话卫生。** 残留 `fh_loader` 占着 COM3；`adb` 可能已占用 5037；PowerShell 变量名大小写不敏感（`$O` 与 `$o` 曾导致路径错乱）；辅助函数的 `$args` 冲突曾把 adb 帮助文本写进证据文件（必须从完整快照重新生成）。
11. **磁盘空间。** 生成大镜像会写满主机磁盘；靠清理陈旧中间镜像回收空间。生成 20 GiB 镜像前先清理。
12. **设备 RTC 是 GMT。** 屏幕/dmesg 时间比本地早 8 h，属正常现象，不是启动 bug。

---

## 6. 下一轮实验队列（尚未执行）

| # | 实验 | 目的 | 状态 |
|---|---|---|---|
| F1 | 硬件功能实测（WiFi、相机、音频、传感器、亮度、触控、指纹、OTA） | 目前只确认 HAL 服务 running，未做功能验证 | **TODO** |
| F2 | 在 F0 刷写集上做 ≥5 次冷启动 + 1 次断电重启 | 超越已通过的 3 次重启验收，验证数据持久性 | **TODO**（3/3 已 PASS） |
| F3 | 用 `system_verity.raw`（`29ad60fb…`）+ `vbmeta_system_f0_v11`（`66e20599…`）+ 启用 AVB 的 `vendor_boot` 恢复 dm-verity/enforcing | 发布态卫生 | **TODO——配方已备，尚未真机验证** |
| F4 | 包装器加 `printk_ratelimit=0` / `printk_ratelimit_burst=9999` | 阻止生产端丢日志 | **TODO**（已提议，未构建） |
| F5 | 干净槽位下测 `chain boot→testkey` | 关闭 E11 的 inconclusive 结论 | **TODO** |
| F6 | 回读 `dataext_b`/`pvmfw_b`/`recovery_b` 并与原厂比对 | 关闭“按原厂假设”的缺口 | **TODO** |
| F7 | 经 fastbootd 完整 fetch 512 MiB `logdump` | 验证最快捕获路径 | **TODO** |
| F8 | 决策是否回退 F0 `system` 里的 policy-hash 块 | 该补丁当前惰性；一旦同时刷原厂 `product`/`system_ext` 会静默切到原厂预编译策略 | **TODO（决策）** |

---

## 7. 证据来源（相对 `<PROJECT_ROOT>`）

- `out/2026-11-10-los24-logdump/LOS24-PLAYBOOK-CONSOLIDATED.md` §5（E1–E13、E-LOS1/2/3 实验台账）、§6.1（被推翻结论）、§6.3（新教训）。
- `out/2026-11-10-los24-logdump/FACTS-SESSIONS.md` §3、§5、§6、§8、§10（历史、不可用通道、禁止事项）。
- `out/2026-11-11-los24-bootfix/SESSION-20261112-FBE-ROOTCAUSE-LOG.md` —— 2026-11-12 FBE 实验轮 #1/#2/#2b/#3 与诊断通道。
- `out/2026-11-11-los24-bootfix/ROOTCAUSE-LOGDUMP-METADATA.md` —— metadata 被写坏与 FBE 链的最终根因。
- `out/2026-11-11-los24-bootfix/SYSTEM-LOGDUMP-REMOVAL-REPORT.md` —— F0 组件制作与离线验证。
- `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` —— F0 真机验收（首启 + 3/3 重启回归）与剩余风险。
- `out/2026-11-11-los24-bootfix/VERIFY-REPORT.md` —— `/vendor` ELOOP 根因与独立复核。
- `out/2026-11-11-los24-bootfix/BOOT-DOCTOR-REVIEW.md` —— 捕获裁决与按 `snap_len` 切分的修正。
- `out/2026-11-11-los24-bootfix/ADB-ROOT-ANALYSIS.md` —— adb 授权、向导绕过、recovery 引导诊断。
- `reports/BOOT-SUCCESS-20261111.md`（位于 `<WORKSPACE>/reports/`）—— 2026-11-11 开机轮的时间线还原，含诚实 caveat（`sys.boot_completed` 未直接读到、未做单变量隔离）。
