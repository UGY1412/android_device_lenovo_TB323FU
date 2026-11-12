Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0 (original text)

# 01 · Device Facts — Lenovo Legion Y700 Gen 5 (TB323FU)

| Field | Value |
|---|---|
| Status | 2026-11-12 — LineageOS 24.0 (Android 17) boots to the Launcher; first boot and a 3× reboot regression PASS |
| Applies to | Lenovo Legion Y700 Gen 5 (拯救者 Y700 五代), model **TB323FU** only; project codename `baldur` / `baldur_prc_wifi` |
| Scope | Hardware/platform identity, stock firmware baseline, partition/LUN geometry, slot state, AVB boot chain, and the "what is actually on the device now" baseline |
| Evidence sources | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md`; `CURRENT-STATE.md` (§1/§4/§9); `out/2026-11-11-los24-bootfix/FLASH-CHECKLIST.md`; `out/2026-11-10-los24-logdump/RESTORE-RUNBOOK.md`; `out/2026-11-10-los24-logdump/restore-map.tsv`; `work/research/B-tb323fu-hardware.md`; `out/2026-11-12-edl-f0/device/postflash-final/getprop-final.txt`; `refs/readback-full/`; device-tree `BoardConfig.mk` |

> **Conventions used in this document set**
> - All LBAs are expressed in **4 KiB logical sectors** (`SECTOR_SIZE_IN_BYTES=4096`), matching the GPT and the Qualcomm Firehose tooling used for this device.
> - SHA-256 values are printed as reported by the source logs; a trailing `…` means the source recorded only the prefix. Full values are given where the source recorded them.
> - `待验证` / "to be verified" marks a data point that is documented but not yet re-measured on the current build.
> - Evidence is graded **measured** (device/log-backed), **declared** (property or documentation only), or **inferred**. Grades are stated where a claim could be mistaken for a measurement.

## 1. Identity

| Item | Value | Evidence |
|---|---|---|
| Model / device name | `TB323FU` | `ro.product.model`, `ro.product.device` (getprop) |
| Marketing name | Lenovo Legion Y700 Gen 5 (联想拯救者 Y700 五代) | project records |
| Serial number | `<SN-REDACTED>` | device report (redacted here) |
| Project codename | `baldur` / `baldur_prc_wifi` | hardware research report |
| SoC | Qualcomm **SM8850P** (platform `canoe`, family `f-canoe`, "kaanapali" platform family), marketed as Snapdragon 8 Elite Gen 5 | `ro.soc.model=SM8850P`, `ro.board.platform=canoe`, `dmesg` cmdline `hqsysfs.pcba_hwid=SM8850P_12+256_11` |
| RAM / storage SKU | 12 GB + 256 GB (from the pcba_hwid string) | `dmesg` kernel cmdline |
| CPU ABI | arm64-v8a only (no 32-bit userspace); runtime CPU variant `oryon` | vendor props, `BoardConfig.mk` |
| Kernel | `6.12.69-android16-6-gb133545a642b-ab15507861-4k` (`#1 SMP PREEMPT Wed May 27 17:46:34 UTC 2026`) | `dmesg` line 2 |
| Kernel page size | 4096 B (`ro.boot.hardware.cpu.pagesize=4096`, `ro.product.page_size=4096`; max supported 16384) | getprop |
| Slot layout | A/B with a dedicated recovery partition, virtual A/B, `super` = 20 GiB, **only `_b` logical partitions exist on this unit** | GPT + LP metadata |
| Bootloader state | unlocked, `verifiedbootstate=orange`, `secure=no` | getprop + fastboot getvar history |
| UFS | `1d84000.ufshc`, UFS ICE v4.0.3, MCQ 9 queues / 8 I/O queues, queue depth 64 | `dmesg` |

## 2. Stock firmware baseline

| Item | Value |
|---|---|
| Stock marketing firmware | `ZUXOS_2.5.10.036_ST_261027` (Android 17) |
| Stock build identity | `TB323FU_CN_OPEN_USER_Q00037.0_A17_DF_2.5.02.165_260924`, build version `DF_2.5.02.165_260924_PRC`, incremental `165` |
| Android version / SDK | 17 / 37 |
| Stock vendor fingerprint | `Lenovo/TB323FU_PRC/TB323FU:17/CQ2A.260712.001/DF_2.5.02.165_260924_PRC:user/release-keys` |
| Stock system fingerprint | `Lenovo/TB323FU_PRC/TB323FU:17/...:user/release-keys` (stock build; superseded on the flashed partitions) |
| Stock kernel | `6.12.69-android16-6-gb133545a642b-ab15507861-4k` (4 KiB pages, KMI `android16-6`) |

### 2.1 LineageOS build currently referenced by these documents

| Item | Value |
|---|---|
| Build fingerprint | `Lenovo/lineage_TB323FU/TB323FU:17/CP2A.260605.016/eng.root:userdebug/test-keys` |
| LineageOS version string | `24-20261107-UNOFFICIAL-TB323FU` |
| Build ID / security patch | `CP2A.260605.016` / `2026-11-01` |
| Product / variant | `lineage_TB323FU` / `userdebug` (test-keys) |
| Target slots | `_b` active at time of the 2026-11-12 acceptance run |
| Notes | The `vendor` partition is stock (untouched), so `ro.vendor.build.fingerprint` still reports the Lenovo stock string. This is expected for the "minimal content replacement" design. |

## 3. Partition / LUN geometry

The device exposes **6 UFS LUNs**. The GPT of each LUN was read back at full length (`refs/readback-full/gpt_main0..5.bin`; the readback set of 156 files / 24.71 GiB was SHA-256 verified 156/156).

### 3.1 LUN overview

| LUN | Partitions | Current LBA | Backup LBA | First usable | Last usable | Capacity |
|---|---|---|---|---|---|---|
| 0 | 14 | 1 | 61390847 | 6 | 61390842 | 234.19 GiB |
| 1 | 9 | 1 | 5119 | 6 | 5114 | 0.02 GiB |
| 2 | 9 | 1 | 5119 | 6 | 5114 | 0.02 GiB |
| 3 | 3 | 1 | 8191 | 6 | 8186 | 0.03 GiB |
| 4 | 99 | 1 | 1048575 | 6 | 1048570 | 4.00 GiB |
| 5 | 6 | 1 | 8191 | 6 | 8186 | 0.03 GiB |

LUN0 carries `super`, `userdata`, `metadata`, `misc`; LUN1/LUN2 are the two XBL slots; LUN3 is CDT/DDR; **LUN4 carries the whole boot chain plus every `_a`/`_b` state partition**; LUN5 is the modem file-system area.

### 3.2 LUN0 — `super` and userdata live here

| Partition | start_lba | sectors | bytes |
|---|---|---|---|
| oemowninfo | 6 | 256 | 1,048,576 |
| ssd | 262 | 2 | 8,192 |
| persist | 264 | 8192 | 33,554,432 |
| misc | 8456 | 256 | 1,048,576 |
| keystore | 8712 | 128 | 524,288 |
| frp | 8840 | 128 | 524,288 |
| **super** | **8968** | **5,242,880** | **21,474,836,480** |
| vbmeta_system_a | 5,251,848 | 16 | 65,536 |
| vbmeta_system_b | 5,251,864 | 16 | 65,536 |
| metadata | 5,251,880 | 16,384 | 67,108,864 |
| rawdump | 5,268,264 | 131,072 | 536,870,912 |
| dataext_a | 5,399,336 | 131,072 | 536,870,912 |
| dataext_b | 5,530,408 | 131,072 | 536,870,912 |
| userdata | 5,661,480 | 55,729,363 | 228,267,470,848 |

### 3.3 LUN4 — selected boot-chain and state partitions

| Partition | start_lba | sectors | bytes | Notes |
|---|---|---|---|---|
| boot_a / boot_b | 119,078 / 489,006 | 24,576 | 100,663,296 | kernel boot image (OEM-signed chain) |
| vbmeta_a / vbmeta_b | 143,706 / 513,634 | 16 | 65,536 | root vbmeta (OEM key on stock; testkey E12 form when rooted) |
| dtbo_a / dtbo_b | 143,722 / 513,650 | 18,432 | 75,497,472 | root vbmeta hash descriptor |
| vendor_boot_a / vendor_boot_b | 302,310 / 672,238 | 24,576 | 100,663,296 | first-stage fstab lives in this ramdisk |
| recovery_a / recovery_b | 334,630 / 696,878 | 25,600 | 104,857,600 | dedicated recovery partition |
| init_boot_a / init_boot_b | 360,742 / 722,990 | 2,048 | 8,388,608 | generic ramdisk (A/B OTA partition) |
| pvmfw_a / pvmfw_b | 362,806 / 725,054 | 256 | 1,048,576 | protected VM firmware; hash-pinned by vbmeta_system |
| efisp | 732,182 | 768 | 3,145,728 | persistent state; **red-line, do not write** |
| devinfo | 732,950 | 1 | 4,096 | persistent state (`ANDROID-BOOT!` header); red-line |
| logfs | 733,207 | 2,048 | 8,388,608 | persistent log area; red-line |
| logdump | 735,255 | 131,072 | 536,870,912 | 512 MiB log-capture partition used by diagnostic boot images |
| uefivarstore | 866,359 | 128 | 524,288 | UEFI variable store; red-line |
| secdata | 866,487 | 7 | 28,672 | persistent state; red-line |
| xbl_sc_logs | 938,766 | 32 | 131,072 | XBL log area |
| dpm | 938,798 | 2 | 8,192 | persistent state |

LUN1/LUN2 each carry one XBL slot (`xbl`, `xbl_config`, `multiimgqti`, `multiimgoem`, `apdp`, TME pieces); LUN3 = `ALIGN_TO_128K_1`, `cdt`, `ddr`; LUN5 = `ALIGN_TO_128K_2`, `modemst1`, `modemst2`, `fsg`, `fsc`, `fs_bkup`. The full 147-row map is in `out/2026-11-10-los24-logdump/restore-map.tsv`.

### 3.4 `super` layout (stock; 4 KiB sectors)

| Item | Value |
|---|---|
| Physical `super` | LUN0 @ LBA 8968, 21,474,836,480 B (20 GiB), 5,242,880 sectors |
| LP metadata | v10.2, `metadata_max=65536`, 3 slots, 4 KiB logical block |
| Group name | `qti_dynamic_partitions` (no slot suffix in the name) |
| Group maximum size | 21,470,642,176 B |
| Logical partition set on this unit | only slot 1 (`_b`): `system`, `system_ext`, `product`, `vendor`, `odm`, `vendor_dlkm`, `system_dlkm` |

Stock logical-partition sizes (each equals the length of the corresponding stock `.img`):

| Logical partition | Bytes |
|---|---|
| system | 10,235,101,184 |
| system_ext | 562,970,624 |
| product | 2,167,775,232 |
| vendor | 2,202,816,512 |
| odm | 334,217,216 |
| vendor_dlkm | 118,259,712 |
| system_dlkm | 14,868,480 |

Physical LP extents on LUN0 (used for direct EDL block writes; verified against `restore-map.tsv` and an independent LP parse):

| Logical partition | Physical start LBA | Sectors | Bytes |
|---|---|---|---|
| system_b | 620,062 | 2,498,804 | 10,235,101,184 |
| system_ext_b | 3,122,496 | 137,444 | 562,970,624 |
| vendor_b | 3,259,940 | 537,797 | 2,202,816,512 |

> The LP metadata of the stock `super` was not modified by the LineageOS port: the whole `super` image is rebuilt/patched only inside the logical-partition regions. The first 64 KiB of `super` keeps the stock SHA-256 prefix `fc016362…c573` after content patching.

### 3.5 Partition table (GPT) anchors

| Object | SHA-256 | Notes |
|---|---|---|
| `gpt_main0` (LUN0 primary) | `162114fe…` | stock layout; checked read-only before/after the 2026-11-12 EDL write |
| `gpt_main4` (LUN4 primary) | `cb20a8b2…c25cc` | `boot_b` is GPT entry #53 |
| `gpt_backup4` (LUN4 backup) | `11892a4f…06ac20` | primary and backup must be written as a pair |
| `boot_b` slot attribute | GPT entry #53, byte 54 = `0x6F` | `0x6F` = ACTIVE + SUCCESSFUL + not-unbootable; other `_b` partitions = `0x44`; unbootable state = `0xEF` |

`AB_FLAG_OFFSET` on Qualcomm is `48 + 6 = 54`, i.e. bit 48–55 of the 8-byte GPT attributes field; `ACTIVE=0x04`, `SUCCESSFUL=0x40`, `UNBOOTABLE=0x80`. A failed boot can set `0x80` again, so content fixes should be completed before repeated boot attempts.

## 4. Slot state and AVB chain facts

Stock root `vbmeta_b` (SHA-256 `ae4ebd61…f54d7`, OEM public key sha1 `8fcb864f…`, rollback index 0) declares:

- `chain` → `boot` (RI location 3), `recovery` (RI location 1), `vbmeta_system` (RI location 2);
- `hash` → `dtbo`, `vendor_boot`;
- `hashtree` → `dataext`, `odm`, `system_dlkm`, `vendor`, `vendor_dlkm`.

Stock `vbmeta_system_b` (SHA-256 `493448e6…0399b`, rollback index `1788566400`, RI location 2) declares:

- `hash` → `init_boot`, `pvmfw`;
- `hashtree` → `product`, `system`, `system_ext`.

Practical consequences, confirmed on this device:

1. **Only the userland partitions are safely replaceable** (`system`, `system_ext`, `product`): each rebuild only requires re-signing `vbmeta_system` with digests taken from the new image footers.
2. `boot` and `recovery` are chained to the **OEM key** and must not be replaced on this port.
3. `init_boot`, `dtbo`, `vendor_boot` are hash-pinned by the root vbmeta (`dtbo`, `vendor_boot`) or by `vbmeta_system` (`init_boot`); replacing them requires a corresponding re-sign.
4. The device's ABL accepts an **AOSP testkey** (`pubkey sha1 2597c218aae470a130f61162feaae70afd97f011`) as the root of trust in the "E12" form: root vbmeta signed with testkey, `chain boot/recovery → OEM`, `chain vbmeta_system → testkey`. chained vbmeta flags **must be 0**; a non-zero flag on a chained vbmeta is rejected as `ERROR_INVALID_METADATA`.
5. dm-verity mismatch on a required partition is **not** forgiven by an unlocked bootloader: the first-stage mount fails and init hits `LOG(FATAL)`. The only way to bypass verity is root-vbmeta `flags=1/2`, which is what the diagnostic flash set uses.

## 5. What is on the device right now (as of 2026-11-12 20:50)

The last write was an **EDL (9008) direct write** on 2026-11-12 20:24–20:26. The authoritative per-partition table (LUN, physical LBA, size, image, SHA-256) is in `03-FLASH.md` §3; summary:

| Partition | Current content |
|---|---|
| `system_b` | `system_raw_nologdump.raw` + a 9-block / 36 KiB block patch (`blocks.tsv`, `system_b_changed_blocks.bin`); removes `logdump.sh`/`logdump.rc` and carries the SELinux policy-sector patch |
| `system_ext_b` | `system_ext_f0diag.img` (SetupWizard removed + auto-provision + logcat→rawdump) |
| `vendor_b` | `vendor_b_full_stock.img` (stock vendor bytes) |
| `vendor_boot_b` | `vendor_boot_diag2.img` (first-stage fstab with avb flags removed + `no_fail`; `androidboot.selinux=permissive` + `printk.devkmsg=on`) |
| `init_boot_b` | `init_boot_logging13.img` (kmsg→logdump capture) |
| `vbmeta_system_b` | `vbmeta_system_v10.img` (paired with logging13; verity-off, so its system digest is not enforced) |
| `product_b` | LineageOS `product_b` (written 2026-11-11 22:46 via fastbootd, untouched since) |
| `vbmeta_b` | E12 testkey root (`7ed20919…`) |
| `boot_b` / `dtbo_b` / `recovery_b` | stock, untouched (rollback anchor `boot_b = 2731d62c…`) |
| GPT / misc / super LP header | stock (`gpt_main0 162114fe…`, `gpt_main4 cb20a8b2…`); BCB empty; not written in this round |

Verification state: first boot reached the Launcher with `sys.boot_completed=1`, `init.svc.bootanim=stopped`, `ro.crypto.state=encrypted` (`ro.crypto.type=file`), `/metadata` on `sda10` (f2fs) and `/data` on `dm-49` (f2fs, inlinecrypt); 3 consecutive `adb reboot` cycles all returned `boot_completed=1` (`RESULT: PASS`, exit 0).

## 6. Hardware at a glance

The full feature/HAL matrix is in `04-HARDWARE-SUPPORT.md`. Headline facts:

| Subsystem | Fact |
|---|---|
| Display | 1904 × 3040 physical pixels, 8.8", CSOT panel with Novatek NT36523N controller, dual DSI, 30/60/90/120/144/165 Hz, 440 dpi, HDR10 / wide color gamut, rounded corners |
| Touch / pen | Novatek NVT capacitive touch + pen input (SPI, cascade, PID 0x609F); Lenovo Tab Pen Plus Bluetooth pen supported |
| Haptics / LED | dual Awinic AW86937 haptic motors; AW22127 LED controller (the stock firmware file `aw22xxx_fw.bin` was reported missing in the stock dmesg capture; the post-flash device log shows it loading successfully) |
| NFC | NXP NFC I²C driver present in stock dmesg; NFC HAL is **not** declared in the `canoe` SKU manifest (only in the unrelated `alor` manifest) → real presence **to be verified** |
| Audio | `audiohalservice.qti`, AGM/PAL, Dolby DAX3; canoe-SKU mixer profiles exist in vendor |
| Camera | `vendor.qti.camera.provider-service_64`; actual sensor models/count **to be verified** |
| Connectivity | Wi-Fi 7-class QTI WLAN HAL (wlan0, wifi-aware0), Bluetooth A2DP/LE-Audio, GNSS; `ro.vendor.config.lgsi.device.nettype=wifi` |
| Storage | UFS 4.x class controller; external SD via `8804000.sdhci`; USB-OTG storage via DWC3 |

## 7. Known caveats and pending verification

1. **Current flash set is a diagnostic state, not a release state**: SELinux permissive, dm-verity off, testkey root vbmeta, `init_boot` = logging13, `system_ext` de-wizarded/auto-provisioned, and a policy-sector patch in `system_b`. See `03-FLASH.md` §8 and the root-cause documents for the cleanup recipe.
2. **Hardware functionality is not measured yet** — only HAL/service presence at boot is confirmed (F1 test round pending). See `04-HARDWARE-SUPPORT.md`.
3. **`/dataext` is missing** from the current LineageOS `system` image root (it exists on stock system-as-root). This was deliberately left out of the first fix; adding it needs `BOARD_ROOT_EXTRA_FOLDERS += dataext` plus a SELinux `file_contexts` mapping. See `02-BUILD.md` §7.
4. **Recorded-history discrepancy (kept for traceability)**: earlier notes stated that `logging13` + `vbmeta_system_v10` were written at 00:35; a read-only pre-check at 20:17 measured `logging10` + `v8` on the device instead. The cause was never determined and does not affect the F0 result; the F0 write overwrote both with `logging13` + `v10` as planned.
5. Device RTC runs in GMT (`persist.sys.timezone=GMT`), so on-screen/log timestamps are 8 h behind Asia/Shanghai. This is normal and does not affect boot.
6. This unit has **only `_b` logical partitions**; A-slot logical partitions do not exist in the current `super` LP metadata. Do not attempt A-slot flashing of logical partitions.
7. Serial number and local paths are redacted in this repository (`<SN-REDACTED>`, `<PROJECT_ROOT>`, `<WORKSPACE>`, `<USER_HOME>`).

## 8. Evidence sources (per section)

| Section | Primary evidence |
|---|---|
| §1 identity | `out/2026-11-12-edl-f0/device/postflash-final/getprop-final.txt`; `dmesg` extract; `work/research/B-tb323fu-hardware.md` §0.2/§4.6 |
| §2 stock baseline | hardware research report §0.2/§5.1; `F0-ACCEPTANCE-REPORT.md` §1; post-flash `getprop-final.txt` |
| §3 partition/LUN geometry | `work/research/B-tb323fu-hardware.md` §2 (GPT re-parse of `refs/readback-full/gpt_main0..5.bin`); `RESTORE-RUNBOOK.md` §3/附录 B; `F0-ACCEPTANCE-REPORT.md` §2; `restore-map.tsv` |
| §4 slot state / AVB | `RESTORE-RUNBOOK.md` §3; `out/2026-11-10-los24-logdump/LOS24-PLAYBOOK-CONSOLIDATED.md` §3.2/§3.3; `FLASH-CHECKLIST.md` §0 |
| §5 current flash set | `F0-ACCEPTANCE-REPORT.md` §2/§3; `CURRENT-STATE.md` §4/§5 |
| §6 hardware | `work/research/B-tb323fu-hardware.md` §1/§3/§4; `postflash-final/ps-A.txt`; `postflash-final/logcat-all.txt` |
| §7 caveats | `F0-ACCEPTANCE-REPORT.md` §5/§8; `CURRENT-STATE.md` §6; `BUILD-FIX-REPORT.md` §8 |
