作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0

# 06 — 根因：`logdump.sh` 每启动 `dd` 写坏 `/metadata` → `init_user0_failed` → 被迫清 data

| 项 | 值 |
|---|---|
| 状态 | 2026-11-12 — 根因 2026-11-11/12 离线定案并产出修复件，**当日完成真机验证**（F0 修复集：首启进桌面 + 连续 3 次重启 PASS） |
| 适用设备 | Lenovo Legion Y700 五代 **TB323FU**，SN `<SN-REDACTED>`，SM8850P（canoe / kaanapali），A/B，4 KiB 页，unlocked（`vbs=orange`），B 槽 active |
| 适用对象 | 2026-11-12 之前构建的 LineageOS 24.0（Android 17）移植 `system_b` 镜像；`/metadata`=`/dev/block/sda10`（f2fs，64 MiB），`/data`=`/dev/block/sda14` / dm-49（f2fs，inlinecrypt） |
| 证据来源 | `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\ROOTCAUSE-LOGDUMP-METADATA.md`、`…\SYSTEM-LOGDUMP-REMOVAL-REPORT.md`、`…\F0-SIDE-EFFECT-AUDIT.md`、`…\SESSION-20261112-FBE-ROOTCAUSE-LOG.md`、`…\NEXT-ROUND-TEST-PLAN.md`；`<PROJECT_ROOT>\out\2026-11-12-edl-f0\F0-ACCEPTANCE-REPORT.md` |

---

## 1. 现象

用户连续多日的核心主诉是：**"必须格式化 data 才能开机；开机一次之后再正常重启，又直接回 recovery（`init_user0_failed`）"**。原厂 recovery 屏幕显示：

```
Can't load Android system. Your data may be corrupt. …
Reason: init_user0_failed
```

（recovery 文案路径 `bootable/recovery/recovery.cpp:301-314`；reason 字符串由 init 通过 `reboot_into_recovery(--reason=…)` 传入。）

单次启动可以进入 LineageOS 欢迎界面并稳定运行 ≥11 分钟（2026-11-11 22:48–23:08），但任何一次重启都以 recovery 收场，或卡在开机动画；清掉 `/data` 后**下一次**首启又能进系统——形成"每次重启都要清 data"的死循环。

## 2. 元凶

LineageOS 构建出的 `system` 镜像里带着一对 bring-up 本不打算发布的调试抓取脚本，它**每次启动都把裸块写进 metadata 分区**：

| 文件 | inode | mode / owner | 大小 | 作用 |
|---|---|---|---|---|
| `/system/bin/logdump.sh` | 431 | 0755 root:2000 | 1,336 B | "LOG CAPTURE v3" shell 脚本；把快照 `dd` 进 metadata |
| `/system/etc/init/logdump.rc` | 791 | 0644 0:0 | 547 B | 在四个启动阶段执行该脚本，并拉起循环服务 |

`/system/etc/init/logdump.rc`（原文）：
```
on early-init
    exec -- /system/bin/logdump.sh once 0
on init
    exec -- /system/bin/logdump.sh once 8
on post-fs-data
    exec -- /system/bin/logdump.sh once 16
    start logdump_loop2
on boot
    exec -- /system/bin/logdump.sh once 24
service logdump_loop2 /system/bin/logdump.sh loop
    class late_start
    user root
    group root system
    disabled
```

`/system/bin/logdump.sh`（关键行）：
```
DEV=/dev/block/by-name/metadata
...
{ cmdline; getprop; dmesg; } > /dev/rawlog.tmp
dd if=/dev/rawlog.tmp of="$DEV" bs=4096 seek=$((OFF_MB*256)) conv=fsync
cp -f /dev/rawlog.tmp /metadata/logdump.txt
```

`once 0` 在 `early-init` 执行，从 **metadata 偏移 0 开始写入 4 KiB 对齐的快照——直接覆盖 f2fs 超级块**；`once 8/16/24` 覆盖分区中段。写入带 `conv=fsync`，真实落到块设备，且发生在 recovery 刚格式化完 metadata **之后**、下一次启动尝试挂载 metadata **之前**。

## 3. 证据链

### 3.1 镜像层（字节证据）

对当时设备上 `system` raw 镜像做 `debugfs`，上述两文件存在且内容与引用一致；修复后两路径均返回 `File not found`，inode 已释放。四个 `exec` 阶段由 rc 原文证明，偏移与真机写入位置对应。

### 3.2 设备层（写入确实发生）

EDL 导出的设备 `/metadata` 分区（`device/metadata_*.bin`）在 **0 / 8 / 16 / 24 MB** 偏移处反复出现如下头部：

```
==== LOGDUMP3 mode=once ... uptime=1.0x ====
--- cmdline ---
```

——正是 `logdump.sh once 0|8|16|24` 的产物。

### 3.3 写坏之后的失败链（上一启动日志区原文）

```
vold: Failed to create /metadata/vold: Read-only file system        ← /metadata 未挂载（目录落在只读 root）
vold: read_key failed in mountFstab
vdc: Command: cryptfs encryptFstab ... Failed
make_f2fs: mkfs.f2fs Ver 1.16.0                                    ← /data 被二次格式化
F2FS-fs (sda14): Mounted with checkpoint version ...               ← userdata 挂载（sda14=userdata）
vold: Failed to create /metadata/vold: Read-only file system        ← /metadata 仍未挂载
init: Command 'mount_all /vendor/etc/fstab.qcom --late' ... failed: queue_fs_event() failed: Invalid code: -1
vold: keystore2 Communication with Keystore earlyBootEnded failed error: -129
cutils: Failed to mkdir(/data/misc/vold/user_keys): No such file or directory
vold: Failed to prepare /data/misc/vold/user_keys: No such file or directory
vdc: Command: cryptfs init_user0 Failed: Status(-8, EX_SERVICE_SPECIFIC): '0: '
```

对照一次已知成功启动（23:08 进欢迎界面那次）的 kmsg：

```
F2FS-fs (sda10): Mounted with checkpoint version = 581f46d7
```

`sda10` 即 metadata。失败启动只有 `sda14`（userdata）、**没有 `sda10` 行**——metadata 根本没挂上。

### 3.4 为什么表现为"清 data → 首启正常 → 下次重启又坏"

1. recovery 的"Factory data reset"真正格式化 `sda10`（metadata）与 `sda14`（data）→ metadata 干净 → 当次首启挂载成功，vold 初始化 FBE，`init_user0` 成功，系统进 UI。
2. 同一次启动中，`logdump.sh once 0` 覆盖 metadata 的 f2fs 超级块（以及 8/16/24 MB 段）。
3. 下次启动首阶段挂载 metadata 失败，而该表项带 `first_stage_mount,no_fail`，失败被**静默吞掉**；首阶段**从不格式化**。"被写坏"≠"wiped"，第二阶段的自动格式化也不会触发。
4. `/metadata` 不可用 → `vold` 无法创建 `/metadata/vold`，`read_key` 失败，`/data` 被二次格式化，`mount_all --late` 失败，post-fs-data 未完成，`/data/misc/vold/user_keys` 不存在，`vdc cryptfs init_user0` 失败。
5. `init_user0` 失败 → init **强制重启进 recovery，reason=`init_user0_failed`** → 闭环。只有再清一次数据才能打破循环。

### 3.5 为什么首阶段 / `fastboot -w` 都救不了

- `first_stage_mount.cpp:377-385`：带 `no_fail` 的表项挂载失败只打 `INFO`，不致命；首阶段**从不格式化**分区。
- 第二阶段的自动格式化只在判定 "wiped"（分区头被清零）时触发；"被写坏但未 wipe"不满足条件。
- 只有 recovery 的清数据路径会真正格式化 metadata（`bootable/recovery/install/wipe_data.cpp:151-153`）。
- 在本机 Windows 平台上，`fastboot -w` 只做 **erase**（输出 `not automatically formatting`），并不格式化 f2fs。所以最终采用的流程是进原厂 recovery 点一次"Factory data reset"。

### 3.6 `init_user0` 源码链（备查）

- `system/core/rootdir/init.rc:1086` — `on post-fs-data`（块从 `:707` 开始，vold 在 `:602` 启动）里的 builtin `init_user0`。
- `system/core/init/builtins.cpp:1190-1192` — `do_init_user0()` → `ExecVdcRebootOnFailure("init_user0")`。
- `builtins.cpp:1151-1177` — 以临时 oneshot service 执行 `exec /system/bin/vdc --wait cryptfs init_user0`；失败时置 `reboot_reason = vdc_arg + "_failed"`，若 `IsFbeEnabled() && !IsGsiRunning()` 则 `reboot_into_recovery({"--prompt_and_wipe_data", "--reason=…"})`；若 FBE 未启用只打 `"Failure (reboot suppressed)"`（不跳 recovery）。
- `system/vold/vdc.cpp:163-164` → `VoldNativeService.cpp:631-635` → `system/vold/FsCrypt.cpp:655-690` `fscrypt_init_user0()`（在 `/data/misc/vold/user_keys` 下创建/加载 DE/CE 密钥、准备特殊目录、`fscrypt_prepare_user_storage`）。

## 4. 修复（F0 修复集）

### 4.1 从 `system` 删除两个文件

对当时 `system` raw 镜像执行 `debugfs -w`：

```
rm /system/bin/logdump.sh
rm /system/etc/init/logdump.rc
```

断言：两路径 `File not found`；扫描 `/system/bin`、`/system/etc/init`、`/system/etc` **无其它** `logdump`/`aera`/`rawlog` 残留；`e2fsck -fn` clean。`logdump_loop2` 服务随其 rc 一并消失。

随后做全镜像扫描，确认没有其它对 `/dev/block/by-name/metadata` 的裸写者：
- 唯一 live 写者就是 `logdump.sh` 自身（已删除）；
- `/system/bin`、`/system/etc/init` 目录块里仍残留被删文件的**名字字节**——ext4 删除不清零数据块，这些字节无法被 lookup 到；
- 原厂 vendor 的 `rawdump`/`ramdump` 机制写的是 **rawdump 分区**，不是 metadata（`/bin/init.qcom.sh`：`RAWDUMP_LINK="/dev/block/bootdevice/by-name/rawdump"`）；
- `/etc/fstab.qcom` 的命中是正常的 metadata **挂载**条目；SELinux 策略文件里的命中只是 label/type 字符串（`vendor_logdump_partition`、`metadata_block_device`）。

结论：删除后没有任何 live 组件再对 metadata 做裸写；`vold`/`fs_mgr`/`make_f2fs` 对它的访问只走正常挂载/格式化/修复路径。

### 4.2 块级补丁（36 KiB，而不是写 10 GB）

修复后的 system raw 是 `system_raw_nologdump.raw`；与被修镜像相比**恰好 9 个块 / 36,864 B 不同**（AVB hashtree/FEC 尾部区域 0 变更）。设备 `system_b` 起始绝对 4 KiB LBA 为 **620,062**，块 `n` 写入 LBA `620062 + n`：

| block_index | 目标 LBA | old sha16 | new sha16 |
|---|---|---|---|
| 0 | 620062 | `09d232326e3bf282` | `f9aaa28b1f1e3ba8` |
| 1 | 620063 | `c41a9b84f11eb1f1` | `3b9c21346ddb31d5` |
| 3 | 620065 | `c8ad46f3c0f44c20` | `d4cc0a1c95ac8d73` |
| 30 | 620092 | `98226916179acdf3` | `20c6722a95aeecbb` |
| 53 | 620115 | `f64aee737d37db85` | `be8d59b287460f5a` |
| 62069 | 682131 | `bdd5e30403307c9b` | `675ccdfb5b07fc58` |
| 65536 | 685598 | `f47a8ec3e9aff231` | `25a57db227761553` |
| 79494 | 699556 | `60f61b5487841a32` | `38b7e4e4c40b7b6d` |
| 81367 | 701429 | `9884c84c86e3ae0c` | `d05ef83d3abc4e01` |

分类：`62069` = `/system/bin` 目录块（删除 `logdump.sh` 入口）；`79494` = `/system/etc/init` 目录块（删除 `logdump.rc` 入口）；`81367` = `/system/etc/selinux/plat_sepolicy_and_mapping.sha256` 数据块（4 KiB policy 补丁，见 doc 08）；`0/1/3/30/53/65536` = ext4 元数据（删除引起的超级块/GDT/inode 表/位图更新）。被删文件本身的数据块（71,131 与 79,567）**不在**这 9 块里，原因同样是 ext4 删除不清零。

### 4.3 F0 写入流程（2026-11-12 实际执行）

1. 设备进 EDL（9008，COM3）。只读预检（`edl-precheck.py`）：GPT LUN0/LUN4 与原厂参考 **MATCH**、misc BCB 空、9 块分类为 8 OLD + 1 NEW（policy 块此前已打过）、记录在役 `init_boot_b`/`vbmeta_system_b` 实测 sha。
2. 用 `flash-system-blocks.py --no-reset` 写入 9 块（36 KiB，LBA 620062..），回读 first/mid/last **MATCH**；写后 dump 复核 9/9 NEW。
3. 其余 5 分区 EDL 直写（不走 fastbootd）：`vendor_b_full_stock`（`08caa9a6…`）、`vendor_boot_diag2`（`40623569…`）、`init_boot_logging13`（`baf1133d…`）、`vbmeta_system_v10`（`2b52e26b…`）、`system_ext_f0diag`（`e1addc29…`）。每件均以 head/tail 回读校验（小分区整件 sha）。
4. `power reset`（fh_loader `<power value="reset"/>`）。
5. 20:29:17 设备落在**原厂 recovery**——**计划内**，因为设备上的旧 metadata 已被旧 logdump 写坏。
6. 用户点一次 **Factory data reset**（约 20:29:5x），真正格式化 `data` + `metadata`。
7. 首启：20:30:22 MTP、20:35:00 adb 在线且 `sys.boot_completed=1`；随后 `f0-postboot-verify.ps1 -RebootTest 3` → **RESULT: PASS（exit 0）**。

### 4.4 真机验收证据

| 判据 | 实测值 | 证据文件 |
|---|---|---|
| `sys.boot_completed` = 1 | `1` | `device/postflash/boot_completed.txt`、`postflash-final/getprop-final.txt` |
| `init.svc.bootanim` 停止 | `stopped` | `postflash/bootanim.txt` |
| 无 SetupWizard / 已 provision | `persist.sys.device_provisioned=1`；`settings device_provisioned=1`、`user_setup_complete=1`；`/system_ext/priv-app/LineageSetupWizard` 不存在；用户目视直接进桌面 | `postflash/getprop-full.txt`、`provision-final.txt`、`setupwizard-check.txt` |
| FBE 正常 | `ro.crypto.state=encrypted`、`ro.crypto.type=file`、`ro.crypto.metadata.enabled=true`、`vold.post_fs_data_done=1`、`sys.user.0.ce_available=true` | `postflash-final/getprop-final.txt` |
| `/metadata` 已挂载 | `/dev/block/sda10 on /metadata type f2fs (rw,…)`；子树含 aconfig/apex/bootstat/gsi/ota/password_slots/prefetch/staged-install/tradeinmode/vold/watchdog | `postflash-final/mounts.txt`、`postflash/metadata-ls.txt` |
| `/data` 已挂载 | `/dev/block/dm-49 on /data type f2fs (rw,…,inlinecrypt)`；`df`：213G / 用 1.8G / 1% | `postflash-final/mounts.txt`、`data-fs.txt` |
| 内核侧 data 挂载 | `F2FS-fs (dm-49): Mounted with checkpoint version = 59dfa388` | `postflash-final/dmesg.txt` |
| 设备上 logdump 已移除 | `/system/bin/logdump.sh: No such file or directory`；`/system/etc/init/logdump.rc: No such file or directory` | `postflash/logdump-check.txt` |
| `init_user0` 正常 | logcat 中恰 1 条 `vold: fscrypt_init_user0`，`init_user0_failed`/`Failed to create /metadata`/`mount_all --late` 命中 0 | `postflash-final/logcat-all.txt`（grep 统计） |
| **重启不再要求清 data（主目标）** | `f0-postboot-verify.ps1 -RebootTest 3` → `RESULT: PASS`、exit 0；每次 `adb reboot` 后 `boot_completed=1`；`persist.sys.boot.reason.history` = 3 条 `reboot,shell`（无 factory_reset/recovery） | `postflash-final/postboot-reboot-regression.log`、`boot-reason-history.txt` |
| 系统服务健康 | zygote64/system_server/webview_zygote 运行；无 logdump 进程；WiFi/蓝牙/相机/传感器/显示/指纹相关 HAL 服务均 running | `postflash-final/ps-A.txt`、`getprop-final.txt` |
| 视觉证据 | 设置界面（USB 偏好页）截图；桌面可达由用户确认 + `boot_completed=1`/`bootanim=stopped`/Launcher 进程佐证 | `postflash-final/screen-final.png` |

## 5. 副作用审计（节选）

1. 删除后**没有其它 live metadata 写者**；其余命中均为 ext4 free block 里的陈旧字节、挂载条目、SELinux label，或假阳性（APK 内的巴斯克语资源串）。
2. **无悬空引用**：`logdump.sh`/`logdump_loop2` 只被同时删除的 `logdump.rc` 引用；没有 `import logdump.rc`；AOSP init 自动扫描 `/system/etc/init`，少一个 rc 文件无影响（`init.cpp:347-380`）。即使假设有遗留 `exec`/`start`，也只记 `Could not create exec service` / `Service not found`，不会阻断启动（`builtins.cpp:244-255`、`270-281`；`parser.cpp:177-184`）。
3. **AVB footer 仍是旧数据**：F0 raw 的 root digest 仍为 `2a3c7c06…`。当前 verity-off 刷写集无影响；恢复 verity 需重算 hashtree/FEC：新 system root digest `9103aeb99e58b9356d7f6d1b7a629a148798926a7206ab9cc4dd978beedd5887`、新 raw sha `29ad60fb…`、配对 `vbmeta_system_f0_v11.img`（`66e20599…`，staged verify PASS），并需换回带 avb 的 `vendor_boot`。
4. **4 KiB policy 补丁当前是惰性的**：F0 仍保留该块（81367），但 `product`/`system_ext` 是 LOS 构建件，其 hash 文件（`75a11da4…`、`71cdbbf6…`）与 stock 预编译值不匹配，init 启动时仍走 CIL 现场编译，补丁不生效。若将来把 stock `product`/`system_ext` 与本 system 一起刷，三者会匹配并静默切到 stock `/odm` 预编译策略——需明确决定是否回退该块（见 doc 08）。
5. **`fastboot -w` ≠ 格式化**：本机 Windows platform-tools 上它只 erase；F0 流程改用 recovery 的"Factory data reset"，因为原厂 recovery 会真正格式化 `data` 与 `metadata`（`wipe_data.cpp:151-153`）。
6. **设备侧动态日志**：装 `init_boot_logging13` 时写的是 `logdump` 分区（`/dev/block/logdump` 的 avc 行是该设计的行为，不是写 metadata）；恢复干净 init_boot 后消失。
7. 依赖 `LOGDUMP3`/`/metadata/logdump.txt` 的旧诊断工具会找不到输入；改用 logdump 分区 kmsg 抓取或 logcat→rawdump。

## 6. 未验证 / 局限

1. "metadata 不再被写坏"是**间接证据**（3 次重启不坏），没有做每次启动的 metadata 对比 dump。
2. logcat/dmesg 证据只覆盖最后一次启动（reboot-3）；持久性由回归日志 + `boot.reason.history` 证明。
3. "Factory data reset"没有原厂 recovery 的机器可读回执；由用户操作确认 + 间接证据（metadata 子树重建时间戳、`/data` 新格式化后 213G/用 1.8G、boot reason history 无 factory_reset/recovery 记录）共同支撑。
4. 硬件功能未实测（WiFi/相机/音频/传感器/亮度/触控/指纹/OTA）；仅确认 HAL 服务 running。
5. 本次修复集未做诊断态收尾：SELinux permissive、dm-verity off、testkey root vbmeta、logging init_boot、system_ext 去向导/自动 provision。发布前必须回退。

## 7. 产物（F0 修复集）

| 产物 | 大小 (B) | SHA-256 |
|---|---|---|
| `system_raw_nologdump.raw` | 10,235,101,184 | `b6ca50f586a80584473c97d44e75f7f3013dd50a17f6f56ef1c47c69b5c709ba` |
| `system_b_changed_blocks.bin`（9 块，36 KiB） | 36,864 | `2e563f37a786f6644fe087a8cbcabc2afbc94d7ce7798499e01be78c533bd5f3` |
| `blocks.tsv` | 375 | `f21ccc7f73019c6b48cd3aec4c61ad12060980b0f4b3744d28da7953c9c660fa` |
| `flash-system-blocks.py` | 9,990 | `b1c47db6cddf65b40b95f6628fe91094e5c9a4a45293deab3a8229bbd931fd13` |
| `edl-dump-system-blocks.py`（只读预检） | 9,169 | `756c1ea7…` |
| `vbmeta_system_f0_v11.img`（仅将来 verity-on 用） | 65,536 | `66e20599e865029665a944cb69db4b3f34910d3fe9ef087309a72f1acf7bb1eb` |

## 8. 证据索引

| 路径 | 内容 |
|---|---|
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\ROOTCAUSE-LOGDUMP-METADATA.md` | 首次根因记录：rc/脚本原文、镜像证据、失败链、修复方案 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SYSTEM-LOGDUMP-REMOVAL-REPORT.md` | 离线删除、9 块差异表、e2fsck/blockdiff、刷写脚本 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\F0-SIDE-EFFECT-AUDIT.md` | 全镜像扫描其它写者、悬空引用分析、verity 恢复配方、14 条回归风险清单 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SESSION-20261112-FBE-ROOTCAUSE-LOG.md` | 发现之前的 FBE A–F 实验归档与设备侧证据 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SESSION-ADDENDUM-20261112-F0.md` | F0 准备阶段汇总 |
| `<PROJECT_ROOT>\out\2026-11-12-edl-f0\F0-ACCEPTANCE-REPORT.md` | 真机验收：时间线、EDL 刷写集、判据表、证据边界、独立审计 |
| `<PROJECT_ROOT>\out\2026-11-12-edl-f0\device\postflash-final\` | 终态证据：getprop、mounts、dmesg、logcat-all.txt（7.8 MB）、重启回归日志、截图 |
