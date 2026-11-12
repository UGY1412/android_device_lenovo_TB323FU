作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0

# 05 — 根因：`/vendor` 自指符号链接环导致首阶段挂载失败（ELOOP → `LOG(FATAL)`）

| 项 | 值 |
|---|---|
| 状态 | 2026-11-12 — 根因于 2026-11-11 定案；修复后的 `system` 镜像此后一直在刷写集中（含 F0 修复集，见 §8） |
| 适用设备 | Lenovo Legion Y700 五代 **TB323FU**，SN `<SN-REDACTED>`，SoC SM8850P（canoe / kaanapali），A/B + 独立 recovery，virtual A/B，4 KiB 页，super 20 GiB，bootloader unlocked（`vbs=orange`），B 槽 active |
| 适用对象 | LineageOS 24.0（Android 17）移植；`super` 内 `system_b` 的 ext4 镜像（逻辑分区大小 10,235,101,184 B） |
| 证据来源 | `<PROJECT_ROOT>\out\2026-11-10-los24-logdump\LOS-SYSTEM-ANALYSIS.md`（根因分析）；`<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\IMAGE-FIX-REPORT.md`（离线打补丁产出）；`<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\VERIFY-REPORT.md`（独立复核）；`<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\BOOTFIX-FACTS.md`（事实表） |

---

## 1. 现象

- 设备停在第一屏不再变化：表现为重启循环或硬死机。**USB 全程不枚举**（无 adb、无 MTP），拿不到用户态日志。
- 首阶段内核日志（initlog 包装器从 `misc` 抓取，`<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\device\kmsg_full.txt`）在 **~0.48–0.50 s** 处硬切断：
  - t≈264 ms `Run /init as init process`
  - t≈265 ms `init: init first stage started!`
  - 加载 `/lib/modules/*.ko`，随后 t≈480–500 ms UFS LUN0–LUN5 枚举（`sd 0:0:0:0..5`）
  - 最后一条 `sd 0:0:0:5 Optimal transfer size` → **日志终止，FATAL 文本没来得及落盘**
- 第二屏从未执行：没有 `exec /system/bin/init selinux_setup`，没有 `Opening SELinux policy`，没有开机动画推进。
- 因此，此前把问题归因于更后阶段（dm-verity digest、SELinux 策略编译、VINTF 矩阵、`/data` 加密/格式化）的实验，实际都没有执行到那些代码路径，不可能是当时的阻断点。

## 2. 结构性根因（字节级）

LineageOS 构建出的 `system.img` 根目录里，本该是挂载点目录的位置变成了**自指符号链接环**：

| 路径 | 原厂 A17 `system_b`（原厂 super 区段） | LOS `raw_system_v3.raw`（= `out/system.img`，footer root digest `37cc913b…`） |
|---|---|---|
| `/vendor` | **directory**，inode 4466，mode 0755（预置挂载点） | **symlink**，inode 2898，size 14，fast link 目标 `"/system/vendor"` |
| `/system/vendor` | symlink → `"/vendor"` | symlink → `"/vendor"`（inode 2892，size 7） |
| `/dataext` | directory（挂载点） | **缺失**（`File not found by ext2_lookup`） |
| `/mnt`、`/metadata`、`/product`、`/system_ext`、`/odm`、`/vendor_dlkm`、`/system_dlkm` | 均为目录 | 均为目录（一致） |
| `/system` | 真目录 | 真目录 |

`/vendor → /system/vendor → /vendor` 构成两跳环，因此任何对 `/vendor` 的路径解析都返回 `ELOOP`：

```
/vendor          Inode 2898  Type: symlink  Size 14  Fast link dest: "/system/vendor"
/system/vendor   Inode 2892  Type: symlink  Size 7   Fast link dest: "/vendor"
```

为什么这是致命而非装饰性问题：`system` 分区以**只读**方式挂载（`ro,barrier=1,discard`），运行时无法创建挂载点；因此 AOSP 要求 `system` 根目录必须自带真实目录作为挂载点。原厂镜像正是这样做的，LOS 构建没有。

## 3. 源码级失败路径（文件:行号）

1. 首阶段 fstab 来自**原厂 `vendor_boot` ramdisk**（`first_stage_ramdisk/fstab.qcom`，7,374 B；设备回读 `vendor_boot_b` sha256 `9349137dc262ab61508014275b623f4d39e5b14bc55c77082848d63a28f381b2` = 原厂参考镜像）。`vendor` 行在首阶段集合内，且**没有** `no_fail` / `formattable`：
   ```
   vendor  /vendor  ext4  ro,barrier=1,discard  wait,slotselect,avb=vbmeta,logical,first_stage_mount
   ```
2. `system/core/init/first_stage_mount_android.cpp:48-62` — `FirstStageMount::Create()` 读默认 fstab 并用 `std::erase_if(fstab, !first_stage_mount)` 过滤；`/vendor` 保留在首阶段列表。
3. `system/core/init/first_stage_mount.cpp:283-308` — `TrySwitchSystemAsRoot()`：先挂 `/system`，再 `SwitchRoot("/system")`。
4. `system/core/init/first_stage_mount.cpp:343-394` — 其余分区按 fstab 顺序挂载（`/system_ext`、`/product`、`/vendor`…）；`first_stage_mount.cpp:186-195` 先调用 `fs_mgr_create_canonical_mount_point(mount_point)`，失败即 return false。
5. `system/fs/fs_mgr/fs_mgr.cpp:2363-2381` — `fs_mgr_create_canonical_mount_point()`：
   - `mkdir("/vendor")` 因已存在（symlink）失败 `EEXIST` → `created_mount_point=false`；
   - `Realpath("/vendor")` 因环失败 **ELOOP** → `ok=false` → 返回 `false`。
6. `first_stage_mount.cpp:376-387` — 挂载失败只有在表项带 `no_fail` 或 `formattable` 时才被忽略；`/vendor` 两者都没有 → `PLOG(ERROR) << "Failed to mount …"` 并 `return false`。
7. `system/core/init/first_stage_init.cpp:551-553` — `DoFirstStageMount()` 返回 false 即 `LOG(FATAL) << "Failed to mount required partitions early …"`。init 是 PID 1 → abort → 内核 panic / 挂死 / 重启循环（取决于 kernel–init 组合）。
8. 该路径上**没有任何容错分支**：`SkipMountingPartitions()` 只在 `/system/system_ext/etc/init/config/skip_mount.cfg` 存在时生效（本镜像没有该文件，且其 pattern 也不会匹配 `/vendor`）；同挂载点多表项的重试分支（`first_stage_mount.cpp:217-226`）不适用，因为 `/vendor` 只有一条表项。

由于失败发生在 FATAL 文本能落盘之前，抓到的 kmsg 在 ~500 ms 结束、没有 `Failed to mount /vendor` 原文。分区级归因靠排除法证明：其余全部首阶段前置条件都做过字节级核对且通过（`/system` digest `37cc913b…`、`/product` `e746c5ea…`、`/system_ext` `24deae32…`，vendor/odm/dlkm descriptor 与原厂一致，LP 元数据与原厂逐字节相同，解锁态 AVB permissive，`/metadata` 带 `formattable` 失败被忽略）——唯一剩下的结构缺陷就是 `/vendor` 环。

## 4. 用真实内核路径解析复现 ELOOP（不是理论推断）

构造出完全相同的两跳环目录树，在 chroot 中经内核实际解析（`_tmp/verify/08_src_more.log`）：

```
os.open   /vendor          => 40 ELOOP Too many levels of symbolic links
realpath  /vendor          => 40 ELOOP Too many levels of symbolic links
os.stat   /vendor          => 40 ELOOP Too many levels of symbolic links
os.open   /system/vendor   => 40 ELOOP Too many levels of symbolic links
realpath  /system/vendor   => 40 ELOOP Too many levels of symbolic links
```

## 5. 环为什么存在：构建树里的陈旧产物

- AOSP 生成 `system` 根目录的规则是 `system/core/rootdir/create_root_structure.mk:54-59`：
  ```
  ifdef BOARD_USES_VENDORIMAGE
    LOCAL_POST_INSTALL_CMD += ; mkdir -p $(TARGET_ROOT_OUT)/vendor
  else
    LOCAL_POST_INSTALL_CMD += ; ln -sf /system/vendor $(TARGET_ROOT_OUT)/vendor
  endif
  ```
- 本移植的 `BoardConfig.mk` 已满足 `BOARD_USES_VENDORIMAGE=true`（由 `build/make/core/board_config.mk:703-717` 从 `BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE` 推导，后者在 `device/lenovo/TB323FU/BoardConfig.mk:251` 设置），规则本应执行 `mkdir -p $OUT/root/vendor`。
- 但 out 的实际状态是：`out/target/product/TB323FU/root/vendor` 仍是 **2026-11-07 12:36:52 创建的旧符号链接**（早于 vendor 独立成镜像），而 full-userspace 的 `BoardConfig.mk` 改于 2026-11-09 21:35、`out/system/vendor` 于 2026-11-10 19:38 才重新生成。`mkdir -p` 对悬空符号链接返回失败但**不会中断 make**，于是旧链接被保留并打进每次重建的 `system.img`。
- 分析结论：不清理 `out/target/product/TB323FU/root`，重编多少次都产出坏镜像；清理后 `mka systemimage` 即可得到正确布局。`/dataext` 缺失是另一个独立的构建配置缺口（原厂 system 自带 `/dataext`；AOSP 支持 `BOARD_ROOT_EXTRA_FOLDERS += dataext`，`create_root_structure.mk:29-31`），属非致命问题，影响第二阶段挂载点。

## 6. 为什么此前"已排除"的结论不成立

实验 E6/E7/E8/E9/E13（关 verity、改 SELinux、VINTF 补丁、格式化 `/data` 等）使用的都是同一构建树产出的坏 `system` 镜像。`raw_system_v3.raw`、`super_test5` 的 system 内容、`super_los_v6` 的 system 内容，**AVB root digest 全部是 `37cc913b…`**——同一张坏镜像。所以那些实验根本没执行到 verity/SELinux/VINTF/`/data` 路径；"verity 已排除""SELinux 已排除""VINTF 已排除""`/data` 已排除"这些结论对这一时段不成立。唯一仍然成立的是 E12（原厂 `super` + AOSP testkey 启动链能开机），因为原厂 system 根目录的 `/vendor` 是目录，不受该 bug 影响。

## 7. 修复：离线 raw 补丁（P0-A）

`system` 逻辑分区本身就是 ext4 镜像；修复只重写 ext4 元数据/根目录块，再用**原始 footer 参数**重算 AVB hashtree/FEC，保证产物仍是字节合法的 AVB 分区。

### 7.1 截掉旧 AVB 尾巴

```bash
cp raw_system_v3.raw system_work.raw
truncate -s 10073513984 system_work.raw     # = footer 的 "Original image size"（非硬编码猜测）
```

### 7.2 debugfs：前态 → 打补丁 → 后态

前态：
```
/vendor         Inode 2898  Type: symlink  Mode 0644 Size 14  Fast link dest: "/system/vendor"
/system/vendor  Inode 2892  Type: symlink  Mode 0644 Size 7   Fast link dest: "/vendor"
/dataext        File not found by ext2_lookup
```

补丁命令（`debugfs -w -f`，命令文件 `logs/debugfs_cmds.txt`）：
```
unlink /vendor
mkdir /vendor
sif /vendor mode 040755
sif /vendor uid 0
sif /vendor gid 0
mkdir /dataext
sif /dataext mode 040755
sif /dataext uid 0
sif /dataext gid 0
```

后态（断言 PASS）：
```
/vendor         Inode 2901  Type: directory  Mode 0755  User 0 Group 0  Size 4096  Links 2  EXTENTS (0):219224
/system/vendor  Inode 2892  Type: symlink    Mode 0644  Size 7   Fast link dest: "/vendor"   （未动）
/dataext        Inode 2902  Type: directory  Mode 0755  User 0 Group 0  Size 4096  Links 2  EXTENTS (0):219225
```

### 7.3 文件系统检查

```
e2fsck -f -y system_work.raw   → pass 1 rc=1  （修正：孤儿 inode 2898 收进 /lost+found；inode 2898 refcount 2→1）
e2fsck -f -y system_work.raw   → pass 2 rc=0  （clean；2902/615296 files, 254290/2459354 blocks）
```

### 7.4 用原始参数重算 hashtree + FEC

```bash
export PATH=/root/los24/out/host/linux-x86/bin:$PATH   # avbtool 生成 FEC 需要 host 'fec' 工具
python3 /root/los24/external/avb/avbtool.py add_hashtree_footer \
  --image system_work.raw \
  --partition_size 10235101184 \
  --partition_name system \
  --hash_algorithm sha256 \
  --salt 2b92bdc70f0956d0b3a1100c51d7bde331ea21642661b0b1a9e79c27d5febfd0 \
  --fec_num_roots 2 \
  --algorithm NONE \
  --prop com.android.build.system.os_version:17 \
  --prop com.android.build.system.fingerprint:Lenovo/TB323FU/TB323FU:17/CP2A.260605.016/eng.root:userdebug/test-keys \
  --prop com.android.build.system.security_patch:2026-11-01
```

结果：大小恰为 **10,235,101,184 B**；`Tree Offset 10073513984 / size 79331328`；`FEC Offset 10152845312 / size 80265216 / num roots 2`；`VBMeta Offset 10233110528 / size 832`；新 **root digest `2a3c7c069c1dd825ff6c797ff920dca6c5df65dc1c066356936d910350682d4f`**。`avbtool verify_image`：`Successfully verified footer and NONE vbmeta struct` + `Successfully verified sha256 hashtree`。

### 7.5 重签 `vbmeta_system`

与 bring-up 其余件同一 testkey 链（AOSP testkey，公钥 sha1 `2597c218aae470a130f61162feaae70afd97f011`），rollback index/location 不变，只有 `system` descriptor 更新：

```bash
python3 /root/los24/external/avb/avbtool.py make_vbmeta_image \
  --output vbmeta_system_v7.img \
  --algorithm SHA256_RSA4096 --key testkey_rsa4096.pem \
  --flags 0 --rollback_index 1788566400 --rollback_index_location 2 \
  --padding_size 65536 \
  --include_descriptors_from_image system_raw_fixed.raw \
  --include_descriptors_from_image stock_product.raw \
  --include_descriptors_from_image stock_system_ext.raw \
  --include_descriptors_from_image pvmfw_b.img \
  --include_descriptors_from_image init_boot_logging4.img
```

descriptor 集合（staged `verify_image` 6/6 PASS）：system `2a3c7c06…`、product `8a8c821e…`（原厂）、system_ext `c7980e63…`（原厂）、init_boot `a87adf96…`（实际所刷 init_boot 变体）、pvmfw `847e80aa…`（原厂）。

### 7.6 重拼 `super`

`super_v7.img` = 原厂 `super`，**仅**把 `system_b` 区段（偏移 **2,503,041,024 B**、长度 **10,235,101,184 B**）替换为新 system：

```bash
python superkit.py build --src super_stock.img --dst super_v7.img --regions regions.json \
  --patch system_b=system_raw_fixed.raw --out build_v7.json
python superkit.py audit --lp --parallel-regions
python superkit.py compare --a audit_stock.json --b audit_v7.json
```

审计结果：9 段中 **8 段与原厂逐字节相同**，只有 `system_b` 变化；LP 元数据（前 64 KiB、primary 208,896 B、backup 196,608 B）与原厂逐字节相同。

### 7.7 产物

| 产物 | 大小 (B) | SHA-256 |
|---|---|---|
| `system_raw_fixed.raw` | 10,235,101,184 | `1e7ec2d126d2889340578182b78121af7b39dbd1bc2165f39852cf4453673ff8` |
| `vbmeta_system_v7.img` | 65,536 | `6b11d5e4a83318f6ff95128404b59a1890b33b167c04806d974feb0b76c04616` |
| `super_v7.img` | 21,474,836,480 | `5779a9a5e73ddcdecea245fc65ad8cc9e398de4a1ab889d8656e8f3b335823bf` |

## 8. 真机验证

- **2026-11-11 22:35（首阶段全通）**——使用 22:18 诊断集（原厂 GPT + `vendor_boot_nofail` + `init_boot_logging10` + `vbmeta_system_v8`），从 `misc` 抓到的 kmsg（`device/kmsg_20261111_223511.txt`）显示：`:1234 init: init first stage started!`；`:2172-2190` **7 个 EXT4 分区挂载成功**（`EXT4-fs (dm-7 … dm-13): mounted filesystem … ro without journal`）；`:2193 init: Opening SELinux policy`；`:2195 init: Compiling SELinux policy`——首阶段通过、进入第二屏，这在修复前从未发生过。
- **22:40**——adb 首次枚举到 LineageOS 用户态：`Lenovo/lineage_TB323FU/TB323FU:17/CP2A.260605.016/eng.root:userdebug/test-keys`，`slot=_b`，`vbs=orange`。
- **22:48–22:50**——用户目视进入 LineageOS 欢迎界面。
- **2026-11-12 F0 修复集**——最终验收用的 `system` 镜像保留同一修复后的根布局（另加 doc 06 的 logdump 删除）。最终验收：`sys.boot_completed=1`、开机动画停止、FBE `file/encrypted`、`/metadata` 与 `/data` 正常挂载、连续 3 次 `adb reboot` 全部 PASS。
- 注意：22:18 那一刷同时改了多个变量（恢复原厂 GPT、`no_fail` fstab、日志包装器、`vbmeta_system_v8`），**未做单变量对照**，因此"仅 `/vendor` 修复"未在真机上单独隔离验证。结构性证明在字节与源码层面已闭环；且原厂"`/vendor` 为目录"的布局恰好是可开机形态，方向得到旁证。复现请按项目状态记录整套刷。

## 9. 已知限制 / 未验证

1. 新建的 `/vendor`、`/dataext` 目录**没有 `security.selinux` xattr**；原厂 `/vendor` 带 `u:object_r:vendor_file:s0`、gid 2000，原厂 `/dataext` 带 `u:object_r:dataext_file:s0`。这不阻断首阶段（SELinux 尚未加载；挂载后目录被各分区文件系统覆盖），但若后续出现 `u:object_r:rootfs` 相关 denial，应补 xattr。
2. `/lost+found/2898` 保留旧 `/vendor` symlink inode；`e2fsck -fn` 报文件系统 clean，该目录不参与启动。
3. `vbmeta_system_v7.img` 与签卡时的 init_boot 变体配对；换 init_boot 需重签 descriptor（另出过 `…_stockib` 变体）。
4. 重算了 hashtree/FEC，但当时未做真机 verity-on 运行（bring-up 集合是 verity-off）。将来切 verity-on 必须使用 system descriptor 与实际 system 镜像匹配的 `vbmeta_system`。
5. 当时未在真机验证"只修 `/vendor`（配旧诊断集）能否开机"——见 §8 caveat。

## 10. 复现摘要

1. 检查 LOS `system` raw 镜像：`debugfs -R "stat /vendor"` 必须输出 `Type: directory`；若输出 `Type: symlink` 且目标为 `/system/vendor`，该镜像存在环。
2. 离线修复：去 footer → `unlink /vendor` + `mkdir /vendor` + `mkdir /dataext`（mode 040755、uid/gid 0）→ `e2fsck -f -y` 两遍（rc=1 后 rc=0）→ `avbtool add_hashtree_footer`（原始 partition size/salt/FEC/props）→ `avbtool make_vbmeta_image`（testkey 链）。
3. 重拼 `super`，仅替换 `system_b` 区段；核对另外 8 段与原厂逐字节相同。
4. 刷入自洽集合后从 kmsg 验证首阶段：`init: init first stage started!` → 7× `EXT4-fs (dm-…)` → `init: Opening SELinux policy`。

## 11. 证据索引

| 路径 | 内容 |
|---|---|
| `<PROJECT_ROOT>\out\2026-11-10-los24-logdump\LOS-SYSTEM-ANALYSIS.md` | 首次根因分析：debugfs 布局对比、构建规则时间戳、源码路径、ELOOP 语义 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\IMAGE-FIX-REPORT.md` | 离线打补丁全过程、avbtool 参数、super 审计、产物 SHA |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\VERIFY-REPORT.md` | 根因独立再推导（R1–R4）与三个产物的独立复核（R5–R9） |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\BOOTFIX-FACTS.md` | 事实表：产物 mtime、刷写集、开机证据摘录 |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\device\kmsg_20261111_223511.txt` | 首阶段全通（7 个 EXT4 挂载；进入第二屏） |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\device\kmsg_20261111_230836.txt` | 22:46 之后同系列启动：`Opening SELinux policy` → `Compiling` → `Loading SELinux policy` |
