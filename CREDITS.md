# Credits / 致谢与三方来源

Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017  
作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017

This repository is an original LineageOS 24 device-tree adaptation for the
Lenovo TB323FU, built on top of AOSP/LineageOS conventions and validated
against a real device. It **does not redistribute** any Lenovo/Qualcomm
proprietary binaries. The table below lists every upstream project that
informed or was referenced by this work.

本仓库是针对联想 TB323FU 的 LineageOS 24 设备树原创适配，基于 AOSP/LineageOS
通用规范并在真机验证；**不再分发**任何联想/高通专有二进制。下表列出所有被参考或
使用的上游项目。

| Upstream / 上游 | License / 许可证 | How used here / 使用方式 |
|---|---|---|
| [AOSP (Android Open Source Project)](https://source.android.com/) | Apache-2.0 | Framework, build system, recovery/first-stage sources; file headers retained where applicable |
| [LineageOS 24.0](https://github.com/LineageOS/android) | Apache-2.0 | Build system, device-tree conventions, product configuration patterns |
| [LineageOS/android_device_oneplus_iceland](https://github.com/LineageOS/android_device_oneplus_iceland) | Apache-2.0 | **Reference only** (SM8850 tablet: VINTF/HAL/partition configuration patterns); no code copied verbatim |
| [LineageOS/android_device_oneplus_sm8850-common](https://github.com/LineageOS/android_device_oneplus_sm8850-common) | Apache-2.0 | **Reference only** (SM8850 platform layout) |
| [TeamWin Recovery Project (TWRP)](https://github.com/TeamWin) | Apache-2.0 | Recovery lineage of the companion recovery trees |
| [TWRP-Test platform_manifest_twrp_aosp](https://github.com/TWRP-Test) | Apache-2.0 | Recovery build manifest used by the companion trees |
| [polygraphene/android_bootable_recovery](https://github.com/polygraphene/android_bootable_recovery) (branch `twrp-16.0-TB322FC`) | Apache-2.0 (per upstream) | Recovery device-tree baseline for the companion OrangeFox/AERA trees |
| [OrangeFox Recovery](https://gitlab.com/OrangeFox) | Mixed (see upstream NOTICE) | Companion OrangeFox tree only; no binaries here |
| [AERA Recovery](https://github.com/AERA-Recovery) | Per upstream NOTICE (TWRP/OrangeFox lineage) | Companion AERA tree only |
| [isrgish/TB323FU-TWRP](https://github.com/isrgish/TB323FU-TWRP) | **No explicit LICENSE** (see note) | Lineage of the TB323FU recovery tree; not redistributed here — recovery repo is prepared as a fork |
| [qingxin94/tb323fu-recovery](https://github.com/qingxin94/tb323fu-recovery) | No license declared | Public AERA-recovery device tree for TB323FU; cross-reference for the companion AERA repo |
| [aweiyry/lenovo-ota-tool](https://github.com/aweiyry/lenovo-ota-tool) | MIT | **Reference only** for Lenovo OTA/partition extraction workflow; no code copied |
| **DeepSeek V4.1 Flash 1017** | Tool (not a copyright holder) | Collaboration tool used to generate/organize parts of the code and documentation; maintainer reviewed and validated everything on hardware |
| Lenovo / Qualcomm proprietary blobs | Proprietary — **not included** | Listed in `proprietary-files.txt` only; builders must extract from their own legally obtained firmware |

## Notes / 说明

- `proprietary-files.txt` lists target paths only; no blob content is stored in
  this repository. / `proprietary-files.txt` 仅列目标路径，不含任何 blob 内容。
- `configs/` contains VINTF interface descriptions extracted from the stock
  firmware; they describe interfaces, and no separate copyright is asserted for
  them. / `configs/` 中的 VINTF 接口描述提取自原厂固件，仅描述接口，不单独主张版权。
- The companion recovery trees (OrangeFox / AERA) are separate repositories;
  their own `NOTICE`/`LICENSES`/`CREDITS` apply. / 两个 recovery 子仓库为独立
  仓库，适用各自的 `NOTICE`/`LICENSES`/`CREDITS`。
- If any upstream author believes this repository misuses their work, please
  open an issue; see `docs/COMPLIANCE.md` (we will remove or adjust within
  72 hours). / 若上游作者认为使用不当，请提 issue（见 `docs/COMPLIANCE.md`，
  我们会在 72 小时内移除或调整）。
