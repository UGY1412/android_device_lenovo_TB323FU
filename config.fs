#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#
# TB323FU — 原厂 vendor 组（AID）声明
# ============================================================================
# 用途：本文件由 TARGET_FS_CONFIG_GEN 消费 —— soong 会把它转成 fs_config 的输入
#       （build/make/core/soong_config.mk:250 的 TargetFSConfigGen），
#       同时 host_init_verifier 在校验 init rc 时需要认识这些 group 名。
#
# 为什么需要它：先例报错（2026-10-11，见 handoff/2026-10-11-编译攻坚实录.md 类 11）：
#     gnss-aidl-service-qti.rc: Unable to decode GID for 'vendor_qti_diag'
# 那批设备属主/组用的就是下面这批原厂私有 GID（2901~2917）。
#
# 格式**必须**是 `[AID_VENDOR_XXX]` 全大写 + `value: <数字>`。
#       类 12 记录的现实教训：格式写错会报
#       `Invalid characters in AID section at "4"... Expecting upper case`。
#
# 来源：旧设备树（2026-10-11 那棵编出 818MB system.img 的树）的 config.fs 原样沿用。
# TODO(verify): 17 个 value 尚未与设备侧 /vendor/etc/passwd 逐项比对，见
#               work/research/ 中的核实记录；若不一致，以设备侧为准。
# ============================================================================

[AID_VENDOR_QTI_DIAG]
value: 2901
[AID_VENDOR_QDSS]
value: 2902
[AID_VENDOR_RFS]
value: 2903
[AID_VENDOR_RFS_SHARED]
value: 2904
[AID_VENDOR_ADPL_ODL]
value: 2905
[AID_VENDOR_QRTR]
value: 2906
[AID_VENDOR_THERMAL]
value: 2907
[AID_VENDOR_FASTRPC]
value: 2908
[AID_VENDOR_QTR]
value: 2909
[AID_VENDOR_NXP_STRONGBOX]
value: 2910
[AID_VENDOR_NXP_WEAVER]
value: 2911
[AID_VENDOR_SSGTZD]
value: 2912
[AID_VENDOR_THALES_STRONGBOX]
value: 2913
[AID_VENDOR_QCC]
value: 2914
[AID_VENDOR_NXP_AUTHSECRET]
value: 2915
[AID_VENDOR_THALES_WEAVER]
value: 2916
[AID_VENDOR_THALES_AUTHSECRET]
value: 2917
