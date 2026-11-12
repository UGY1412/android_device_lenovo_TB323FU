Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0

# 03 · Flash — TB323FU flashing, verification and rollback

| Field | Value |
|---|---|
| Status | 2026-11-12 — the EDL (9008) direct-write route below is the one that produced the accepted first boot and 3× reboot regression (PASS); the fastbootd route is kept as a historical alternative |
| Applies to | Lenovo Legion Y700 Gen 5, model **TB323FU**, slot `_b`, unlocked bootloader |
| Scope | Write channels and their real capabilities, the exact current flash set (partition / LUN / LBA / size / image / SHA-256), step-by-step routes, post-write verification, stock-restore anchors, red lines, troubleshooting |
| Evidence sources | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md`; `out/2026-11-11-los24-bootfix/F0-FLASH-BUNDLE.md`; `out/2026-11-11-los24-bootfix/FLASH-CHECKLIST.md`; `out/2026-11-11-los24-bootfix/F0-ACCEPTANCE-CHECKLIST.md`; `out/2026-11-11-los24-bootfix/MORNING-RUNBOOK.md`; `out/2026-11-10-los24-logdump/RESTORE-RUNBOOK.md`; `out/2026-11-10-los24-logdump/LOS24-PLAYBOOK-CONSOLIDATED.md` (§3.1–§3.6); `refs/readback-full/` |

> **Read this first.** This guide records steps verified on one physical unit. Flashing can brick the device, erase `/data`, or trip anti-rollback if the wrong package is used. Before writing anything: identify the partition and LUN, confirm the image SHA-256, and know your rollback anchor. Never trust an EDL `SUCCESS` message — the only proof of a write is a read-back hash or a content fingerprint.

## 1. Write-channel capability matrix (measured on this device)

| Channel | LUN0 | LUN4 | Notes / evidence |
|---|---|---|---|
| Bootloader fastboot (`is-userspace=no`) | read-only | read-only | only `getvar` / `reboot` / `reboot recovery`; `flash` returns `remote: 'unknown command'`; `oem edl` also unknown |
| fastbootd (`is-userspace=yes`) | `super` and logical partitions | `vbmeta_b`, `init_boot_b`, … | entered by `adb reboot fastboot` / `fastboot reboot fastboot` from a bootable system or recovery; auto-sparse transport, 13 GB ≈ 20 s class |
| recovery `dd` | Yes | | any physical/logical partition via `/dev/block/by-name/*`; verified by SHA-256 read-back |
| EDL + `fh_loader` (2026-11-10+ form) | Yes | | requires `--zlpawarehost=1` and XML with `label` / `partofsingleimage=false` / `readbackverify=false`; write then read back and compare |
| EDL old form (no `--zlpawarehost`, bare LBA) | partial | fake success | prints `{All Finished Successfully}` after `ERROR: invalid gpt entry number 128` — do not use |
| EDL read | fake-success history | fake-success history | use only with two independent reads / content fingerprints |
| GeekFlashTool (full package) | Yes | | only "one-click back to stock" history; once corrupted the LUN0 backup GPT (5-sector bug) |
| `adb reboot edl` (soft EDL) | No | | lands in a 9008 that does not answer Sahara; writes are silently dropped |

**One-tool rule:** only one host tool may own the 9008 port at a time; a GUI tool holding COM3 must be closed and the cable re-plugged to re-enter EDL. Only one Sahara/programmer handshake is allowed per EDL entry.

## 2. Current flash set (last write: 2026-11-12 20:24–20:26, EDL direct write)

All LBAs are 4 KiB sectors. `GPT = refs/readback-full/gpt_main0.bin / gpt_main4.bin`. Physical LBA of an LP partition = `super` start LBA 8968 + `offset/4096` (two independent sources agree, and an independent LP parse confirmed that all seven `_b` logical partitions are single-extent, linear mappings).

| Partition | LUN | Physical LBA | Sectors | Size (B) | Content written | SHA-256 |
|---|---|---|---|---|---|---|
| `system_b` | 0 | 620062 | 2,498,804 | 10,235,101,184 | **9-block / 36 KiB patch** on top of `system_raw_nologdump.raw` (blocks 0,1,3,30,53,62069,65536,79494,81367; removes `logdump.sh` + `logdump.rc`, plus the policy sector) | raw `b6ca50f5…`; block data `2e563f37…`; block list `f21ccc7f…` |
| `system_ext_b` | 0 | 3122496 | 137,444 | 562,970,624 | `system_ext_f0diag.img` (SetupWizard removed + aera-provision + logcat→rawdump) | `e1addc29…` |
| `vendor_b` | 0 | 3259940 | 537,797 | 2,202,816,512 | `vendor_b_full_stock.img` (stock vendor bytes) | `08caa9a6…` |
| `vendor_boot_b` | 4 | 672238 | 24,576 | 100,663,296 | `vendor_boot_diag2.img` (first-stage fstab avb flags removed + `no_fail`; `androidboot.selinux=permissive` + `printk.devkmsg=on`) | `40623569…` |
| `init_boot_b` | 4 | 722990 | 2,048 | 8,388,608 | `init_boot_logging13.img` (kmsg→logdump capture) | `baf1133d…` |
| `vbmeta_system_b` | 0 | 5251864 | 16 | 65,536 | `vbmeta_system_v10.img` (paired with logging13; verity-off, so the system digest is not enforced) | `2b52e26b…` |
| `misc` | 0 | 8456 | 256 | 1,048,576 | **not written** (BCB measured empty; no need to clear before reset) | — |
| `/data`, `/metadata` | — | — | — | — | formatted by the user via stock-recovery **Factory data reset** (`fastboot -w` only erases on Windows; it does not format) | — |

Unmodified partitions: `boot_b`, `dtbo_b`, `recovery_b`, `vbmeta_b` (E12 testkey root), GPT, `super` LP header, `media` and all other partitions.

Full documents for the patched pieces:

| Piece | Full SHA-256 |
|---|---|
| `system_raw_nologdump.raw` (10,235,101,184 B) | `b6ca50f586a80584473c97d44e75f7f3013dd50a17f6f56ef1c47c69b5c709ba` |
| `system_b_changed_blocks.bin` (36,864 B) | `2e563f37a786f6644fe087a8cbcabc2afbc94d7ce7798499e01be78c533bd5f3` |
| `blocks.tsv` (375 B) | `f21ccc7f73019c6b48cd3aec4c61ad12060980b0f4b3744d28da7953c9c660fa` |
| `flash-system-blocks.py` (9,990 B) | `b1c47db6cddf65b40b95f6628fe91094e5c9a4a45293deab3a8229bbd931fd13` |
| `vendor_b_full_stock.img` (2,202,816,512 B) | `08caa9a653332bc2e86063f4dd7f545b7760cc83524a68713b6df1eea6897957` |
| `vendor_boot_diag2.img` (100,663,296 B) | `406235697d5df9a95a5425b6ddeed26413cda11da41a88c5612317909345f969` |
| `init_boot_logging13.img` (8,388,608 B) | `baf1133d9699240dd64b069d5792a7b21348121d1b16d53f14b405d8c5ff0c78` |
| `vbmeta_system_v10.img` (65,536 B) | `2b52e26b9c1bc8f15562d5e22a1fc2eced0d5721a432e15846ee26901fce4afc` |
| `system_raw_fixed.raw` (pre-F0 system; contains logdump — rollback only) | `1e7ec2d126d2889340578182b78121af7b39dbd1bc2165f39852cf4453673ff8` |
| `vbmeta_system_v8.img` (pre-F0 paired signature) | `bfd496d922e66d9cc547769d8eb4846d41ce46a52d23e0245a5d4499f98fe2f7` |
| `init_boot_logging10.img` (pre-F0 paired init_boot) | `4511a32e…` |

## 3. Route A (recommended, verified): EDL / 9008 direct write

### 3.1 Prerequisites

| Item | Value |
|---|---|
| Device mode | 9008 / EDL (`Qualcomm HS-USB QDLoader 9008`, historical COM3) |
| Toolchain | `fh_loader.exe` (SHA-256 prefix `22507A0B…C5DBA`), `QSaharaServer.exe` (`F1274519…C838DBD`), programmer `devprg_legion-y700-5-2.0.11.043` (Lenovo-specific, 8 files) |
| Port | `\\.\COM3` (always confirm in Device Manager) |
| Power | battery > 30%; keep the cable connected throughout the whole procedure |
| Rule | keep the Firehose connection alive (no reset) until all writes are done, then issue a single `power reset` |

### 3.2 Step 1 — read-only pre-check

```powershell
python edl-precheck.py
```

Checks performed before any write:

- GPT LUN0/LUN4 compared against the stock `refs/readback-full` images (expected MATCH); current slot state;
- `misc` BCB (boot control block) contents (expected empty);
- classification of the 9 target `system_b` blocks as `OLD` / `NEW` (expected 8 OLD + 1 NEW before F0);
- records the in-service `init_boot_b` / `vbmeta_system_b` SHA-256 (for traceability).

**Do not reset after the pre-check** — the Firehose connection is reused by the write steps.

### 3.3 Step 2 — write the 9-block / 36 KiB system patch

```powershell
python flash-system-blocks.py --no-reset
```

- block indexes: `0, 1, 3, 30, 53, 62069, 65536, 79494, 81367` (4 KiB each, 36,864 B total);
- target LBAs (LUN0, 4 KiB LBA = 620062 + block index): `620062, 620063, 620065, 620092, 620115, 682131, 685598, 699556, 701429` (8 extents);
- the script validates that `blocks.tsv` is strictly ascending/unique, that the block data is exactly 9 × 4096 B, and that every LBA lies inside the `system_b` extent;
- it reads back first / middle / last after writing and prints `ALL OK` only when the compare succeeds.

Why a block patch instead of writing 10 GiB: the fix changes exactly 9 blocks (36 KiB), so the EDL transfer is seconds instead of minutes and the untouched regions cannot be corrupted by a long transfer interruption.

### 3.4 Step 3 — write the remaining five partitions

```powershell
python edl-write-f0.py --no-reset
```

Writes, over one Firehose connection, with per-partition head/tail read-back (and full read-back for the small partitions):

| Order | Partition | Size | LUN |
|---|---|---|---|
| 1 | `vendor_b` | 2.05 GiB | 0 |
| 2 | `system_ext_b` | 537 MiB | 0 |
| 3 | `vendor_boot_b` | 96 MiB | 4 |
| 4 | `init_boot_b` | 8 MiB | 4 |
| 5 | `vbmeta_system_b` | 64 KiB | 0 |

For LUN4 partitions the EDL XML must carry `label=`, `partofsingleimage="false"`, `readbackverify="false"`, `sparse="false"`, `SECTOR_SIZE_IN_BYTES="4096"` and the CLI must use `--zlpawarehost=1`; mirrors must be inside `--search_path` and referenced by basename.

### 3.5 Step 4 — post-write verification (mandatory)

```powershell
python edl-dump-system-blocks.py --no-reset     # expect NEW 9/9
python edl-write-f0.py --verify-only            # per-partition read-back compare
```

Acceptance is **content equality**, not the Firehose `SUCCESS` line. In the accepted run: 9 blocks all `NEW`, every written partition read back `ALL OK`, and geometry was independently re-computed from both `restore-map.tsv` and `regions.json` with zero discrepancies.

### 3.6 Step 5 — reset and first boot

1. `power reset` (fh_loader `<power value="reset"/>`; in the accepted run the 9008 device disappeared within seconds and the unit landed in **stock recovery** — this is expected because the old `/metadata` was already corrupted by the old `logdump`).
2. **The user taps "Factory data reset" once.** This genuinely formats `/data` + `/metadata` (stock recovery performs the format; `fastboot -w` in Windows platform-tools only erases).
3. The unit reboots, MTP enumerates in ~1 min, and adb appears; expected first boot to Launcher in 3–6 min (no SetupWizard because it was removed from `system_ext`, and provisioning is forced).

### 3.7 Step 6 — acceptance

```powershell
f0-postboot-verify.ps1 -RebootTest 3
```

PASS criteria (all must hold):

- adb online and `sys.boot_completed=1` for the first boot and for each of the 3 reboot cycles;
- `init.svc.bootanim=stopped`;
- `/metadata` mounted (`sda10` f2fs) and `/data` mounted (`dm-49` f2fs, inlinecrypt);
- `ro.crypto.state=encrypted`, `ro.crypto.type=file`;
- `init_user0` appears once as normal `fscrypt_init_user0`; zero `init_user0_failed` / `Failed to create /metadata` / `mount_all --late` hits;
- `logdump.sh` / `logdump.rc` absent on the device;
- script prints `RESULT: PASS` with exit code 0.

Observed timeline of the accepted run (local time):

| Time | Event |
|---|---|
| 20:11 | device confirmed in 9008 (COM3) |
| 20:17 | EDL read-only pre-check: GPT MATCH, BCB empty, 9 blocks = 8 OLD + 1 NEW; in-service `init_boot_b=logging10`, `vbmeta_system_b=v8` |
| 20:24:36 | 9-block patch written + read-back MATCH |
| 20:24:40–20:24:53 | 5 partitions written + read-back ALL OK (vendor 2.05 GiB / 8.3 s) |
| 20:28:16 | post-write dump: 9 blocks = **NEW 9/9** |
| 20:28:34 | `power reset` |
| 20:29:17 | lands in stock recovery (planned) |
| ~20:29:5x | user taps **Factory data reset** |
| 20:30:22 | MTP enumerated |
| 20:35:00 | **first boot PASS**: adb online, `boot_completed=1` |
| 20:37:51–20:39:27 | **3/3 reboot regression PASS** (`RESULT: PASS`, exit 0) |

## 4. Route B (historical alternative): fastbootd full-image write

Used on 2026-11-11 to reach the first boot; kept as a fallback when EDL is unavailable and the unit can reach fastbootd.

```powershell
fastboot devices
fastboot reboot fastboot          # enter fastbootd (userspace fastboot)
fastboot getvar is-userspace      # expect: yes
fastboot getvar current-slot      # expect: b

fastboot flash system_b system_raw_nologdump.raw     # 10 GiB, image must equal extent length exactly
fastboot flash vendor_b vendor_b_full_stock.img
fastboot flash vendor_boot_b vendor_boot_diag2.img
fastboot flash init_boot_b init_boot_logging13.img
fastboot flash vbmeta_system_b vbmeta_system_v10.img
fastboot flash system_ext_b system_ext_f0diag.img
fastboot -w
fastboot reboot
```

Notes:

- fastbootd sizes logical partitions from the image footer and resizes automatically (the group has enough headroom); the 10 GiB image must be **exactly** the logical-partition size, i.e. 10,235,101,184 B.
- `fastboot flash super` rejects sparse images; `super` must be raw if it is ever flashed this way.
- After `fastboot -w`, a first boot on this unit may still land in stock recovery's factory-reset screen (planned or unexpected, depending on metadata state); tapping "Factory data reset" once is the supported way to format.
- If the 10 GiB transfer fails or times out, switch to Route A's 36 KiB block patch instead of retrying the 10 GiB write.

Historical single-variable baseline from 2026-11-11 (kept for reference): before the first LineageOS boot the device carried `boot_b 2731d62c…`, `vendor_boot_b 9349137d…`, `init_boot_b 6ac4a4e8…` (logging4 wrapper), `vbmeta_b 7ed20919…`, `vbmeta_system_b 784ac7d3…` (old los4), and `super_v7.img` (`5779a9a5…`) paired with `vbmeta_system_v7.img` (`6b11d5e4…`).

## 5. Route C — full stock restore (R12 set)

The stock boot chain requires exactly this set (parsed from the stock `vbmeta_b` and `vbmeta_system_b`):

| # | Partition | LUN | LBA (4 KiB) | Sectors | Bytes | Stock file | SHA-256 | Channel |
|---|---|---|---|---|---|---|---|---|
| 1 | `super` (all 7 LP inside) | 0 | 8968 | 5,242,880 | 21,474,836,480 | `super.img` | `78e54bd36dc1d6971d338ffb49670c6809cad36ca16f6004d0b281af331cf4e5` | EDL |
| 2 | `vbmeta_system_b` | 0 | 5251864 | 16 | 65,536 | `vbmeta_system_b.img` | `493448e6…0399b` | EDL |
| 3 | `dataext_b` | 0 | 5530408 | 131,072 | 536,870,912 | `dataext_b.img` | `e231c8c7…ac86fb` | EDL |
| 4 | `vbmeta_b` | 4 | 513634 | 16 | 65,536 | `vbmeta_b.img` | `ae4ebd619bb57c0d4f50e6619d1a5937bc805b8eaff90f83becdf2631dbf54d7` | EDL |
| 5 | `boot_b` | 4 | 489006 | 24,576 | 100,663,296 | `boot_b.img` | `2731d62ca182c811ed51e4c4e33fe22da4191218569499cdb7debf793c072bec` | EDL |
| 6 | `dtbo_b` | 4 | 513650 | 18,432 | 75,497,472 | `dtbo_b.img` | `6cdc8d3b…239db49` | EDL |
| 7 | `vendor_boot_b` | 4 | 672238 | 24,576 | 100,663,296 | `vendor_boot_b.img` | `9349137dc262ab61508014275b623f4d39e5b14bc55c77082848d63a28f381b2` | EDL |
| 8 | `recovery_b` | 4 | 696878 | 25,600 | 104,857,600 | `recovery_b.img` | `a3b34a80…62acea0` | EDL |
| 9 | `init_boot_b` (vbmeta_system hash) | 4 | 722990 | 2,048 | 8,388,608 | `init_boot_b.img` | `a31072c0b26f5df8581e2f23e9a39cb8476c00b2b9f251c701db433141653e68` | EDL |
| 10 | `pvmfw_b` (vbmeta_system hash) | 4 | 725054 | 256 | 1,048,576 | `pvmfw_b.img` | `d24b59dc…affc98` | EDL |
| 11 | `metadata` (optional, **not written by default**) | 0 | 5251880 | 16,384 | 67,108,864 | `metadata.img` | `7c043a52…f292ba4c` | EDL |
| 12 | `misc` (optional, **not written by default**) | 0 | 8456 | 256 | 1,048,576 | `misc.img` | `5c90f3ad…7a25fe` | EDL |

- Stock `super` SHA-256: `78e54bd3…cf4e5`; its first 64 KiB SHA-256 = `fc0163625355ffd46479d9a6c671187a3879954d43cb3c2cf46407dc3b68c573` (LP metadata unchanged after content patching).
- `metadata` / `misc` are optional: stock `metadata` is a 2026-10-06 snapshot that may conflict with current `/data`; `misc` BCB is currently empty and writing it does not change slot selection.
- **Never** write `devinfo`, `efisp`, `uefivarstore`, `logfs`, `secdata`, `frp`, `keystore`, `modemst1/2`, `fsg`, `fsc` individually; they hold persistent unlock/slot state and were byte-identical to the stock readback set.
- GeekFlashTool full restore is the last-resort channel (24.71 GiB; skips `USRDATA,userdata,last_parti,rawdump`); after a full restore, clear data once (`Reason: init_user0_failed` is expected and normal).

## 6. Verification and the "fake success" traps

1. **EDL `SUCCESS` is not proof.** Historical traps on this device: (a) `program` with `label=` fails table lookup but `fh_loader` still prints `{All Finished Successfully}`; (b) if the image is outside `--search_path`, no program is even sent and it still prints SUCCESS; (c) the old form was rejected for LUN4 GPT parsing.
2. **EDL reads can also fake success.** Eight different partitions once read back the same pseudo-random stream, and `misc` started with a `<response…>` header. Judge a read-back by its SHA-256/size/content fingerprint, and retry or switch channels on suspicion.
3. **`super` read-back head checks** (when not hashing 20 GiB): u32 @0x1000 = `0x616C4467` (LP geometry magic) and one of u32 @0x3000/0x13000/0x23000 = `0x414C5030` (LP metadata header). Random/zero/`<response` bytes mean the write did not land.
4. **Block-patch pre-check states:** `OLD` → write; `NEW` → already fixed, skip; `MIXED` → previous write was interrupted, re-run Route A's block step; `OTHER` → baseline differs from expectation, do not write the block patch, use the full-image route or restore the baseline first.
5. **Geometry cross-check before writing:** `restore-map.tsv` and `regions.json` must agree on every LP physical LBA; an independent LP parse should confirm every `_b` partition is single-extent and linear.
6. **Per-partition SHA-256 record:** every flashed image and every anchor used here is listed with a hash in this document or in `01-DEVICE-FACTS.md`; `Get-FileHash -Algorithm SHA256` on the host before flashing.

## 7. Rollback anchors

| Anchor | File | SHA-256 |
|---|---|---|
| Stock full readback (156 files / 24.71 GiB) | `refs/readback-full/` | 156/156 verified |
| Stock `super` | `refs/readback-full/super.img` | `78e54bd36dc1d6971d338ffb49670c6809cad36ca16f6004d0b281af331cf4e5` |
| Stock `vbmeta_b` | `refs/readback-full/vbmeta_b.img` | `ae4ebd619bb57c0d4f50e6619d1a5937bc805b8eaff90f83becdf2631dbf54d7` |
| Stock `boot_b` | `refs/readback-full/boot_b.img` | `2731d62ca182c811ed51e4c4e33fe22da4191218569499cdb7debf793c072bec` |
| Stock `vendor_boot_b` | `refs/readback-full/vendor_boot_b.img` | `9349137dc262ab61508014275b623f4d39e5b14bc55c77082848d63a28f381b2` |
| Stock `init_boot_b` | `refs/readback-full/init_boot_b.img` | `a31072c0b26f5df8581e2f23e9a39cb8476c00b2b9f251c701db433141653e68` |
| Pre-F0 bootable baseline (system) | `system_raw_fixed.raw` | `1e7ec2d1…` |
| Pre-F0 paired signature | `vbmeta_system_v8.img` | `bfd496d9…` |
| Pre-F0 paired init_boot | `init_boot_logging10.img` | `4511a32e…` |
| Fixed `super` (content-patched baseline) | `super_v7.img` | `5779a9a5e73ddcdecea245fc65ad8cc9e398de4a1ab889d8656e8f3b335823bf` |
| F0 target raw system (verity-on preparation) | `system_raw_nologdump.raw` (re-signed form `29ad60fb…`, root digest `9103aeb9…`) | `b6ca50f5…` |
| Future verity-on signature | `vbmeta_system_f0_v11.img` | `66e20599…` |

Restoring the pre-F0 bootable state = `system_raw_fixed.raw` + `vendor_b_full_stock` + `vendor_boot_diag2` + `init_boot_logging10` + `vbmeta_system_v8`.

## 8. Diagnostic state vs. release state

The accepted 2026-11-12 flash set is deliberately **diagnostic**:

| Item | Current diagnostic value | Release requirement |
|---|---|---|
| SELinux | permissive | enforcing |
| dm-verity | off (`vendor_boot_diag2` has avb flags removed) | on, with an avb-enabled `vendor_boot` |
| root `vbmeta_b` | E12 testkey | may stay testkey form on an unlocked device, but must be re-audited |
| `init_boot_b` | logging13 (continuous kmsg capture) | stock or clean init_boot |
| `system_ext_b` | SetupWizard removed, auto-provision, logcat→rawdump | stock-like user build |
| `system_b` | logdump removed (keep!) + policy-sector patch (inert while product/system_ext are LOS) | keep logdump removal; revert the policy sector before enabling verity |
| `/metadata` | formatted after fix | fine |

Verity-on cleanup recipe: restore an avb-enabled `vendor_boot`; re-hash `system` and rebuild `vbmeta_system` (`vbmeta_system_f0_v11.img`, `66e20599…`, root digest `9103aeb9…`, raw SHA-256 `29ad60fb…`); revert the policy-sector patch; replace `init_boot` with the stock/clean image; then switch SELinux to enforcing.

## 9. Red lines

1. Do **not** write the bootloader area (`xbl`/`abl`/`tz`/`uefi`/`hyp`/`aop`/`cpucp`/`devcfg`/`qupfw`/`shrm`/`imagefv`/`keymaster`/`modem`/`dsp`/`bluetooth`/TME/`dcp`/`soccp`/`pdp`/`spuservice`/…) unless the bootloader version is confirmed identical and a full rollback is mandatory (GeekFlashTool only).
2. Do **not** write GPT unless it is proven corrupted, and then write primary + backup as a pair.
3. Do **not** write the A-slot for logical partitions — this unit has only `_b` LP partitions.
4. Do **not** trust EDL `SUCCESS`; compare read-back hashes/content.
5. One 9008 connection = one host tool.
6. Do **not** hand-edit LP metadata or resize logical partitions.
7. Do **not** restore `devinfo`/`efisp`/`uefivarstore`/`logfs`/`secdata` individually.
8. Do **not** use the old EDL form (no `--zlpawarehost=1`, no `partofsingleimage`, bare LBA) for any partition.
9. Do **not** flash an older bootloader or "downgrade to A16 to rescue".
10. Do **not** interrupt a `super` write; do not flash before host-side SHA-256 verification passes.

## 10. Troubleshooting

| Symptom | Meaning | Action |
|---|---|---|
| `target not stable` / port open > 3 s | Sahara/programmer state stuck | re-send programmer; if it persists, unplug/re-plug and re-enter EDL |
| `SAHARA_NAK_HASH_TABLE_AUTH_FAILURE` | programmer / XBL version mismatch or state machine dead | re-enter 9008; verify `devprg_legion-y700-5-2.0.11.043` |
| `{All Finished Successfully}` but read-back differs | fake success | check `--zlpawarehost=1`, XML fields, `search_path`; rewrite that partition |
| `Not a valid GPT signature` / `invalid gpt entry` | old form / bare-LBA write rejected | switch to the `fh-write-*.xml` + `--zlpawarehost=1` form |
| Read-back all-zero or starts with `<?xml` | fake read | re-read; after two failures switch channel; judge by device behavior |
| Cable drop during `super` write | incomplete image | re-enter EDL and rewrite the **whole** `super` from scratch |
| First screen stuck / USB never enumerates | content/mount failure | verify the flash set is complete (especially `super`, `vbmeta_system`, `dataext`); see `05`–`08` |
| Bootloader fastboot within ~8 s | boot-chain/AVB or early-init fatal | verify `vbmeta_b`/`vbmeta_system_b`/GPT state; 8 s is NOT automatically a signature failure |
| Boots but cannot decrypt `/data` / boot loops | `/data` does not match the new system | recovery **Format Data** (the only supported way to clear) |
| 9008 not appearing | USB/power state | hold power 10 s, then hold Volume-Up (and Volume-Down) while plugging the long-edge port |
| Multiple partitions fail in a row | EDL channel unstable | stop EDL and use GeekFlashTool full restore; do not leave a half-written state |

## 11. Evidence sources

| Topic | Evidence |
|---|---|
| Accepted EDL run, write set, timeline, acceptance | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` (§1–§3, §8) |
| F0 bundle, pre-check states, block patch, routes | `out/2026-11-11-los24-bootfix/F0-FLASH-BUNDLE.md`; `FLASH-CHECKLIST.md`; `F0-ACCEPTANCE-CHECKLIST.md`; `MORNING-RUNBOOK.md` |
| Channel matrix, fake-success traps, R12 restore set, LBA quick reference | `out/2026-11-10-los24-logdump/RESTORE-RUNBOOK.md` (§0–§4, §8, 附录 B); `LOS24-PLAYBOOK-CONSOLIDATED.md` §3.2–§3.6 |
| Partition/LUN geometry | `01-DEVICE-FACTS.md` §3; `restore-map.tsv` |
| Rollback anchors / stock hashes | `refs/readback-full/`; `RESTORE-RUNBOOK.md` §3 |
| Diagnostic-state cleanup | `03` §8; `out/2026-11-11-los24-bootfix/F0-SIDE-EFFECT-AUDIT.md` |
