#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#
# 第二段（release config）**不是自由选项** —— 它决定 PLATFORM_SEPOLICY_VERSION，
#      进而决定我们的 system 能否与原厂 vendor 的 precompiled_sepolicy 合并。
#
#   机制（完整推导链见 work/research/D-lunch-release-sepolicy.md）：
#     lunch 第2段 → TARGET_RELEASE
#       → build/release/flag_values/<release>/RELEASE_BOARD_API_LEVEL
#       → BOARD_API_LEVEL（board_config.mk:1019；被 .KATI_READONLY 锁死、手工设置直接 $(error)）
#       → PLATFORM_SEPOLICY_VERSION（config.mk:877）
#
#   实测值：  bp2a → 202504   ✓ 与原厂 vendor 的 plat_sepolicy_vers.txt 精确同版本
#            ap3a → 202404   ✗ 硬冲突，必然起不来（LOS 官方树常见写 ap3a —— 照搬即死）
#            ap2a → 202404   ✗ 同上
#
#   判据：>= 202504 即安全（更大的值会靠 mapping/202504.cil 重映射）。
#   ⇒ **不要改这段**。真要换世代，先读 build/release/flag_values/<新段>/RELEASE_BOARD_API_LEVEL.textproto。

PRODUCT_MAKEFILES := \
    $(LOCAL_DIR)/lineage_TB323FU.mk

COMMON_LUNCH_CHOICES := \
    lineage_TB323FU-cp2a-user \
    lineage_TB323FU-cp2a-userdebug \
    lineage_TB323FU-cp2a-eng
