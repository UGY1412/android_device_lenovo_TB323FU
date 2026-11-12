# TB323FU — LineageOS 24 device tree

Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017

Unofficial LineageOS 24 (Android 17) device tree for the **Lenovo Legion Y700
Gen5 (TB323FU, SM8850P / kaanapali)** tablet.

This repository documents and automates the **complete port to first boot**:
device configuration, build fixes, first-stage mount debugging, secure-boot
(AVB) handling, EDL/fastbootd flashing procedures, and the root-cause
investigations that were required to make LineageOS boot on this device.

中文说明见 [README.zh-CN.md](README.zh-CN.md)。

## Status (2026-11-12)

| Item | Status |
|---|---|
| Build (LineageOS 24.0, `lineage_TB323FU-cp2a-userdebug`) | buildable, images verified |
| First boot | boots to LineageOS home screen |
| Reboot stability | 3/3 consecutive reboots passed (`sys.boot_completed=1`) |
| /data file-based encryption (FBE) | `ro.crypto.state=encrypted`, `type=file` |
| Hardware functions | partly unverified — see [04-HARDWARE-SUPPORT](docs/en/04-HARDWARE-SUPPORT.md) |
| Current build state | debug/bring-up state (SELinux permissive, dm-verity off, test-keys, verbose boot logging) — see [04](docs/en/04-HARDWARE-SUPPORT.md) |

This is a **porting base**, not a release ROM. Expect device-specific bugs and
read the docs before flashing.

## Device

| Item | Value |
|---|---|
| Model | Lenovo Legion Y700 Gen5 (TB323FU) |
| Platform | Qualcomm SM8850P / kaanapali (`canoe`) |
| Partitions | A/B + independent recovery, virtual A/B, 4 KiB pages, 20 GiB super |
| Display | 1904×3040 portrait, 120 Hz |
| Stock firmware basis | Lenovo A17 (`TB323FU_CN_OPEN_USER_Q00037.0_A17_ZUXOS_2.5.10.036_ST_261027`) |
| Unlock | bootloader unlocked (orange state), B slot active |

Full partition/LUN tables and the flashing geometry are in
[docs/en/01-DEVICE-FACTS.md](docs/en/01-DEVICE-FACTS.md).

## Quick start (build)

Requirements: Linux (WSL2 Ubuntu 24.04 works), ~60 GiB source + ~150 GiB
output space, `repo`, JDK, and the LineageOS 24.0 manifest.

```bash
# 1) sync LineageOS 24.0
repo init -u https://github.com/LineageOS/android -b lineage-24.0 --git-lfs --no-repo-verify
repo sync -c -j"$(nproc)"

# 2) place this device tree
mkdir -p device/lenovo
git clone https://github.com/UGY1412/android_device_lenovo_TB323FU device/lenovo/TB323FU
# (or symlink your working copy)

# 3) extract proprietary blobs from YOUR OWN stock firmware
#    edit extract-files.py paths, then:
cd device/lenovo/TB323FU && ./extract-files.py /path/to/your/dump

# 4) build
source build/envsetup.sh
lunch lineage_TB323FU-cp2a-userdebug
mka systemimage    # or `m bacon` once the product supports it
```

The stock 6.12 GKI kernel is used (no kernel source is included in this
repository; extract it from your own firmware). Build steps, caveats and
known build errors: [docs/en/02-BUILD.md](docs/en/02-BUILD.md).

> The device tree deliberately contains **no binaries**: `prebuilt/Image`
> (kernel) and `prebuilts/dtbo.img` are excluded. See
> [docs/en/02-BUILD.md](docs/en/02-BUILD.md) for how to obtain them.

## Quick start (flash)

Boards must be unlocked. Two flashing routes are documented:

- **EDL (9008)** — recommended for a bricked/incomplete device
  (`docs/en/03-FLASH.md` §EDL).
- **fastbootd** — for a device that can still reach recovery/fastbootd
  (`docs/en/03-FLASH.md` §fastbootd).

Both routes require an **unlocked bootloader** and a **factory data reset**
(metadata corruption from older builds must be cleared). Never flash a
half-verified image set; every partition has an expected SHA-256 in the docs.

## Documentation

Full bilingual index: [docs/README.md](docs/README.md)

| # | Topic | EN | 中文 |
|---|---|---|---|
| 01 | Device facts (partitions/LUN/kernel/slots) | [EN](docs/en/01-DEVICE-FACTS.md) | [中文](docs/zh-CN/01-DEVICE-FACTS.md) |
| 02 | Build guide & common build errors | [EN](docs/en/02-BUILD.md) | [中文](docs/zh-CN/02-BUILD.md) |
| 03 | Flashing (EDL / fastbootd) & rollback | [EN](docs/en/03-FLASH.md) | [中文](docs/zh-CN/03-FLASH.md) |
| 04 | Hardware support matrix | [EN](docs/en/04-HARDWARE-SUPPORT.md) | [中文](docs/zh-CN/04-HARDWARE-SUPPORT.md) |
| 05 | Root cause: `/vendor` self-referential symlink | [EN](docs/en/05-ROOTCAUSE-VENDOR-SYMLINK.md) | [中文](docs/zh-CN/05-ROOTCAUSE-VENDOR-SYMLINK.md) |
| 06 | Root cause: logdump corrupting `/metadata` | [EN](docs/en/06-ROOTCAUSE-LOGDUMP-METADATA.md) | [中文](docs/zh-CN/06-ROOTCAUSE-LOGDUMP-METADATA.md) |
| 07 | FBE / `init_user0` analysis | [EN](docs/en/07-FBE-INIT-USER0.md) | [中文](docs/zh-CN/07-FBE-INIT-USER0.md) |
| 08 | SELinux precompiled policy issues | [EN](docs/en/08-SELINUX-POLICY.md) | [中文](docs/zh-CN/08-SELINUX-POLICY.md) |
| 09 | AVB / test-key / boot-chain notes | [EN](docs/en/09-AVB-CHAIN-NOTES.md) | [中文](docs/zh-CN/09-AVB-CHAIN-NOTES.md) |
| 10 | Debug channels without pstore | [EN](docs/en/10-DEBUG-CHANNELS.md) | [中文](docs/zh-CN/10-DEBUG-CHANNELS.md) |
| 11 | Error catalog (40+ real errors) | [EN](docs/en/11-ERROR-CATALOG.md) | [中文](docs/zh-CN/11-ERROR-CATALOG.md) |
| 12 | Experiment log (what failed & why) | [EN](docs/en/12-EXPERIMENT-LOG.md) | [中文](docs/zh-CN/12-EXPERIMENT-LOG.md) |

Read [05](docs/en/05-ROOTCAUSE-VENDOR-SYMLINK.md),
[06](docs/en/06-ROOTCAUSE-LOGDUMP-METADATA.md) and
[11](docs/en/11-ERROR-CATALOG.md) first if your device is stuck at the first
screen or boot-looping.

## Tools

`tools/` contains the reference scripts used during bring-up (EDL flashing of
F0 images, block-level system patching, super-image assembly, boot-log
classification). They are **reference implementations**: paths were redacted
to `<PROJECT_ROOT>` / `<WORKSPACE>` placeholders and must be adapted. See
[tools/README.md](tools/README.md).

## Related repositories

- Recovery (OrangeFox / TWRP lineage): [android_device_lenovo_TB323FU-orangefox](https://github.com/UGY1412/android_device_lenovo_TB323FU-orangefox)
- Recovery (AERA Recovery): [android_device_lenovo_TB323FU-aera](https://github.com/UGY1412/android_device_lenovo_TB323FU-aera)

## Credits

See [CREDITS.md](CREDITS.md) for every upstream project used or referenced
(AOSP, LineageOS, TWRP/TeamWin, TWRP-Test, polygraphene, OrangeFox, AERA,
isrgish, aweiyry/lenovo-ota-tool, DeepSeek V4.1 Flash 1017).
Attribution and compliance policy: [docs/COMPLIANCE.md](docs/COMPLIANCE.md).

## License

Original files: Apache-2.0 (see [LICENSE](LICENSE) and [NOTICE](NOTICE)).
Third-party files keep their own notices. No proprietary binaries are
distributed.

## Disclaimer

THIS PROJECT IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. Flashing,
unlocking, or modifying a device can cause data loss, an unbootable device,
or loss of access to encrypted data. You are solely responsible for deciding
whether to build, flash, or use this project and for keeping backups. The
maintainers accept no liability for damage, data loss, or other consequences.

This is an unofficial community project. Lenovo, Legion, Qualcomm, Snapdragon,
Android, LineageOS, TeamWin, OrangeFox and AERA are trademarks of their
respective owners. This project is not affiliated with or endorsed by them.
