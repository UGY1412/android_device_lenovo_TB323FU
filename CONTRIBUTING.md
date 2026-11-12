# Contributing / 贡献指南

Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017  
作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017

Thanks for helping make TB323FU customs better. / 感谢参与改进 TB323FU。

## Ground rules / 基本规则

1. **No proprietary binaries** — never attach Lenovo/Qualcomm blobs, kernel
   images, `*.img`/`*.raw` files or full firmware. Use `proprietary-files.txt`
   and `extract-files.py` instead.
   不要提交联想/高通二进制、内核镜像、`*.img`/`*.raw` 或完整固件；请用
   `proprietary-files.txt` + `extract-files.py`。
2. **Keep notices** — do not strip copyright/license headers from files that
   came from upstream projects (AOSP, LineageOS, TWRP, OrangeFox, AERA...).
   保留上游版权/许可证头，不要删除。
3. **Evidence first** — bug reports and fixes should include logs/commands and
   expected vs actual behaviour. Mark anything not tested on hardware as
   `[untested]`. / 以证据为准；未上机验证请标注 `[untested]`。
4. **Small, single-purpose commits** — one logical change per commit; describe
   what device/partition/behaviour it affects.
   提交保持单一目的，写清影响的设备/分区/行为。
5. **No secrets** — no device serial numbers, personal paths, Wi-Fi MACs,
   ADB keys or logs that contain them. / 不提交设备序列号、个人路径、MAC、
   ADB 密钥或包含它们的大段日志。

## Where to send what / 提交到哪

| Change / 改动 | Target / 目标 |
|---|---|
| Device tree, build fixes, docs | Issues / PRs in this repository |
| OrangeFox/TWRP recovery tree | Issues / PRs in the `...-orangefox` repository |
| AERA recovery tree | Issues / PRs in the `...-aera` repository |

## Workflow / 流程

1. Open an issue describing the problem (device state + logs + expected/actual).
2. Fork, create a branch, make the change, verify what you can.
3. Open a pull request; reference the issue; list what was tested on hardware.
4. Maintainer reviews (compliance + evidence + no binary regressions), then merges.

## Attribution / 署名

If your contribution is based on another project's code or documentation, say
so in the PR and update `CREDITS.md` / `docs/ATTRIBUTION.md` if needed.
如果你的改动基于其它项目的代码/文档，请在 PR 中说明，必要时更新
`CREDITS.md` / `docs/ATTRIBUTION.md`。
