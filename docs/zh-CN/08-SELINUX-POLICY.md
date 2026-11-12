作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0

# 08 — SELinux：预编译策略校验不匹配与 4 KiB policy 扇区补丁

| 项 | 值 |
|---|---|
| 状态 | 2026-11-12 — 已解决。验收集已不依赖 4 KiB 扇区补丁（该补丁当前是惰性的）；是否回退该块仍是一个待定决策（见 §7）。 |
| 适用设备 | Lenovo Legion Y700 五代 **TB323FU**，SN `<SN-REDACTED>`，SM8850P（canoe / kaanapali），A/B，4 KiB 页，unlocked（`vbs=orange`），B 槽 active |
| 适用对象 | LineageOS 24.0（Android 17）移植的 `system_b`（LOS 平台策略）与原厂 `vendor_b`/`odm_b`（原厂 vendor/ODM 策略）混装于 `super` 的场景；`system_b` 内 `/system/etc/selinux/plat_sepolicy_and_mapping.sha256` |
| 证据来源 | `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SELINUX-COMPILE-ANALYSIS.md`、`…\F0-SIDE-EFFECT-AUDIT.md`、`…\BOOTFIX-FACTS.md`、`…\SYSTEM-LOGDUMP-REMOVAL-REPORT.md`；`<PROJECT_ROOT>\out\2026-11-10-los24-logdump\LOS-SYSTEM-ANALYSIS.md`；`<PROJECT_ROOT>\out\2026-11-12-edl-f0\F0-ACCEPTANCE-REPORT.md` |

---

## 1. 它出现在启动流程的哪一步

首阶段通过之后（doc 05），内核日志进入第二屏：

```
init: Opening SELinux policy
init: Compiling SELinux policy
```

（`device/kmsg_20261111_223511.txt:2193` / `:2195`；`…230836.txt:2175/2177`）。"Compiling" 表示 init 决定**不用**预编译策略，正在设备上现场运行 `secilc`。若 CIL 输入之间不一致，这次编译会在运行时失败，启动在 `Using genfs …` 之后几毫秒内死亡——错误文本被 panic/限流吞掉，于是表现为"SELinux 步骤开始约 20 ms 后静默重启"。

## 2. init 如何选择预编译还是现场编译

`system/core/init/selinux.cpp`（LOS 24 树）：

- `FindPrecompiledSplitPolicy()` `:133-185` —— 只有在**三组 sha256 全部相等**时才使用预编译策略（`/odm/etc/selinux/precompiled_sepolicy`，或 `/vendor` 下的）：
  - `/system/etc/selinux/plat_sepolicy_and_mapping.sha256` ↔ `precompiled_sepolicy.plat_sepolicy_and_mapping.sha256`
  - `/system_ext/etc/selinux/system_ext_sepolicy_and_mapping.sha256` ↔ `…system_ext…`
  - `/product/etc/selinux/product_sepolicy_and_mapping.sha256` ↔ `…product…`
  - 每个文件只比较**第一行**字符串，无签名、无内容校验。
- `GetVendorMappingVersion()` `:187-197` —— mapping 版本取自 `/vendor/etc/selinux/plat_sepolicy_vers.txt`（本机 `202504`）。
- `GetUserdebugPlatformPolicyFile()` `:205-222` —— 只有 `INIT_FORCE_DEBUGGABLE` 且解锁时才用 debug 策略；本机**无 `/force_debuggable`、无 `/userdebug_plat_sepolicy.cil`**（debugfs 已确认），走正常平台策略。
- genfs 选择 `:333-347` —— `get_genfs_labels_version()`；vendor `genfs_labels_version.txt = 202504`，因此取 `/system/etc/selinux/plat_sepolicy_genfs_202504.cil`（设备日志吻合）。
- `compile_args` 顺序 `:349-392`（与设备实际调用一致）：
  ```
  /system/bin/secilc
    <plat_policy.cil>            # /system/etc/selinux/plat_sepolicy.cil
    -m -M true -G -N -v -c <SEPOLICY_VERSION>
    <plat_mapping.cil>           # /system/etc/selinux/mapping/202504.cil
    -o <compiled_sepolicy>       # /dev/sepolicy.XXXXXX
    -f <filecontext 输出>        # /sys/fs/selinux/null
    [<plat_compat.cil>]          # /system/etc/selinux/mapping/202504.compat.cil
    [<system_ext_policy.cil>]    # /system_ext/etc/selinux/system_ext_sepolicy.cil
    [<system_ext_mapping.cil>]   # /system_ext/etc/selinux/mapping/202504.cil
    [<system_ext_compat.cil>]    # /system_ext/etc/selinux/mapping/202504.compat.cil
    [<product_policy.cil>]       # /product/etc/selinux/product_sepolicy.cil
    [<product_mapping.cil>]      # /product/etc/selinux/mapping/202504.cil
    [<plat_pub_versioned.cil>]   # /vendor/etc/selinux/plat_pub_versioned.cil
    [<vendor_policy.cil>]        # /vendor/etc/selinux/vendor_sepolicy.cil
    [<odm_policy.cil>]           # /odm/etc/selinux/odm_sepolicy.cil
    [<genfs_cil>]                # /system/etc/selinux/plat_sepolicy_genfs_202504.cil
  ```

`-c` 来自 init 编译期宏：AOSP `system/core/init/Android.bp` 设 `-DSEPOLICY_VERSION=30`；原厂 `/odm/etc/selinux/precompiled_sepolicy` 二进制头的 policyvers 字段也是 `0x1e`（=30）。离线用 `-c 30/31/32/33` 测试结果相同（§5），该值不构成风险。

## 3. 设备上的不匹配

- 原厂 `/odm/etc/selinux/precompiled_sepolicy` 是按**原厂平台策略**编译的，其记录的三个 hash 为：plat `2fc99e11d7b3fb553103a4b77e3df001d0b64dc3cd741fab3c7b3c8a40582f2e`、system_ext `50cb98e2…`、product `4ae60473…`。
- LOS `system` 镜像带着不同的平台策略，其 `plat_sepolicy_and_mapping.sha256` 第一行是 `bb683371…`。plat 这一对**不匹配**，`FindPrecompiledSplitPolicy()` 返回空，init 退化为在设备上现场编译 `secilc`。
- 当 **product/system_ext 仍是原厂**（它们的 hash 文件恰好匹配预编译值）时，现场编译**失败**：原厂 OEM 的 `system_ext_sepolicy.cil` / `product_sepolicy.cil` 引用了只存在于原厂平台策略里的 type。用真实镜像输入离线复现（`_tmp/selinux`，LOS 24 树产出的 host `secilc`）：

```
$ secilc <LOS plat> -m -M true -G -N -v -c 30 <LOS mapping/202504.cil> \
    -o actual.policy -f <fc> <LOS mapping/202504.compat.cil> \
    <stock system_ext/system_ext_sepolicy.cil> <stock se mapping/202504.cil> <stock se mapping/202504.compat.cil> \
    <stock product/product_sepolicy.cil> <stock product mapping/202504.cil> \
    <stock vendor/plat_pub_versioned.cil> <stock vendor/vendor_sepolicy.cil> <stock odm/odm_sepolicy.cil> \
    <LOS plat_sepolicy_genfs_202504.cil>
rc=254
Failed to resolve typeattributeset statement at .../stock_system_ext/etc/selinux/system_ext_sepolicy.cil:2
Failed to resolve AST
Failed to compile cildb: -2
```

- 根因：原厂 OEM 策略引用了 OEM 平台独有的 type（例如 `mediaserverwrapper`；原厂 plat 声明 1 处、LOS plat 0 处，vendor/odm 都没有）。`(typeattributeset domain (... mediaserverwrapper ...))` 无法 resolve，`secilc` 立即失败——与设备上"genfs 行之后约 20 ms 死亡"的现象完全吻合。往 LOS plat 追加 stub `(type mediaserverwrapper)` 后，错误只是移到 `system_ext_sepolicy.cil:3`（下一个 OEM 独有 type）⇒ **不是单符号问题，补 stub 不可行**。

## 4. 4 KiB policy 扇区补丁（22:39 使用的 workaround）

思路：在原厂 `product`/`system_ext`（其 hash 文件已匹配预编译值）仍安装的情况下，把 LOS 的 plat hash 行改成原厂值，让 `FindPrecompiledSplitPolicy()` 认为预编译策略匹配，从而加载 `/odm` 的预编译策略、**跳过会失败的现场 `secilc`**。

### 4.1 目标

- `system_b` 的 ext4 **块 81,367**——文件偏移 333,279,232（= 81,367 × 4,096）；绝对 4 KiB LBA **701,429**（= `system_b` 起始 620,062 + 81,367）。
- 该块属于 inode 1043 = `/system/etc/selinux/plat_sepolicy_and_mapping.sha256`（65 B 文本；原内容为 LOS plat 策略 sha）。
- 补丁文件：`selinux_hash_sector.bin`，**4,096 B**，sha256 `d05ef83d3abc4e01ae19aefb446a5412653e9c29c63fdcb8d68b5abc5015f615`。
- 写入后文件内容（第一行）：`2fc99e11d7b3fb553103a4b77e3df001d0b64dc3cd741fab3c7b3c8a40582f2e`（原厂预编译 plat hash）；写后 `debugfs cat` 实测一致。

### 4.2 写入与效果

- 22:39 的刷写步骤中经 EDL 写入 LBA 701,429（与 `vendor_boot_diag2.img` 同一批）；记录见刷写事实表（`BOOTFIX-FACTS.md`）。这一写使 `system_b` 内容恰好变了一个 4 KiB 扇区，因此 `system_b` 不再等同 `super_v7.img` 的替换件整体（打过该扇区后，整件 `super` sha `5779a9a5…` 不再适用）。
- 写入并 `power reset` 后，**22:40** adb 首次枚举到 LineageOS 用户态（`watch-boot.log:131`，watch 起 18.4 s）。上一次启动（22:35）的日志停在 `Compiling SELinux policy`，即编译步骤是最后观测到的活动；打补丁后启动越过了它。
- **22:48–22:50**，在刷入 LOS `product_b`/`system_ext_b`（22:45/22:46）并 `fastboot -w` 之后，用户目视进入 LineageOS 欢迎界面。
- **注意**：22:39 那一步改的不止一个变量（`vendor_boot_diag2` + policy 扇区 + 后续 product/system_ext 替换）。补丁的因果作用（跳过失败的编译）由离线编译数据与 22:35/22:40 两次启动日志支撑，但**未作为单变量真机测试隔离验证**。

## 5. 正确解法：刷入 LOS `product`/`system_ext`

用 LOS 三件套（`system`=修好的 LOS，`product`/`system_ext`=LOS raw，`vendor`/`odm`=原厂）离线复刻编译成功：

| `policyvers` (-c) | rc | 输出 |
|---|---|---|
| 30（AOSP 实际值） | **0** | 1,485,976 B，sha256 `3b337c371881a106bf19f2fe718d06a48c5cb13c8915f37f3bca921a243a27d7` |
| 31 | **0** | 1,485,984 B |
| 32 | **0** | 1,485,984 B |
| 33 | **0** | 1,489,704 B |

无 stdout/stderr 错误；host 编译耗时 0.62 s（x86），设备 ARM 预计 ~2–5 s。因为 LOS 的 `product`/`system_ext` 策略文件与 LOS 平台策略自洽，现场编译会成功，不需要绕开编译。

真机上于 **22:45/22:46** 执行：刷 `product_b`（sha `8624234c…`）与 `system_ext_b`（sha `68b48149…`）+ `fastboot -w`；22:48 用户目视进入欢迎界面。同一改动同时消除了 `com.motorola.android.providers.settings` 签名冲突（该原厂 Moto 应用来自原厂 `system_ext`）。

相关输入 hash（来自实际镜像）：
- LOS `product/etc/selinux/product_sepolicy.cil`：空策略，sha256 `01ba4719…daca546b`（1 B，正常）；`product_sepolicy_and_mapping.sha256` = `75a11da4…`。
- LOS `system_ext/etc/selinux/system_ext_sepolicy.cil`：sha256 `ef46d746…`；`system_ext_sepolicy_and_mapping.sha256` = `71cdbbf6…`。
- 原厂 `vendor_sepolicy.cil` = `1862deda…`、`plat_pub_versioned.cil` = `e0996b2d…`（均来自原厂 `vendor_b`）；原厂 `odm_sepolicy.cil` 为空（1 B）。

**重要推论：** 换成 LOS `product`/`system_ext` 后，它们的 hash 文件（`75a11da4…` / `71cdbbf6…`）不再匹配原厂预编译值（`4ae60473…` / `50cb98e2…`），`FindPrecompiledSplitPolicy()` 再次失败，init 回到现场编译路径——4 KiB policy 扇区补丁**变为惰性**（它只改了 plat 这一对，在另外两对不匹配时没有意义）。

## 6. 为什么不强行走预编译策略

强行走预编译需要把三个 hash 文件都改回原厂值（plat 已由扇区补丁完成；product/system_ext 还需改写）。评估过的风险：

1. init 只做字符串比较、无签名校验——技术上可行。
2. 原厂 `precompiled_sepolicy` 二进制是按**原厂平台策略**编译的，而 LOS system 的用户态配置是 LOS 的：`plat_file_contexts`、`plat_property_contexts`、`plat_service_contexts`、各 `.rc` 里的 `seclabel`、以及 system 分区文件的 xattr 都会引用 **LOS plat 独有 type**（离线实测：LOS plat 有而原厂 plat 没有的 type/attr = 46 个）。加载原厂策略后这些标签/域无法解析 → `avc denied` / invalid context 风暴，`system_server`/各服务大概率起不来。
3. 这同时是对 AOSP 一致性元数据的伪造（hash 文件是"预编译策略与当前 system/system_ext/product 匹配"的契约），不受支持，后续升级/回滚易复发。
4. 三个 hash 文件都在受 verity 保护的分区里，改它们同样要重建 `super` + 重签 `vbmeta_system`——**改动成本并不比"直接刷 LOS `product`/`system_ext`"小**，而后者已验证 rc=0。
5. 仅作为 fallback（未使用）：离线编译策略并注入 `/odm/etc/selinux/precompiled_sepolicy`（odm 是 `super` 内逻辑分区），同时改写三个 hash 文件；还需重建 `vbmeta_b` 的 odm hashtree descriptor 并重签。该路线保证策略与 LOS 三件套一致（等价于现场编译），但改动面大得多。

## 7. 验收集（F0）中的现状

- F0 的 `system` 镜像仍含 4 KiB policy 块（块 81,367 → LBA 701,429）：相对被修镜像的 9 块差异中包含它（`bb683371…` → `2fc99e11…`）。
- 它**是惰性的**：F0 集使用 LOS `product`/`system_ext`（`system_ext_f0diag`、`product_b`），三处预编译校验全不匹配，init 启动时现场编译。间接证据：设备正常启动、SELinux 处于 permissive、没有策略相关失败。
- **待定决策**（已记录、尚未执行）：(a) 把该块回退为 LOS 原值（F0 差异变为 8 块，补丁无法被静默激活）；或 (b) 保留该块，并在刷写清单中写明约束："除有意使用原厂 `/odm` 预编译策略外，禁止与 stock `product`/`system_ext` 同刷"。为得到干净的可发布镜像，推荐 (a)。
- 恢复 verity-on 的配方（与本篇独立）：重算 system hashtree → 新 root digest `9103aeb99e58b9356d7f6d1b7a629a148798926a7206ab9cc4dd978beedd5887`、新 raw sha `29ad60fb…`、`vbmeta_system_f0_v11.img`（`66e20599…`，staged verify PASS），并换用带 avb 的 `vendor_boot`。**严禁**用当前 `system` + `vbmeta_system_v10`（其 system digest 是旧值 `2a3c7c06…`）直接切 verity-on——dm-verity 会 EIO。

## 8. 未验证 / 局限

1. 设备端 ARM `secilc` 的实际执行从未被捕获：分析只静态确认 `/system/bin/secilc` 存在且可执行（aarch64 ELF，mode 0700，sha256 `11f25d00…`），并在 host 复刻了编译；设备端 exec/内存/路径失败没有观测到。
2. LOS 三件套下运行期 SELinux denial 的数量没有量化；bring-up 以 `androidboot.selinux=permissive` 运行（观测到 `avc denied … permissive=1`，例如 F0 最后一次启动有 3,541 条），denial 不阻断启动，仅作诊断用。转 enforcing 需要单独做一轮策略工作。
3. 是否回退 4 KiB policy 块（§7）仍未定（**待验证/待决策**）。
4. `llndk.libraries.txt` 从未逐行 diff（只核对了 size 相同），`/mnt/vendor` 下的二级挂载点也未逐项核对；两者都与 SELinux 编译路径无关。

## 9. 证据索引

| 路径 | 内容 |
|---|---|
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SELINUX-COMPILE-ANALYSIS.md` | init 编译路径（带行号）、真实输入 hash、rc=254 失败原文、LOS 三件套 rc=0 矩阵、伪造预编译 hash 的评估、fallback 方案 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SYSTEM-LOGDUMP-REMOVAL-REPORT.md` §3 | policy 块精确定位（81,367 / LBA 701,429 / 偏移 333,279,232 / inode 1043）、补丁文件 SHA、写后 `debugfs cat` 断言 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\BOOTFIX-FACTS.md` | 22:39 policy 扇区写入记录、刷写事实表、已验证可开机组合 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\F0-SIDE-EFFECT-AUDIT.md` §4#5、§5 | policy 补丁惰性分析、回退建议、verity 恢复配方 |
| `<PROJECT_ROOT>\out\2026-11-10-los24-logdump\LOS-SYSTEM-ANALYSIS.md` §2-① | 原厂 `/odm` 预编译策略 hash 与强制现场编译的不匹配 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\device\kmsg_20261111_223511.txt` | 第二屏 `Opening SELinux policy` / `Compiling SELinux policy`（`:2193/:2195`） |
