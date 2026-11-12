# Compliance / 合规说明

Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017  
作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017

> See NOTICE and CREDITS for attribution.
> 本文是项目实践说明，不构成法律意见。

## 1. What this repository contains / 本仓库包含什么

Only **text**: device configuration, build metadata, scripts, documentation,
and lists of proprietary file paths. / **只有文本**：设备配置、构建元数据、
脚本、文档以及专有文件路径清单。

## 2. What it does NOT contain / 本仓库不包含什么

- Lenovo/Qualcomm proprietary binaries, firmware, libraries, HALs
- Kernel images (`prebuilt/Image`), DTBO images (`prebuilts/dtbo.img`)
- Any partition image (`*.img`, `*.raw`, `*.bin`), super image, or flashable ZIP
- Raw device logs, `dmesg`/`logcat` dumps, ADB keys, or keys of any kind
- Device serial numbers, personal paths, or Wi-Fi/Bluetooth MAC addresses
  (replaced with `<SN-REDACTED>`, `<PROJECT_ROOT>`, `<WORKSPACE>`,
  `<USER_HOME>`, `<MAC>`)

Builders must obtain proprietary files from firmware they are legally
entitled to use. / 使用者必须从自己合法持有的固件中提取专有文件。

## 3. Attribution / 归属

Every upstream project that informed this work is listed in
[../CREDITS.md](../CREDITS.md) and mapped per-path in
[ATTRIBUTION.md](ATTRIBUTION.md). Files derived from upstream projects keep
their original notices. / 所有参考/使用的上游项目均在 CREDITS 与 ATTRIBUTION 中
列明；上游衍生文件保留原通知。

Special notes / 特别说明:

- **isrgish/TB323FU-TWRP** has no explicit license in its repository. We do
  **not** redistribute that tree here; the companion OrangeFox/TWRP
  repository is prepared as a **fork** of it so that GitHub keeps the
  attribution chain, and we clearly document our changes.
- **qingxin94/tb323fu-recovery** is a public AERA-recovery device tree for the
  same model; the companion AERA repository credits it as a reference.
- **LineageOS/AOSP/TWRP/OrangeFox/AERA** files retain their licenses.
- **DeepSeek V4.1 Flash 1017** is credited as a co-author for collaboration on code and documentation.

## 4. Redistribution of binaries / 二进制再分发

If you build images yourself, you are responsible for the proprietary content
in them. Do not upload Lenovo/Qualcomm firmware or full images to public
services; share your own build according to the licenses that apply to you.
你自己编译的镜像所含专有内容由你负责；不要把原厂固件或整包镜像上传到公开服务。

## 5. Takedown & contact / 下架与联系

If you are an upstream author and believe this repository uses your work
incorrectly, please open an issue on GitHub (or contact `@UGY1412`). We will
respond and, where appropriate, **remove or adjust the content within 72
hours**. / 若你是上游作者并认为使用不当，请在 GitHub 提 issue（或联系
`@UGY1412`）；我们会在 **72 小时内**移除或调整相关内容。

## 6. Trademarks / 商标

Lenovo, Legion, Qualcomm, Snapdragon, Android, LineageOS, TeamWin (TWRP),
OrangeFox and AERA are trademarks of their respective owners. This project is
unofficial and not endorsed by them. / 相关商标归各自所有者；本项目为非官方项目，
未获其认可。

## 7. Security & safety / 安全提示

Flashing modifies boot-critical partitions. Use only verified images (SHA-256
in [03-FLASH](en/03-FLASH.md)), keep a full stock backup, and understand the
recovery path for your device before writing anything.
刷写会改动启动关键分区；请只用已校验镜像、保留原厂全量备份，并先确认变砖恢复路径。
