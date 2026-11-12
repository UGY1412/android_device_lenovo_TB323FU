#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#
# TB323FU — Lenovo Legion Y700 Gen 5 (SM8850 / kaanapali / canoe)
# ============================================================================
# 设计意图（改任何一行之前先读这段）
# ============================================================================
# 本设备树是【最小内容替换】形态，**只编译三个分区**：
#       system / system_ext / product
#
# 以下全部保持联想原厂件，既不编译也不刷写：
#   * 硬件层：vendor / odm / vendor_dlkm / system_dlkm
#   * 内核与启动链：boot / init_boot / vendor_boot / dtbo / recovery
#   * fstab（它住在原厂 vendor_boot 的 ramdisk 里，我们不碰）
#
# 为什么这样做（依据见仓库 REBOOT-REPORT.md）：
#   * 厂商硬件抽象层与内核模块【不能】跨机型/跨代复用 —— 它们的 ABI 绑死内核与板级；
#   * 而 userland（system 侧）可以换 —— 这正是"只刷 GSI 就能进系统"证明过的那件事；
#   * 本机内核是 6.12.69-android16-6，而盘上那份 A16 QPST 包的内核是 android16-5
#     ⇒ vendor_dlkm 的 .ko 与设备内核 vermagic 不匹配，**只能继续用设备自己的**。
#
# 随之而来的三条硬约束：
#   1) root vbmeta（`vbmeta`）**不是编译产物**：
#      它由工具从原厂件改写而来 —— chain(boot)/chain(recovery) 与 vendor 侧 hashtree
#      保持原厂，只有 chain(vbmeta_system) 指向我们的 testkey。
#      （见 out/2026-10-15-testkey-vbmeta/ 与 tmp/recon/mk_testkey_vbmeta.py）
#   2) `vbmeta_system` 是编译产物，用 AOSP testkey 签（本机 ABL 信任它）。
#   3) super **不重建**，只把三个逻辑分区刷进现有 super（fastbootd 会按需 resize）。
# ============================================================================

# Architecture
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-2a-dotprod
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := oryon
TARGET_2ND_ARCH :=
# TARGET_USES_64_BIT_BINDER 已废弃 —— lunch 实测 warning 原文：
#   "TARGET_USES_64_BIT_BINDER has been deprecated. All devices use 64-bit binder
#    by default now. Uses of TARGET_USES_64_BIT_BINDER should be removed."
# ⇒ 不设（保持全树零 warning）。
TARGET_SUPPORTS_64_BIT_APPS := true

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
# 密度 440：取自 props-lenovo-system/build.prop 的 `ro.sf.lcd_density=440`
#           （vendor 侧 `vendor.display.lcd_density=440` 一致）。
#
# ⚠️ 为什么放在 BoardConfig 而不是 device.mk：
#     消费者在 **BoardConfig 阶段**就会被读到 —— 实测本机 AOSP 树里
#     `build/make/core/sysprop_config.mk:131-133`（生成 `ro.sf.lcd_density`）、
#     `Makefile:2520-2523`（recovery density）、`soong_config.mk:547`、
#     `soong_extra_config.mk:84` 都在用；同厂商参考树也把它放在 BoardConfig.mk。
#     （来源：子代理 A 的对照报告 §5.3 缺口 5）
#
# 注意：TARGET_SCREEN_HEIGHT/WIDTH 不在这里 —— 它们的消费者在 product 层
#      （`vendor/lineage/config/common.mk` 用 `?=` 只在未设时给 1080×1920 默认），
#      必须先于它赋值才有效，所以留在 device.mk 是对的，两边别对调。
TARGET_SCREEN_DENSITY := 440

# Platform  (实测：ro.board.platform=canoe / ro.vendor.board.family=f-*)
BOARD_USES_QCOM_HARDWARE := true
TARGET_BOARD_PLATFORM := canoe
TARGET_BOOTLOADER_BOARD_NAME := canoe

# ---------------------------------------------------------------------------
# ★（不编内核，但要显式声明内核版本）
# ---------------------------------------------------------------------------
# 本设备树**不编译内核** —— 使用原厂 prebuilt 内核（boot/init_boot/vendor_boot/dtbo
# 全部保持原厂件，我们只换 system/system_ext/product）。
#
# 但 LOS 的内核任务文件 `vendor/lineage/build/tasks/kernel.mk` 仍会被
# `build/make/core/Makefile:8024` 无条件 include，其中第 122-124 行会做版本比较：
#     ifeq ($(call is-version-greater-or-equal,$(TARGET_KERNEL_VERSION),5.15),true)
# 而 `TARGET_KERNEL_VERSION` 的默认推导（`vendor/lineage/config/BoardConfigKernel.mk:77-79`）
# 是从 **内核源码的顶层 Makefile** 里 grep `^VERSION =` / `^PATCHLEVEL =`：
#     TARGET_KERNEL_VERSION ?= $(shell echo $(KERNEL_VERSION)"."$(KERNEL_PATCHLEVEL))
# 我们不提供源码 ⇒ `TARGET_KERNEL_SOURCE`（默认 `kernel/lenovo/TB323FU`）不存在 ⇒
# grep 无输出 ⇒ 该值退化成单个 "." ⇒ 版本比较函数直接报
#     `vendor/lineage/build/tasks/kernel.mk:122: error: Argument missing.`
# （2026-10-14 实测踩到，卡了整整一轮编译）
#
# ⇒ 按官方指引覆盖。依据就在 `BoardConfigKernel.mk:39` 的注释里：
#     "TARGET_KERNEL_VERSION = ... Can be overriden in device trees
#      in the event of prebuilt kernel."
# 取值来源：设备实测内核 `6.12.69-android16-6` ⇒ 主版本 6.12。
# ⚠️ 只写 "主版本.次版本"（不写第三段），因为 `kernel.mk:123` 会拿它跟 6.1 比大小。
TARGET_KERNEL_VERSION := 6.12

# `kernel.mk:141-145` 是个二选一检查：
#     ifeq ($(TARGET_PREBUILT_KERNEL),)
#         ifeq ($(BOARD_KERNEL_IMAGE_NAME),)
#             $(error BOARD_KERNEL_IMAGE_NAME not defined.)
# 第 9 轮时我们既不提供内核源码、也不提供 prebuilt 内核文件（启动链全部用原厂件），
# 所以给后者；第 10 轮起改为同时给出 TARGET_PREBUILT_KERNEL（见下方新增段），
# 因为 ninja 需要 $(PRODUCT_OUT)/kernel 这个文件才能跑 VINTF 内核检查。它的唯一用途是拼一个"内部内核产物路径"
# （`TARGET_PREBUILT_INT_KERNEL := $(KERNEL_OUT)/arch/$(KERNEL_ARCH)/boot/$(BOARD_KERNEL_IMAGE_NAME)`），
# 而那条路径在本路线里永远不会被构建或读取 —— 给值即可，不产生任何产物。
# 取值 "Image" 与原厂（arm64 未压缩内核）一致。
BOARD_KERNEL_IMAGE_NAME := Image

# ---------------------------------------------------------------------------
# ★ 第 10 轮（2026-10-14）：补 TARGET_PREBUILT_KERNEL —— 本单唯一变量
# ---------------------------------------------------------------------------
# 第 9 轮已越过 kernel.mk 的 $(error)，但 ninja 停在：
#     FAILED: ninja: 'out/target/product/TB323FU/kernel', needed by
#     'out/target/product/TB323FU/obj/PACKAGING/check_vintf_all_intermediates/kernel_version.txt',
#     missing and no known rule to make it
# 静态定位（证据：out/2026-10-15-lineage10/static-locate-0{1,2,3}.txt）：
#   1) build/make/core/Makefile:987-989 —— 未设 TARGET_NO_KERNEL / BOARD_KERNEL_BINARIES 时
#      INSTALLED_KERNEL_TARGET := $(PRODUCT_OUT)/kernel；
#   2) build/make/core/product_config.mk:512-515 —— 未显式设置时默认把
#      PRODUCT_OTA_ENFORCE_VINTF_KERNEL_REQUIREMENTS 置为 true ⇒ Makefile:5382 块生效 ⇒
#      Makefile:5414-5420 的 kernel_version.txt / kernel_configs.txt 依赖 $(PRODUCT_OUT)/kernel；
#   3) 该 kernel 文件的生成规则在 vendor/lineage/build/tasks/kernel.mk:735
#      （$(INSTALLED_KERNEL_TARGET): $(KERNEL_BIN)，命令为 $(transform-prebuilt-to-target)），
#      整段被 ifeq ($(NEEDS_KERNEL_COPY),true) 包住；第 9 轮实际走的分支 kernel.mk:175-186
#      只置了 HAS_PREBUILT_KERNEL，并把 KERNEL_BIN 赋成 $(TARGET_PREBUILT_KERNEL) ——
#      而该变量为空 ⇒ 规则退化为"无命令目标" ⇒ ninja 认作 no known rule。
# ⇒ 给出 TARGET_PREBUILT_KERNEL 后，kernel.mk:149-151 会置 NEEDS_KERNEL_COPY := true，
#   copy 规则成立，$(PRODUCT_OUT)/kernel 才会真被产出。
#
# 取值 = 设备自己的原厂内核（**不用** AOSP GKI prebuilt，避免版本串与本机 KMI 不符）：
#   refs/readback-full/boot_b.img（2026-10-06 全量回读）
#     → system/tools/mkbootimg/unpack_bootimg.py → kernel（42,097,152 B）
#     → 本目录 prebuilt/Image（SHA-256 bb251454c689ad55ab4fad6580ffffc6eb47f8ca6414e70b617b4d95c3bec69c）
#   版本串（extract_kernel.py --output-release）：6.12.69-android16-6-gb133545a642b-ab15507861-4k
# 该文件只服务于编译期 VINTF 内核兼容性检查，不进任何刷写件（启动链仍是全原厂件）。
TARGET_PREBUILT_KERNEL := device/lenovo/TB323FU/prebuilt/Image

# A/B
AB_OTA_UPDATER := true
AB_OTA_PARTITIONS += \
    product \
    system \
    system_ext \
    vbmeta_system

# ---------------------------------------------------------------------------
# Partitions — 尺寸全部取自【本机全盘回读的 super slot 1（_b）】实测值，
#              不是从别的机型抄的。
# ---------------------------------------------------------------------------
BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := ext4

BOARD_SYSTEMIMAGE_PARTITION_SIZE := 10235101184
BOARD_SYSTEM_EXTIMAGE_PARTITION_SIZE := 562970624
BOARD_PRODUCTIMAGE_PARTITION_SIZE := 2167775232

TARGET_COPY_OUT_SYSTEM := system
TARGET_COPY_OUT_SYSTEM_EXT := system_ext
TARGET_COPY_OUT_PRODUCT := product

BOARD_SUPER_PARTITION_SIZE := 21474836480

# 动态分区：声明组名与上限，用于编译期尺寸校验。
#
# ⚠️ 组名**不带槽位后缀**。AOSP 会把这里的每个组名 to-upper 后当作变量前缀用
#    （即 `BOARD_QTI_DYNAMIC_PARTITIONS_PARTITION_LIST` / `_SIZE`），
#    若写成 `qti_dynamic_partitions_b`，构建系统就会去找
#    `BOARD_QTI_DYNAMIC_PARTITIONS_B_PARTITION_LIST` —— 不存在 ⇒ 组配置读成空。
#    槽位后缀（`_a`/`_b`）由构建系统按 A/B 自动生成。
#    依据：LineageOS 官方同平台树 `android_device_oneplus_sm8850-common` 的
#    `BoardConfigCommon.mk` 就是这么写的（不带后缀，用下划线组名）。
#    旁证：设备侧实测 super 的 LP 元数据里同时存在 `qti_dynamic_partitions_a` 与 `_b` 两组。
BOARD_SUPER_PARTITION_GROUPS := qti_dynamic_partitions
BOARD_QTI_DYNAMIC_PARTITIONS_PARTITION_LIST := system system_ext product vendor odm vendor_dlkm system_dlkm
BOARD_QTI_DYNAMIC_PARTITIONS_SIZE := 21470642176

BOARD_FLASH_BLOCK_SIZE := 262144
BOARD_USES_METADATA_PARTITION := true
BOARD_PRODUCTIMAGE_MINIMAL_PARTITION_RESERVED_SIZE := false

# 不编译的镜像：显式留空，避免构建系统去找它们
# （vendor / odm / vendor_dlkm / system_dlkm / boot / dtbo / recovery 全部用原厂件）

# ---------------------------------------------------------------------------
# Verified Boot — AOSP testkey，flags 必须为 0
# ---------------------------------------------------------------------------
# 本机 ABL 信任 AOSP testkey 作为 AVB root of trust（实证见 REBOOT-REPORT §1.4 N7：
# 社区"唯一能开机"的包用的就是这把 key）。LineageOS 官方设备树同样直接用它。
#
# ⚠️ chained vbmeta 的 flags 必须为 0：libavb 的 avb_slot_verify.c 对
#    非主 vbmeta 且 flags != 0 的情况直接判 ERROR_INVALID_METADATA（不可恢复）。
BOARD_AVB_ENABLE := true
BOARD_AVB_ALGORITHM := SHA256_RSA4096
BOARD_AVB_KEY_PATH := external/avb/test/data/testkey_rsa4096.pem
BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 0

# ⚠️⚠️ 这里**故意不设** BOARD_AVB_{SYSTEM,SYSTEM_EXT,PRODUCT}_KEY_PATH / _ALGORITHM。
#   踩过的坑（2026-10-14，编译在 soong 分析阶段失败）：
#     `build/soong/fsgen/vbmeta_partitions.go:175-180` 的判定是
#         includeAsChainedPartitionInVbmeta(p) := p 存在于 PartitionQualifiedVariables
#                                              && len(BoardAvbKeyPath) > 0 && p != "recovery"
#     ⇒ 一旦给这三个分区设了 KEY_PATH，它们就会被当成**独立的 chained partition**，
#       进而由 `build/soong/filesystem/vbmeta.go:243` 检查各自的
#       `BOARD_AVB_<P>_ROLLBACK_INDEX_LOCATION` —— 而那个我们（正确地）没设
#       ⇒ 读出空字符串 ⇒ ParseInt 得 0 ⇒
#       `error: chained_partitions: rollback index location must be 1, 2, 3, ...`（重复 3 次）。
#   正确做法：这三个分区**由 vbmeta_system 统一签名**，不设各自的 KEY_PATH。
#   同一处源码注释写明：`--include_descriptors_from_image` 正是在
#   "`BOARD_AVB_<partition>_KEY_PATH` 未设" 时才传 —— 这正是我们要的路径。
#   对照范例：`device/google/cuttlefish/shared/BoardConfig.mk:198-208` 同样只设
#   VBMETA_SYSTEM 的 key，没有这三个分区的 key。

BOARD_AVB_VBMETA_SYSTEM := system system_ext product
BOARD_AVB_VBMETA_SYSTEM_KEY_PATH := external/avb/test/data/testkey_rsa4096.pem
BOARD_AVB_VBMETA_SYSTEM_ALGORITHM := SHA256_RSA4096
# ⚠️ 必须 >= 原厂 vbmeta_system 的 rollback index（实测 1788566400 = 2026-09-05），
#    否则可能触发降级保护。原厂 ri_location = 2（从 OEM vbmeta 的 chain descriptor 读出）。
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX := 1788566400
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION := 2

# ---------------------------------------------------------------------------
# 构建辅助
# ---------------------------------------------------------------------------
# 原厂 vendor 组（AID）声明（vendor_qti_diag 等 17 个，GID 2901~2917）。
# 两条用途：① soong 的 fs_config 用它给镜像内文件设 owner/group；
#          ② host_init_verifier 校验 init rc 的 group 名时需要它们有定义。
# 先例报错（2026-10-11，handoff/2026-10-11-编译攻坚实录.md 类 11）：
#     gnss-aidl-service-qti.rc: Unable to decode GID for 'vendor_qti_diag'
# ⚠️ 路径要写成 `device/lenovo/TB323FU/config.fs`：本文件里**没有**定义 DEVICE_PATH
#    （故意不定义 —— BoardConfig.mk 被 include 的时点早于它，写 $(DEVICE_PATH) 会展开成空）。
TARGET_FS_CONFIG_GEN += device/lenovo/TB323FU/config.fs

# ---------------------------------------------------------------------------
# 未决项（跑之前/之后要处理的）
# ---------------------------------------------------------------------------
# TODO(1) pvmfw：原厂 vbmeta_system 里带 `pvmfw` 的 hash descriptor，我们这份不含。
#        如果启动卡在 pVM 相关的地方，需要把原厂 pvmfw 的 descriptor 补进来。
# TODO(2) VINTF：本设备树暂不提供 framework compatibility matrix 片段；
#        原厂 device matrix 会有若干条要求无人认领 —— 按 AOSP 源码，boot 期这类
#        不匹配只 Slog.e，不阻塞启动（见 REBOOT-REPORT §4.1）。
# SEPolicy：重建 vendor/odm 时使用 Qualcomm 公共 vendor 策略（sm8850），
# 设备特化策略后续再补（目录暂空）。参考 OnePlus sm8850-common 做法。
include device/qcom/sepolicy_vndr/SEPolicy.mk
BOARD_VENDOR_SEPOLICY_DIRS += device/lenovo/TB323FU/sepolicy/vendor
BOARD_ODM_SEPOLICY_DIRS += device/lenovo/TB323FU/sepolicy/odm


# ============================================================================
# FULL USERSPACE BUILD（2026-11-09 起）：不再只编 system 侧。
# 依据：社区可开机移植包是"整套用户态一起换"；system-only 与 stock vendor 的
# 用户态接口不兼容（实证 E6S：ABL 放行、内核启动、早期 init 失败）。
# 启动链仍保持原厂 OEM 签名（boot/vendor_boot/dtbo/init_boot/recovery 不编译）。
# ============================================================================
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_VENDORIMAGE_PARTITION_SIZE := 2202816512
BOARD_ODMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_ODMIMAGE_PARTITION_SIZE := 334217216
BOARD_VENDOR_DLKMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_VENDOR_DLKMIMAGE_PARTITION_SIZE := 118259712
BOARD_SYSTEM_DLKMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_SYSTEM_DLKMIMAGE_PARTITION_SIZE := 14868480

TARGET_COPY_OUT_VENDOR := vendor
TARGET_COPY_OUT_ODM := odm
TARGET_COPY_OUT_VENDOR_DLKM := vendor_dlkm
TARGET_COPY_OUT_SYSTEM_DLKM := system_dlkm

# 分区列表（供 super 尺寸校验；我们仍自行构建/刷写 super）
BOARD_SUPER_PARTITION_SIZE := 21474836480
BOARD_QTI_DYNAMIC_PARTITIONS_SIZE := 21470642176


# vendor blobs（extract_utils 生成）
-include vendor/lenovo/TB323FU/BoardConfigVendor.mk

# 重建 vendor/odm 的 props（由原厂 build.prop 提取，排除 build 系统自动生成项）
TARGET_VENDOR_PROP := device/lenovo/TB323FU/configs/properties/vendor.prop
TARGET_ODM_PROP := device/lenovo/TB323FU/configs/properties/odm.prop
