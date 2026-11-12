作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0

# 09 — AVB 信任链笔记（Lenovo Legion Y700 五代 TB323FU / LineageOS 24）

| 项 | 值 |
|---|---|
| 文档状态 | 2026-11-12；启动行为已真机验证（F0 验收 PASS） |
| 适用设备 | Lenovo Legion Y700 五代 **TB323FU**（SM8850P，canoe/kaanapali），bootloader 已解锁（verified-boot state = orange），当前槽位 = B |
| 范围 | 原厂固件的 Android Verified Boot（AVB）拓扑、已被验证可启动 LineageOS 24 的信任链、可改/禁改边界、重签方法、与 dm-verity 的耦合、槽位状态存储位置、校验命令 |
| 不覆盖 | 内核/DTB 修改、固件刷写纪律、SELinux 策略内容、recovery 镜像内部实现 |
| 相关文档 | [01 · 设备事实](01-DEVICE-FACTS.md)（身份/分区几何）、[03 · 刷写](03-FLASH.md)（刷写集与回退）、[05 · 根因：/vendor ELOOP](05-ROOTCAUSE-VENDOR-SYMLINK.md)、[08 · SELinux](08-SELINUX-POLICY.md)、[11 · 报错目录](11-ERROR-CATALOG.md)、[12 · 实验台账](12-EXPERIMENT-LOG.md) |
| 证据原则 | 本文每个数字都来自离线镜像分析或真机日志；未闭环的结论明确标 **待验证（UNVERIFIED）**；不把“应该能行”的推测写成事实 |

> **路径约定**：证据路径以项目根目录为基准，统一脱敏为 `<PROJECT_ROOT>`；构建树为 WSL Ubuntu 下的 `/root/los24`（LineageOS 24.0 / Android 17）。本仓库中序列号统一显示为 `<SN-REDACTED>`，MAC 地址统一显示为 `<MAC>`。

---

## 1. 结论速览（TL;DR）

1. 原厂信任链是**哈希钉死（hash-pinned）而不能整体替换**的：root `vbmeta_b` 用 OEM 密钥签名，钉住 `boot_b`、`recovery_b`（chain 分区）以及 `dtbo_b`、`vendor_boot_b`（hash 描述符）。
2. 唯一被证明可与自编内容共存的形态是 **AOSP testkey 子树**：root `vbmeta_b` 用 AOSP testkey 重签 + `vbmeta_system_b` 用 testkey 重签 + **原厂** `boot_b`/`recovery_b`/`dtbo_b`/`vendor_boot_b` + 原厂内容 = 能开机到 `sys.boot_completed=1`（实验 E12）。自造的非 testkey 密钥必失败。
3. root `vbmeta_b` 是**唯一**能整体关闭 dm-verity 的位置（`flags=1/2`）。分区级 digest 不符**不会**因为 bootloader 解锁而被豁免，会在挂载读块时报 dm-verity EIO。
4. 改 `vendor_boot_b`（fstab 标志）会被解锁态 ABL 容忍：设备显示 orange、可能停在第一屏，但**不会**自己落 bootloader fastboot；把 `init_boot_b` 换成非 OEM、未被 hash-pin 的件，一直在 ~8–12 s 回落 bootloader fastboot。
5. `slot-unbootable` 存在 **GPT 分区属性**里（LUN4、`boot_b`、entry 索引 53、属性字节 54）：`0x6F` = active + successful + bootable，`0xEF` = 置了 unbootable 位（0x80）。它不在 `misc`、`devinfo`、`efisp` 或 `uefivarstore`。
6. F0 能开机刷写集是**刻意关 verity 的诊断态**：`vendor_boot_diag2`（首阶段 fstab 去掉全部 `avb=`）+ `vbmeta_system_v10`（system digest `2a3c7c06…`）+ AVB footer 仍是旧值的 `system_b`。只有 verity-off 时这组合才安全；要恢复 verity 必须重算 hashtree 并配对应 `vbmeta_system`（见 §8.4）。

---

## 2. 术语

| 术语 | 本文含义 |
|---|---|
| root vbmeta | 顶层 `vbmeta`（本机为分区 `vbmeta_b`，LUN4 LBA 513634，65,536 B） |
| chain 分区 | 自身 vbmeta 之所以被加载，是**因为** root vbmeta 里有指向它的 `chain` 描述符（如 `vbmeta_system_b`） |
| hash 描述符 | root vbmeta 把某分区的确切字节（`dtbo_b`、`vendor_boot_b`、`init_boot_b`）钉为 `sha256(salt ‖ data[0:image_size])` |
| hashtree 描述符 | 文件系统镜像的 dm-verity 树/FEC 布局（`system`、`system_ext`、`product`、`vendor`、`odm` 等） |
| rollback index（RI） | 防回滚计数，只能升不能降 |
| RI location | 该值在 bootloader 里使用哪个回滚索引槽；原厂 `vbmeta_system` 用 location **2** |
| footer | 附加在镜像尾部的 AVB 元数据；`init_boot`/`dtbo`/`vendor_boot` 的 `Algorithm` 是 `NONE`（只被 hash 钉，不是被签名） |
| first-stage fstab | **原厂** `vendor_boot_b` ramdisk 内的 `first_stage_ramdisk/fstab.qcom`，决定首阶段挂载哪些分区、是否使用 dm-verity |
| orange / verified-boot state | `ro.boot.verifiedbootstate=orange` = bootloader 已解锁；AVB 校验错误被 ABL 容忍 |

---

## 3. 推理 AVB 所必需的分区/LUN 事实

LBA 全部以 **4 KiB 扇区**为单位。只列与 AVB 相关的部分。

| 对象 | LUN | 起始 LBA | 大小 |
|---|---|---|---|
| `super`（物理） | 0 | 8968 | 20 GiB（21,474,836,480 B） |
| `vbmeta_system_b` | 0 | 5,251,864 | 16 扇区（65,536 B） |
| `misc` | 0 | 8456 | 256 扇区（1 MiB） |
| `metadata` | 0 | 5,251,880 | 64 MiB（块设备 `sda10`） |
| `userdata` | 0 | — | `sda14` |
| `vbmeta_b` | 4 | 513,634 | 16 扇区（65,536 B） |
| `boot_b` | 4 | 489,006 | 24,576 扇区（100,663,296 B） |
| `vendor_boot_b` | 4 | 672,238 | 24,576 扇区 |
| `init_boot_b` | 4 | 722,990 | 2,048 扇区（8,388,608 B） |
| `dtbo_b` / `recovery_b` / `pvmfw_b` | 4 | 513,650 / 696,878 / 725,054 | — |
| `logdump`（诊断目标，不被 AVB 覆盖） | 4 | 735,255 | 512 MiB |

`super` 的逻辑分区由 liblp 映射；本移植只改写了 `system_b` 一个逻辑分区。`system_b` 的物理 LBA = 620,062（super 起点 8968 + 611,094），长度 2,498,804 扇区（10,235,101,184 B）。

---

## 4. 原厂 AVB 拓扑

```
root vbmeta_b   （OEM 密钥 8fcb864f…，flags=0，rollback_index=0）
 ├─ CHAIN  boot_b            → OEM 密钥 8fcb864f…        （不要替换）
 ├─ CHAIN  recovery_b        → OEM 密钥 8fcb864f…        （不要替换；替换有红屏 / 不可启动风险）
 ├─ CHAIN  vbmeta_system_b   → 重签后 testkey 可被接受（E12 形态）
 ├─ HASH   dtbo_b            （sha256(salt‖content)；footer Algorithm=NONE）
 ├─ HASH   vendor_boot_b     （同上；footer Algorithm=NONE）
 └─ TREE   dataext_b、odm_b、system_dlkm_b、vendor_b、vendor_dlkm_b

vbmeta_system_b  （原厂：OEM 密钥，flags=0，RI=1788566400，RI location=2）
 ├─ HASH   init_boot_b       （原厂：image_size=2,555,904 / salt 99caf6df… / digest dcf52c78…）
 ├─ HASH   pvmfw_b           （761,856 B / digest 847e80aa…）
 └─ TREE   product、system、system_ext   （hashtree root 必须等于镜像 footer）
```

原厂基准哈希（SHA-256，已对全量回读对齐）：

| 分区 | SHA-256 |
|---|---|
| `vbmeta_b` | `ae4ebd619bb57c0d4f50e6619d1a5937bc805b8eaff90f83becdf2631dbf54d7` |
| `vbmeta_system_b` | `493448e6…` |
| `boot_b` | `2731d62ca182c811ed51e4c4e33fe22da4191218569499cdb7debf793c072bec` |
| `init_boot_b` | `a31072c0b26f5df8581e2f23e9a39cb8476c00b2b9f251c701db433141653e68` |
| `vendor_boot_b` | `9349137dc262ab61508014275b623f4d39e5b14bc55c77082848d63a28f381b2` |
| `dtbo_b` | `6cdc8d3bbf2ff9123ad303db9837e666c5f7a1da4a0654a5799439aba239db49` |
| `recovery_b` | `a3b34a80b8e15a9ef6f66831b64d6f10f4a37ad2676b4102eb43e529862acea0` |
| `pvmfw_b` | `d24b59dc…` |
| `dataext_b` | `e231c8c7…` |
| `super` | `78e54bd36dc1d6971d338ffb49670c6809cad36ca16f6004d0b281af331cf4e5` |

首阶段 fstab（从原厂 `vendor_boot_b` ramdisk 解出，7,374 B）里带 `first_stage_mount` 的挂载行共 13 条：`system`、`system_ext`、`product`、`vendor`、`vendor_dlkm`、`system_dlkm`、`odm`（都带 `avb=…,logical,first_stage_mount`），加上启动链的物理分区。只有 `system` 行额外带 7 个 GSI `avb_keys=/avb/*-gsi.avbpubkey`；`/dataext` 只在第二阶段挂载。

---

## 5. 真正被验证能启动 LineageOS 24 内容的信任链

**E12 配置（原厂内容，证明签名模型）：**

```
root vbmeta_b      = AOSP testkey 重签（公钥 sha1 2597c218aae470a130f61162feaae70afd97f011）
 ├─ CHAIN boot_b     → OEM 密钥 8fcb864f…  （保持原厂 boot）
 ├─ CHAIN recovery_b → OEM 密钥 8fcb864f…  （保持原厂 recovery）
 ├─ CHAIN vbmeta_system_b → testkey 2597c218…
 └─ HASH/HASH/TREE  dtbo_b / vendor_boot_b / dataext,odm,system_dlkm,vendor,vendor_dlkm
vbmeta_system_b    = AOSP testkey 重签，flags=0，RI=1788566400，RI location=2
 ├─ HASH init_boot_b  （原厂件或诊断包装器，digest 按实际重算）
 ├─ HASH pvmfw_b      （原厂 digest）
 └─ TREE product / system / system_ext（digest 按实际镜像重算）
```

结果：`sys.boot_completed=1`，原厂指纹。关键细节是：**自造密钥被拒绝，而 AOSP testkey 被这台 ABL 接受**；只有 `boot`/`recovery` 必须保持 OEM 签名，因为它们是 OEM root 的 *chain* 分区。

本移植可开机的刷写集沿用这套 testkey 形态（root `vbmeta_b` = `7ed20919…`，`vbmeta_b_testkey_E12.img`），并在 `system`/`product`/`system_ext`/`init_boot` 任一发生改动时重签 `vbmeta_system_b`。

---

## 6. 为什么 AVB 自洽是硬前提（与 dm-verity 的耦合）

- first-stage init 从**原厂** `vendor_boot_b` ramdisk 读 fstab（`first_stage_ramdisk/fstab.qcom`），改 `system` 内容不会改变它；逻辑分区由 `slotselect` 解析成 `*_b`。
- 对每个带 `avb=` 的分区，`fs_avb` 依据镜像自带 hashtree 建立 dm-verity 设备（`system` 先尝试 GSI `avb_keys`，失败再回退 `avb=vbmeta_system` 的描述符）。**真正的校验发生在文件系统读块时，而不是建 dm 表时**；挂载是否成功由数据块与事先建好的 tree/FEC 的 `sha256` 决定。
- 因此内容与 footer 不匹配时，表现为**读 `system` 时 EIO**，而不是一句友好的“校验失败”。这也是离线必须跑 `avbtool verify_image` 的原因。
- digest 不匹配**不会**被 `unlocked`/orange 豁免。解锁只容忍签名类错误（`ERROR_VERIFICATION`、`PUBLIC_KEY_REJECTED`）；结构损坏的 chained vbmeta（`ERROR_INVALID_METADATA`）与数据 hashtree 不匹配仍然失败（EIO / `AvbHandle::Open()` 返回 null）。
- **唯一**的整体关闭开关是顶层 root vbmeta 的 `flags=1/2`；分区级 `vbmeta_system flags=1` 无效（E7 实验已跑过，未改变失败现象）。
- 本移植使用的诊断捷径：把 `vendor_boot` 变体的首阶段 fstab 里**全部 `avb=`/`avb_keys=` 标志去掉**（并加 `no_fail`），逻辑分区就能不建 dm-verity 直接挂载。这只是诊断/点亮用配置，不是发布配置。

---

## 7. 可改边界（以及代价）

| 组件 | 机制 | 能改吗 | 已观测后果 |
|---|---|---|---|
| `system`、`system_ext`、`product`（逻辑分区） | `vbmeta_system` 的 hashtree 描述符 | **能**，但必须用新 root digest 重签 `vbmeta_system_b` 并在同一次刷写中写入 | verity-off：任意内容能启动；verity-on：旧 digest → 挂载时 dm-verity EIO |
| `init_boot` | `vbmeta_system` 的 hash 描述符 | **能**——按实际镜像重算（原厂 `image_size` 2,555,904；包装器件更大，如 2,736,128） | 自编 init_boot（非 OEM 签名/未被链约束）观测到 ~8–12 s 回落 bootloader fastboot |
| `vbmeta_system` | chain 分区 → 必须由 root 信任的 key 签名 | **能用 testkey**（root 里 chain 的目标公钥必须是 AOSP testkey） | 可用（E12 及之后全部构建） |
| root `vbmeta_b` | 顶层 vbmeta | **能用 AOSP testkey**；**绝不能用自造密钥** | 自造 key → 8 s 落 fastboot；testkey → 能开机 |
| `boot`、`recovery` | chain 分区 → OEM 密钥 | **不能，保持原厂** | 换成 testkey 重签后未观测到干净开机（唯一一次尝试 12 s 回 fastboot，且当时槽位已 unbootable，实验不可用） |
| `vendor_boot` | root vbmeta 的 hash 描述符 | **解锁态 ABL 容忍 hash 不符** | 显示 orange；可能停在第一屏；本身不会落 fastboot |
| `dtbo` | root vbmeta 的 hash 描述符 | 本移植未改 | 若改，必须在 root vbmeta 里重算 hash |
| `dataext`、`odm`、`vendor`、`vendor_dlkm`、`system_dlkm`（内容） | root vbmeta 的 hashtree 描述符 | 只能用设备可接受的 key 重签 root vbmeta 才能改 | `dataext_b` 内容按原厂假设；损坏只会 vold 告警（非致命） |
| `super` LP 元数据 | 不被 AVB 覆盖 | 禁止手改 | 用 liblp 工具/fastbootd；手写 LP 元数据有 super 不可启动风险 |

---

## 8. 重签方法（实际用过的命令）

`avbtool` 用 LineageOS 构建树内的 AOSP 版本：`/root/los24/external/avb/avbtool.py`。本文使用的 testkey 是公开的 AOSP `testkey_rsa4096.pem`（`<PROJECT_ROOT>/tmp/recon/testkey_rsa4096.pem`，SHA-256 `6a224754880a57ab9cbd308267cd157d94cf05a1c8cb851aec4090e045d24121`），公钥 SHA-1 为 `2597c218aae470a130f61162feaae70afd97f011`。**AOSP testkey 是公开密钥，绝不能当作生产安全锚点。**

### 8.1 `system` 的 hashtree footer（修完内容后）

```bash
export PATH=/root/los24/out/host/linux-x86/bin:$PATH   # 需要 host 侧 'fec' 工具
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
python3 /root/los24/external/avb/avbtool.py verify_image \
  --image system_work.raw --key /root/los24/external/avb/test/data/testkey_rsa4096.pem
```

`--calc_max_image_size` 必须等于 10,073,513,984 B（恰好等于 ext4 数据区大小）。生成的 footer 必须与原 LOS footer 逐项比对：`Image Size`、`Original image size`、`salt`、`Tree offset/size`、`FEC offset/size`、`FEC roots`、`Partition Name`、`Algorithm: NONE`，以及三个 `com.android.build.system.*` prop。本次开机修复镜像的数字：原图 10,235,101,184 B，AVB image size 10,073,513,984 B，salt `2b92bdc7…`，tree 79,331,328 B @ 10,073,513,984，FEC 80,265,216 B @ 10,152,845,312，FEC roots 2，旧 root digest `37cc913b…` → 新 root digest `2a3c7c06…`。

### 8.2 `init_boot` 的 hash footer（诊断包装器或原厂件）

```bash
avbtool add_hash_footer \
  --image payload.img \
  --partition_size 8388608 \
  --partition_name init_boot \
  --hash_algorithm sha256 \
  --algorithm SHA256_RSA4096 \
  --key testkey_rsa4096.pem \
  --rollback_index 1788566400
```

`mkbootimg` 必须产 header v4 且 **`kernel_size=0`**（1 字节 kernel 会导致包装器永不执行），`--os_version 17.0.0 --os_patch_level 2026-09`，页大小 4096。`init_boot_logging13.img` 的实测值：payload 2,736,128 B，footer digest `4bf06b0c…`，salt `c1250c11…`，整件 8,388,608 B，`verify_image` PASS。

### 8.3 `vbmeta_system`（testkey，描述符全部取自实际镜像）

```bash
avbtool make_vbmeta_image \
  --output vbmeta_system_v10.img \
  --algorithm SHA256_RSA4096 --key testkey_rsa4096.pem \
  --flags 0 --rollback_index 1788566400 --rollback_index_location 2 \
  --padding_size 65536 \
  --include_descriptors_from_image init_boot_logging13.img \
  --include_descriptors_from_image stock_product.raw \
  --include_descriptors_from_image stock_system_ext.raw \
  --include_descriptors_from_image system_raw_fixed.raw \
  --include_descriptors_from_image pvmfw_b.img
```

`v10` 的实测头：pubkey sha1 `2597c218…`、`SHA256_RSA4096`、RI 1788566400、RI location **2**、flags 0、65,536 B、sha256 `2b52e26b9c1bc8f15562d5e22a1fc2eced0d5721a432e15846ee26901fce4afc`。staged `verify_image` 必须在同目录放有真实分区镜像（avbtool 按分区名找文件）。

### 8.4 F0 刷写集之后恢复 dm-verity（配方，尚未进发布流程）

1. 以 F0 内容（删 logdump 后的 system）重建 hashtree/FEC 并签名：
   - 新的 verity-ready `system` raw：SHA-256 `29ad60fb…`（10,235,101,184 B），新 root digest `9103aeb9…`；
   - 用该 digest 重建 `vbmeta_system` → `vbmeta_system_f0_v11.img`，SHA-256 `66e20599…`，其余描述符不变（`init_boot` 2,736,128/`4bf06b0c…`、`pvmfw` 761,856/`847e80aa…`、`product` `8a8c821e…`、`system_ext` `c7980e63…`、`system` `9103aeb9…`）。
2. 刷**完整** verity-ready `system` 镜像（9 块增量补丁保留旧 footer，仅 verity-off 可用）。
3. 把诊断版 `vendor_boot` 换回启用了 AVB 的变体（首阶段 fstab 保留 `avb=` 标志）。
4. 才启用 verity。**不要**在 F0 当前 `vendor_boot_diag2` + `vbmeta_system_v10` 下启用 verity：system digest 与改过的内容不匹配 → dm-verity EIO。
5. 此过程**不需要**改 root `vbmeta_b`（testkey 形态）。

---

## 9. 配对矩阵（“刷进去了但开不了机”的高发区）

| 刷写组合 | `system` 内容 | `vbmeta_system` | `init_boot` | `vendor_boot` | 备注 |
|---|---|---|---|---|---|
| `super_v7` | `system_raw_fixed.raw`（`1e7ec2d1…`） | `vbmeta_system_v7`（`6b11d5e4…`，system `2a3c7c06…`）/ `v8`（`bfd496d9…`） | 原厂或 `logging4`/`logging10` | 原厂、`vendor_boot_nofail`、`diag2` | 首套能开机组合 |
| F0 就绪（verity-off） | `system_raw_nologdump.raw`（`b6ca50f5…`）或其 9 块补丁 | `vbmeta_system_v10`（`2b52e26b…`，system digest `2a3c7c06…`） | `init_boot_logging13`（`baf1133d…`） | `vendor_boot_diag2`（`40623569…`） | 2026-11-12 真机验证通过（3/3 重启） |
| F0 + verity-on（未来） | `system_verity.raw`（`29ad60fb…`，root digest `9103aeb9…`） | `vbmeta_system_f0_v11`（`66e20599…`） | `init_boot_logging13` | 启用 AVB 的 `vendor_boot` | **尚未真机验证** |
| 原厂内容对照 | 原厂 `super` | 原厂 `vbmeta_system_b`（`493448e6…`） | 原厂 | 原厂 | 能开机（E12 用该内容 + testkey vbmeta） |

**硬规则：** `system` 内容 digest、`vbmeta_system` 的 system 描述符、镜像自身 footer 三者必须一致；`init_boot` 内容必须与其 hash 描述符一致；`vbmeta_system` 必须由 root vbmeta 信任的 key 签名。跨行混搭就是经典的“刷写 OK、第一屏就死 / EIO”。

---

## 10. `slot-unbootable` 等槽位状态（GPT 属性）

Qualcomm bootctrl HAL 把 A/B 槽位元数据存在 LUN4 的 **GPT 分区属性**里，不在 `misc`：

- 每个 128 字节 GPT entry 内 `AB_FLAG_OFFSET = 54`（属性 bits 48–55）；
- `AB_PARTITION_ATTR_SLOT_ACTIVE = 0x04`、`BOOT_SUCCESSFUL = 0x40`、`UNBOOTABLE = 0x80`；
- 本机 `boot_b` 是 LUN4 GPT entry #53。实测值：原厂/健康 `byte54 = 0x6F`；unbootable 态 `0xEF`。
- 修复 = 写回原厂 `gpt_main4`（LBA 0，6 扇区）**和** `gpt_backup4`（LBA 1,048,571，5 扇区）这一对，然后复位。主备必须成对写。
- 失败启动会再次置 unbootable 位；**先修内容再启动**，且在 `slot-unbootable:b=yes` 时不要把启动结果当实验结论。

快速读属性（用 EDL 拉出 GPT 后）：

```python
# gpt_main4.bin = LUN4 LBA0 起 6 扇区；boot_b 为 entry #53
d = open("gpt_main4.bin", "rb").read()
byte54 = d[2*4096 + 53*128 + 54]
print(hex(byte54))            # 0x6F = active+successful+bootable；0xEF = unbootable 置位
```

---

## 11. Rollback index、flags 与 ABL 行为

- root `vbmeta_b`：`flags=0`、rollback index 0、RI location 0。`vbmeta_system_b`：`flags=0`、RI `1788566400`、RI location **2**。重签 `vbmeta_system` 必须保持这些值（RI 只能升不能降）。
- 本项目对 `vendor_boot` 重打包时曾把 `os_version/os_patch_level` 降到 15.0.0 / 2025-07（原厂 17.0.0 / 2026-09）。AVB 不校验这些字段，但 Qualcomm 防回滚逻辑是否读取它们**待验证**。尽量保持原厂值。
- 原厂 `abl_b` 镜像里能找到的行为字符串：`State: Unlocked, AvbSlotVerify returned %a, continue boot`、`Device is unlocked, Skipping boot verification`、`Reset unbootable slots failed enter fastboot mode`、`No bootable slots found enter fastboot mode`。这解释了为什么解锁态即使 hash 不匹配也能继续走到内核，而找不到可启动槽位时会落 fastboot。
- “8 s / 12 s 落 fastboot”**不是** AVB 的唯一症状：AOSP init 遇到致命错误后也会请求重启到 bootloader。应把它当作“启动链或早期用户态致命”，不要自动归因于“签名被拒”。

---

## 12. 校验清单（刷写前后都跑）

```bash
# 1. 离线：镜像签名/hashtree 是否自洽？
avbtool info_image   --image system_work.raw
avbtool verify_image --image system_work.raw --key testkey_rsa4096.pem

# 2. 离线：vbmeta_system 的描述符是否等于镜像 footer？
avbtool info_image --image vbmeta_system_v10.img | grep -A8 "system"
avbtool info_image --image system_work.raw          | grep -E "Root Digest|Image Size|Salt"

# 3. 真机：槽位/启动状态
fastboot getvar current-slot
fastboot getvar slot-unbootable:b        # 必须为 no
fastboot getvar is-userspace             # yes = fastbootd，no = bootloader fastboot
fastboot getvar unlocked                 # yes = 已解锁
adb shell getprop ro.boot.verifiedbootstate   # orange = 解锁，green = 锁定

# 4. 真机：dm-verity 是否真的生效？
adb shell getprop ro.boot.veritymode
adb shell dmesg | grep -Ei "dm-verity|avb|verification"
adb shell cat /proc/mounts | grep -E "system|vendor|product"

# 5. EDL 写后：回读并算哈希
certutil -hashfile <readback>.bin SHA256    # 或 Windows 下 Get-FileHash
# 与刷写清单里记录的期望 sha256 比对
```

“AVB 链正确”的验收判据：(a) 每张重签镜像 `avbtool verify_image` PASS；(b) `vbmeta_system` 描述符等于镜像 footer；(c) 回读哈希等于写入镜像；(d) 设备启动无 dm-verity EIO；(e) `slot-unbootable:b=no`。

---

## 13. 已知坑

1. **描述符/镜像不匹配**：用**旧** system digest 重签 `vbmeta_system` 是最常见的错误。始终从实际镜像 footer 取 `Root Digest`。
2. **配对过期**：为 `init_boot_logging10` 生成的 `vbmeta_system`（image size 2,732,032 / digest `a87adf96…`）描述不了 `init_boot_logging13`（2,736,128 / `4bf06b0c…`）。必须成套刷。
3. **`verify_image` 需要分区文件**：avbtool 的 staged 校验按分区名解析文件；要么在同目录放好 `system`、`product`、`system_ext`、`init_boot`、`pvmfw`，要么只用 `verify_image --image <file>` + key 的形式。
4. **需要 FEC 工具**：带 FEC 的 `add_hashtree_footer` 需要构建树里的 host `fec` 二进制（`out/host/linux-x86/bin/fec`）；缺了会失败或静默产出不同结果。
5. **内容一改，原厂 `vbmeta_system` 就过期**（例如被替换成 LOS 构建的 `product`/`system_ext`）；所以能开机的刷写集始终会重签 `vbmeta_system`。
6. **`dataext_b` 内容从未回读**；root vbmeta 的 dataext hashtree 是基于“原厂内容”的假设。一旦它被格式化过，第二阶段 `/dataext` 挂载会 dm-verity EIO（非致命，但 vold/数据扩展会异常）。
7. **把 `recovery_b` 换成非原厂 recovery** 可能让 `AvbHandle::Open()` 返回 null（chained vbmeta 元数据非法，`ERROR_INVALID_METADATA` 即使解锁态也不容忍）。保持原厂 `recovery_b`，或先验其 AVB 元数据。
8. **禁止手改 GPT/LP 元数据**去“修槽位”；应当整对写回原厂 GPT。
9. **AOSP testkey 是公开的**。要发布任何东西都需要重新设计安全模型；本仓库记录的是 bring-up，不是生产签名服务。

---

## 14. 未闭环 / 待验证项

1. `boot→testkey` 链在干净状态下的行为：唯一一次尝试 12 s 回 fastboot，但当时槽位已标 unbootable，结果**不可用（inconclusive）**。
2. 没有 OEM 私钥，无法对 `init_boot`/`boot` 做 OEM 重签；ABL 是否接受 OEM 签名的自定义 boot 镜像未知。
3. bootloader 的回滚索引存储是否读取 `vendor_boot` 里的 `os_version/os_patch_level`（重打包值为 15.0.0/2025-07）——未知。
4. 开机修复轮从未回读 `dataext_b`、`pvmfw_b`、`recovery_b` 的物理内容（按原厂假设）。回读并核对其 AVB digest 是待办。
5. F0 内容的 verity-on 运行（`system_verity.raw` + `vbmeta_system_f0_v11` + 启用 AVB 的 `vendor_boot`）已离线备好但**尚未真机验证**。
6. 是否存在第二份冗余槽位状态存储（RPMB 或其它持久区）未被证明；所有逐字节比对只覆盖明文分区。

---

## 15. 参考材料（相对 `<PROJECT_ROOT>`）

- `out/2026-11-11-los24-bootfix/VERIFY-REPORT.md` —— 信任链/摘要/root digest 配对的逐字节独立复核、ELOOP 根因（§1–§3）、“若仍失败”的分析（§4）。
- `out/2026-11-11-los24-bootfix/IMAGE-FIX-REPORT.md` —— 完整 `avbtool` 命令行、footer 参数、staged `verify_image` 输出。
- `out/2026-11-11-los24-bootfix/INITLOG13-BUILD-REPORT.md`、`INITLOG12-BUILD-REPORT.md` —— `init_boot` hash footer 与 `vbmeta_system` 配对值。
- `out/2026-11-11-los24-bootfix/F0-SIDE-EFFECT-AUDIT.md` §3 —— verity 恢复配方（`system_verity.raw`、`vbmeta_system_f0_v11.img`）。
- `out/2026-11-11-los24-bootfix/FLASH-CHECKLIST.md` —— 最小单变量刷写集、LUN/扇区/期望 sha。
- `out/2026-11-11-los24-bootfix/F0-FLASH-BUNDLE.md` —— 回退锚点与原厂哈希。
- `out/2026-11-10-los24-logdump/LOS24-PLAYBOOK-CONSOLIDATED.md` §3.3 —— 原厂链归属与可改边界；§3.2 —— 槽位状态在 GPT 属性。
- `out/2026-11-10-los24-logdump/RECOVERY-PLAYBOOK.md` §问题 3 —— 链拓扑与 AVB 绕过路线。
- `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` —— 已开机的刷写集及其哈希。
