# Attribution map / 逐目录来源映射

Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017  
作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017

This file records where each part of the repository came from, so that reuse
and audits do not require guessing. Data was collected from the project's
build logs, stock-firmware dumps and documented investigation reports.

本文件记录仓库各部分的来源，便于复用与审计。信息来自项目构建日志、原厂固件
导出与已归档的排查报告。

| Path / 路径 | Origin / 来源 | License / 许可 | Notes / 说明 |
|---|---|---|---|
| `Android.bp`, `AndroidProducts.mk`, `BoardConfig.mk`, `device.mk`, `lineage_TB323FU.mk` | Original adaptation by the maintainer for TB323FU (2026-10/11), following AOSP/LineageOS conventions | Apache-2.0 | Device-specific values measured/verified on hardware |
| `config.fs`, `lineage.dependencies` | Original / AOSP build convention | Apache-2.0 | — |
| `proprietary-files.txt` | Generated from a stock firmware dump of the maintainer's own device | List only (no license asserted) | Paths/hashes only; **no blob content** stored |
| `extract-files.py` | Original script (generic extraction helper) | Apache-2.0 | Edit source/destination paths before use |
| `configs/` (110 files) | Extracted from **stock vendor** (Lenovo A17): VINTF HAL manifests, `modules.load.system_dlkm`, etc. | Interface descriptions; no separate copyright asserted | Needed to build a working VINTF manifest for the stock vendor HALs |
| `overlay/` | Original LineageOS-style overlays for TB323FU | Apache-2.0 | Display/feature defaults |
| `sepolicy/` | Original device sepolicy additions | Apache-2.0 | Minimal; stock vendor sepolicy provides the rest |
| `tools/` | Original reference scripts written during bring-up (EDL/boot-fix) | Apache-2.0 | Sanitized: absolute paths replaced with `<PROJECT_ROOT>` / `<WORKSPACE>` |
| `docs/en/*.md`, `docs/zh-CN/*.md` | Original documentation derived from the project's investigation reports | Apache-2.0 (text) | Sources cited at the top of each document |
| `docs/screenshots/*.png` | Screenshot captured from the maintainer's device | — | Contains no personal data |
| `README*`, `AUTHORS.md`, `CREDITS.md`, `NOTICE`, `LICENSE`, `CONTRIBUTING.md` | Original | Apache-2.0 / as stated | — |

## Third-party references (not copied) / 仅参考、未复制

AOSP, LineageOS 24.0, `LineageOS/android_device_oneplus_iceland`,
`LineageOS/android_device_oneplus_sm8850-common`, TWRP, TWRP-Test,
polygraphene's TB322FC recovery tree, OrangeFox, AERA, `isrgish/TB323FU-TWRP`,
`qingxin94/tb323fu-recovery`, `aweiyry/lenovo-ota-tool` — see
[../CREDITS.md](../CREDITS.md) for the full list with licenses and usage.

## If you believe something is missing / 如发现归属缺失

Open an issue with the path and the original source; see
[COMPLIANCE.md](COMPLIANCE.md).
