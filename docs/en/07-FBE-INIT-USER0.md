Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0

# 07 — FBE / `init_user0` mechanism, the dual-fstab rule, and the A–F experiment matrix

| Field | Value |
|---|---|
| Status | 2026-11-12 — mechanism closed; the A–F matrix is retained as design/record. The "reboot always `init_user0_failed`" symptom was later traced to metadata corruption by `logdump.sh` (doc 06), not to the FBE key path; on the fixed set the device boots and reboot-reboots with FBE fully enabled |
| Device | Lenovo Legion Y700 Gen 5 **TB323FU**, SN `<SN-REDACTED>`, SM8850P (canoe / kaanapali), A/B, 4 KiB pages, super 20 GiB, unlocked (`vbs=orange`), B slot active |
| Applies to | LineageOS 24.0 (Android 17) bring-up with FBE on `/data` (`fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized+wrappedkey_v0` in the stock fstab), stock `vendor_b` + `vendor_boot_b` |
| Evidence sources | `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\INIT_USER0-ANALYSIS.md`, `…\PLAINFBE-REPORT.md`, `…\VENDOR-CHECKPOINT-OFF-REPORT.md`, `…\VENDOR-FSTAB-MOD-REPORT.md`, `…\NEXT-ROUND-TEST-PLAN.md`, `…\SESSION-20261112-FBE-ROOTCAUSE-LOG.md`; `<PROJECT_ROOT>\out\2026-11-12-edl-f0\F0-ACCEPTANCE-REPORT.md` |

---

## 1. Context

After the `/vendor` symlink-loop fix (doc 05) the port could reach the LineageOS welcome screen on a *freshly wiped* `/data`, but a normal reboot landed in stock recovery:

```
Can't load Android system. Your data may be corrupt. …
Reason: init_user0_failed
```

The working hypothesis at that point was that the FBE (file-based encryption) "unlock/restore" path failed on reboot while the "create" path succeeded on first boot. The A–F matrix below was designed to isolate which FBE feature (checkpoint, wrapped keys, metadata encryption, inlinecrypt, plain v2 software keys, or FBE off) caused it.

**Outcome in hindsight:** the log evidence recovered from the previous boot's `misc` region showed that `/metadata` simply was not mounted at all (`vold: Failed to create /metadata/vold: Read-only file system`); the real cause was the every-boot `dd` write to `/metadata` by the debug `logdump.sh` (doc 06). With that removed and metadata properly formatted once by recovery, FBE works end-to-end: final acceptance shows `ro.crypto.state=encrypted`, `ro.crypto.type=file`, `ro.crypto.metadata.enabled=true`, `vold.post_fs_data_done=1`, `sys.user.0.ce_available=true`, `/data` f2fs `inlinecrypt`, and 3/3 reboots PASS. The A–F matrix therefore remains useful as (a) an accurate description of the FBE semantics on this device, and (b) the record of what was ruled out — but it is no longer needed to solve the reboot symptom.

## 2. `init_user0` failure mechanism (source-level)

1. `system/core/rootdir/init.rc:1086` — builtin `init_user0` in the `on post-fs-data` block (`:707`; `/data` mounted earlier; vold started at `:602`; keystore/keymaster early-boot finished).
2. `system/core/init/builtins.cpp:1190-1192` — `do_init_user0()` → `ExecVdcRebootOnFailure("init_user0")`.
3. `builtins.cpp:1151-1177` — `ExecVdcRebootOnFailure()`:
   - runs `exec /system/bin/vdc --wait cryptfs init_user0` as a temporary oneshot service;
   - on failure: `reboot_reason = vdc_arg + "_failed"`; if `IsFbeEnabled() && !IsGsiRunning()` → `reboot_into_recovery({"--prompt_and_wipe_data", "--reason=<reason>"})` and logs `"... Rebooting into recovery, reason: init_user0_failed"`;
   - **if FBE is not enabled, it only logs `"Failure (reboot suppressed)"` and does not bounce to recovery** — this is the safety net that makes "FBE off" attractive for bring-up.
4. `system/vold/vdc.cpp:163-164` — `cryptfs init_user0` → `vold->initUser0()`; `system/vold/VoldNativeService.cpp:631-635` → `fscrypt_init_user0()`.
5. `system/vold/FsCrypt.cpp:655-690` — `fscrypt_init_user0()`:
   - if `IsFbeEnabled()`: create `/data/misc/vold/user_keys/{de,ce}`, `create_de_key(0)`/`create_ce_key(0)` when missing, `load_all_de_keys()`;
   - `prepare_special_dirs()`: create `/data/data`, bind-mount to `/data/user/0`, handle `/data/media/obb`;
   - `fscrypt_prepare_user_storage("", 0, STORAGE_FLAG_DE)`;
   - on success set `fscrypt_init_user0_done = true` (used by `vold main.cpp:315/324`; comment: basic FBE setup failure → boot will fail).
   - Key wrapping/unwrapping goes through **KeyMint/Keymaster + keystore2**; the metadata-encryption key directory is `/metadata/vold/metadata_encryption` (from fstab `keydirectory=`).
6. Recovery UI text: `bootable/recovery/recovery.cpp:301-314` `prompt_and_wipe_data()` title "Can't load Android system …" + `"Reason: " + device->GetReason()`; the reason comes from init's `reboot_into_recovery(--reason=…)` (via misc/BCB). So the user-visible `Reason: init_user0_failed` is passed by init, not produced by dm-verity/ABL.

## 3. Why there are two fstab instances — and why both matter

`/data` is described in **two different fstab files**, and they exercise different parts of the stack:

1. **First stage** — `first_stage_ramdisk/fstab.qcom` inside the `vendor_boot` ramdisk (7,374 B; device read-back `vendor_boot_b` sha256 `9349137dc262ab61508014275b623f4d39e5b14bc55c77082848d63a28f381b2` = stock). This is what `fs_mgr` reads to set `ro.crypto.type` (`system/fs/fs_mgr/fs_mgr.cpp:1174`). `IsFbeEnabled()` is exactly `ro.crypto.type == "file"` (`builtins.cpp:1125-1127`), and `ro.crypto.state` is set by init from `mount_all`/`installkey` (`builtins.cpp:582/597`).
2. **Second stage** — `/vendor/etc/fstab.qcom` inside the stock `vendor_b` partition (inode 1034, 7,374 B, mode 0644, label `u:object_r:vendor_configs_file:s0`, sha256 `4524469bf2480b1deb8f3f17545d6ac8588a220223609104f6340356d263e7b6`). The stock vendor `init.qcom.rc` runs `mount_all /vendor/etc/fstab.qcom` (`--early`/`--late`), and **vold also parses `fileencryption`/`keydirectory`/`metadata_encryption` from this file**.

Consequences:

- **Changing only the `vendor_boot` first-stage fstab is not enough**: first stage would set `ro.crypto.type=file` (or not), but the second-stage `mount_all` still applies the stock `/data` flags, and vold still sees the stock FBE parameters.
- **`fastboot -w` alone cannot disable FBE**: without removing the fstab flags, the next format simply re-creates an encrypted `/data` and `init_user0` runs again.
- A change to the stock `/vendor/etc/fstab.qcom` lives in `vendor_b` (a logical partition inside `super`), so it requires rebuilding `vendor_b`, recomputing the vendor AVB hashtree, **and re-signing the vendor ht descriptor in the root `vbmeta_b`** (stock vendor descriptor: partition `vendor`, salt `4b41bf18…`, root digest `cd1f240f…`, algorithm `NONE`, image size 2,167,975,936 B) — otherwise a verity-enabled boot gets EIO.

The stock `/data` line (verbatim, from `/vendor/etc/fstab.qcom` line 53):
```
/dev/block/bootdevice/by-name/userdata  /data  f2fs  noatime,nosuid,nodev,discard,reserve_root=32768,resgid=1065,fsync_mode=nobarrier,inlinecrypt  latemount,wait,check,formattable,fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized+wrappedkey_v0,keydirectory=/metadata/vold/metadata_encryption,metadata_encryption=aes-256-xts:wrappedkey_v0,quota,reservedsize=128M,sysfs_path=/sys/devices/platform/soc/1d84000.ufshc,checkpoint=fs
```

## 4. FBE flag semantics

- `fileencryption=…:v1` / `:v2` selects the **fscrypt policy version**, *not* the wrapped-key mode.
- The key type is selected by the flags: `wrappedkey_v0` → `kHwWrappedV0`, `wrappedkey` → `kHwWrapped`, neither → `kRaw` (software key), per `system/vold/KeyUtil.cpp:303-320`.
- `inlinecrypt_optimized` corresponds to the IV_INO_LBLK_32 / 32-DUN optimization (`FsCrypt.cpp:335-341`); dropping it is safe.
- Therefore "pure v2 + software key" (E) is a kernel-supported combination and was a legitimate experiment.

## 5. Candidate failure modes (ranked, as designed)

| Rank | Hypothesis | Source/mechanism evidence | Discriminating criterion |
|---|---|---|---|
| 1 | `checkpoint=fs` + repeated EDL resets/power loss → vold checkpoint restore fails | `vold/Checkpoint.cpp:84-152` (restore relies on metadata + keymaster snapshots); `init.rc` `on post-fs-data` starts with `vdc checkpoint prepareCheckpoint` (`:710`) | `vold`/`checkpoint` errors in logcat; `/metadata/vold/checkpoint`; `persist.vold.dont_commit_checkpoint` |
| 2 | `/data` and `/metadata` FBE state inconsistent (one got wiped while the other did not) | `keydirectory=/metadata/vold/metadata_encryption` lives on `/metadata`; DE/CE keys live in `/data`; wiping either breaks unwrap | presence of `/data/misc/vold/user_keys`, `/metadata/vold/metadata_encryption`; `ro.crypto.*` |
| 3 | LOS `vold`/`keystore2` ↔ stock `KeyMint`/gatekeeper HAL (AIDL version mix) makes `create/load_*_key` fail | bring-up mixed LOS `system` (vold/keystore2) with stock `vendor` (KeyMint/onekeymint/gatekeeper); FBE depends on those HALs | `keystore2`/`keymaster`/`vold` errors in logcat |
| 4 | Misattribution: FBE vs dm-verity/ABL | recovery text is `prompt_and_wipe_data`, not a verity corruption message | already excluded |

All four end in the same non-zero `init_user0` exit and the reason string only carries the name, so they cannot be distinguished offline; a logcat from a normal boot is required.

## 6. The A–F experiment matrix (design)

Rule for every group: **both fstabs must be modified identically**, then wipe `/data` + `/metadata`, then test *both* first boot and reboot. Images were produced offline with `debugfs` (single-line fstab edit), `e2fsck -fn` clean, full-tree diff = only the fstab file.

| Group | Change (both fstabs) | Images | Status / observed result |
|---|---|---|---|
| **A** | remove **only** `checkpoint=fs` from `/data` flags (keep all FBE flags) | `vendor_b_checkpoint_off.img` (`4d93028e4577657cba251bbad0db62994965da71fb10bf25bd48d42e81209291`; fstab 7,374→7,360 B, only `checkpoint=fs` removed); `vendor_boot_diag6.img` (`e15ab973…`, first-stage same change) | Partial test (2026-11-12 00:30–00:40) used `vendor_b_checkpoint_off` + `vendor_boot_diag2`: **36–47 s → recovery, reason `init_user0_failed`**, but the first-stage fstab still carried `checkpoint=fs`, i.e. the test was **not clean**. `vendor_boot_diag6` was built and SHA-verified but **not device-tested** before the F0 root cause superseded the matrix. |
| **B** | same as A + additionally force-clear `/data`+`/metadata` | same as A | Not executed (F0 root cause superseded). |
| **C** | remove **only** `wrappedkey_v0` (keep `v2+inlinecrypt_optimized+metadata_encryption+checkpoint`) | `vendor_b_nokw.img` (`cc2e446c…`); `vendor_boot_diag7.img` (`6162b02f…`) | Built and checked offline; **not device-tested** (F0 superseded). Discriminator if tested: failure at *creation* would mean stock KeyMint rejects the format. |
| **D** | remove `metadata_encryption=` + `keydirectory=` (keep checkpoint and the rest) | `vendor_b_nometa.img` + `vendor_boot_diag8.img` (planned, not built) | Not built (F0 superseded). Analysis predicted failure at the *mount* stage rather than at `init_user0` if the hypothesis were correct. |
| **E** | **pure v2 software keys**: drop mount option `inlinecrypt`; `fileencryption` shortened to `aes-256-xts:aes-256-cts:v2`; drop `keydirectory=`, `metadata_encryption=`, `checkpoint=fs` | `vendor_b_plainfbe.img` (`1cf8ff58993d7ca19af8e1cfb7c310523c2e74fb545d627a891c993fd55edb36`; fstab 7,374→7,218 B); `vendor_boot_diag5.img` (`2a2f42d0450a0fcfc89bef6b12339366ccc0f5d0942eaf650141e02edbc44509`; first-stage same, bootconfig identical to diag2 `f6302812…`, AVB footer recomputed → new digest `6f7ab065…`) | **Tested 2026-11-12 00:59–01:10**: boot animation stuck for >280 s, USB never enumerated (empty PnP, no adb in 280 s), user confirmed "still stuck on boot animation". FBE stayed ON and `init_user0` was passed. Conclusion: FBE-on + software keys still does not reach the desktop; the symptom equals FBE-off ⇒ the boot-animation hang is not caused by the encryption mode. Device ran out of battery afterwards. |
| **F** | **FBE off** (remove `inlinecrypt` mount option + `fileencryption`, `keydirectory`, `metadata_encryption`, `checkpoint` flags) | `vendor_b_raw_mod.img` (`18cebcb3aaa2afbbf3b598861ce1a5d3ea7cbf12f9b6cd8eb823921156c87eff`; fstab 7,374→7,176 B); `vendor_boot_diag4.img` (`5572278678a697dd64b7f14327d64b3dd2414e60f3c5564d8cb6c11ec15267b6`) | **Tested 2026-11-11 23:50–00:20**: first time past `init_user0` → LineageOS boot animation, but stuck there; USB never enumerated. kmsg: `init: starting service 'zygote'` then repeated `init: Service 'zygote' (pid N) received SIGKILL`; `init: processing action (sys.init.updatable_crashing=1)` + `flags_health_check UPDATABLE_CRASHING`; `init: Control message: Could not find 'aidl/android.system.net.netd.INetd/default'`; at 117 s `UCSI ... usb = 0` / `nvt_charger: USB plug out` (user unplugged to go to EDL), so "USB not enumerating" is partly the unplug; logcat was not captured. |

### 6.1 Pre-matrix discovery that changed the direction (A0)

While reading the **STALE region** of `misc_20261112_005239.bin` (split by `ctl.snap_len`, so the previous boot's log is not mixed), the decisive chain appeared: `/metadata` was **not mounted** (`vold: Failed to create /metadata/vold: Read-only file system`, no `F2FS-fs (sda10)` line), while a known-good boot had exactly that line. This produced the rule that every boot must be judged on **whether `F2FS-fs (sda10)` appears** (`sda10` = metadata). This clue was then traced to the `logdump.sh` every-boot write (doc 06) — the matrix's premise (FBE key/checkpoint corruption) was wrong.

### 6.2 What the E/F results still tell us

- **F (FBE off) proves** that with FBE off the device passes `init_user0` and reaches the boot animation — i.e. the `/data` encryption path was not the blocker for the animation-stage hang, and the `init_user0` recovery bounce was caused by the *data/metadata state*, not by the encryption flags alone.
- **The animation-stage hang** is a separate defect: `zygote` / `system_server` is repeatedly killed or crashes, so `sys.boot_completed` is never set. `received SIGKILL` does not name the sender (`sigchld_handler.cpp:100-119`); an init-initiated kill would additionally show `Sending SIGKILL to … process group` (`service.cpp:283-295`), so OOM/lmkd, `crash_dump`/watchdog, or init's Reap group cleanup are the candidates. The `critical window=off` in `init.zygote64.rc` makes `ParseCritical` return early (`service_parser.cpp:120-143`), so after the 4th crash zygote goes down the "updatable_crashing" path (`service.cpp:381-425`) — only aconfig flag reset plus apexd `WaitForBootStatus` (rollback only when a staged session exists) — which matches the observed `flags_health_check UPDATABLE_CRASHING`. The capture window lacked lmkd/OOM/crash_dump/tombstone hits (but had 1,138 seq gaps), so the original kill reason remains unclosed.
- **Both E and F showed "USB never enumerated"**: in F this was partly caused by the user unplugging the cable at 117 s (UCSI `usb = 0`). Future tests must keep the cable connected for the whole window.

## 7. Safety / mechanics for any future FBE experiment

1. Change **both** fstabs in the same commit set, and verify both images (`debugfs cat` of the fstab, `e2fsck -fn`, full-tree diff = only fstab).
2. Wipe both `/data` and `/metadata` (`fastboot -w` erases only on this Windows host; a real format needs recovery "Factory data reset" or a tool that formats).
3. If `/vendor/etc/fstab.qcom` is modified, the vendor AVB digest changes; with verity on, the root `vbmeta_b` vendor hachtre descriptor must be re-signed. The FBE-off/plain-FBE images produced during this bring-up kept the AVB tail stale and therefore work only with verity off + unlocked.
4. Keep SELinux permissive (the bring-up state) while testing: a policy denial would otherwise mask or compound the fstab effects.
5. Do not mix an FBE-off `/data` with an FBE-on fstab (or vice versa): the "half-encrypted" state produces its own failures.
6. Record every boot: flashed image SHAs, `fastboot -w` yes/no, first boot result, reboot result, and the kmsg/logcat evidence.

## 8. Unverified / next steps

1. A, B, C, D never received a clean single-variable device test: `vendor_boot_diag6` (A) and `vendor_boot_diag7` (C) are built and verified offline but not flashed; D was never built. This is acceptable because F0 removed the actual cause; retain the matrix only if a future FBE problem appears.
2. The animation-stage `zygote`/`system_server` kill reason is still unclosed (needs full kmsg via the `logdump` partition capture + `logcat -b crash` + `/data/tombstones`).
3. FBE-on with the final F0 set is verified working (`ro.crypto.*=encrypted/file`, `vold.post_fs_data_done=1`): the accepted set uses the **stock** `vendor_b` and `vendor_boot_diag2`, i.e. all FBE flags are the stock ones again — no FBE workaround remains in the accepted set.
4. Reverting to verity-on/enforcing will require a clean `vendor_b`/`vendor_boot` plus the v11 verity recipe (see doc 06 §5.3 / doc 08).

## 9. Evidence index

| Path | Content |
|---|---|
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\INIT_USER0-ANALYSIS.md` | `init_user0` source chain, two-fstab explanation, minimal FBE-off recipe, candidate ranking |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\VENDOR-FSTAB-MOD-REPORT.md` | FBE-off vendor_b patch (fstab line 53, 7,374→7,176 B), self-checks, AVB caveat |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\PLAINFBE-REPORT.md` | plain-v2/software-key images (vendor fstab 7,374→7,218 B; diag5), offline checks, digest |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\VENDOR-CHECKPOINT-OFF-REPORT.md` | checkpoint-only removal image, line-level diff, rollback package list |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\NEXT-ROUND-TEST-PLAN.md` | A–F matrix, per-boot criteria (`F2FS-fs (sda10)`), pitfalls list |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SESSION-20261112-FBE-ROOTCAUSE-LOG.md` | experiment archive 23:00–01:10, FBE-off / plain-FBE / checkpoint results, zygote kill evidence |
| `<PROJECT_ROOT>\out\2026-11-12-edl-f0\F0-ACCEPTANCE-REPORT.md` | final state with FBE fully enabled (no workaround) |
