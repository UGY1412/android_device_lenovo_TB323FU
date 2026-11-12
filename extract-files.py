#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#
# TB323FU blobs 提取：从本机官方固件生成本地 vendor 树（vendor/lenovo/TB323FU）。
# 用法（在 ROM 树内）：
#     cd device/lenovo/TB323FU && ./extract-files.py --src <固件根> 
#   固件根下应有 vendor/ odm/ system_ext/（由原厂镜像挂载得到）。
#
# 注意：extract-utils 的实际 CLI 以 ROM 树里的 tools/extract-utils 为准，
#       sync 完成后按其接口微调（本文件为第一版）。

from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)

module = ExtractUtilsModule(
    'TB323FU',
    'lenovo',
    namespace_imports=[
        'device/lenovo/TB323FU',
    ],
)

# NOTE: ExtractUtilsModule.__init__ 会自动注册 proprietary-files.txt；
# 不要再次 add_proprietary_file，否则所有模块会生成两遍（2026-11-09 实测）。

if __name__ == '__main__':
    utils = ExtractUtils.device(module)
    utils.run()
