作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0 (original text)

# 10 — 调试与日志取证通道（Lenovo Legion Y700 五代 TB323FU）

| 项 | 值 |
|---|---|
| 文档状态 | 2026-11-12；下列通道行为已在 LineageOS 24 开机修复轮与 F0 验收轮真机实际使用 |
| 适用设备 | Lenovo Legion Y700 五代 **TB323FU**（SM8850P，canoe/kaanapali），已解锁（verified-boot state orange），当前槽位 B，B 槽逻辑分区位于 `super` |
| 范围 | 所有能读写设备或取日志的通道、各自能力与限制、启动期捕获包装器的构建/安装、日志判读方法、以及如何据此判断一次启动 |
| 相关文档 | [03 · 刷写](03-FLASH.md)（通道与刷写集）、[06 · 根因：logdump/metadata](06-ROOTCAUSE-LOGDUMP-METADATA.md)、[07 · FBE / init_user0](07-FBE-INIT-USER0.md)、[11 · 报错目录](11-ERROR-CATALOG.md)、[12 · 实验台账](12-EXPERIMENT-LOG.md) |
| 证据原则 | 通道能力结论来自真机实际命令或镜像/日志分析；未验证项明确标 **待验证（UNVERIFIED）** |

> **路径约定**：`<PROJECT_ROOT>` = 项目证据目录，`<WORKSPACE>` = 工程临时工作区，`<USER_HOME>` = Windows 用户目录，`<SN-REDACTED>` = 设备序列号，`<MAC>` = 任意 MAC 地址。厂商工具包路径统一写成 `<USER_HOME>\Downloads\...`。

---

## 1. 结论速览：通道矩阵

| 通道 | 读 | 写 | 持久性 | 主要用途 | 主要坑 |
|---|---|---|---|---|---|
| 硬件 EDL / 9008（`fh_loader`） | ✅ LUN0 + LUN4 | ✅ LUN0 + LUN4（仅新 XML 写法） | 不适用 | 全分区读写、GPT 修复、救砖、取 `misc`/`logdump`/`metadata` | 会假成功；每次写后必须回读；同一 9008 会话只用一个工具；只能冷进 |
| fastbootd（`is-userspace=yes`） | ✅ `fastboot fetch` | ✅ 物理 + 逻辑分区 | 不适用 | 快速大文件写入（`super`、`system`）、免 EDL 读分区、`set_active` | 只能从可启动系统/原厂 recovery 进入；分区名不带 `_b` 后缀 |
| Bootloader fastboot（`is-userspace=no`） | ✅ 仅 `getvar` | ❌ | 不适用 | 查槽位/变量、`reboot`/`reboot recovery` | `flash`/`set_active`/`oem edl` 全是 `unknown command` |
| 原厂 recovery（adb） | ✅ | ✅ 可 `dd` 原始分区 | 不适用 | 兜底读写、factory reset | recovery 引导会**跳过首阶段挂载**并使用 monolithic `/sepolicy`，不是正常启动的调试环境 |
| 系统 `adb` | ✅ | ⚠️ 需已授权 | 不适用 | `logcat`/`dmesg`/`getprop`/`ps`、最后手段取证 | 授权状态存在 `/data/misc/adb/adb_keys`，清 data 后主机需重新授权 |
| pstore / ramoops / last_kmsg | ❌ | — | — | — | 无 ramoops DT 节点；`dtb_size=0`；VT/FB 关闭；EFI pstore 无记录（失败非 panic 型） |
| `logfs`（ABL 日志） | ❌ | — | — | — | 本机早前已被清零，FAT 损坏，只剩陈旧会话 |
| `misc` beacon（init 包装器） | ✅ | ✅ 由包装器写 | 每次启动覆盖 | 最早期的启动阶段证据（first-stage init） | 只有很小的控制块 + 最多 508 KiB 流式缓冲 |
| `logdump` 分区（INITLOG13） | ✅ | ✅ 由包装器写 | 每次启动（可回绕） | 完整 `/dev/kmsg` 流，512 MiB | 不在任何 AVB 描述符内（可安全写）；故障后必须取回 |
| `rawdump` 分区（logcat 服务） | ✅ | ✅ 由服务写 | 每次启动 | 用户态起来后的 logcat/crash buffer | 服务起得晚（`class core`/`post-fs-data`），早期崩溃会漏 |
| `metadata` 分区当捕获目标 | ✅ | ❌ **禁止** | 每次启动 | — | F0 前的 `logdump.sh` 往它里面裸写块，毁了 f2fs 超级块，制造了 `init_user0_failed` 循环 |

---

## 2. 硬件 EDL（Qualcomm 9008）——主通道

### 2.1 进入方式

本机唯一被反复验证的物理步骤：

1. 关机（长按电源约 10–15 s）。
2. 按住 **音量+**，把 USB 线插到**长边**接口。
3. 设备管理器出现 `Qualcomm HS-USB QDLoader 9008 (COMx)`。

`adb reboot edl`（软 EDL）**不能**用于刷写：设备会枚举成一个不应答 Sahara 的 9008 端口，写入被静默丢弃。永远走冷启动序列。

### 2.2 工具链与调用

Programmer：`devprg_legion-y700-5-2.0.11.043` / `prog_firehose_ddr.elf`（厂商工具包，例如 `<USER_HOME>\Downloads\高通工具箱-2026.9.28-1\`），默认端口 `\\.\COM3`。会话由 `QSaharaServer.exe` 启动，随后用 `fh_loader.exe` 执行 XML 命令。

```powershell
# 每个 XML 只做一条 <program>/<read>；写 LUN4 必须用新写法
& $FH --port="\\.\COM3" --memoryname=ufs --search_path="<PROJECT_ROOT>\refs\readback-full" `
      --sendxml="<PROJECT_ROOT>\out\...\fh-read-misc.xml" `
      --noprompt --zlpawarehost=1 --skip_configure
```

XML 要求：`SECTOR_SIZE_IN_BYTES="4096"`、准确的 `physical_partition_number`、`start_sector`、`num_partition_sectors`，必要时 `partofsingleimage="true"`、`readbackverify="true"`。旧式裸 LBA 写 LUN4 会报 `invalid gpt entry number 128` 之后仍然打印 SUCCESS——不要信。

### 2.3 命令速查（已验证）

| 任务 | 命令 / 模板 | 备注 |
|---|---|---|
| 退出 EDL | `fh_loader ... --sendxml=fh-reset.xml`（`<power value="reset"/>`） | 每个写会话最后一步 |
| 读分区 | `fh-read-*.xml` 模板 + `--sendxml`，产出 `.bin` | 回读文件必须核 SHA-256 |
| 写分区 | 带 `<program>` 元素的 `fh-write-*.xml` | 一个 XML 只写一个分区；写后回读并算哈希 |
| 块级补丁 | `<program ... start_sector="620062" num_partition_sectors="1">` 写 4 KiB 块 | F0 的 9 块补丁（共 36 KiB）即此法 |
| GPT 修复 | 写原厂 `gpt_main4`（LBA 0，6 扇区）+ `gpt_backup4`（LBA 1,048,571，5 扇区） | 必须成对写 |
| 只清 BCB | 读-改-写 `misc` 前 2 KiB | 不要整片擦 `misc`；AOSP 只用前 2 KiB |

### 2.4 假成功纪律

EDL 的**读和写都可能报成功但什么都没做**（或返回随机数据）。强制规则：

1. 每次写后回读同一段并比对 SHA-256（小分区全片比对；大分区至少首/中/尾三块）。
2. 把 `SUCCESS`/`All Finished Successfully` 当作“XML 解析没报错”，不是“设备已写入”。
3. 同一个 9008 会话不要同时跑两个主机工具。换工具前重新进 EDL（拔插）。
4. `target not stable`、端口 10 s 才打开、programmer 上传失败，都是会话级症状：从冷 EDL 重来，不要反复重试同一个 XML。
5. 脚本异常退出时 `fh_loader.exe` 可能还占着 COM3：下一轮前先杀掉 `fh_loader`/`QSaharaServer`。

### 2.5 用 EDL 取 `misc` / `logdump` / `metadata`

```powershell
# 大小：misc = 1 MiB（LUN0 LBA 8456，256 扇区）
#       logdump = 512 MiB（LUN4 LBA 735255）
#       metadata = 64 MiB（LUN0 LBA 5251880）
# 读回后必须检查内容，不要假设文件非全零
```

大读取可能在半途失败但仍生成一个文件。信任内容之前，先看开头是否有期望标记（包装器的 `"IL13"` 控制块、logdump 的 `==== INITLOG13` 头、logcat 服务的 `AERA_...` 标记）。

---

## 3. fastbootd —— 快速、免 EDL 的通道

### 3.1 进入方式与能力

- 进入：从可启动系统 `adb reboot fastboot`，或从原厂 recovery `adb shell reboot bootloader` 再 `fastboot reboot fastboot`。
- `fastboot getvar is-userspace` = `yes` 确认处于 fastbootd。
- 写：物理分区（`boot_b`、`init_boot_b`、`vbmeta_b`、`vbmeta_system_b` 等）与逻辑分区（`system`、`system_ext`、`product`），`set_active`、`resize-logical-partition`。
- 读：platform-tools 37+ 支持 `fastboot fetch <partition> <out_file>`；这是设备能进 fastbootd 时取 `misc`、`logdump`、`metadata` 最快的方式。
- 速度参考：20 GiB `super`（实际 payload 约 13 GiB）约 20 s；2.2 GiB `vendor` 经 EDL 约 8 s；通常 USB 稳定性才是瓶颈。

### 3.2 分区命名规则（代价很高的错误）

fastbootd 的分区名**不带槽位后缀**：`fastboot flash vendor ...`、`vendor_boot ...`、`system_ext ...`、`init_boot ...`、`vbmeta_system ...`。写 `vendor_b` 会报 `unknown partition`（实测 `system_ext_b` 反而能过，但不要依赖这个例外）。

### 3.3 `fastboot -w` 不是格式化

Windows 版 platform-tools 若没有 host 端 `mke2fs`/`make_f2fs`，`fastboot -w` 只做**擦除**并打印：

```
Erase successful, but not automatically formatting.
File system type raw not supported.
```

后果：`fastboot -w` 之后下一次启动可能看到 raw/空的 `metadata`/`userdata` 而失败（`init_user0_failed`）。可靠的格式化方式是原厂 recovery 的 **Factory data reset**（会真正执行 `make_f2fs`），或显式验证过的 `fastboot format`。

### 3.4 限制

- 槽位 unbootable 时 `fastboot reboot fastboot` 失败：`Failed to boot into userspace fastboot; one or more components might be unbootable.`
- 本机 bootloader fastboot 是只读的；`set_active`/`flash`/`oem edl` 全部返回 `remote: 'unknown command'`。

---

## 4. 原厂 recovery —— 恢复模式调试与关键语义陷阱

- 原厂 recovery 暴露 adb（`adb devices` 里出现 `<SN-REDACTED> recovery`），可以用 `dd` 读写原始分区（历史上用于写 `init_boot_b`）。
- **陷阱：** bootloader 回退到 recovery 时 `IsRecoveryMode()` 为真，首阶段挂载被**整体跳过**（`First stage mount skipped (recovery mode)`），rootfs 来自 recovery ramdisk，并使用 **monolithic `/sepolicy`**。此时抓到的日志不能用于判断首阶段或用户态行为：没有 `EXT4-fs (dm-…)` 挂载行，也没有 split-policy 的 `Opening SELinux policy`，2.7 s 死亡是预期现象（recovery init 自行中止）。
- recovery 的正确用途：factory reset、`dd`、作为进入 fastbootd 的入口。不要把 recovery 引导当成“ROM 坏了”的证据。

---

## 5. 系统 `adb` —— UI 起来后能提供什么

- 授权状态存在 `/data/misc/adb/adb_keys`；本 ROM `ro.adb.secure=1`，清 data 后主机必须重新授权（`adb devices` 显示 `unauthorized`，shell 报 `device unauthorized`）。
- transport 在但 `adb shell` 报 `FAIL closed`，通常是授权/`adbd` 状态问题，不是 ROM bug；先看 `getprop init.svc.adbd` 与 `adb devices` 状态。
- 常用一次性取数：

```bash
adb shell getprop sys.boot_completed
adb shell getprop init.svc.bootanim
adb shell getprop ro.crypto.state
adb shell getprop ro.boot.verifiedbootstate
adb shell cat /proc/mounts
adb shell dmesg
adb logcat -b all -d
adb shell ps -A
```

- 本 ROM 的 `adb_root` 是被动 AIDL 服务（**不会**重启 `adbd`）；删它的 `.rc` 是安全的，但修不了授权问题。

---

## 6. 启动期捕获包装器（init_boot）——最早、最可靠的证据

### 6.1 为什么需要包装器

设备在用户态之前就死（首阶段挂载失败、早期 init fatal）时，`adb`/`logcat` 都不存在，`misc`/`logfs`/pstore 也帮不上忙。唯一够早的通道是**改造 `init_boot` ramdisk**：把原厂 `/init` 改名为 `/init.real`，加一个薄包装器作为 `/init`，fork 后在父进程 `execv("/init.real")`，子进程读 `/dev/kmsg` 并持久化。

### 6.2 硬性设计约束（踩坑换来的）

| 约束 | 原因 |
|---|---|
| `init_boot` header 里 `kernel_size = 0` | 1 字节 kernel 会让设备快到包装器根本来不及执行就反复重启 |
| 父进程必须立即 `execv("/init.real")` | 包装器不能 sleep/等块设备：UFS 模块探测约 1.16 s，只有真 init 继续跑才会出现 |
| 子进程自己打开 `/dev/kmsg`（mknod 1:11） | `/proc/kmsg` 不保证可读；`/dev/kmsg` 才是文档化接口 |
| 子进程打开目标后要立即 flush | 等日志攒满再写，panic 时什么都没落盘 |
| 目标块设备要用 GPT 定位，不能硬编码编号 | `misc` LBA 8456 只对原厂 GPT 有效 |
| 包装器不能破坏 PID 1 语义 | 父进程必须仍是 exec `/init.real` 的 init 进程 |

### 6.3 本项目用过的实现（按实用性排序）

| 包装器 | 目标 | 布局 | 适用 |
|---|---|---|---|
| `initlog9` / `logging4` | `misc` | 0x81000 起流式写 | 遗留；最早证明包装器会执行（其日志是在内核死亡点断掉的，不是设计如此） |
| `initlog10` / `logging10` | `misc` | 0x81000 起 508 KiB 流式，~1.5 s 写满 | 只够抓早期阶段，看不到用户态 |
| `initlog12` / `logging12` | `misc` | 环形缓冲 + 每 ~1 s 覆盖写 0x81000 的最新快照 | 适合长时间卡死；ring 曾有拼接 bug（必须按 `ctl.snap_len` 切分） |
| `initlog13` / `logging13` | `logdump`（512 MiB） | 连续原始 `/dev/kmsg` 字节 + 文件头 + 回绕标记；misc 控制块心跳 | **推荐**；能覆盖长启动，且不会破坏 `metadata` |

### 6.4 `misc` 控制块布局（已核对的字段偏移）

`misc` 字节偏移 `0x80000`：

| 偏移 | 类型 | 含义 |
|---|---|---|
| +0 | u32 | 启动计数 |
| +4 | char[4] | magic：`IL9\0`、`IL10`、`IL12`、`IL13` |
| +8 | u32 | stage：1 = 已打开 kmsg，2 = 已打开 logdump，5 = 正在流式写，9 = DONE（流结束且包装器主动请求重启） |
| +12 | u32 | ticks（10 ms 单位） |
| +16 | u32 | 已写入日志目标的字节数 |
| +20 | u32 | 已从 kmsg 读取的字节数（IL13）/ 总捕获量（IL12） |
| +24 | u32 | uptime 秒 |
| +28 | u32 | 回绕次数（IL13）/ 快照次数（IL12） |
| +64 | char[] | `/proc/cmdline` |

用小脚本读并做合理性检查：

```python
import struct
d = open("misc_fetched.bin", "rb").read()
o = 0x80000
print("counter", struct.unpack_from("<I", d, o+0)[0])
print("magic  ", d[o+4:o+8])
print("stage  ", struct.unpack_from("<I", d, o+8)[0])
print("ticks  ", struct.unpack_from("<I", d, o+12)[0])
print("written", struct.unpack_from("<I", d, o+16)[0])
print("uptime ", struct.unpack_from("<I", d, o+24)[0])
print("cmdline", d[o+64:o+64+256].split(b"\x00")[0])
```

判读规则：`stage=5` 且 `ticks` 很小，或日志停在 UFS `sd 0:0:0:5` 行之后，说明内核死在 first-stage 挂载阶段；`stage=9` 且日志尾部有 `DONE-EDL`，说明包装器正常走完捕获窗口并主动请求重启（不是启动失败）。

### 6.5 `logdump` 分区（INITLOG13）格式

- 512 MiB，LUN4 LBA 735255；**不被任何 vbmeta 描述符引用**，写它不会破坏 AVB。
- 分区开头是 `==== INITLOG13 boot=<N> uptime=<S> ====\n`，之后是原始 kmsg 字节（每条为 `pri,seq,ts;消息`，长消息有续行）。
- 写满后回绕到偏移 0 并写 `==== LOGWRAP ====`，回绕计数 +1。解析时从**最后一个** `==== INITLOG13` 头开始，取最近一次启动段。
- `printk` 限流仍可能在**产生端**丢行；`printk.devkmsg=on` 有帮助但不会关闭 ratelimit。要拿全首阶段日志，可考虑在 `/proc` 挂载后写 `printk_ratelimit=0` / `printk_ratelimit_burst=9999`（下一轮项，尚未进入默认包装器）。

---

## 7. 用户态捕获：logcat 落 `rawdump`

### 7.1 已验证可用的设计

一个 `system_ext` init 服务（`class core`/`post-fs-data`）：

1. 等 `logd.ready=true`（有上限重试）；
2. 先写头（`==== AERA_LOGCAT2_BEGIN uptime=… ====`）、`getprop`、`dmesg`；
3. 把 `logcat -b all -v threadtime` 持续写入 `/dev/block/by-name/rawdump`（或经 sysfs 找到的 `rawdump` 块设备）。

`rawdump` 为 512 MiB，不被 AVB 覆盖，可安全写。厂商内核 ramdump 路径也使用 `rawdump`，极端内核 panic 会覆盖日志——对 system_server 崩溃场景可接受。

### 7.2 两个“静默产出空捕获”的 bug（不要重犯）

| 现象 | 原因 | 修法 |
|---|---|---|
| `logdump` 里只有 `AERA_LOGCAT_BEGIN` 头、没有 logcat 行 | `logcat -v pid` 不是合法格式（报 `logcat: Invalid -v 'pid'`，进程退出） | 用 `-v threadtime`（可再带 `,usec`） |
| `logdump` 里有头/getprop/dmesg，但 logcat 段为空 | `exec logcat -G 16M ...`——`-G` 只设置 buffer 大小，随后**立即返回 EXIT_SUCCESS**（`system/logging/logcat/logcat.cpp:1165`），根本不会进入读日志循环 | 拆成两步：`logcat -b all -G 16M >/dev/null 2>&1`，再 `exec logcat -b all -v threadtime` |

### 7.3 捕获健康度判据

| 特征 | 判定 |
|---|---|
| 出现 `==== INITLOG13` 头 | kmsg 捕获有效 |
| 出现 `AERA_LOGCAT2_BEGIN` / `AERA_DIAG_BEGIN` 头但后面没内容 | `CAPTURE-FAILED` |
| 目标分区是 64 MiB 全零 / 全 0 | `CAPTURE-NOT-RUN`（服务从未执行） |
| `logcat: Invalid -v '...'` | `CAPTURE-FAILED` |
| 日志在到达用户态前突然结束 | 捕获被截断——**不要**据此判“F0 无效”；F0 状态记为 unknown |
| `metadata` dump 里出现 `==== LOGDUMP3` / `AERA_DMESG` | `PRE-F0-DIAG`：旧 `logdump.sh` 曾活跃（这是 F0 前行为，不是本次启动的阶段日志） |

> **规则：** F0 前的 `logdump.sh` 用裸 `dd` 往 `metadata` 分区写快照，毁掉 f2fs 超级块，导致重启 → `init_user0_failed` → 要求清数据的循环。F0 已把它从发布的 `system` 删除。**永远不要**用 `metadata` 做诊断写入；用 `logdump`（kmsg）与 `rawdump`（logcat）。

---

## 8. 读取与判读捕获

### 8.1 阶段判据（不依赖任何工具）

| 阶段 | 正向证据 | 反向证据 |
|---|---|---|
| S0 first-stage | `init first stage started!`、`EXT4-fs (dm-…)` ×7+、`Opening SELinux policy` / `Compiling SELinux policy` | `Failed to mount required partitions`、`[libfs_avb] Device path not found: /dev/block/by-name/…`、`ELOOP`、`fs_mgr_create_canonical_mount_point` |
| S1a metadata | `F2FS-fs (sda10): Mounted with checkpoint version = …` | `vold: Failed to create /metadata/vold: Read-only file system`、没有 `sda10` 行 |
| S1b init_user0 | 无失败行，继续走到 zygote | `vdc: Command: cryptfs init_user0 Failed: Status(-8, EX_SERVICE_SPECIFIC)`、`vdc call failed with error code: 25`、`Failed to mkdir(/data/misc/vold/user_keys)`、`Reason: init_user0_failed` |
| S2 system_server | 每 ~5 s 一次的 `starting service 'zygote'`、logcat 的 `Exit zygote because system server (pid …) has terminated`、logcat crash buffer 的 `*** FATAL EXCEPTION IN SYSTEM PROCESS` | 只启动一次 zygote 后静默（捕获被截断） |
| S3 成功 | `sys.boot_completed=1`、`init.svc.bootanim=stopped`、logcat `Boot completed` | — |
| F0 生效 | 发布的 `system` 里没有 `logdump.sh`/`logdump.rc`；本次 kmsg 无 `starting service 'exec … logdump.sh`、无 `avc: denied { execute_no_trans } … path="/system/bin/logdump.sh"`；`F2FS-fs (sda10)` 存在 | 出现任何 `logdump.sh` exec/avc 行 → **F0 未生效** |

设备块映射（原厂 GPT）：`sda10 = metadata`、`sda14 = userdata`。GPT 一变就要从 GPT dump 重新推导。

### 8.2 grep 一行命令

```bash
# 首阶段
grep -aE "init first stage started|Failed to mount required partitions|libfs_avb|ELOOP|EXT4-fs|Opening SELinux policy" logdump.bin

# metadata / FBE 链
grep -aE "F2FS-fs \(sda10\)|Failed to create /metadata/vold|read_key failed|encryptFstab|make_f2fs" logdump.bin

# init_user0 链
grep -aE "init_user0|user_keys|mount_all /vendor/etc/fstab.qcom|queue_fs_event|vdc call failed" logdump.bin

# zygote / system_server（kmsg 侧）
grep -aE "starting service 'zygote'|received SIGKILL|Sending SIGKILL|updatable_crashing" logdump.bin

# logcat 侧（rawdump 或 live adb）
grep -aE "Exit zygote because system server|FATAL EXCEPTION IN SYSTEM PROCESS|WATCHDOG KILLING|AndroidRuntime" rawdump.bin

# 捕获健康度
grep -aE "INITLOG13|AERA_LOGCAT|Invalid -v|LOGWRAP" logdump.bin
```

### 8.3 `boot-doctor` 自动化

`boot-doctor.py`（reviewed 版）把上述判据转成裁决。用法：

```bash
python3 boot-doctor-reviewed.py <dump.bin> --tag <label> --out <outdir>
# 目录模式：每个文件单独裁决，绝不混用不同启动的证据
python3 boot-doctor-reviewed.py <evidence_dir> --out <outdir>
```

裁决：`S0-first-stage`、`S1-metadata-missing`、`S1-init_user0-failed`、`S2-system_server`、`S3-success`、`S3-indirect (device alive N s, capture truncated)`、`CAPTURE-FAILED`、`CAPTURE-NOT-RUN`、`PRE-F0-DIAG`、`STALE-PREV-BOOT`、`F0-likely-effective`、`F0-NOT-EFFECTIVE`、`F0-unknown`。

reviewed 版内置规则：

- 先按**文件名**分类，再看 magic，最后才用大小兜底（64 MiB 的 logdump 不能被当成 `metadata`）；
- `metadata` 快照文本不参与启动阶段裁决，只用于 `PRE-F0-DIAG`；
- `sys.boot_completed` 必须匹配严格正则 `sys\.boot_completed[=:\s]+1`（文本里任意 `=1` 都是假阳性）；
- 捕获被截断时，用 `misc` 控制块的 uptime 做 `S3-indirect`；
- 分析前先按 `ctl.snap_len` 切分 `misc` 的流式区域（一份 7 s 失败件的文件里还混着上一次启动的 init_user0 失败链，混读会得出错误时间线）。

### 8.4 失败捕获 SOP

1. 用诊断集复现（推荐 `vendor_boot_diag2` + `init_boot_logging13` + 配对 `vbmeta_system`），绝不让 `metadata` 当捕获目标。
2. 等设备要么启动、要么回退（recovery / fastboot），记录模式和等待时间。
3. 能进 fastbootd 就 `fastboot fetch misc logdump metadata`；否则冷进 EDL 读同样三个分区。
4. 先检查捕获健康度（文件头/全零），再分析。
5. 用 `boot-doctor` 或上面的 grep 得到裁决；记录裁决、证据行、以及本次启动的精确镜像/分区清单（必须记录 `vendor_boot` 的 SHA-256——光看 cmdline 区分不了诊断变体）。
6. 改一个变量再重复。

---

## 9. 已知坑（速查）

1. 不要信 EDL 的 SUCCESS；必须回读并算哈希。
2. 不要用软 EDL；只能冷进 9008。
3. 一个 9008 会话只用一个工具；重试前杀掉残留 `fh_loader`。
4. `misc` 日志必须先按 `snap_len` 切分再分析。
5. `metadata` 不是捕获目标（F0 教训）——用 `logdump`/`rawdump`。
6. `logcat -G` 单独用会立即退出；`logcat -v pid` 非法——两者都会静默产生空捕获。
7. fastbootd 分区名不带 `_b` 后缀。
8. `fastboot -w` 只擦除；格式化要用 recovery factory reset。
9. recovery 引导没有首阶段挂载——不要当正常启动分析。
10. 换 `vendor_boot` 变体不记录 SHA，结果不可复现（`printk.devkmsg=on` 等从系统里看不出来）。
11. 记录 `misc`/`logdump` 的取回大小与首字节；截断的取回看起来像“短捕获”。
12. `sda10`/`sda14` 这类块号依赖 GPT；GPT 变过后要重新推导。
13. 包装器只能看到内核 `printk`；Java/crash 日志必须靠 logcat（`rawdump`）。

---

## 10. 待验证项

1. `fastboot fetch` 在本机 fastbootd 上原则可用（platform-tools 37+），但 512 MiB `logdump` 的端到端 fetch 在已记录轮次中未跑完。
2. 包装器加 `printk_ratelimit=0` + `printk_ratelimit_burst=9999`（阻止产生端丢行）只是提议，**尚未构建/验证**。
3. `rawdump` logcat 服务在结构上已验证（脚本/init/sha），但真实 system_server 崩溃循环下的设备端输出未记录。
4. 某些 `init_boot` 变体为什么比其他快，其内存/设备树原因未刻画。
5. 某次失败中 ABL 回退 recovery 的具体触发（BCB、重试逻辑还是按键/音序）未完全闭环（记录到的一次里 `misc` BCB 为空却仍然回退）。

---

## 11. 参考材料（相对 `<PROJECT_ROOT>`）

- `out/2026-11-11-los24-bootfix/BOOT-DOCTOR-REVIEW.md` —— 完整阶段判据表、`boot-doctor` 规则映射、裁决矩阵、reviewed 工具用法。
- `out/2026-11-11-los24-bootfix/REBUILD-ZYGOTE-TIMELINE.md` —— kmsg 判据表、`snap_len` 切分规则、`libfs_avb` 证据。
- `out/2026-11-11-los24-bootfix/ADB-ROOT-ANALYSIS.md` —— adb 授权分析、recovery 模式/SELinux 证据、logcat 服务可行性。
- `out/2026-11-11-los24-bootfix/INITLOG12-BUILD-REPORT.md`、`INITLOG13-BUILD-REPORT.md` —— 包装器设计、`misc` 控制布局、`logdump` 格式。
- `out/2026-11-11-los24-bootfix/SYSTEMEXT-LOGCAT2-REPORT.md`、`SYSTEMEXT-LOGCAT3-REPORT.md` —— logcat 落 rawdump 服务及其两个 bug。
- `out/2026-11-11-los24-bootfix/SYSTEM_SERVER_CRASH-HYPOTHESES.md` §5 —— metadata 写入失败链与捕获方案。
- `out/2026-11-11-los24-bootfix/SESSION-20261112-FBE-ROOTCAUSE-LOG.md` §5 —— 捕获工具清单与 `fastboot fetch` 的发现。
- `out/2026-11-10-los24-logdump/RECOVERY-PLAYBOOK.md`、`LOS24-PLAYBOOK-CONSOLIDATED.md` §3.6/§3.7 —— 通道能力矩阵与 pstore/logfs 失败史。
- `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` §3/§7 —— F0 验收证据（boot_completed、metadata/data 挂载、3 次重启回归）。
