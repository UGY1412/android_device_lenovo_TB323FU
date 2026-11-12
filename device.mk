#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#
# TB323FU device configuration — 【最小内容替换】形态
# ============================================================================
# 本文件**只放设备侧配置**。
# product 继承链与 PRODUCT_* 身份字段都在 lineage_TB323FU.mk 里 —— 这是
# LineageOS 的标准分工（对照官方同平台树：FAIR-lineage.mk / FAIR-device.mk）。
# 把职责混在一起会导致 PRODUCT_* 落在错误的继承层。
# ============================================================================
#
# 本设备树**故意不 inherit 任何 vendor blobs 树**。
# 常规设备树会写：
#     $(call inherit-product, vendor/<oem>/<device>/<device>-vendor.mk)
# 那会把厂商 HAL / 库 / 固件打进 system 侧镜像。本项目不这么做的原因：
#   * 硬件层（vendor / odm / vendor_dlkm / system_dlkm）在设备上**保持原厂**、不参与编译；
#   * 厂商 blobs 与内核 ABI 绑死（本机内核 6.12.69-android16-6），混进来只会制造 VINTF/符号冲突；
#   * 真正需要换掉的只有 userland framework —— 那正是本设备树的产出。
# ============================================================================

# ---------------------------------------------------------------------------
# 屏幕
# ---------------------------------------------------------------------------
# 密度 440 已移到 **BoardConfig.mk**（它的消费者在 BoardConfig 阶段；见那边的注释），
#    不要在这里重复设。
# 分辨率 3040×1904 —— **已核实，两个独立来源**（work\research\B-tb323fu-hardware.md §1）：
#   ① handoff\2026-10-12-flash1\grab\logfs-full.strings.txt:29773 —— ABL 自打印
#      `DisplayDxe: Resolution 1904x3040`
#   ② handoff\2026-10-12-flash1\grab\dmesg.txt:2810 —— 内核 `hactive=1904, vactive=3040, fps=120`
#   面板 CSOT + NT36523N（dmesg.txt:2040），双 DSI（:2066），30~165 Hz（:2067-2087）。
#   注意：这两个必须留在 product 层 —— `vendor/lineage/config/common.mk` 用 `?=` 只在未设时
#   给 1080×1920 默认，我们必须先于它赋值才生效（继承顺序不能反，见 A 报告 §5.3 缺口 5）。
TARGET_SCREEN_HEIGHT := 3040
TARGET_SCREEN_WIDTH := 1904

# 平板形态（同厂商参考树的 device.mk 里也有这一行）
#  来源：子代理 A 的对照报告 §5.3 缺口 6（lolipuru asphalt 的 device.mk:25）
PRODUCT_CHARACTERISTICS := tablet

# ---------------------------------------------------------------------------
# AAPT
# ---------------------------------------------------------------------------
PRODUCT_AAPT_CONFIG := normal
# 参考树（联想同厂 8.8" 平板 sm8475-common/common.mk:33-34）用 **xxhdpi**；本机 440 dpi 也落在
#   xxhdpi(480) 桶（AOSP 分级 xhdpi=320 / xxhdpi=480）。
#   修正记录：我先前写的是 xhdpi，那是**错的** —— 会让 system 只打 320dpi 资源，
#   在 440dpi 屏上图标被放大发糊。此项不阻塞编译、只影响观感，因此错了很难事后察觉。
PRODUCT_AAPT_PREF_CONFIG := xxhdpi

# ---------------------------------------------------------------------------
# Soong
# ---------------------------------------------------------------------------
PRODUCT_SOONG_NAMESPACES += $(LOCAL_PATH)

# ---------------------------------------------------------------------------
# TODO（等编译跑起来后按实际报错处理）
# ---------------------------------------------------------------------------
# TODO(1) overlay：若要当平板桌面用，需要把 `config_isDesktopModeSupported := true`
#         写进 overlay —— 先例作者实测：缺这一条时"小窗/桌面模式"相关配置会被整体忽略。
#         （来源：AwHsR15/aviumui-y700-2023-asphalt 的 README）
# TODO(2) VINTF：本设备树暂不提供 framework compatibility matrix 片段。原厂 device matrix
#         会有若干条要求无人认领；按 AOSP 源码，boot 期这类不匹配只 Slog.e，不阻塞启动。
# TODO(3) 不 inherit vendor blobs 树 ⇒ PRODUCT_PACKAGES 里不要引用任何 vendor/lenovo 下的目标，
#         否则会在 soong/kati 阶段报 "module not found"。

# ---------------------------------------------------------------------------
# 保留此行作为说明（不要打开）
# ---------------------------------------------------------------------------
# $(call inherit-product, vendor/lenovo/TB323FU/TB323FU-vendor.mk)


# ---------------------------------------------------------------------------
# EARLY LOG CAPTURE (debug build only): snapshot kernel/init logs into the
# AVB-unprotected metadata partition; read back via EDL after a hang.
# 2026-11-10: added while bringing up full-user-space LOS.
# ---------------------------------------------------------------------------
PRODUCT_COPY_FILES += \
    device/lenovo/TB323FU/logdump/logdump.sh:$(TARGET_COPY_OUT_SYSTEM)/bin/logdump.sh \
    device/lenovo/TB323FU/logdump/logdump.rc:$(TARGET_COPY_OUT_SYSTEM)/etc/init/logdump.rc

# ---------------------------------------------------------------------------
# Framework / Settings resource overlays (static RRO merge)
# ---------------------------------------------------------------------------
#   overlay/frameworks/base/core/res/res/values/config.xml
#     - config_showNavigationBar = true (device has no hardware nav keys)
#   overlay/packages/apps/Settings/res/values/lineage_config.xml
#     - config_show_peak_refresh_rate_switch / config_show_min_refresh_rate_switch
#       = true (expose refresh-rate pickers in Display settings)
# Android 17 build/make still merges DEVICE_PACKAGE_OVERLAYS statically into the
# target APK when PRODUCT_ENFORCE_RRO_TARGETS is not set (see
# build/make/core/package_internal.mk:137-160); no separate RRO APK is produced.
DEVICE_PACKAGE_OVERLAYS += $(LOCAL_PATH)/overlay
