作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0

# 02 · 构建 —— TB323FU 的 LineageOS 24.0（Android 17）

| 字段 | 内容 |
|---|---|
| 状态 | 2026-11-12 —— 构建配方已验证；2026-11-12 验收所用最终镜像产出于 2026-11-11，可按下列步骤复现 |
| 适用设备 | 联想拯救者 Y700 五代，型号 **TB323FU**；LineageOS 24.0 / Android 17，产品 `lineage_TB323FU-cp2a-userdebug` |
| 范围 | 构建主机、源码树、设备树配置、lunch/构建命令、构建树 `/vendor` 符号链接根治、批次/配对纪律、已知构建失败 |
| 证据来源 | `out/2026-11-11-los24-bootfix/BUILD-FIX-REPORT.md`；`out/2026-11-11-los24-bootfix/BUILD-FIX-MANIFEST.json`；`<WORKSPACE>/research/a17-rom-survey/BUILD-LOG.md`；`<PROJECT_ROOT>/tmp/aera-recovery/ENV.md`；设备树 `BoardConfig.mk`/`device.mk`；`out/2026-11-11-los24-bootfix/SELINUX-COMPILE-ANALYSIS.md` |

> 设计前提（**最小内容替换**）：本移植只编译 `system`、`system_ext`、`product` 与 `vbmeta_system` 签名。`vendor`、`odm`、`vendor_dlkm`、`system_dlkm`、内核与整条启动链（`boot` / `init_boot` / `vendor_boot` / `dtbo` / `recovery`）保持联想原厂件。不编译内核；仅使用一个原厂 prebuilt 内核满足构建期 VINTF 内核检查。

## 1. 构建主机

| 项 | 值 |
|---|---|
| 宿主系统 | Windows 10.0.19045.5856 + WSL2 |
| WSL 发行版 | Ubuntu 24.04.5 LTS（`VERSION_ID="24.04"`） |
| WSL 版本 / 内核 | WSL 3.0.1.0 / `6.18.40.1-microsoft-standard-WSL2` |
| CPU | Intel Xeon E5-2666 v3 @ 2.90 GHz；宿主 20 逻辑核，WSL 限 **18**（`processors=18`） |
| 内存 / swap | 47 GiB / 16 GiB（`memory=48GB`、`swap=16GB`） |
| 根文件系统 | `/dev/sdd` 上的 ext4；`rw,relatime,discard,errors=remount-ro` |
| 构建用户 | WSL 内 root（无需桌面用户） |
| JDK | 默认 **21.0.12.1**（`openjdk-21-jdk-headless`），另装 17.0.20.1；用 `update-alternatives --set java /usr/lib/jvm/java-17-openjdk-amd64/bin/java`（以及 `javac`）切换 |
| repo 启动器 | `/root/bin/repo` launcher **v2.71**；离线 repo 源码在 `/opt/aera-repo-src`（`REPO_URL=/opt/aera-repo-src`） |

### 1.1 依赖基线

依赖按 AOSP Ubuntu 24.04 清单核查并补齐到 `dpkg` 697 → 853 个包。该轮安装的 25 个直接包：

`cpio`、`device-tree-compiler`、`python3-venv`、`zstd`、`pigz`、`diffstat`、`jq`、`ninja-build`、`cmake`、`p7zip-full`、`android-sdk-libsparse-utils`、`android-sdk-platform-tools`、`dosfstools`、`f2fs-tools`、`libelf-dev`、`dwarves`（pahole）、`libncurses-dev`、`libncurses6`、`libxml2-dev`、`libbz2-dev`、`libreadline-dev`、`libwxgtk3.2-dev`、`libsdl1.2-dev`、`moreutils`、`openjdk-21-jdk-headless`。

`mkbootimg` / `avbtool` **有意不**系统级安装：AOSP 会从源码树构建（`system/tools/mkbootimg`、`external/avb`），本设备树也自带 `prebuilts/` 副本。

### 1.2 网络 / 镜像

| 目标 | 状态 | 说明 |
|---|---|---|
| AOSP（USTC 镜像） | 可达（约 0.1 s） | `~/.gitconfig` 把 `https://android.googlesource.com/` 改写为 `https://mirrors.ustc.edu.cn/aosp/` |
| LineageOS Gerrit | 经 TUNA 镜像 | `https://review.lineageos.org/` → `https://mirrors.tuna.tsinghua.edu.cn/git/lineageOS/` |
| Gerrit LFS | 直连 | LFS blob 必须直连 Gerrit；镜像改写对 LFS 有意移除 |
| `github.com` git 协议 | 可达 | 用于 donor 树 |
| `gitlab.com` | **不可达** | 只有复用 OrangeFox 时代源码树时才涉及 |
| `raw.githubusercontent.com` | 不可达 | 本构建不需要 |

## 2. 源码树

```bash
repo init -u https://github.com/LineageOS/android -b lineage-24.0 \
  --git-lfs --no-repo-verify --repo-rev main --depth=1
repo sync
```

- 源码树位置：`/root/los24`。
- 最终体积：`.repo` 70 GB，工作树总计 105 GB。
- sync 后缺失：3 个 darwin 主机 prebuilts（disabled group；Linux 构建无关）。
- 四个架构的 WebView prebuilt LFS 件均在位（260/98/157/359 MB）。
- 同步经验：浅拉 `--depth=1` 只对「全新」project 生效；需要重置部分已拉取的 project，最终全树以 `-j3` 成功（更高并发时 USTC 对约 550 个 project 返回 HTTP 429）。

## 3. 设备树配置（关键值）

本仓库设备树放置于 `device/lenovo/TB323FU`。下列值对构建有实质影响：

| 配置项 | 值 | 理由 |
|---|---|---|
| `TARGET_BOARD_PLATFORM` / `TARGET_BOOTLOADER_BOARD_NAME` | `canoe` | 设备 `ro.board.platform=canoe` |
| `TARGET_ARCH` / `TARGET_ARCH_VARIANT` | `arm64` / `armv8-2a-dotprod` | 仅 64 位 SoC（`arm64-v8a`，32 位 ABI 列表为空） |
| `TARGET_CPU_VARIANT_RUNTIME` | `oryon` | `ro.bionic.cpu_variant=oryon` |
| `TARGET_KERNEL_VERSION` | `6.12` | 原厂内核 `6.12.69-android16-6`；本树不编内核但 `kernel.mk` 仍做版本比较 |
| `TARGET_PREBUILT_KERNEL` | `device/lenovo/TB323FU/prebuilt/Image` | 从 `boot_b.img` 抽出的原厂内核；SHA-256 `bb251454…`；**仅**用于 VINTF 内核版本检查 |
| `BOARD_SYSTEMIMAGE_PARTITION_SIZE` | `10235101184` | 原厂 `system` extent 长度 |
| `BOARD_SYSTEM_EXTIMAGE_PARTITION_SIZE` | `562970624` | 原厂 `system_ext` 长度 |
| `BOARD_PRODUCTIMAGE_PARTITION_SIZE` | `2167775232` | 原厂 `product` 长度 |
| `BOARD_SUPER_PARTITION_SIZE` | `21474836480` | 原厂 `super`（20 GiB） |
| `BOARD_QTI_DYNAMIC_PARTITIONS_SIZE` | `21470642176` | LP 组上限 |
| `BOARD_SUPER_PARTITION_GROUPS` | `qti_dynamic_partitions` | 组名**不带**槽位后缀 |
| `BOARD_*IMAGE_FILE_SYSTEM_TYPE` | `ext4`（system、system_ext、product、vendor、odm、vendor_dlkm、system_dlkm） | 原厂 fstab 七个逻辑分区全声明 ext4；magic 实测一致 |
| `TARGET_COPY_OUT_SYSTEM` / `_SYSTEM_EXT` / `_PRODUCT` | `system` / `system_ext` / `product` | full-userspace 布局 |
| `BOARD_AVB_ENABLE` | `true` | AVB v2 |
| `BOARD_AVB_ALGORITHM` | `SHA256_RSA4096` | 设备接受 AOSP testkey 作为信任根 |
| `BOARD_AVB_KEY_PATH` | `external/avb/test/data/testkey_rsa4096.pem` | AOSP testkey（公钥 sha1 `2597c218…`） |
| `BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS` | `--flags 0` | chained vbmeta 必须 flags 0 |
| `BOARD_AVB_VBMETA_SYSTEM` | `system system_ext product` | 一个 `vbmeta_system` 统一签三个分区 |
| `BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX` / `_LOCATION` | `1788566400` / `2` | 原厂值；不得降低 |
| `TARGET_SCREEN_DENSITY` | `440` | `ro.sf.lcd_density=440` |
| `TARGET_FS_CONFIG_GEN` | `device/lenovo/TB323FU/config.fs` | init/soong 需要 17 个高通 vendor AID（GID 2901–2917） |
| `PRODUCT_SHIPPING_API_LEVEL` | `37` | LOS24 `cp2a` = SDK 37 / board API 202604；`COMMON_LUNCH_CHOICES` 由 `bp2a` 改为 `cp2a` |
| `TARGET_COPY_OUT_VENDOR` + `BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE` | `vendor` + `ext4` | 2026-11-09 起 full-userspace 构建；这也是下文 `/vendor` 符号链接问题的由来 |

完整文件：`BoardConfig.mk`、`device.mk`、`lineage_TB323FU.mk`、`AndroidProducts.mk`、`config.fs`。

## 4. Lunch 与构建命令

```bash
cd /root/los24
export REPO_URL=/opt/aera-repo-src
export PATH=/root/bin:$PATH
export USE_CCACHE=false
export ALLOW_MISSING_DEPENDENCIES=true
export LC_ALL=C
source build/envsetup.sh
lunch lineage_TB323FU-cp2a-userdebug
mka systemimage out/target/product/TB323FU/vbmeta_system.img
```

以下注意点均在本树实测：

1. **`system` 与 `vbmeta_system` 必须在同一条 `mka` 中产出。** 第二次 `mka` 的刷新可能重建 `system`/`system_ext`/`product` staging 并改变 AVB root digest，从而在无提示的情况下破坏与旧 `vbmeta_system` 的配对。
2. `mka vbmeta_systemimage`（phony target）在本树**不存在**：`Schedule Failure: unknown target "vbmeta_systemimage"`。请使用上面的文件路径目标。
3. Android 17 / LOS24 中 `system_ext` 的 make 目标去掉了下划线：用 `systemextimage`，不要用 `system_extimage`。2026-11-07 使用的四件命令为：
   ```bash
   mka systemimage systemextimage productimage vbmetasystemimage -j12
   ```
   （该次 `vbmetasystemimage` 在同一条调用中可用；但重建场景以文件路径形式为准。）
4. `ALLOW_MISSING_DEPENDENCIES=true` 必须在 `source build/envsetup.sh` **之前**设置；首次带该环境的构建会触发一次性 Soong 全量 re-analysis（4 分 16.94 秒）。之后保持环境不变，否则每次构建都要付这笔开销。
5. `lunch` 身份核对：

   | 变量 | 值 |
   |---|---|
   | `PLATFORM_VERSION` | 17 |
   | `LINEAGE_VERSION` | `24.0-20261106-UNOFFICIAL-TB323FU` |
   | `TARGET_PRODUCT` | `lineage_TB323FU` |
   | `TARGET_BUILD_VARIANT` | `userdebug` |
   | `BUILD_ID` | `CP2A.260605.016` |
   | `WITH_GMS` | false |

## 5. 构建树 `/vendor` 符号链接根治（「卡第一屏」的构建侧缺陷）

**现象。** 产出的 `system.img` 根目录存在自指符号链接环：`/vendor → /system/vendor`，而 `/system/vendor → /vendor`。first-stage 挂载时 `fs_mgr_create_canonical_mount_point()` 对挂载点调用 `realpath()`，命中 `ELOOP`，`DoFirstStageMount()` 返回 false，`first_stage_init` 打出 `LOG(FATAL)` —— 设备永远到不了第二阶段。

**机制（源码级，AOSP + 设备树配置）。**

1. full-userspace（`BOARD_USES_VENDORIMAGE=true`）下，`system/core/rootdir/create_root_structure.mk` 本应创建**目录** `root/vendor`（第 54–55 行：`mkdir -p $(TARGET_ROOT_OUT)/vendor`）。
2. 旧的 2026-11-07 `out/` 是在 `TARGET_COPY_OUT_VENDOR` 仍为 legacy `system/vendor` 时构建的，其中含有 `root/vendor -> /system/vendor`。2026-11-09 切到 full-userspace 后，该符号链接变成 stale 残留。
3. root 结构重建只发生在 `init.environ.rc` 的 `LOCAL_POST_INSTALL_CMD` 里；若 `out/.../root/init.environ.rc` 已存在且比依赖新，ninja 不会重跑该规则。即使重跑，`mkdir -p …/vendor` 面对悬空符号链接也会失败，但整条命令用 `;` 串联、最后一条 `ln -sf` 返回 0 → make 认为成功，坏链接保留。
4. `build_image.py` 把 `out/.../root` 拷入镜像根（`shutil.copytree(root_dir)`），坏符号链接随之进入 `system.img`。

**实际采用的修复（2026-11-11，不改源码/设备树，不做 `make clean`）：**

```bash
cd /root/los24
P=out/target/product/TB323FU

# 0) 保留坏 staging 的证据
mkdir -p /root/buildfix/bak
cp -a $P/root/vendor /root/buildfix/bak/root-vendor.symlink
stat $P/root/vendor > /root/buildfix/bak/root-vendor.before.txt
readlink $P/root/vendor >> /root/buildfix/bak/root-vendor.before.txt
sha256sum $P/system.img > /root/buildfix/bak/old-system-img.sha256

# 1) 先删除 stale 符号链接
rm -f $P/root/vendor

# 2) 强制 root 结构 post-install 重跑（删除被跟踪的载体文件）
rm -f $P/root/init.environ.rc

# 3) 增量重建（不要 clean out/）
source build/envsetup.sh
export ALLOW_MISSING_DEPENDENCIES=true
export LC_ALL=C
lunch lineage_TB323FU-cp2a-userdebug
mka systemimage 2>&1 | tee /root/buildfix/build-$(date +%Y%m%d-%H%M%S).log

# 4) staging 断言
test -d $P/root/vendor && echo "OK: root/vendor is a directory"
```

**重建后的证据：**

- staging：`root/vendor` = 目录 0755，mtime 2026-11-11 21:40:19（修复前：`lrwxrwxrwx … root/vendor -> /system/vendor`，mtime 2026-11-07 12:36:52）。
- 最终镜像（`debugfs -R "stat /vendor" new-system.img`）：`Type: directory Mode: 0755 User: 0 Group: 2000`，xattr `security.selinux = "u:object_r:vendor_file:s0"`。
- `/system/vendor` 仍是指向 `/vendor` 的符号链接；`/vendor` 本身是空的挂载点目录。
- `e2fsck -fn` 干净：`2900/615296 files (0.7% non-contiguous), 254287/2459354 blocks`。
- AVB root digest 按预期变化：`37cc913b3c2dc6813b454abaea1b347db0779665b256a88d1fa8ef5621af1553`（旧）→ `ba9495595acfaab2a99c9da6acd6fee65b8ab5b7d73b5afc57f126bb5e52046f`（最终）。
- `/dataext` 仍不在镜像中（见 §7）。

**复发预防。** 该修复只在 `root/init.environ.rc` 不被单独回滚时成立。复发场景：（1）从 2026-11-07 之前的 `out/.../root/` 快照恢复；（2）源码树在 legacy 与 full-userspace 之间再次切换；（3）脚本向 `root/` 手工塞符号链接而未强制重装 `init.environ.rc`。建议的 wrapper 加固：

```bash
# 构建前自愈
if [ -L out/target/product/TB323FU/root/vendor ]; then
  rm -f out/target/product/TB323FU/root/vendor
  rm -f out/target/product/TB323FU/root/init.environ.rc
fi
# 构建后断言
test -d out/target/product/TB323FU/root/vendor || { echo "FATAL: root/vendor not dir"; exit 1; }
```

## 6. 修复批次的最终产物（2026-11-11 21:49–21:50）

| 产物 | 大小（B） | SHA-256 | AVB root digest |
|---|---|---|---|
| `out/target/product/TB323FU/system.img`（sparse） | 1,043,829,244 | `331acc2b17cfc421cbabd61eb1d7933b1f9d88c2d2c7a81571da9568d6922db2` | `ba9495595acfaab2a99c9da6acd6fee65b8ab5b7d73b5afc57f126bb5e52046f` |
| `system_ext.img`（sparse） | 465,404,172 | `d86e4b4d358dd940cfdea19f2fa06c29fb9f92de389c04bc2d344e6b0b149e35` | `b687aa29a164de7cd699aece4c4a64b84f577f06dba431b71fd9658a3d8d569c` |
| `product.img`（sparse） | 533,258,592 | `1e9ac21f3b21e046724633d006768c2d7705aa5cad22fe6bdbeac52df1c6a658` | `34610c0793381e170016db9fa01323397ffbdee48dfddbde52f6ef63ed490741` |
| `vbmeta_system.img` | 65,536 | `b8fa5f4dbfd6f69b75aa2f9f8dece8cd40a60c0545aff35fa78352b5ea94b946` | `SHA256_RSA4096`，公钥 sha1 `2597c218aae470a130f61162feaae70afd97f011`，rollback index `1788566400`，flags 0 |
| `super` 拼包 raw：`new-system.img` | 10,235,101,184 | `f716cfe5c7f5827b12b64bdf7dc782a20d7ad9b4622e40381f39b2124a2e0b7f` | 与 `BOARD_SYSTEMIMAGE_PARTITION_SIZE` 精确相等 |
| raw `new-system_ext.img` | 562,970,624 | `af79baa59f367b4c788c1d9f4bf976e6ff94aa04459518bac6e92313a6998c51` | 与 board 尺寸一致 |
| raw `new-product.img` | 2,167,775,232 | `38af4ee21e5c8c4cf49e18a499d61bc70e0ab1f5ef4525f2b877eeeff3034a82` | 与 board 尺寸一致 |

`vbmeta_system.img` 内嵌的 hashtree descriptor 与上述三个镜像逐一相等（`system ba949559…`、`system_ext b687aa29…`、`product 34610c07…`），已用 `avbtool info_image` 核对——AVB 链自洽。

更早批次（2026-11-07）产物，供历史参考：`system c7caea7d…`、`system_ext 488c5815…`、`product 3c732a7c…`、`vbmeta_system 37f16224…`。

## 7. 已知缺口：`/dataext`

原厂 system-as-root 镜像有 `/dataext` 目录；LineageOS 镜像没有（`debugfs -R "stat /dataext"` → File not found）。它**不是**卡第一屏的原因，且最小修复集中有意排除。正确的后续补法：

```make
# device/lenovo/TB323FU/BoardConfig.mk，放在 full-userspace 段附近
BOARD_ROOT_EXTRA_FOLDERS += dataext
```

再补一条 SELinux `file_contexts` 映射（当前树内 sepolicy 没有 `dataext` 标签；AOSP 机制是 `create_root_structure.mk:29-31` 的 `mkdir -p … $(BOARD_ROOT_EXTRA_FOLDERS)`）。没有 context 时新目录可能落到 `rootfs` 或构建失败；建议单独一轮处理，并用 `debugfs -R "stat /dataext"` 验证。

影响：first-stage init 来自原厂 `vendor_boot` ramdisk；若其 init 对 `/dataext` 有 `mkdir` 兜底，缺该目录不会阻塞启动——只影响依赖该挂载点的服务。这正是本次验收未受阻的原因。

## 8. 把新镜像接入 `super` 拼包

`vbmeta_system` 在 LUN0 上是**物理**分区（不在 `super` 内）；`system`/`system_ext`/`product` 是 `super` 内的 LP region。项目工具 `superkit.py`（regions / audit / build / compare 子命令）只修补这三个 region：

```bash
cd <WORKSPACE>/_tmp/super    # 项目工作区的 WSL 视图

# (a) 从原厂 lpdump 生成 region 映射（已有 regions.json 可跳过）
python3 superkit.py regions --lpdump lpdump_stock_all.txt --size 21474836480 --out regions.json

# (b) 用本批 raw 覆盖 base super 的三个 region
python3 superkit.py build \
  --src  <base_super.img> \
  --dst  /root/buildfix/super_systemfix-20261111.img \
  --regions regions.json \
  --patch system=/root/buildfix/new-system.img,system_ext=/root/buildfix/new-system_ext.img,product=/root/buildfix/new-product.img \
  --out  /root/buildfix/super-build-20261111.json

# (c) 审计：只有 system/system_ext/product 三个 region 的 SHA 变化；LP 元数据不动
python3 superkit.py audit --file /root/buildfix/super_systemfix-20261111.img \
  --regions regions.json --out /root/buildfix/super-audit-20261111.json --lp
python3 superkit.py compare --a <base_audit.json> --b /root/buildfix/super-audit-20261111.json \
  --out /root/buildfix/super-compare-20261111.json
```

预期：`compare` 中只有 `system`、`system_ext`、`product` 变化；`audit --lp` 的前 64 KiB SHA-256 保持原厂值 `fc0163625355ffd46479d9a6c671187a3879954d43cb3c2cf46407dc3b68c573`。

**配对铁律（硬约束）：**

- `vbmeta_system` 必须与同批次的 `system` + `system_ext` + `product` 一起构建/刷写；混批会破坏 dm-verity。
- 离线修补路线产出的 `system` root digest 不同，其 `vbmeta_system` **不可**与构建头产出的那套互换。
- `fastboot flash super` 拒绝 sparse 镜像：拼包一律产出 raw `super`。
- 每次都要重新用 `simg2img` 抽 raw、重新记录 `avbtool info_image` 的 root digest，并重新核对 `vbmeta_system` 的 descriptor 之后才允许拼包。

## 9. 已知构建失败与修复

| 报错 / 现象 | 根因 | 修复 |
|---|---|---|
| `prebuilt_libbundleaidl`（vendor/lenovo/TB323FU/Android.bp:32469）依赖 `android.media.audio.common.types` **V4 与 V5 两个版本** | 早前把一个 3 GB 的 A16 时代 vendor blobs 树放进 `/root/los24/vendor/lenovo/TB323FU`；Soong 全树扫描，其 4800 个 prebuilt 模块引用旧 AIDL V4 | 删除该 vendor blobs 树（最小内容设计不编 vendor blobs；`device.mk` 里的 `inherit` 已注释） |
| `ninja: unknown target "system_extimage"` | Android 17 改名（去掉下划线） | 用 `systemextimage`；`mka systemimage systemextimage productimage vbmetasystemimage` |
| `vendor/lineage/build/tasks/kernel.mk:122: error: Argument missing.` | 无内核源码，`TARGET_KERNEL_VERSION` 退化为 `.` | 设 `TARGET_KERNEL_VERSION := 6.12`（只写「主版本.次版本」；`kernel.mk:123` 会与 6.1 比较） |
| `ninja: 'out/target/product/TB323FU/kernel' … missing and no known rule to make it` | `TARGET_PREBUILT_KERNEL` 为空 → `NEEDS_KERNEL_COPY` 为 false → kernel 桩无生成规则 | 把 `TARGET_PREBUILT_KERNEL` 指向 `device/lenovo/TB323FU/prebuilt/Image`（原厂内核，42,097,152 B，SHA-256 `bb251454…`） |
| 构建被 exit 143 终止（`Got signal: terminated`） | 同一个 WSL 实例内有第二个（recovery）构建并行 | 串行化构建，或降低 job 数并对构建 `nice` |
| 构建被 exit 137 终止（`Killed`） | `-j16/-j18` 且另一构建并行时，47 GiB 内存耗尽 | 降低 job 数（`-j8` 成功）；最终完整构建在先前 `-j12/-j18/-j16` 尝试后以 `-j8` 完成 |
| 首次带 `ALLOW_MISSING_DEPENDENCIES=true` 的构建多花 4 分 17 秒 | Soong 全量 re-analysis，一次性开销 | 保持环境稳定跨构建复用 |
| LOS `system` + 原厂 `product`/`system_ext` 时运行期 `secilc` 失败 `rc=254`（`system_ext_sepolicy.cil:2` 的 `Failed to resolve typeattributeset`） | 原厂 `product`/`system_ext` 策略引用了 LOS 平台策略中不存在的 OEM 独有 type | 同时刷入 LOS `product` 与 `system_ext`，运行期 secilc 编译 `rc=0`（host 端复现，`-c 30/31/32/33` 全部通过）。详见 `08-SELINUX-POLICY.md` |

## 10. 构建耗时参考

| 构建轮次 | 结果 |
|---|---|
| 2026-11-07 首次完整构建 | 04:40:21 开始，12:59:05 `build completed successfully (57:52)`，`BUILD_EXIT=0`；四件产物 + `avbtool verify_image rc=0` |
| 2026-11-11 root-fix `mka systemimage` | 共 9 分 18 秒 = Soong re-analysis 4 分 16.94 秒（一次性）+ kati + ninja `1m52.06s`；`build completed successfully (09:18)` |
| 2026-11-11 第二次 `mka`（重建 `vbmeta_system` + 三个镜像） | 5 分 40 秒 |
| 环境稳定后的常规增量构建 | 约 5 分钟 |

## 11. 验证命令（刷写前必跑）

```bash
# 从 sparse 抽 raw
simg2img out/target/product/TB323FU/system.img /root/buildfix/new-system.img

# 文件系统检查
e2fsck -fn /root/buildfix/new-system.img

# 挂载点断言
debugfs -R "stat /vendor" /root/buildfix/new-system.img
debugfs -R "stat /system/vendor" /root/buildfix/new-system.img
debugfs -R "stat /dataext" /root/buildfix/new-system.img

# AVB 身份
out/host/linux-x86/bin/avbtool info_image --image out/target/product/TB323FU/system.img | grep "Root Digest"
out/host/linux-x86/bin/avbtool verify_image --image out/target/product/TB323FU/vbmeta_system.img \
  --key external/avb/test/data/testkey_rsa4096.pem

# 配对：列出的 root digest 必须等于三个镜像各自的 root digest
out/host/linux-x86/bin/avbtool info_image --image out/target/product/TB323FU/vbmeta_system.img

# 哈希
sha256sum out/target/product/TB323FU/system.img out/target/product/TB323FU/system_ext.img \
  out/target/product/TB323FU/product.img out/target/product/TB323FU/vbmeta_system.img
```

## 12. 证据来源

| 主题 | 证据 |
|---|---|
| 主机/依赖/JDK/repo/网络 | `<PROJECT_ROOT>/tmp/aera-recovery/ENV.md`（§1–§3） |
| 源码树 / lunch / 构建时间线 / 失败记录 | `<WORKSPACE>/research/a17-rom-survey/BUILD-LOG.md` |
| `/vendor` 符号链接根治、产物表、`/dataext` | `out/2026-11-11-los24-bootfix/BUILD-FIX-REPORT.md`、`BUILD-FIX-MANIFEST.json` |
| BoardConfig 取值 | 设备树 `BoardConfig.mk` |
| 运行期 `secilc` 失败分析 | `out/2026-11-11-los24-bootfix/SELINUX-COMPILE-ANALYSIS.md` |
| super 拼包工具 | `_tmp/super/superkit.py` + `regions.json` + `lpdump_stock_all.txt` |
