Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0

# 12 — Experiment Log: Failed Experiments & Excluded Hypotheses (TB323FU / LineageOS 24)

| Item | Value |
|---|---|
| Document status | 2026-11-12; covers all experiment rounds from 2026-11-07 to 2026-11-12 (including pre-history relevant to the conclusions) |
| Applicable device | Lenovo Legion Y700 5th Gen **TB323FU** (SM8850P, canoe/kaanapali), unlocked, active slot B, `super` 20 GiB, 4 KiB sectors, virtual A/B |
| Purpose | **Prevent repeat work.** Every entry records the exact configuration, the observed result, and whether the conclusion is confirmed, inconclusive, or superseded. Read this before designing a "new" experiment — it has probably already been tried. |
| Evidence policy | Results are graded: **HW** = on-device observation/log/readback; **IMG** = offline image analysis; **DECL** = only declared by a script without readback; **USER** = user-observed screen state. Unclosed items are marked **UNVERIFIED**. |
| Companion document | `11-ERROR-CATALOG.md` (what a log line means); `09-AVB-CHAIN-NOTES.md` (why a chain change succeeds/fails); `10-DEBUG-CHANNELS.md` (how to capture the evidence). |
| Related docs | [01 — Device Facts](01-DEVICE-FACTS.md), [03 — Flash](03-FLASH.md), [05 — Root cause: /vendor ELOOP](05-ROOTCAUSE-VENDOR-SYMLINK.md), [06 — Root cause: logdump/metadata](06-ROOTCAUSE-LOGDUMP-METADATA.md), [07 — FBE / init_user0](07-FBE-INIT-USER0.md), [08 — SELinux](08-SELINUX-POLICY.md), [11 — Error Catalog](11-ERROR-CATALOG.md) |

> **Path convention.** `<PROJECT_ROOT>` = project evidence tree, `<WORKSPACE>` = engineering scratch workspace, `<USER_HOME>` = Windows user profile, `<SN-REDACTED>` = device serial, `<MAC>` = any MAC address.

---

## 1. How to read the ledger

- **Configuration** column = the *only* variable that was intended to change. When more than one item changed, the entry is explicitly marked "multi-variable" and its conclusion is downgraded.
- **Result** = what was actually observed (screen state, `adb`, `boot_completed`, recovery, log evidence).
- **Status** = `CONFIRMED` (hardware-verified, repeatable), `INCONCLUSIVE` (confounded by another factor), `SUPERSEDED` (later experiment disproved the earlier conclusion), `NOT RUN` (prepared but never executed).
- The opening rounds (E-numbers) used the same device state repeatedly; many of them are `INCONCLUSIVE` because the slot was already unbootable at the time. Do not cite those as clean evidence.

---

## 2. Master experiment ledger

### 2.1 2026-11-07 — first AVB/chain experiments (E-series)

| # | Config (intended single variable) | Result | Conclusion / status |
|---|---|---|---|
| E1 | 11-07 08:37; stock boot-chain readback + self-built `super_b` + `vbmeta_system_b_full` (added init_boot/pvmfw descriptors) + testkey root | fastbootd flash all OKAY (super 18 sparse chunks, 42.19 s); boot failed back to bootloader fastboot | Missing descriptors for partitions that the chain references (`pvmfw_b`, `dataext_b`) → mixed chain. **INCONCLUSIVE for AVB policy**, useful as a "descriptor completeness" lesson |
| E5 | 11-07 (planned); E1 + `pvmfw_b`/`dataext_b` re-flash | Not executed as a clean round (device was being recovered via full-image restore) | **NOT RUN** as a single-variable round |
| E6 | 11-07 09:14; LOS `system`/`system_ext`/`product` + full vbmeta chain + testkey root + readback `pvmfw`/`dataext`, `set_active b` | First screen → reboot loop; no fallback to fastboot, no corrupt screen; `e2fsck` clean on the four partitions | LOS content problem exists independently of the chain. **CONFIRMED** that "content, not flashing" is the failure domain |
| E7 | 11-07 09:26; same as E6 but `vbmeta_system` `flags=1` (verity off) | Still reboot loop after the first screen | **dm-verity/hashtree is not the cause.** CONFIRMED (superseded the "verity" hypothesis) |
| E8 | 11-07 10:35; re-signed `system` (3 VINTF HAL entries added, no SELinux xattrs) | Changed to **hang at first screen, no reboot** | Behavior changed; footer/descriptor inconsistency suspected. **INCONCLUSIVE** |
| E9 | 11-07 10:59; LOS `system` + full OEM VINTF manifest/matrix (in-place, xattrs kept) | Hang at first screen | **VINTF is not the cause.** CONFIRMED |
| E10 | 11-07; root `flags=1` (community-package style) | Invalid: slot `unbootable:b=yes`, ABL did not attempt to boot | **INCONCLUSIVE** (do not cite as "flags bypass works/fails") |
| E11 | 11-07 11:42; stock `boot` + permissive + testkey re-sign + `chain boot→testkey` | 12 s → back to fastboot; but `slot-unbootable:b` was already yes | **INCONCLUSIVE** (confounded). The clean test "does `boot→testkey` work on a bootable slot" was never run |
| **E12** | 11-07 11:56–12:03; **stock content** + testkey root vbmeta (`chain boot/recovery→OEM`, `chain vbmeta_system→testkey`) + testkey `vbmeta_system` | **Boots: `sys.boot_completed=1`, stock fingerprint** | **CONFIRMED: the device accepts an AOSP-testkey root + testkey vbmeta_system + stock content.** This is the decisive experiment of the whole bring-up |
| E13 | 11-07 12:02; LOS `system` (OEM VINTF) + `vbmeta_system_v4` + the verified E12 chain | Still hang at first screen | **VINTF hypothesis fully excluded; failure is in the LOS user-space content.** CONFIRMED |
| G0 | 11-08; LOS three-part content + `vendor_boot` with panic injection (`panic=10 … pstore.backend=efi`) + patched root, aiming at EFI pstore | Blocked by `slot-unbootable:b`; ABL never attempted the boot | **NOT RUN** (log channel never validated by this route) |

### 2.2 2026-11-09 → 2026-11-10 — full flash and wrapper experiments

| # | Config | Result | Conclusion / status |
|---|---|---|---|
| F1 | 11-09 20:09–20:20; full B-slot flash: `boot→vendor_boot→dtbo→init_boot→recovery→vbmeta→vbmeta_system→super` (sparse 40/40, 54.9 s) + `set_active b` | All checks passed, kernel starts, stuck in the system-start phase (no longer kicked back after ~20 s) | Flashing method was correct; the remaining failure is inside early userspace. **CONFIRMED** |
| E-LOS1 | 11-10 21:38–21:47; `super_test5` (stock super with only `system_b` replaced) + `vbmeta_system_full5` + stock boot chain; EDL write + reset | Reboot loop → EDL | The loop is not caused by the diagnostic wrapper; a "clean" LOS first boot also loops. **CONFIRMED** |
| E-LOS2 | 11-10 22:03–22:42; wrapper vB (`init_boot_new`, correct open, no sleep) + `full6`, then vC (`initlog`, `O_RDONLY / O_WRONLY` bug + `sleep(90)`) | No beacon at 22:06; user observed "pause ~90 s, then repeated reboots"; 22:42 readback OK but `misc` still had no beacon | The wrapper can execute (the 90 s pause matches `sleep`), but at `/init` time the UFS block device does not exist yet (module probe ~1.16 s) and the open flags were wrong. **CONFIRMED mechanism; wrapper unusable** |
| E-LOS3 | 11-10 23:26 → 11-11 00:53; ① restore-stock 15 partitions; ② 00:03 EDL rewrite stock GPT → device bootable again; ③ `init_boot_logging` (**kernel_size=1**) + `vbmeta_system_los`; ④ `logging2` (**kernel_size=0**) + `los2`; ⑤ 00:53 read `misc` | ③ fast reboot loop, wrapper never executes; ④ hang at first screen; ⑤ `misc` @0x80000 = `counter=67 / "IL7" / stage=2` + cmdline | **Two confirmed lessons:** (a) a self-built `init_boot` must have `kernel_size=0`; (b) the wrapper must flush/mark immediately and must not sleep in the parent before `exec /init.real`. `stage=2` proved the wrapper ran and found `misc`, but no stream was flushed |

### 2.3 2026-11-11 — the boot session (A/B groups → diagnostic set → first desktop)

| # | Config | Result | Conclusion / status |
|---|---|---|---|
| A-group | 21:51–21:53; EDL flash `super_v7` (system `/vendor` loop fixed) + `vbmeta_system_v7_stockib` + **stock** `init_boot` | Device rebooted once into the bootloader menu; first stage still died (~0.5 s) | Fixing the `/vendor` symlink loop alone was not sufficient to pass first stage in this configuration. **CONFIRMED observation, cause NOT isolated** |
| B-group | 22:00; fastbootd flash `vbmeta_system_v7` + `init_boot_logging4` (IL9 wrapper) | ~15–18 s later back to bootloader; `misc` log cut at ~482 ms | Same first-stage death; wrapper worked (log captured) but the fatal point was not persisted. **INCONCLUSIVE for the root cause** |
| Diagnostic set | 22:18–22:19; EDL flash stock GPT + `vendor_boot_nofail` (`no_fail` on 13 fstab lines) + `init_boot_logging10` + `vbmeta_system_v8`; all readback MATCH | **22:35: first second stage reached** — `dm-7…dm-13` all mounted with dm-verity, `Opening SELinux policy`, then `Compiling SELinux policy` | **`/vendor` fix proven effective** (first-stage mounts all succeeded, genuine dm-verity mounts, not just `no_fail`). **CONFIRMED.** The caveat: this set changed several items at once, so "which change unlocked first stage" is not single-variable proven |
| diag2 | 22:38–22:44; `vendor_boot_diag2` (all `avb=` flags removed + `no_fail` + `androidboot.selinux=permissive` + `printk.devkmsg=on`) + 1×4 KiB policy-hash sector patch (LUN0 LBA 701429, sector sha `d05ef83d…`) + EDL readback MATCH | 22:39:42 reset → **+18.4 s adb online** (first Android userspace); `system_server` crashed on a signature mismatch | SELinux runtime compile issue bypassed by the policy sector; user-space entry achieved. **CONFIRMED** (the policy sector is a side effect: `system_b` whole-partition SHA no longer equals the image) |
| LOS user-space set | 22:45:59; fastbootd flash LOS `product_b` + LOS `system_ext_b` + `fastboot -w` | 22:48–22:50 **user visually reached the LineageOS welcome screen** (first boot-success criterion), boot animation later stable ≥660 s at 23:08 | Signature conflict fixed (all three user-space partitions now LOS). **CONFIRMED — first "boots to UI" milestone.** `sys.boot_completed` was never directly read in this round (only UI observed) |
| system_ext_mod | 23:12–23:13; EDL flash `system_ext_mod.img` (remove `adb_root.rc`, add `ro.setupwizard.mode=DISABLED`, aera-logdump/provision) | Flashed and readback MATCH; subsequent boots did not enter the system | The mod was never validated on a successful boot. **NOT RUN (no clean result)** |
| 2.7 s death | 23:16; boot died after 2.7 s and fell to stock recovery | kmsg shows `Opening SELinux policy from monolithic file /sepolicy`; `logdump` first 64 MiB all zero | **The boot was a recovery boot** (first-stage mount skipped, recovery ramdisk root). It was **not** a failure of the modified `system_ext` and **not** a `no_fail`-swallowed error. **CONFIRMED diagnosis** |
| diag3 | 23:19:24; EDL flash `vendor_boot_diag3` (cmdline `printk.devkmsg=on`) | Boot still fell to recovery (+37 s) | Not a fix. **SUPERSEDED** (diag2 remained the booting variant) |
| BCB clear | 23:44:47; cold EDL read `metadata`/`misc`/GPT; `misc` BCB = `boot-recovery`; wrote 4 KiB zeros to BCB, readback MATCH, reset | 23:45:05–23:48:10 still recovery (`adb = <SN-REDACTED> recovery`) | **Clearing the BCB is not sufficient** to restore system boot. **CONFIRMED** (BCB is a result, not the cause) |

### 2.4 2026-11-12 — FBE experiments (the user's main complaint)

User complaint being investigated: *"the device only boots after formatting data; after a reboot it returns to recovery with `init_user0_failed`."*

| # | Config | Result | Conclusion / status |
|---|---|---|---|
| FBE-off | 23:50–00:20; `vendor_b_raw_mod` (raw vendor image: `/data` line loses `fileencryption`/`keydirectory`/`metadata_encryption`/`checkpoint`/`inlinecrypt`) + `vendor_boot_diag4` (first-stage fstab loses FBE too) + `fastboot -w` | **First time past `init_user0`**: enters the LineageOS boot animation; then hangs there for minutes (the round recorded >5 min) with USB not enumerating | `init_user0_failed` is bypassable by disabling FBE, but the next blocker (zygote/system_server crash loop) appears. kmsg: repeated `Service 'zygote' (pid N) received SIGKILL`, `sys.init.updatable_crashing=1`. **CONFIRMED for FBE bypass, NOT a fix** |
| FBE-on + checkpoint removal (vendor only) | 00:30–00:40; `vendor_b_checkpoint_off` (stock vendor with only `checkpoint=fs` removed from `/data`) + `vendor_boot_diag2` (first-stage fstab still had checkpoint) + `fastboot -w` | 36–47 s → recovery, `Reason: init_user0_failed` | **Experiment was not clean**: the first-stage fstab still had `checkpoint=fs`, and the two fstab locations must agree. **INCONCLUSIVE** |
| 2b — restore known-good set | 00:35–00:52; re-flash the known-good set (EDL: `vendor_b_full_stock`, `system_ext_raw`, `init_boot_logging10`, `vbmeta_system_v8`, EDL-zero userdata/metadata heads) | Still 47 s → recovery; then stock GPT + clear BCB → still 39 s → recovery | **Lesson:** EDL-zeroing `userdata`/`metadata` superblocks is **not equivalent** to the `fastboot -w`/recovery wipe flow; after repeated raw clears the "first boot reaches wizard" state could not be reproduced. **CONFIRMED process lesson** |
| 7 s death | 00:44; read `misc` (`IL12`): `counter=1247 ticks=700 uptime=7s snaps=2`; last init record `init: [libfs_avb] Device path not found: /dev/block/by-name/vbmeta_b` (6.50 s) | Device died ~7 s after boot, inside first stage | The boot's first-stage fstab still had AVB flags (or the GPT was not stock at that moment — stock GPT was only rewritten at 00:56). **CONFIRMED** mechanism; the exact variant config was not recorded (lesson) |
| #3 — plain v2 software-key FBE | 00:59–01:10; `vendor_b_plainfbe` (FBE stays on, no wrappedkey/metadata-encryption/checkpoint/inlinecrypt; `:v2`) + `vendor_boot_diag5` + `fastboot -w` | Hangs at boot animation >280 s, USB does not enumerate; user confirms "still stuck at boot animation" | The "stuck animation" root cause is **not** the encryption scheme. **CONFIRMED exclusion** (matches FBE-off symptom) |

### 2.5 2026-11-12 — root cause (logdump writes into `metadata`) and F0 verification

| # | Config | Result | Conclusion / status |
|---|---|---|---|
| Root cause | Offline image proof: LOS `system` shipped `/system/bin/logdump.sh` + `/system/etc/init/logdump.rc`; the rc runs `logdump.sh once 0 / 8 / 16 / 24` on `early-init`/`init`/`post-fs-data`/`boot`, and the script does `dd … of=/dev/block/by-name/metadata bs=4096 seek=$((OFF_MB*256)) conv=fsync` | `once 0` overwrites the metadata f2fs superblock **every boot**: first boot after a factory reset is fine → that boot damages metadata → **next** reboot fails to mount metadata → vold/FBE chain fails → `init_user0_failed` → recovery asks to wipe data → loop | **CONFIRMED root cause of the user's main complaint.** The failure chain was reconstructed line-by-line from the previous boot's stale log region (`Failed to create /metadata/vold` → `read_key failed` → `encryptFstab Failed` → `make_f2fs` → `queue_fs_event` → `user_keys` missing → `vdc cryptfs init_user0 Failed`) |
| F0 component | Remove `logdump.sh` + `logdump.rc` from `system` (9 blocks / 36 KiB changed: block 0,1,3,30,53,62069,65536,79494,81367) + keep the policy sector (block 81367, inert in the current set) | `system_raw_nologdump.raw` sha `b6ca50f5…`, 9-block diff exactly matches `blocks.tsv`; `e2fsck -fn` clean | **CONFIRMED offline** |
| F0 hardware verification | 20:24 EDL direct write of the six F0 pieces (9-block system patch + `system_ext_f0diag` + `vendor_b_full_stock` + `vendor_boot_diag2` + `init_boot_logging13` + `vbmeta_system_v10`), readback ALL OK; `power reset`; stock recovery (expected, old metadata was damaged) → user factory data reset → 20:35 `sys.boot_completed=1` → 3/3 reboot regression PASS | No `init_user0_failed`, `/metadata` (sda10 f2fs) and `/data` (dm-49 f2fs inlinecrypt) mount normally, `logdump.sh/rc` absent, adb online | **CONFIRMED — the user-visible bug is fixed.** Acceptance: `f0-postboot-verify.ps1 -RebootTest 3` → `RESULT: PASS` (exit 0) |
| Verity-restore preparation | Recompute system hashtree (`system_verity.raw`, sha `29ad60fb…`, new root digest `9103aeb9…`) + `vbmeta_system_f0_v11` (sha `66e20599…`) + an AVB-enabled `vendor_boot` | Offline `avbtool verify_image` staged verification PASS | **NOT RUN on hardware** — do not enable verity with the F0 set |
| `fastboot fetch` availability | Found while preparing capture: platform-tools 37 supports `fastboot fetch <partition> <file>` in fastbootd | Allows pulling `misc`/`logdump`/`metadata` without cold EDL | **CONFIRMED command exists**; the 512 MiB fetch was not completed end-to-end (**UNVERIFIED** for large partitions) |

---

## 3. Excluded / disproven hypotheses (do not re-run)

| Hypothesis | Status | Evidence |
|---|---|---|
| "A self-signed `vbmeta` always dies at 8 s" | **DISPROVEN** | E12: AOSP testkey root + testkey `vbmeta_system` + stock content boots `sys.boot_completed=1`. Only a **privately generated, non-testkey** key always failed. See `09-AVB-CHAIN-NOTES.md` §5 |
| "The 8 s fallback to fastboot is caused by AVB signature rejection" | **DISPROVEN as a single cause** | Two `init_boot` footers are `Algorithm: NONE` (they are not signed at all). The 8 s value matches AOSP init's `sleep(5)` + reboot-to-bootloader path after a fatal error. Multiple causes: mixed chain/missing descriptors, non-OEM `init_boot`, unbootable slot |
| "Turning dm-verity off (`vbmeta_system flags=1`) fixes the first-screen failure" | **DISPROVEN** | E7: same reboot loop with verity off |
| "VINTF manifest/matrix mismatch is the first-screen cause" | **DISPROVEN** | E9 and E13 with full OEM VINTF still hang |
| "SELinux denials are the blocker" | **DISPROVEN (in that phase)** | The real issue was runtime `secilc` failing with rc=254 because OEM `product`/`system_ext` policy references OEM-only types; using the LOS user-space batch gives rc=0 |
| "Clearing data fixes the reboot problem" | **DISPROVEN as a fix** | It only works until the current boot writes into `metadata` again (F0 root cause). It is a workaround with a one-boot lifetime |
| "`fastboot -w` formats `/data` and `/metadata`" | **DISPROVEN on Windows** | platform-tools without host `mke2fs`/`make_f2fs` only erases; prints `Erase successful, but not automatically formatting. File system type raw not supported.` |
| "Erasing/writing `devinfo`/`efisp`/`uefivarstore` clears `slot-unbootable`" | **DISPROVEN** | These partitions were byte-identical to factory; the slot state lives in GPT attributes (LUN4 `boot_b`, entry #53, attr byte 54). Erasing them changes nothing |
| "`slot-unbootable` is stored in `misc` / RPMB / `persist`" | **DISPROVEN as stated** | No `BCAB` AOSP bootloader-control magic anywhere in `misc`; all byte comparisons of these partitions showed factory-identical content; the fix that worked was rewriting the stock GPT pair |
| "`vendor_boot` cannot be modified because AVB will reject it" | **DISPROVEN** | The unlocked ABL tolerates the hash mismatch (`State: Unlocked, AvbSlotVerify returned …, continue boot`); observed only orange + first-screen failure, no 8 s fallback |
| "`vendor_boot` with `no_fail` is what made the boot succeed" | **DISPROVEN as the root fix** | At 22:35 the log shows genuine `dm-7…dm-13` mounted file systems (not swallowed failures). The actual fix was the `/vendor` symlink loop removal; the 22:18 set changed several things at once, so `no_fail`'s contribution is not isolated |
| "The presence of `dm-N` proves AVB verification passed" | **DISPROVEN** | dm-verity tables are created even with `kVerificationError`; verification is deferred to block reads (EIO on mismatch) |
| "A self-built `init_boot` with a 1-byte kernel works" | **DISPROVEN** | `kernel_size=1` → fast reboot loop, wrapper never executes; must be `kernel_size=0` |
| "The wrapper can wait/sleep for block devices before `exec /init.real`" | **DISPROVEN** | UFS module probe needs real init to proceed (~1.16 s); a parent that sleeps blocks the boot and the device never appears for the child |
| "A `system_ext` service can capture early boot logs" | **DISPROVEN for early stages** | `class core`/`post-fs-data` starts after init has already progressed; captures missed the crash. Use an `init_boot` wrapper |
| "`pstore`/`ramoops`/`last_kmsg`/`logfs` can provide failed-boot logs" | **DISPROVEN** | No ramoops DT node (`dtb_size=0`, all reserved-memory lookups -1), VT/FB off, EFI pstore has no records (failures are not panic-type), `logfs` was zeroed and its FAT destroyed |
| "`adb_root.rc` restarting `adbd` causes `adb shell FAIL closed`" | **DISPROVEN** | Source analysis: `adb_root` is a passive AIDL service; authorization after a data wipe is the real cause |
| "A recovery boot's log can be used to diagnose the ROM" | **DISPROVEN** | Recovery mode skips first-stage mounts and uses a monolithic `/sepolicy`; a 2.7 s death there is expected |
| "The `vbmeta_system` from an earlier round still matches the current `system`" | **DISPROVEN** | Every content change invalidates the system descriptor; a stale pairing produces dm-verity EIO under verity-on. See `09-AVB-CHAIN-NOTES.md` §9 |
| "After `init_boot` re-flash, `dataext_b`/`pvmfw_b`/`recovery_b` can be assumed stock" | **UNVERIFIED assumption** | Their contents were never read back in the boot-fix round. `recovery_b` changed to a non-stock recovery can make `AvbHandle::Open()` fail (`ERROR_INVALID_METADATA`) |
| "Clearing the BCB restores system boot" | **DISPROVEN** | After BCB was cleared the device still booted into recovery (23:45–23:48) |
| "The LOS user-space failure is a VINTF/AVB problem" | **SUPERSEDED** | The first-stage failure was a filesystem topology bug (`/vendor` symlink loop); the user-space failure was a signature mismatch (OEM vs LOS user-space mix); both were fully reproduced and fixed |

---

## 4. Failed configurations (do-not-repeat list)

Each line is a configuration that was tried and did **not** reach the desktop. Reproducing them wastes device cycles unless a new single variable is being tested.

| Configuration (key items + sha prefixes) | Observed result | Why it failed |
|---|---|---|
| `super_test5` + `vbmeta_system_full5` + stock chain | reboot loop → EDL | `/vendor` symlink loop still present in `system` |
| `super_b` + `vbmeta_system_b_full` + testkey root (E1) | fallback to bootloader fastboot | descriptors referenced `pvmfw_b`/`dataext_b` that were not flashed |
| LOS content + OEM `vbmeta_system` (pre-E12) | first screen then loop / hang | content vs descriptor mismatch |
| `vbmeta_system` `flags=1` (E7) | same loop | verity not the cause |
| OEM VINTF replacement (E9/E13) | hang at first screen | VINTF not the cause |
| `init_boot_new`/`init_boot_dbg*` (1-byte kernel) | reboot loop, wrapper never runs | `kernel_size` must be 0 |
| `init_boot` with wrapper doing `sleep(90)` before `exec` | 90 s pause then reboot loop, no persistent log | parent must exec immediately; child handles device polling |
| `vendor_b_raw_mod` (FBE off) | boot animation hang, no USB | next blocker (system_server/zygote) appears |
| `vendor_b_checkpoint_off` only | still `init_user0_failed` | unclean: first-stage fstab still had `checkpoint=fs` |
| `vendor_b_plainfbe` (v2 software keys) | boot animation hang | encryption scheme not the cause of the animation hang |
| `system_ext_mod` (adb_root.rc removed, `ro.setupwizard.mode=DISABLED`) | never validated on a clean boot | `ro.setupwizard.mode` has no runtime consumer in this tree; the reliable bypass is deleting the wizard APK |
| `system_ext_logcat` / `diag3` capture services | empty logdump / header only | `logcat -v pid` invalid; `class core` starts too late |
| `vendor_boot_diag3/4/5` as boot attempts | recovery or hang | not the root cause; diagnostic variants only |
| `fastboot reboot fastboot` from bootloader fastboot | `AdbWriteEndpointSync failed: 超时121` | BL fastboot cannot reach fastbootd when the slot is unbootable |
| EDL-zeroing `userdata`/`metadata` superblocks | could not reproduce the "first boot to wizard" state | raw zeroing ≠ recovery wipe/format; the `wiped`-flag/format path matters |
| Stock GPT + BCB clear as a boot fix | still recovery | BCB was a result; content/FBE chain was the cause |
| "Disable wizard by `ro.setupwizard.mode=DISABLED` only" | no effect | property is not consumed; remove the `LineageSetupWizard` directory + set `device_provisioned`/`user_setup_complete` |
| "Delete `adb_root.rc` to fix adb" | no effect on authorization | passive service; `/data/misc/adb/adb_keys` was wiped |

---

## 5. Process pitfalls that cost the most time (non-technical)

1. **Trusting stale documents.** Conclusions older than the latest flash set were repeatedly wrong ("self-signed vbmeta always dies", "never booted", "`/data` excluded"). Always re-read the current state + the latest evidence directory before acting.
2. **No single-variable discipline in the boot round.** The 22:18 diagnostic set changed GPT, `vendor_boot` flags, `init_boot` wrapper and `vbmeta_system` at once. It proved the `/vendor` fix worked but could not isolate "no_fail" vs "GPT" vs "avb-off". Future rounds should change one item.
3. **Not recording image SHA per boot.** The 7 s death could not be attributed to a specific `vendor_boot` variant because only filenames, not SHA-256, were logged. Record the SHA of every flashed partition before each boot.
4. **Mixing multiple boots' logs.** `misc` ring/snapshot regions from different boots look continuous. Split by `ctl.snap_len` (IL12) or the last `INITLOG13` header before analysis.
5. **Trusting flash tool success messages.** EDL reports success on failed LUN4 writes; every write must be read back and hashed.
6. **Capture scripts that silently do nothing.** `logcat -v pid` (invalid) and `logcat -G` (sets size then exits) both produced "header-only" captures that were mistaken for "no crash".
7. **Recovery boot mistaken for a ROM failure.** A recovery-mode boot skips first-stage; analysing it as a normal boot leads to wrong conclusions.
8. **Diagnostic writes into `metadata`.** The pre-F0 capture script wrote raw blocks into `metadata`; this created the very `init_user0_failed` loop it was meant to diagnose.
9. **Unclean data-state manipulation.** Erasing superblocks with EDL is not the same as a recovery format; the "first boot after factory reset" state could not be reproduced this way.
10. **Tool/session hygiene.** A stale `fh_loader` holds COM3; an `adb` server may already own 5037; PowerShell variables are case-insensitive (`$O` vs `$o`) and caused path mix-ups in capture scripts; helper-function `$args` conflicts produced evidence files that were actually adb help text (must be regenerated from full snapshots).
11. **Disk space.** Large image generation filled the host disk; free space was recovered from stale intermediate images. Clean before generating 20 GiB images.
12. **Device RTC is GMT.** Screen/dmesg times are 8 h behind local time; this is normal and not a boot bug.

---

## 6. Next-round experiment queue (not yet run)

| # | Experiment | Purpose | Status |
|---|---|---|---|
| F1 | Hardware function tests (Wi-Fi, camera, audio, sensors, brightness, touch, fingerprint, OTA) | only HAL services "running" was verified; no functional tests | **TODO** |
| F2 | ≥5 cold boots + one power-loss reboot on the F0 set | data persistence beyond the 3-reboot acceptance | **TODO** (3/3 already PASS) |
| F3 | Restore dm-verity/enforcing with `system_verity.raw` (`29ad60fb…`) + `vbmeta_system_f0_v11` (`66e20599…`) + AVB-enabled `vendor_boot` | release-state hygiene | **TODO — recipe ready, not hardware-verified** |
| F4 | `printk_ratelimit=0` / `printk_ratelimit_burst=9999` in the wrapper | stop producer-side log dropping | **TODO** (proposed, unbuilt) |
| F5 | Clean-slot test of `chain boot→testkey` | close the E11 inconclusive result | **TODO** |
| F6 | Read back `dataext_b`/`pvmfw_b`/`recovery_b` and compare with stock | close the "assumed stock" assumptions | **TODO** |
| F7 | Full 512 MiB `logdump` fetch via fastbootd | validate the fastest capture path | **TODO** |
| F8 | Decide whether to revert the policy-hash block in the F0 `system` | the patch is currently inert; if stock `product`/`system_ext` is ever flashed together it would silently switch to the stock precompiled policy | **TODO (decision)** |

---

## 7. Evidence sources (relative to `<PROJECT_ROOT>`)

- `out/2026-11-10-los24-logdump/LOS24-PLAYBOOK-CONSOLIDATED.md` §5 (experiment ledger E1–E13, E-LOS1/2/3), §6.1 (overturned conclusions), §6.3 (new lessons).
- `out/2026-11-10-los24-logdump/FACTS-SESSIONS.md` §3, §5, §6, §8, §10 (history, impossible channels, do-not-do list).
- `out/2026-11-11-los24-bootfix/SESSION-20261112-FBE-ROOTCAUSE-LOG.md` — 2026-11-12 FBE experiment rounds #1/#2/#2b/#3 and diagnosis channels.
- `out/2026-11-11-los24-bootfix/ROOTCAUSE-LOGDUMP-METADATA.md` — final root cause of the metadata damage and the FBE chain.
- `out/2026-11-11-los24-bootfix/SYSTEM-LOGDUMP-REMOVAL-REPORT.md` — F0 component construction and offline verification.
- `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` — F0 hardware acceptance (boot + 3/3 reboot regression) and remaining risks.
- `out/2026-11-11-los24-bootfix/VERIFY-REPORT.md` — `/vendor` ELOOP root cause and independent verification.
- `out/2026-11-11-los24-bootfix/BOOT-DOCTOR-REVIEW.md` — capture verdicts and the split-by-`snap_len` correction.
- `out/2026-11-11-los24-bootfix/ADB-ROOT-ANALYSIS.md` — adb authorization, wizard bypass, recovery-boot diagnosis.
- `reports/BOOT-SUCCESS-20261111.md` (under `<WORKSPACE>/reports/`) — timeline reconstruction of the 2026-11-11 boot round, including the caveats (`sys.boot_completed` not directly read, single-variable not isolated).
