Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0 (original text)

# 06 — Root cause: `logdump.sh` `dd`-writes `/metadata` on every boot → `init_user0_failed` → forced data wipe

| Field | Value |
|---|---|
| Status | 2026-11-12 — root cause fixed offline on 2026-11-11/12 and **verified on device** the same day (F0 repair set: first boot to desktop + 3/3 reboots PASS) |
| Device | Lenovo Legion Y700 Gen 5 **TB323FU**, SN `<SN-REDACTED>`, SM8850P (canoe / kaanapali), A/B, 4 KiB pages, unlocked (`vbs=orange`), B slot active |
| Applies to | the LineageOS 24.0 (Android 17) port's `system_b` images built before 2026-11-12; `/metadata` = `/dev/block/sda10` (f2fs, 64 MiB), `/data` = `/dev/block/sda14` / dm-49 (f2fs, inlinecrypt) |
| Evidence sources | `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\ROOTCAUSE-LOGDUMP-METADATA.md`, `…\SYSTEM-LOGDUMP-REMOVAL-REPORT.md`, `…\F0-SIDE-EFFECT-AUDIT.md`, `…\SESSION-20261112-FBE-ROOTCAUSE-LOG.md`, `…\NEXT-ROUND-TEST-PLAN.md`; `<PROJECT_ROOT>\out\2026-11-12-edl-f0\F0-ACCEPTANCE-REPORT.md` |

---

## 1. Symptom

The user's core complaint for days was: **"the device only boots after formatting data; after booting once, a normal reboot goes straight back to recovery (`init_user0_failed`)"**. The stock recovery screen read:

```
Can't load Android system. Your data may be corrupt. …
Reason: init_user0_failed
```

(recovery text path `bootable/recovery/recovery.cpp:301-314`; the reason string is passed by init via `reboot_into_recovery(--reason=…)`.)

A single boot could reach the LineageOS welcome screen and stay up for ≥11 minutes (22:48–23:08 on 2026-11-11), but any reboot ended in recovery, or the device hung on the boot animation. Clearing `/data` made the *next* first boot work again — a perfect "wipes required every reboot" loop.

## 2. The culprit

The LineageOS-built `system` image contained a debug capture script pair that the bring-up did not intend to ship, and it wrote **raw blocks into the metadata partition on every boot**:

| File | Inode | Mode / owner | Size | Role |
|---|---|---|---|---|
| `/system/bin/logdump.sh` | 431 | 0755 root:2000 | 1,336 B | "LOG CAPTURE v3" shell script; `dd` snapshot into metadata |
| `/system/etc/init/logdump.rc` | 791 | 0644 0:0 | 547 B | init rc that runs the script at four boot stages and starts a loop service |

`/system/etc/init/logdump.rc` (verbatim):
```
on early-init
    exec -- /system/bin/logdump.sh once 0
on init
    exec -- /system/bin/logdump.sh once 8
on post-fs-data
    exec -- /system/bin/logdump.sh once 16
    start logdump_loop2
on boot
    exec -- /system/bin/logdump.sh once 24
service logdump_loop2 /system/bin/logdump.sh loop
    class late_start
    user root
    group root system
    disabled
```

`/system/bin/logdump.sh` (essential line):
```
DEV=/dev/block/by-name/metadata
...
{ cmdline; getprop; dmesg; } > /dev/rawlog.tmp
dd if=/dev/rawlog.tmp of="$DEV" bs=4096 seek=$((OFF_MB*256)) conv=fsync
cp -f /dev/rawlog.tmp /metadata/logdump.txt
```

`once 0` runs at `early-init` and writes a 4 KiB-aligned snapshot starting at **metadata offset 0 — directly over the f2fs superblock**. `once 8/16/24` overwrite the middle of the partition. The writes are `conv=fsync`, so they are really on the block device, and they happen **after** recovery has formatted metadata and **before** the next boot tries to mount it.

## 3. Evidence chain

### 3.1 Image-level (byte evidence)

`debugfs` on the shipped `system` raw image (before the fix) shows both files present with the content quoted above; after the fix both paths return `File not found` and the inode numbers are released. The four `exec` stages were proven by the rc text, and the offsets map to the observed writes.

### 3.2 Device-level (the writes really landed)

EDL dumps of the device's `/metadata` partition (`device/metadata_*.bin`) contain repeated headers at **0 / 8 / 16 / 24 MB**:

```
==== LOGDUMP3 mode=once ... uptime=1.0x ====
--- cmdline ---
```

— exactly the artifacts of `logdump.sh once 0|8|16|24`.

### 3.3 Failure chain after the corruption (verbatim kmsg, previous boot's log region)

```
vold: Failed to create /metadata/vold: Read-only file system        ← /metadata not mounted (dir falls on read-only root)
vold: read_key failed in mountFstab
vdc: Command: cryptfs encryptFstab ... Failed
make_f2fs: mkfs.f2fs Ver 1.16.0                                    ← /data got formatted a second time
F2FS-fs (sda14): Mounted with checkpoint version ...               ← userdata mounts (sda14 = userdata)
vold: Failed to create /metadata/vold: Read-only file system        ← /metadata still not mounted
init: Command 'mount_all /vendor/etc/fstab.qcom --late' ... failed: queue_fs_event() failed: Invalid code: -1
vold: keystore2 Communication with Keystore earlyBootEnded failed error: -129
cutils: Failed to mkdir(/data/misc/vold/user_keys): No such file or directory
vold: Failed to prepare /data/misc/vold/user_keys: No such file or directory
vdc: Command: cryptfs init_user0 Failed: Status(-8, EX_SERVICE_SPECIFIC): '0: '
```

Contrast with a known-good boot (the 23:08 boot that reached the welcome screen) — its kmsg contains:

```
F2FS-fs (sda10): Mounted with checkpoint version = 581f46d7
```

`sda10` is metadata. The failing boots have `sda14` (userdata) but **no `sda10` line** — metadata was not mounted at all.

### 3.4 Why this produces "clear data → first boot OK → next reboot broken"

1. recovery "Factory data reset" really formats `sda10` (metadata) and `sda14` (data) → metadata is clean → the first boot mounts it, vold initializes FBE, `init_user0` succeeds, the system reaches the UI.
2. During that same boot, `logdump.sh once 0` overwrites metadata's f2fs superblock (and 8/16/24 MB regions).
3. On the next boot, first-stage tries to mount metadata, fails, and the failure is **silently swallowed** because the fstab entry carries `first_stage_mount,no_fail`; first stage never formats. "Corrupted" ≠ "wiped", so the second-stage auto-format does not trigger either.
4. Without `/metadata`: `vold` cannot create `/metadata/vold`, `read_key` fails, `/data` is formatted a second time, `mount_all --late` fails, post-fs-data never completes, `/data/misc/vold/user_keys` does not exist, `vdc cryptfs init_user0` fails.
5. `init_user0` failure triggers a **forced reboot into recovery with reason `init_user0_failed`** → the loop closes. Only another full data wipe can break it.

### 3.5 Why first stage / `fastboot -w` cannot save it

- `first_stage_mount.cpp:377-385`: a failed mount of an entry marked `no_fail` is only logged (`INFO`), never fatal; first stage **never formats** a partition.
- The second-stage auto-format path only fires for a "wiped" determination (header cleared); a corrupted-but-not-wiped filesystem does not qualify.
- Only the recovery wipe path really formats metadata (`bootable/recovery/install/wipe_data.cpp:151-153`).
- On this Windows host, `fastboot -w` only **erases** (`not automatically formatting`); it does not format f2fs. That is why the accepted procedure uses stock recovery's "Factory data reset" once.

### 3.6 `init_user0` source chain (for reference)

- `system/core/rootdir/init.rc:1086` — built-in `init_user0` inside `on post-fs-data` (block starts at `:707`; vold started at `:602`).
- `system/core/init/builtins.cpp:1190-1192` — `do_init_user0()` → `ExecVdcRebootOnFailure("init_user0")`.
- `builtins.cpp:1151-1177` — runs `exec /system/bin/vdc --wait cryptfs init_user0` as a temporary oneshot service; on failure sets `reboot_reason = vdc_arg + "_failed"`, and if `IsFbeEnabled() && !IsGsiRunning()` calls `reboot_into_recovery({"--prompt_and_wipe_data", "--reason=…"})`; if FBE is disabled it only logs `"Failure (reboot suppressed)"` (no recovery bounce).
- `system/vold/vdc.cpp:163-164` → `VoldNativeService.cpp:631-635` → `system/vold/FsCrypt.cpp:655-690` `fscrypt_init_user0()` (creates/loads DE/CE keys under `/data/misc/vold/user_keys`, prepares special dirs, `fscrypt_prepare_user_storage`).

## 4. Fix (F0 repair set)

### 4.1 Remove the two files from `system`

`debugfs -w` on the current `system` raw image:

```
rm /system/bin/logdump.sh
rm /system/etc/init/logdump.rc
```

Assertions: both paths `File not found`; a scan of `/system/bin`, `/system/etc/init`, `/system/etc` finds **no other** `logdump`/`aera`/`rawlog` remnants; `e2fsck -fn` clean. The `logdump_loop2` service disappears with its rc.

A full-image scan then checked for any other live writer of `/dev/block/by-name/metadata`:
- the only live writer was `logdump.sh` itself (now deleted);
- `/system/bin` and `/system/etc/init` directory blocks still contain the **stale name bytes** of the deleted files — ext4 deletion does not zero data blocks, and such bytes are not reachable by lookup;
- the stock vendor's `rawdump`/`ramdump` machinery writes the **rawdump partition**, not metadata (`/bin/init.qcom.sh`: `RAWDUMP_LINK="/dev/block/bootdevice/by-name/rawdump"`);
- `/etc/fstab.qcom` hits are the normal metadata **mount** entry, and SELinux policy files only contain label/type strings (`vendor_logdump_partition`, `metadata_block_device`).

Conclusion: after deletion, no live component writes raw blocks to metadata; `vold`/`fs_mgr`/`make_f2fs` access it only via the normal mount/format/repair paths.

### 4.2 Block-level patch (36 KiB instead of a 10 GB write)

The fixed `system` raw is `system_raw_nologdump.raw`; compared with the pre-fix image it differs in **exactly 9 blocks / 36,864 B** (AVB hashtree/FEC tail area: 0 changed blocks). Because the device's `system_b` starts at absolute 4 KiB LBA **620,062**, block `n` goes to LBA `620062 + n`:

| block_index | target LBA | old sha16 | new sha16 |
|---|---|---|---|
| 0 | 620062 | `09d232326e3bf282` | `f9aaa28b1f1e3ba8` |
| 1 | 620063 | `c41a9b84f11eb1f1` | `3b9c21346ddb31d5` |
| 3 | 620065 | `c8ad46f3c0f44c20` | `d4cc0a1c95ac8d73` |
| 30 | 620092 | `98226916179acdf3` | `20c6722a95aeecbb` |
| 53 | 620115 | `f64aee737d37db85` | `be8d59b287460f5a` |
| 62069 | 682131 | `bdd5e30403307c9b` | `675ccdfb5b07fc58` |
| 65536 | 685598 | `f47a8ec3e9aff231` | `25a57db227761553` |
| 79494 | 699556 | `60f61b5487841a32` | `38b7e4e4c40b7b6d` |
| 81367 | 701429 | `9884c84c86e3ae0c` | `d05ef83d3abc4e01` |

Classification: `62069` = `/system/bin` directory block (removal of the `logdump.sh` entry); `79494` = `/system/etc/init` directory block (removal of `logdump.rc`); `81367` = `/system/etc/selinux/plat_sepolicy_and_mapping.sha256` data block (the 4 KiB policy patch, see doc 08); `0/1/3/30/53/65536` = ext4 metadata (superblock/GDT/inode table/bitmap updates caused by the deletions). The deleted files' own data blocks (71,131 and 79,567) are **not** in this set, again because ext4 does not zero them.

### 4.3 F0 write procedure (executed 2026-11-12)

1. Enter EDL (9008, COM3). Read-only pre-check (`edl-precheck.py`): GPT LUN0/LUN4 MATCH the stock reference, misc BCB empty, the 9 blocks classified as 8 OLD + 1 NEW (the policy block was already patched), and the live `init_boot_b`/`vbmeta_system_b` SHAs recorded.
2. Write the 9 blocks (36 KiB) at LBA 620062.. with `flash-system-blocks.py --no-reset`; re-read first/mid/last → MATCH; a post-write dump re-classified 9/9 as NEW.
3. EDL-direct-write the other 5 partitions (no fastbootd): `vendor_b_full_stock` (`08caa9a6…`), `vendor_boot_diag2` (`40623569…`), `init_boot_logging13` (`baf1133d…`), `vbmeta_system_v10` (`2b52e26b…`), `system_ext_f0diag` (`e1addc29…`). Every write verified by head/tail re-read (small partitions full SHA).
4. `power reset` (fh_loader `<power value="reset"/>`).
5. The device landed in **stock recovery** at 20:29:17 — **expected**, because the old metadata on the device was already corrupted by the old logdump.
6. User tapped **Factory data reset** once (~20:29:5x) — this really formats `data` + `metadata`.
7. First boot: MTP at 20:30:22, adb at 20:35:00 with `sys.boot_completed=1`; then `f0-postboot-verify.ps1 -RebootTest 3` → **RESULT: PASS (exit 0)**.

### 4.4 Device acceptance evidence

| Criterion | Measured value | Evidence file |
|---|---|---|
| `sys.boot_completed` = 1 | `1` | `device/postflash/boot_completed.txt`, `postflash-final/getprop-final.txt` |
| `init.svc.bootanim` stopped | `stopped` | `postflash/bootanim.txt` |
| No SetupWizard / provisioned | `persist.sys.device_provisioned=1`; `settings device_provisioned=1`, `user_setup_complete=1`; `/system_ext/priv-app/LineageSetupWizard` does not exist; user sees the desktop directly | `postflash/getprop-full.txt`, `provision-final.txt`, `setupwizard-check.txt` |
| FBE healthy | `ro.crypto.state=encrypted`, `ro.crypto.type=file`, `ro.crypto.metadata.enabled=true`, `vold.post_fs_data_done=1`, `sys.user.0.ce_available=true` | `postflash-final/getprop-final.txt` |
| `/metadata` mounted | `/dev/block/sda10 on /metadata type f2fs (rw,…)`; subtree contains aconfig/apex/bootstat/gsi/ota/password_slots/prefetch/staged-install/tradeinmode/vold/watchdog | `postflash-final/mounts.txt`, `postflash/metadata-ls.txt` |
| `/data` mounted | `/dev/block/dm-49 on /data type f2fs (rw,…,inlinecrypt)`; `df`: 213 G, 1.8 G used, 1 % | `postflash-final/mounts.txt`, `data-fs.txt` |
| kernel-side data mount | `F2FS-fs (dm-49): Mounted with checkpoint version = 59dfa388` | `postflash-final/dmesg.txt` |
| logdump removed on device | `/system/bin/logdump.sh: No such file or directory`; `/system/etc/init/logdump.rc: No such file or directory` | `postflash/logdump-check.txt` |
| `init_user0` healthy | logcat has exactly 1 `vold: fscrypt_init_user0` line, 0 `init_user0_failed`, 0 `Failed to create /metadata`, 0 `mount_all --late` | `postflash-final/logcat-all.txt` (grep counts) |
| **no more forced data wipe on reboot (main goal)** | `f0-postboot-verify.ps1 -RebootTest 3` → `RESULT: PASS`, exit 0; after each `adb reboot` `boot_completed=1`; `persist.sys.boot.reason.history` = 3× `reboot,shell` (no factory_reset/recovery) | `postflash-final/postboot-reboot-regression.log`, `boot-reason-history.txt` |
| system services healthy | zygote64/system_server/webview_zygote running; no logdump process; WiFi/BT/camera/sensor/display/fingerprint HAL services running | `postflash-final/ps-A.txt`, `getprop-final.txt` |
| visual evidence | screenshot of Settings (USB preferences page); desktop reachability from user confirmation + `boot_completed=1`/`bootanim=stopped`/Launcher process | `postflash-final/screen-final.png` |

## 5. Side-effect audit (selected findings)

1. **No other live metadata writer** after deletion; all remaining hits are stale free-block bytes, mount entries, SELinux labels, or false positives (Basque resource strings in APKs).
2. **No dangling references**: `logdump.sh`/`logdump_loop2` were referenced only by the deleted `logdump.rc`; there is no `import logdump.rc`; AOSP init auto-scans `/system/etc/init` and a missing rc file is a non-event (`init.cpp:347-380`). Even a hypothetical leftover `exec`/`start` only logs `Could not create exec service` / `Service not found` and does not block boot (`builtins.cpp:244-255`, `270-281`; `parser.cpp:177-184`).
3. **AVB footer is stale**: the F0 raw still carries the old root digest `2a3c7c06…`. This is fine with verity off (current set), but re-enabling verity requires recomputing hashtree/FEC: new system root digest `9103aeb99e58b9356d7f6d1b7a629a148798926a7206ab9cc4dd978beedd5887`, new raw SHA `29ad60fb…`, paired `vbmeta_system_f0_v11.img` (`66e20599…`, staged verify PASS); an avb-enabled `vendor_boot` is also required.
4. **4 KiB policy patch is currently inert**: the F0 set still contains it (block 81367), but `product`/`system_ext` are the LOS builds whose hash files (`75a11da4…`, `71cdbbf6…`) do not match the stock precompiled values, so init compiles CIL at boot and the patch has no effect. If stock `product`/`system_ext` are ever flashed together with this `system`, all three hashes match and init would silently switch to the stock `/odm` precompiled policy — decide explicitly whether to revert that block (see doc 08).
5. **`fastboot -w` ≠ formatting**: on this Windows platform-tools it only erases; the accepted F0 procedure uses recovery "Factory data reset" because stock recovery formats both `data` and `metadata` (`wipe_data.cpp:151-153`).
6. **Dynamic logcat/dmesg on the device** when `init_boot_logging13` is installed writes the `logdump` partition (avc lines about `/dev/block/logdump` are that design, not metadata writes); restoring a clean init_boot removes them.
7. Diagnostic tooling that parsed `LOGDUMP3`/`/metadata/logdump.txt` no longer finds its input; use the logdump-partition kmsg capture or logcat→rawdump instead.

## 6. Unverified / limitations

1. The "metadata is no longer written" property is proven **indirectly** (3 reboots without corruption), not by per-boot metadata dumps.
2. logcat/dmesg evidence covers the last boot only (reboot-3); persistence is proven by the regression log + `boot.reason.history`.
3. "Factory data reset" has no machine-readable receipt from stock recovery; it is established by user confirmation plus indirect evidence (metadata subtree rebuild timestamps, `/data` freshly formatted 213 G / 1.8 G used, no factory_reset/recovery entry in boot reason history).
4. Hardware functions were not exercised (WiFi/camera/audio/sensors/brightness/touch/fingerprint/OTA); only HAL services running was confirmed.
5. Diagnostic-state cleanup was not done in this fix set: SELinux permissive, dm-verity off, testkey root vbmeta, logging init_boot, system_ext without wizard / with auto-provision. Publishing requires reverting these.

## 7. Artifacts (F0 repair set)

| Artifact | Size (B) | SHA-256 |
|---|---|---|
| `system_raw_nologdump.raw` | 10,235,101,184 | `b6ca50f586a80584473c97d44e75f7f3013dd50a17f6f56ef1c47c69b5c709ba` |
| `system_b_changed_blocks.bin` (9 blocks, 36 KiB) | 36,864 | `2e563f37a786f6644fe087a8cbcabc2afbc94d7ce7798499e01be78c533bd5f3` |
| `blocks.tsv` | 375 | `f21ccc7f73019c6b48cd3aec4c61ad12060980b0f4b3744d28da7953c9c660fa` |
| `flash-system-blocks.py` | 9,990 | `b1c47db6cddf65b40b95f6628fe91094e5c9a4a45293deab3a8229bbd931fd13` |
| `edl-dump-system-blocks.py` (read-only pre-check) | 9,169 | `756c1ea7…` |
| `vbmeta_system_f0_v11.img` (future verity-on only) | 65,536 | `66e20599e865029665a944cb69db4b3f34910d3fe9ef087309a72f1acf7bb1eb` |

## 8. Evidence index

| Path | Content |
|---|---|
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\ROOTCAUSE-LOGDUMP-METADATA.md` | first root-cause write-up: rc/script text, image evidence, failure chain, fix plan |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SYSTEM-LOGDUMP-REMOVAL-REPORT.md` | offline removal, 9-block diff table, e2fsck/blockdiff, flashing script |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\F0-SIDE-EFFECT-AUDIT.md` | whole-image scan for other writers, dangling-reference analysis, verity restore recipe, 14-item regression risk list |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SESSION-20261112-FBE-ROOTCAUSE-LOG.md` | experiment archive: the FBE A–F attempts that preceded the discovery, all staged-archive evidence |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SESSION-ADDENDUM-20261112-F0.md` | F0 preparation summary |
| `<PROJECT_ROOT>\out\2026-11-12-edl-f0\F0-ACCEPTANCE-REPORT.md` | on-device acceptance: timeline, EDL write set, criterion table, evidence boundaries, independent audits |
| `<PROJECT_ROOT>\out\2026-11-12-edl-f0\device\postflash-final\` | final evidence: getprop, mounts, dmesg, logcat-all.txt (7.8 MB), reboot regression log, screenshot |
