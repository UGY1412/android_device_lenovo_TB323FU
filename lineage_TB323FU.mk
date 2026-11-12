#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#
# TB323FU — 产品定义（lunch 目标：lineage_TB323FU-bp2a-userdebug）
# ============================================================================
# 职责分工（照 LineageOS 官方同平台树的写法）：
#     lineage_TB323FU.mk  ← 本文件：产品定义。继承基础 product、设备配置、Lineage 公共配置，
#                                    并在此声明全部 PRODUCT_* 身份字段。
#     device.mk           ← 设备配置。只放本设备特有的东西（屏幕、overlay、额外包）。
#
# 混职责（例如在 device.mk 里 inherit 基础 product 并声明 PRODUCT_NAME）会让 PRODUCT_*
# 落在错误的继承层，是 "Don't have a product spec for: ..." 一类 lunch 失败的常见成因。
# ============================================================================

# Inherit from those products. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
# ★ 用 full_base_telephony.mk（**不是** full_base.mk）—— 两者继承链完全不同，不是同义：
#     full_base.mk           → generic_no_telephony.mk        （不含 telephony）
#     full_base_telephony.mk → aosp_base.mk + telephony.mk    （含 telephony）
#   三条依据：
#     ① 本机原厂 vendor **确实有完整 radio HAL 栈**（实测 tmp/donor-collect/
#        lenovo-vendor.vintf.tsv:80-87 = android.hardware.radio.{config,data,messaging,
#        modem,network,sap,sim,voice} 八项；:67-79 = vendor.qti.hardware.radio.* 十三项，
#        全部声明在 etc/vintf/manifest/qspa/qspa-modem.xml）；
#     ② 原厂 system 的 compatibility_matrix.202504.xml:147-156 同样要求这批接口（AIDL 3-4）；
#     ③ 2026-10-11 那棵编出 818MB system.img 的树用的就是它
#        （handoff/2026-10-11-2235-linux-reasonix.md §2）。
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)
# virtual_ab_ota/compression.mk **自身已经 inherit 了 launch_with_vendor_ramdisk.mk**
# （见该文件首行），并额外开启 virtual A/B 压缩：4 条 ro.virtual_ab.* 属性 +
# snapuserd / snapuserd.vendor_ramdisk / snapuserd.recovery 三个包。
# ⇒ 二选一，**不要两个都继承**（重复继承会重复叠加 PRODUCT_PACKAGES）。
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/compression.mk)

# Dalvik heap 参数 —— 参考树同平台树用 6144（sm8475-common/common.mk:20）。
#   选它的依据：本机 **12 GB RAM**（B 报告实测 cmdline `hqsysfs.pcba_hwid=SM8850P_12+256_11`），
#   而本机树共 10 个变体、其中最大就是 6144（无 8/12 GB 档）。
#   ⚠️ 路径陷阱：它们在 **frameworks/native/build/**，不在 build/make/target/product/。
#   不继承的后果：用 ART 默认堆参数 ⇒ 大应用易 GC 抖动/被系统杀，属"能用但体验差"。
$(call inherit-product, frameworks/native/build/phone-xhdpi-6144-dalvik-heap.mk)

# Inherit from the device configuration.
$(call inherit-product, device/lenovo/TB323FU/device.mk)

# FULL USERSPACE: vendor blobs（由 extract-files.py 生成）
$(call inherit-product-if-exists, vendor/lenovo/TB323FU/TB323FU-vendor.mk)

# Inherit some common Lineage stuff.
#
# 已核实（2026-10-15，实取 `vendor/lineage/config/` 清单）：
#   common_full_tablet.mk           → common_mobile_full.mk + tablet.mk + **telephony.mk**
#   common_full_tablet_wifionly.mk  → 同上但**不含** telephony
#   common_full_phone.mk / common_mobile.mk / common_mobile_full.mk / tablet.mk 也都存在
#
# **选 tablet（含 telephony）而非 wifionly**，依据如下 —— 本机信号是矛盾的：
#   * 指向 WiFi 版：`ro.product.board=baldur_prc_wifi`（带 wifi 字样）
#   * 指向带基带：本机 vendor 侧有**完整的 radio HAL 栈**
#     （`android.hardware.radio.{config,data,messaging,modem,network,sap,sim,voice}`
#      + 一串 `vendor.qti.hardware.radio.*`），
#     且 system_ext 里 `ro.telephony.sim_slots.count=2`、`telephony.active_modems.max_count=2`。
#   取舍：带着 telephony 只是多几个服务（无害）；该有却没有会**直接编译缺件**。⇒ 保守取 tablet。
#   （若日后确认确无基带且要瘦身，换 `common_full_tablet_wifionly.mk` 只需改这一行。）
$(call inherit-product, vendor/lineage/config/common_full_tablet.mk)

# ---------------------------------------------------------------------------
# Product identity — 取自设备实测属性（archive/metadata/profiles/props-lenovo-system/build.prop）
# ---------------------------------------------------------------------------
PRODUCT_NAME := lineage_TB323FU
PRODUCT_DEVICE := TB323FU
PRODUCT_BRAND := Lenovo
PRODUCT_MODEL := TB323FU
PRODUCT_MANUFACTURER := Lenovo
PRODUCT_SYSTEM_NAME := TB323FU
PRODUCT_SYSTEM_DEVICE := TB323FU

# 设备当前固件是 SDK 37（Android 17 用户态），LineageOS 23 的 framework 是 A16。
# 这里只声明我们自己的 shipping level；**内核不改** —— 仍是原厂的 6.12.69-android16-6。
PRODUCT_SHIPPING_API_LEVEL := 37

# 不预装 Google 服务，保持 LineageOS 默认的 vanilla 形态
WITH_GMS := false

# ---------------------------------------------------------------------------
# Build characteristics
# ---------------------------------------------------------------------------
TARGET_SUPPORTS_64_BIT_APPS := true
TARGET_SUPPORTS_32_BIT_APPS := false
PRODUCT_USE_DYNAMIC_PARTITIONS := true

# 本设备树只产出 system / system_ext / product 三个逻辑分区，
# **不重建 super、不产出 vendor 侧镜像**（理由见 BoardConfig.mk 头部）。
PRODUCT_BUILD_SUPER_PARTITION := false
PRODUCT_BUILD_PVMFW_IMAGE := false
