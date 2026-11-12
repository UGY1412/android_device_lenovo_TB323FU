Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0 (original text)

# 11 — Error Catalog (Lenovo Legion Y700 5th Gen, TB323FU / LineageOS 24)

| Item | Value |
|---|---|
| Document status | 2026-11-12; all entries below were observed on this device during the 2026-11-07 → 2026-11-12 bring-up, or are error constants/strings quoted from the stock firmware binaries. None of them is invented. |
| Applicable device | Lenovo Legion Y700 5th Gen **TB323FU** (SM8850P, canoe/kaanapali), unlocked, active slot B, `super` 20 GiB / 4 KiB sectors, virtual A/B |
| Purpose | Turn a raw log line into a diagnosis and an action. This is the most-used document in this repository for "the device does not boot / the flash did not take / the capture is empty". |
| Reading order | Find the exact line in §2–§6, then run the matching command in §7. If the same line appears in a *different* boot context than expected, check the capture-health rules in §6 first. |
| Related docs | [05 — Root cause: /vendor ELOOP](05-ROOTCAUSE-VENDOR-SYMLINK.md), [06 — Root cause: logdump/metadata](06-ROOTCAUSE-LOGDUMP-METADATA.md), [07 — FBE / init_user0](07-FBE-INIT-USER0.md), [08 — SELinux](08-SELINUX-POLICY.md), [09 — AVB Chain Notes](09-AVB-CHAIN-NOTES.md), [10 — Debug Channels](10-DEBUG-CHANNELS.md), [12 — Experiment Log](12-EXPERIMENT-LOG.md) |
| Evidence policy | Verbatim text is quoted from on-device logs; where a value is variable, the source reports use placeholders (`N`, `<mp>`, `<pid N>`) and those are kept. Criteria that have no literal error message are marked **(criterion)**. Anything not closed is marked **UNVERIFIED**. |

> **Path convention.** `<PROJECT_ROOT>` = project evidence tree, `<WORKSPACE>` = engineering scratch workspace, `<USER_HOME>` = Windows user profile, `<SN-REDACTED>` = device serial, `<MAC>` = any MAC address.

---

## 1. Source index

Evidence files below are relative to `<PROJECT_ROOT>` and live in `out/2026-11-11-los24-bootfix/` unless stated otherwise.

| Ref | File |
|---|---|
| [S1] | `out/2026-11-11-los24-bootfix/VERIFY-REPORT.md` |
| [S2] | `out/2026-11-11-los24-bootfix/BOOT-DOCTOR-REVIEW.md` |
| [S3] | `out/2026-11-11-los24-bootfix/REBUILD-ZYGOTE-TIMELINE.md` |
| [S4] | `out/2026-11-11-los24-bootfix/SESSION-20261112-FBE-ROOTCAUSE-LOG.md` (2026-11-12 FBE root-cause experiment log) |
| [S5] | `out/2026-11-11-los24-bootfix/INIT_USER0-ANALYSIS.md` |
| [S6] | `out/2026-11-11-los24-bootfix/SYSTEM_SERVER_CRASH-HYPOTHESES.md` |
| [S7] | `out/2026-11-11-los24-bootfix/ADB-ROOT-ANALYSIS.md` |
| [S8] | `out/2026-11-11-los24-bootfix/SELINUX-COMPILE-ANALYSIS.md` |
| [S9] | `out/2026-11-11-los24-bootfix/SYSTEM-LOGDUMP-REMOVAL-REPORT.md` |
| [S10] | `out/2026-11-11-los24-bootfix/ROOTCAUSE-LOGDUMP-METADATA.md` |
| [S11] | `out/2026-11-11-los24-bootfix/NEXT-ROUND-TEST-PLAN.md` |
| [S12] | `out/2026-11-11-los24-bootfix/SESSION-ADDENDUM-20261112-F0.md` |
| [S13] | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` |
| [S14] | `out/2026-11-11-los24-bootfix/F0-SIDE-EFFECT-AUDIT.md` |
| [S15] | `out/2026-11-11-los24-bootfix/SYSTEMEXT-LOGCAT3-REPORT.md` |
| [S16] | `out/2026-11-11-los24-bootfix/SCRIPT-BUG-AUDIT.md` |
| [S17] | `out/2026-11-11-los24-bootfix/BOOTFIX-FACTS.md` |
| [S18] | `out/2026-11-10-los24-logdump/FACTS-SESSIONS.md` |
| [S19] | `out/2026-11-10-los24-logdump/RECOVERY-PLAYBOOK.md` |
| [S20] | `out/2026-11-10-los24-logdump/LOS24-PLAYBOOK-CONSOLIDATED.md` |
| [S21] | `out/2026-11-11-los24-bootfix/FLASH-CHECKLIST.md` |
| [S22] | `out/2026-11-11-los24-bootfix/F0-FLASH-BUNDLE.md` |
| [S23] | `reports/BOOT-SUCCESS-20261111.md` (under `<WORKSPACE>/reports/`) |
| [S24] | `out/2026-11-11-los24-bootfix/INITLOG13-BUILD-REPORT.md` |
| [S25] | `out/2026-11-11-los24-bootfix/INITLOG12-BUILD-REPORT.md` |
| [S26] | `out/2026-11-11-los24-bootfix/SYSTEMEXT-LOGCAT2-REPORT.md` |
| [S27] | `out/2026-11-11-los24-bootfix/ZYGOTE-CRASH-ANALYSIS.md` |
| [S28] | `out/2026-11-11-los24-bootfix/IMAGE-FIX-REPORT.md` |
| [S29] | `out/2026-11-11-los24-bootfix/VENDORBOOT-DIAG2-REPORT.md` |
| [S30] | `out/2026-11-11-los24-bootfix/VENDORBOOT-NOFAIL-REPORT.md` |

---

## 2. Category A — AVB / first-stage mount

| ID | Verbatim text | Meaning | Handling | Source |
|---|---|---|---|---|
| AVB-01 | `init: [libfs_avb] Device path not found: /dev/block/by-name/vbmeta_b` | first-stage fstab asked for AVB on `vbmeta_b`, but `/dev/block/by-name/vbmeta_b` was not available within the 1 s `WaitForFile` window. Typical causes: the booted `vendor_boot` is **not** the avb-off diagnostic variant, or GPT/by-name is not stock | confirm the flashed `vendor_boot` SHA-256 is `vendor_boot_diag2` (`40623569…`) or another avb-off variant; verify stock GPT; recapture | [S3] §4.2, [S4] §2, [S2] §1 |
| AVB-02 | `Failed to mount required partitions early` | first-stage init received `false` from `DoFirstStageMount()`; PID 1 aborts → kernel panic/reboot. The message itself is usually swallowed before it reaches storage | treat as "first-stage mount failed"; identify the partition from adjacent lines (`libfs_avb`, `Failed to mount <mp>`, `ELOOP`); check fstab/vbmeta/GPT | [S1] §1 F2, [S2] §1 stage 0 |
| AVB-03 | `os.open   /vendor          => 40 ELOOP Too many levels of symbolic links` (also `realpath /vendor`, `os.stat /vendor`, `/system/vendor`) | LOS `system` root had `/vendor → /system/vendor` and `/system/vendor → /vendor` (mutual symlink loop); `fs_mgr_create_canonical_mount_point("/vendor")` fails, `/vendor` is a required mount → first-stage FATAL | rebuild the `system` raw with `/vendor` as a real directory (0755) and `/dataext` as a directory; keep `/system/vendor → /vendor`; re-sign hashtree | [S1] §1.3 F4, [S28] §(root cause) |
| AVB-04 | `Failed to mount /system` | `TrySwitchSystemAsRoot()` could not mount `/system`; first-stage fatal | verify `system` content vs `vbmeta_system` digest and that a bootable `vendor_boot` (avb on/off matching the set) is flashed | [S2] §1 stage 0, [S1] §1 F2 |
| AVB-05 | `[libfs_avb] Failed to load vbmeta` / `Failed to setup verity` (pattern; partition name varies) | AVB/verity initialization failed for that partition; the following mount fails (or is ignored only if `no_fail` is present) | check the vbmeta partition content and descriptor pairing; under an unlocked bootloader only signature errors are tolerated, not broken metadata | [S2] §1 stage 0 |
| AVB-06 | `ERROR_INVALID_METADATA` (libavb error constant) | a chained vbmeta/partition has no valid AVB metadata (e.g. a non-stock `recovery_b` with an unrelated boot image). This error is **not** excused by unlocked/permissive; `AvbHandle::Open()` can return null and first-stage dies at the same point as AVB-03 | read back `recovery_b` and compare with the stock `a3b34a80…` image; restore stock recovery when it differs | [S1] §4.2, [S20] §2.2 N2 |
| AVB-07 | `ERROR_VERIFICATION` / `PUBLIC_KEY_REJECTED` (libavb error constants) | signature/hash verification error. With the bootloader unlocked, ABL/`fs_avb` treats these as permissive (`IsAvbPermissive()`), so they are expected when testkey or modified content is used | not an action item by itself; do not "fix" by locking the bootloader. Confirm the boot state via `ro.boot.verifiedbootstate` | [S1] §1 F6.5, [S20] §2.2 N2 |
| AVB-08 | `Failed to mount <mp>, ignoring mount for no_fail partition` (INFO) | first-stage mount failed but the fstab entry has `no_fail`, so the failure is ignored and boot continues | diagnostic variants only; never treat "no fatal" as "the partition mounted". Check for the *positive* line `EXT4-fs (dm-…) … mounted filesystem` instead | [S6] §5 Q1, [S30] §(note) |
| AVB-09 | `Failed to boot into userspace fastboot; one or more components might be unbootable.` | the slot is marked unbootable or the boot chain is broken, so the bootloader refuses to boot fastbootd | fix slot attributes/content first (stock GPT pair + a known-bootable image set); do not keep retrying `fastboot reboot fastboot` | [S18] §9 CANNOT 3 |
| AVB-10 | `Your device is corrupt` | user-visible corrupt-screen path; ABL/AVB rejected the boot and/or the slot is unbootable → recovery/data-wipe prompt | do not clear data as a reflex; read GPT slot attributes and the current vbmeta/chain first; recover with EDL | [S23] §4, [S20] §3.2 |
| AVB-11 | `Reset unbootable slots failed enter fastboot mode` / `No bootable slots found enter fastboot mode` | strings inside the stock ABL image: ABL could not reset/prove a bootable slot and entered fastboot | write the stock GPT main+backup pair and re-check `slot-unbootable:b`; then verify a known-bootable set | [S19] §1.1 (ABL binary strings) |

---

## 3. Category B — `/metadata`, FBE and `init_user0`

| ID | Verbatim text | Meaning | Handling | Source |
|---|---|---|---|---|
| FBE-01 | `vold: Failed to create /metadata/vold: Read-only file system` | `/metadata` was not mounted; the directory falls into the read-only root. Root cause in this project: the LOS `system` shipped `logdump.sh`, which raw-wrote into the `metadata` partition every boot and destroyed the f2fs superblock | check the F2FS mount line (see §7); remove the `logdump.sh`/`logdump.rc` from `system` (F0); factory-reset once so metadata is formatted by recovery | [S11] §(chain), [S12] §(evidence), [S10] |
| FBE-02 | `vold: read_key failed in mountFstab` | metadata-encryption/FBE key couldn't be read; almost always a downstream symptom of FBE-01 (metadata absent) | fix the metadata mount first; only then test checkpoint/wrappedkey variants | [S3] §6 stale chain, [S12] |
| FBE-03 | `cryptfs encryptFstab Failed` | FBE fstab setup failed after the metadata key read failed (vold-side log line) | same as FBE-02 | [S12] §(chain), [S10] |
| FBE-04 | `make_f2fs` appearing in the 6–8 s window **(criterion)** | `/data` was formatted again because the fstab entry is `formattable` and encryption state was interrupted — a symptom of the metadata chain, not an independent bug | treat FBE-01/02/03 as the cause; do not chase `make_f2fs` | [S2] §1 stage 1a |
| FBE-05 | `init: Command 'mount_all /vendor/etc/fstab.qcom --late' … failed: queue_fs_event() failed: Invalid code: -1` | second-stage `mount_all --late` failed → `on post-fs-data` never ran | inspect why `mount_all` failed (usually metadata/data); verify `/metadata` and `/data` mounts before this line | [S10], [S2] §1 stage 1a, [S12] |
| FBE-06 | `cutils: Failed to mkdir(/data/misc/vold/user_keys): No such file or directory` / `vold: Failed to prepare /data/misc/vold/user_keys` | `/data/misc` was never created because `post-fs-data` did not run | treat as a consequence of FBE-05; fix the mount chain | [S2] §1 stage 1b |
| FBE-07 | `vdc: Command: cryptfs init_user0 Failed: Status(-8, EX_SERVICE_SPECIFIC): '0: '` | `init_user0` failed directly; init reboots into recovery with `--reason=init_user0_failed` | capture the full chain (FBE-01→07) with an init_boot wrapper; do not only read the last line | [S10], [S2] §1 stage 1b, [S6] §5 |
| FBE-08 | `init: vdc call failed with error code: 25` / `vdc terminated by exit(25)` | vold returned a non-zero status for the `vdc cryptfs init_user0` call | same as FBE-07 | [S2] §1 stage 1b |
| FBE-09 | `Can't load Android system. Your data may be corrupt.` + `Reason: init_user0_failed` | recovery prompt shown after init deliberately called `reboot_into_recovery(--prompt_and_wipe_data --reason=init_user0_failed)` | the reason string is the diagnostic key: it points at FBE, not at dm-verity/ABL. Fix the metadata/FBE chain instead of wiping data repeatedly | [S5] §1.6, [S4] §1 |
| FBE-10 | `init: [libfs_avb] Device path not found: /dev/block/by-name/vbmeta_b` in the *previous* boot's stale log region | if read without splitting the `misc` log by `ctl.snap_len`, a stale failure chain from the previous boot can be mistaken for the current one | split by `ctl.snap_len` before analysis; the 7 s failure file contained the previous boot's init_user0 chain after `snap_len` | [S3] §(snap_len), [S2] §2 G11 |

---

## 4. Category C — userspace, system_server, adb and SELinux

| ID | Verbatim text | Meaning | Handling | Source |
|---|---|---|---|---|
| USR-01 | `init: Service 'zygote' (pid N) received SIGKILL` | zygote was killed; this line does **not** identify the killer | search for `Exit zygote because system server`, crash-buffer `FATAL EXCEPTION`, OOM/lmkd, watchdog; capture logcat | [S27] §(receiver), [S4] §1 |
| USR-02 | `init: Sending SIGKILL to service 'zygote' (pid N) process group...` | init reaping the leftover process group *after* the zygote received SIGKILL; not the original kill cause | never read this as "init killed zygote first"; correlate order with USR-01 | [S2] §1 stage 2, [S3] §(conclusion) |
| USR-03 | `init: processing action (sys.init.updatable_crashing=1) from (/system/etc/init/flags_health_check.rc:10)` / `flags_health_check UPDATABLE_CRASHING` | cascade after the 4th+ crash; a symptom, not the root cause | record it, then find the first crash in the sequence | [S2] §1 stage 2, [S4] §1 |
| USR-04 | `Exit zygote because system server (pid N) has terminated` | direct fingerprint that `system_server` died (zygote SIGCHLD handler). **Only appears in logcat**, not in kmsg | capture logcat (rawdump) or the crash buffer; this is the key line for system_server-level failures | [S2] §1 stage 2 |
| USR-05 | `*** FATAL EXCEPTION IN SYSTEM PROCESS` | Java crash stack top of `system_server` in the logcat crash buffer | read the stack below this line; classify VINTF/HAL vs keystore/keymint vs other | [S2] §1 stage 2, [S6] §6 |
| USR-06 | `WATCHDOG KILLING SYSTEM PROCESS` | `system_server` was killed by the watchdog | capture the watchdog stack in logcat; usually requires a longer capture window | [S2] §1 stage 2 |
| USR-07 | `Signature mismatch on system package com.motorola.android.providers.settings for shared user android.uid.system/1000` | signature conflict caused by mixing LOS `system` (testkey) with OEM `product`/`system_ext` (Lenovo signatures); `system_server` crashes | flash `product` and `system_ext` from the same LOS build batch, then wipe data once; keep the three user-space partitions in one batch | [S23] §1–§2, [S20] §6.1 |
| USR-08 | `logcat: Invalid -v 'pid'` | invalid logcat format option; the process exits and the capture is empty | use `-v threadtime` (optionally `,usec`); never `-v pid` | [S4] §5, [S2] §1 stage 4 |
| USR-09 | `exec logcat -G 16M -b all -v threadtime` produces a header but no log lines **(criterion)** | `logcat -G` only sets the buffer size and then returns `EXIT_SUCCESS` immediately (`system/logging/logcat/logcat.cpp:1165`); the read loop is never entered | split into two commands: `logcat -b all -G 16M >/dev/null 2>&1`, then `exec logcat -b all -v threadtime` | [S15] §(bug), [S16] §1.1 |
| USR-10 | `avc: denied { execute_no_trans } ... path="/system/bin/logdump.sh"` | the current boot's `system` still tries to execute the old `logdump.sh` → the F0 fix is not in effect | verify `/system/bin/logdump.sh` and `/system/etc/init/logdump.rc` do not exist in the flashed image; reflash the F0 system | [S2] §1 stage 4 |
| USR-11 | `avc: denied ... permissive=1` (observed volumes: 3,541 lines in one full logcat; 94 lines for `/dev/block/logdump` in logcat and 7 in dmesg) | SELinux denials in permissive mode: logged but **not enforced**, therefore not fatal. The `/dev/block/logdump` ones are the intended behavior of the `initlog13` writer | in the diagnostic state this is expected; after switching to enforcing, add/verify the `logdump` partition label and allow rules | [S13] §9, [S14] §4 #13 |
| USR-12 | `adb shell` commands report `FAIL closed` while `adb devices` shows the transport | transport is up but the shell service is refused; most likely host key authorization was lost (`fastboot -w`/factory reset clears `/data/misc/adb/adb_keys`, and `ro.adb.secure=1`) | re-authorize USB debugging on the device (or check `adb devices` shows `unauthorized`); `adb_root.rc` is a passive service and is **not** the cause | [S7] §0/§3, [S17] §(adb) |
| USR-13 | `device unauthorized` | host public key is not present in `/data/misc/adb/adb_keys` | accept the RSA prompt on the device, or re-add the host key; do not weaken `ro.adb.secure` except for short diagnostics | [S7] §3 |
| USR-14 | `Opening SELinux policy from monolithic file /sepolicy` / `First stage mount skipped (recovery mode)` | the boot is a **recovery** boot: first-stage mounting is skipped and a monolithic `/sepolicy` from the recovery ramdisk is used. This is not the normal LOS boot path | recognize and exclude; fix the fallback cause (BCB/slot/content), then recapture. Do not diagnose the ROM from this log | [S7] §7.1/§7.3 |
| USR-15 | `DM_DEV_STATUS` ioctl fails `ENXIO` → `Could not update logical partition` | in the recovery-mode fallback, `MountMissingSystemPartitions()` tried to remap `system_ext`/`product` but their dm-linear devices never existed, because first-stage never ran | same as USR-14: this is a recovery-boot artifact | [S7] §7.2 |
| USR-16 | `Failed to resolve typeattributeset statement at /system_ext/.../system_ext_sepolicy.cil:2` → `Failed to compile cildb: -2` (secilc rc=254) | runtime SELinux policy compilation failed: the OEM `product`/`system_ext` policies reference OEM-only types (`mediaserverwrapper` etc.) that the LOS platform policy does not define | use LOS `product` + `system_ext` in the same batch (verified rc=0), or the precompiled-policy path; stub types are not a viable fix | [S8] §(matrix A/E/F) |

---

## 5. Category D — flashing toolchain (EDL / fastboot / GPT)

| ID | Verbatim text | Meaning | Handling | Source |
|---|---|---|---|---|
| FLS-01 | `invalid gpt entry number 128` (followed by a SUCCESS line) | old-style fh_loader LUN4 write failed but still printed success (false success) | use the new XML style (`--zlpawarehost=1`, `partofsingleimage`/`readbackverify`, real partition labels), then read back and hash | [S20] §2.2 N9, [S19] §1.3 |
| FLS-02 | `Not a valid GPT signature` (×8 in one soft-EDL attempt) | writes were sent to a soft (`adb reboot edl`) session and silently discarded; 8 errors = nothing written | never flash in soft EDL; cold 9008 only (power off + Volume+ + long-edge USB) | [S18] §4.2, [S19] §2 |
| FLS-03 | `{ERROR: Something failed during patching}` / `<response value="NAK" .../>` | Firehose `patch` command is NAKed by this device's programmer | do not use patch; write whole sectors/partitions with `program` | [S19] §1.3 |
| FLS-04 | `target not stable` | EDL session unstable: port takes ~10 s to open, programmer upload or reads fail, device enters/exits crashdump | re-enter cold EDL, reset the session from the toolkit ("read info"), retry once; do not loop indefinitely | [S18] §4.2, [S20] §4.3 |
| FLS-05 | `Sahara protocol error` | soft-EDL or otherwise unhealthy 9008 session | cold EDL entry + session reset | [S4] §5 |
| FLS-06 | `AdbWriteEndpointSync failed: 超时121` (timeout 121) | entering fastbootd from bootloader fastboot timed out; device stays in bootloader fastboot | do not enter fastbootd from the read-only bootloader fastboot; use recovery adb or cold EDL instead | [S17] §(history) |
| FLS-07 | `remote: 'unknown command'` (for `flash`, `set_active`, `oem edl`) | bootloader fastboot is read-only on this device | use fastbootd (physical+logical writes, `set_active`) or EDL; BL fastboot is only `getvar`/`reboot`/`reboot recovery` | [S18] §9 CANNOT 1, [S4] §5 |
| FLS-08 | `unknown partition` when flashing `vendor_b`/`vbmeta_system_b` etc. in fastbootd | fastbootd partition names carry no `_b` suffix | use `vendor`, `vendor_boot`, `system_ext`, `init_boot`, `vbmeta_system`, … (short names) | [S4] §5, [S11] §(pitfalls) |
| FLS-09 | `Erase successful, but not automatically formatting. File system type raw not supported.` | `fastboot -w` on this Windows platform-tools only **erases** (no host `mke2fs`/`make_f2fs`), so `metadata`/`userdata` are left unformatted | use stock recovery "Factory data reset" (real `make_f2fs`), or an explicitly verified `fastboot format`; then reboot | [S16] §1.1, [S6] §5 (fastboot -w) |
| FLS-10 | `Invalid sparse file format at header magic` | a sparse image was sent through the bootloader fastboot path | flash `super`/large images through fastbootd (sparse transfer works) or write raw through EDL | [S18] §4.3 |
| FLS-11 | EDL write/read-back SHA differs from the expected value (checklist expects `MATCH`) **(criterion)** | the write did not land, or the read was a false success / partial transfer | re-write, then read back head+middle+tail (or the whole partition) and compare SHA-256; never continue on a mismatch | [S21] §3, [S13] §2 |
| FLS-12 | GPT backup table differs from the main table / from the reference file by a few bytes (observed: entries attr `0x77→0x6F` + header CRC, 9 bytes) **(criterion)** | ABL or a tool re-committed one copy; the slot `unbootable` bit is still 0 in both, so it is not blocking, but the pair is not byte-identical | write the stock GPT main+backup pair as a couple; if only one differs, rewrite both and re-read both | [S20] §7 U6, [S19] §Problem 2 step 2 |

---

## 6. Category E — capture health / log hygiene

| ID | Verbatim text | Meaning | Handling | Source |
|---|---|---|---|---|
| CAP-01 | `logcat: Invalid -v 'pid'` (again, see USR-08) | capture dies at startup; the target partition contains only the header | fix the script (`-v threadtime`) and re-capture | [S4] §5, [S2] §1 stage 4 |
| CAP-02 | header present but no content, e.g. `==== AERA_LOGCAT_BEGIN uptime=… ====` only **(criterion)** | `CAPTURE-FAILED` — the capture service started but its stream never ran | check the service command line (USR-08/USR-09); fix and reflash | [S2] §1 stage 4 |
| CAP-03 | log target is all zeros (e.g. 64 MiB of 0x00) **(criterion)** | `CAPTURE-NOT-RUN` — the capture service never executed at all | the boot died before the service started, or the wrong partition was read; check the boot stage first | [S2] §1 stage 4, [S2] §0 |
| CAP-04 | `==== LOGDUMP3 mode=once ... uptime=... ====` / `AERA_DMESG` found in a `metadata` dump | `PRE-F0-DIAG`: the pre-F0 `logdump.sh` was active (it wrote into `metadata`). Metadata snapshots are from **past** boots, not a live boot-stage log | use it only as "F0 not yet applied" evidence; do not use it to judge the current boot | [S2] §1 stage 4, [S10] |
| CAP-05 | `init: 305/718 output lines suppressed` / `init: 718 output lines suppressed` | kernel `printk` ratelimit dropped lines at the producer; `printk.devkmsg=on` helps `devkmsg` reads but does not remove `printk_ratelimit` | set `printk_ratelimit=0` and `printk_ratelimit_burst=9999` once `/proc` is mounted (proposed wrapper step, **UNVERIFIED**); increase `log_buf_len` if possible | [S23] §5, [S7] §7.4 |
| CAP-06 | `misc` log region contains two boots concatenated **(criterion)** | `initlog12`/`initlog13` write a ring/stream; without splitting by `ctl.snap_len` (IL12) or the last `==== INITLOG13` header, stale records from the previous boot pollute the timeline | split by control-block length / last header before grepping | [S3] §(snap_len), [S2] §2 G11 |
| CAP-07 | `Failed to mount /dataext` | second-stage `/dataext` mount failed (usually because `dataext_b` content does not match the root-vbmeta hashtree); non-fatal but breaks data-extension behavior | read back `dataext_b` and compare with stock; do not diagnose it as a boot blocker | [S1] §4.3 |

---

## 7. Judgement commands (run these before/after the table lookup)

### 7.1 Boot state and slot

```bash
adb devices -l                                  # device / unauthorized / recovery
adb shell getprop sys.boot_completed            # "1" = boot completed
adb shell getprop init.svc.bootanim             # "stopped" required for success
adb shell getprop ro.boot.verifiedbootstate     # orange = unlocked (diagnostic state)
fastboot getvar current-slot
fastboot getvar slot-unbootable:b               # must be "no"
fastboot getvar is-userspace                    # yes = fastbootd
```

### 7.2 First-stage / AVB

```bash
grep -aE "init first stage started|Failed to mount required partitions|libfs_avb|ELOOP|Failed to mount" logdump.bin
grep -aE "EXT4-fs \(dm-|Opening SELinux policy|Compiling SELinux policy" logdump.bin
grep -aE "silently ignoring|no_fail" logdump.bin           # diagnostic fstab only
```

**Success criterion for first stage:** at least 7 `EXT4-fs (dm-…) … mounted filesystem` lines, followed by `Opening SELinux policy` (or `Compiling SELinux policy`). A missing `EXT4-fs` block with a `libfs_avb` line = dead in first stage.

### 7.3 Metadata / FBE / init_user0

```bash
grep -aE "F2FS-fs \(sda10\)|Failed to create /metadata/vold|read_key failed|encryptFstab" logdump.bin
grep -aE "init_user0|user_keys|mount_all /vendor/etc/fstab.qcom|queue_fs_event|vdc call failed" logdump.bin
adb shell cat /proc/mounts | grep -E "metadata|userdata"   # only if adb works
```

**Success criterion for metadata:** `F2FS-fs (sda10): Mounted with checkpoint version = …` exists in the current boot segment. `sda10 = metadata`, `sda14 = userdata` for the stock GPT.

### 7.4 system_server / userspace

```bash
grep -aE "starting service 'zygote'|received SIGKILL|Sending SIGKILL|updatable_crashing" logdump.bin
grep -aE "Exit zygote because system server|FATAL EXCEPTION IN SYSTEM PROCESS|WATCHDOG KILLING" rawdump.bin
adb logcat -b all -d | grep -E "Boot completed|init_user0|FATAL EXCEPTION"
```

**Success criterion:** `sys.boot_completed=1` **and** `init.svc.bootanim=stopped`. A UI screenshot alone is not a criterion.

### 7.5 Captures

```bash
python3 boot-doctor-reviewed.py <dump.bin> --tag <label> --out <outdir>
python3 boot-doctor-reviewed.py <evidence_dir> --out <outdir>     # one verdict per file, no cross-boot mixing
python3 - <<'PY'
import struct
d=open("misc_fetched.bin","rb").read(); o=0x80000
print(d[o+4:o+8], struct.unpack_from("<I",d,o+8)[0], struct.unpack_from("<I",d,o+24)[0])
PY
```

### 7.6 Images (offline)

```bash
avbtool info_image   --image <partition_image>      # footer parameters, root digest
avbtool verify_image --image <partition_image> --key testkey_rsa4096.pem
certutil -hashfile <image> SHA256                   # Windows
Get-FileHash <image> -Algorithm SHA256              # PowerShell
```

---

## 8. Decision tree (first 60 seconds)

```
Device behaviour?
├─ 8–12 s → bootloader fastboot
│   ├─ check slot-unbootable:b / GPT attr (FLS, AVB-11)
│   ├─ check vbmeta chain + descriptors (AVB-06/07) and whether the init_boot is OEM/chain-compatible
│   └─ check whether BL fastboot is the only channel (FLS-07) → cold EDL
├─ hangs at first screen / reboots before UI
│   ├─ capture: init_boot wrapper → misc/logdump; check AVB-01..08 / FBE-01..06
│   └─ if `libfs_avb` present → wrong vendor_boot variant or GPT, not content
├─ reaches UI but no adb / adb FAIL closed
│   └─ USR-12/13 (authorization) before declaring a ROM bug
└─ reaches userspace then dies in a loop
    └─ logcat chain: USR-01/02 → USR-04/05/06; F0 capture health CAP-01..06 first
```

---

## 9. Notes on evidence quality

1. Several lines above are **downstream symptoms** (FBE-02…06, USR-02/03). They are listed because they are the lines people actually see first; the handling column always points at the real cause.
2. `(criterion)` entries have no single literal error line; they describe a check that failed. Do not quote them as "the device printed this".
3. Exact string spellings were taken from the source files; placeholders `<mp>`, `N`, `<pid N>` are the reports' placeholders.
4. Two errors could not be closed: (a) the exact trigger that makes the ABL fall back to recovery in one recorded 2.7 s boot (BCB was empty); (b) whether `printk_ratelimit=0` fully stops producer-side line drops. Both are marked **UNVERIFIED**.
5. If a new line is observed, add it here with (i) the exact text, (ii) the boot stage, (iii) the image set, (iv) the source capture file. Do not add a line that was not observed.
