Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0

# 10 — Debug & Log Capture Channels (Lenovo Legion Y700 5th Gen, TB323FU)

| Item | Value |
|---|---|
| Document status | 2026-11-12; channel behaviors below were exercised on hardware during the LineageOS 24 boot-fix and F0 validation rounds |
| Applicable device | Lenovo Legion Y700 5th Gen **TB323FU** (SM8850P, canoe/kaanapali), unlocked (verified-boot state orange), active slot B, B slot has logical partitions in `super` |
| Scope | Every channel that can read/write data or retrieve logs from this device, what each channel can and cannot do, how to build/install the boot-time capture wrappers, how to read the captures, and how to judge a boot from them |
| Related docs | [03 — Flash](03-FLASH.md) (channels and write sets), [06 — Root cause: logdump/metadata](06-ROOTCAUSE-LOGDUMP-METADATA.md), [07 — FBE / init_user0](07-FBE-INIT-USER0.md), [11 — Error Catalog](11-ERROR-CATALOG.md), [12 — Experiment Log](12-EXPERIMENT-LOG.md) |
| Evidence policy | Channel capability statements come from actual commands run against the device or from image/log analysis. Anything not proven is marked **UNVERIFIED**. |

> **Path convention.** `<PROJECT_ROOT>` = project evidence tree, `<WORKSPACE>` = engineering scratch workspace, `<USER_HOME>` = Windows user profile, `<SN-REDACTED>` = device serial, `<MAC>` = any MAC address. Tools that live in a vendor toolkit are shown with a generic `<USER_HOME>\Downloads\...` path.

---

## 1. TL;DR channel matrix

| Channel | Read | Write | Persistent? | Best use | Main caveat |
|---|---|---|---|---|---|
| Hardware EDL / 9008 (`fh_loader`) | LUN0 + LUN4 | LUN0 + LUN4 (new XML style only) | n/a | Full partition read/write, GPT repair, brick recovery, pulling `misc`/`logdump`/`metadata` | False success; each write must be read back; one tool per 9008 session; cold entry only |
| fastbootd (`is-userspace=yes`) | `fastboot fetch` | physical + logical partitions | n/a | Fast large writes (`super`, `system`), `fetch` without EDL, `set_active` | Only reachable from a bootable system/recovery; partition names have no `_b` suffix |
| Bootloader fastboot (`is-userspace=no`) | `getvar` only | No | n/a | Slot/var probes, `reboot`/`reboot recovery` | `flash`/`set_active`/`oem edl` = `unknown command` |
| Stock recovery (adb) | Yes | `dd` to raw partitions | n/a | Fallback read/write, factory reset | A recovery boot **skips first-stage mounts** and uses a monolithic `/sepolicy`; not a normal-boot debugging environment |
| `adb` (system userspace) | Yes | only when authorized | n/a | `logcat`/`dmesg`/`getprop`/`ps`, last-resort capture | Authorization state is stored in `/data/misc/adb/adb_keys`; a data wipe de-authorizes the host |
| pstore / ramoops / last_kmsg | No | — | — | — | No ramoops DT node; `dtb_size=0`; VT/FB off; EFI pstore has no records (failures are not panic-type) |
| `logfs` (ABL log) | No | — | — | — | Zeroed/handled by tools earlier in the project; FAT destroyed, contains stale sessions only |
| `misc` beacon (init wrapper) | Yes | via wrapper | overwritten every boot | Earliest boot-stage evidence (first-stage init) | Only small control block + up to 508 KiB streaming buffer |
| `logdump` partition (INITLOG13) | Yes | via wrapper | per boot (wrap) | Full `/dev/kmsg` stream, 512 MiB | Not covered by any AVB descriptor (safe to write); must be fetched after the failure |
| `rawdump` partition (logcat service) | Yes | via service | per boot | logcat/crash buffer when the UI is up | Service starts late (`class core`/`post-fs-data`); early crashes are missed |
| `metadata` partition as capture target | Yes | **forbidden** | per boot | — | The pre-F0 `logdump.sh` wrote raw blocks into it and destroyed the f2fs superblock; this caused the `init_user0_failed` loop |

---

## 2. Hardware EDL (Qualcomm 9008) — the primary channel

### 2.1 How to enter

The only physically verified sequence on this device:

1. Power off (hold power ~10–15 s).
2. Hold **Volume+** and plug the USB cable into the **long-edge** port.
3. Device Manager shows `Qualcomm HS-USB QDLoader 9008 (COMx)`.

`adb reboot edl` (soft EDL) does **not** work for flashing: the device enumerates as a 9008 port that does not answer Sahara, and writes are silently discarded. Always use the cold sequence.

### 2.2 Toolchain and invocation

Programmer: `devprg_legion-y700-5-2.0.11.043` / `prog_firehose_ddr.elf` (vendor toolkit, e.g. `<USER_HOME>\Downloads\高通工具箱-2026.9.28-1\`), port `\\.\COM3` by default. The session is started with `QSaharaServer.exe`, then `fh_loader.exe` is used for XML commands.

```powershell
# one <program>/<read> per XML; new-style invocation is mandatory for LUN4
& $FH --port="\\.\COM3" --memoryname=ufs --search_path="<PROJECT_ROOT>\refs\readback-full" `
      --sendxml="<PROJECT_ROOT>\out\...\fh-read-misc.xml" `
      --noprompt --zlpawarehost=1 --skip_configure
```

XML requirements: `SECTOR_SIZE_IN_BYTES="4096"`, exact `physical_partition_number`, `start_sector`, `num_partition_sectors`, and `partofsingleimage="true"`, `readbackverify="true"` where applicable. Old-style plain-LBA writes to LUN4 produced `invalid gpt entry number 128` and then still printed SUCCESS — do not trust them.

### 2.3 Command reference (verified)

| Task | Command / template | Notes |
|---|---|---|
| Reset out of EDL | `fh_loader ... --sendxml=fh-reset.xml` (`<power value="reset"/>`) | Last step of every write session |
| Read a partition | `fh-read-*.xml` template, `--sendxml`, read-back `.bin` | Verify SHA-256 of the returned file |
| Write a partition | `fh-write-*.xml` with `<program>` element | Write one partition per XML; read back and hash |
| Block-level patch | `<program ... start_sector="620062" num_partition_sectors="1">` for a 4 KiB block | Used for the 9-block F0 patch (36 KiB total) |
| GPT repair | write stock `gpt_main4` (LBA 0, 6 sectors) + `gpt_backup4` (LBA 1,048,571, 5 sectors) | Both pieces must be written as a pair |
| Clear BCB only | read-modify-write `misc` first 2 KiB | Do not erase the whole `misc`; AOSP only uses the first 2 KiB |

### 2.4 False-success doctrine

EDL **both reads and writes can report success while doing nothing** (or returning random data). Mandatory rules:

1. After every write, read the same range back and compare SHA-256 (for small partitions, compare the whole partition; for big ones compare head + middle + tail blocks).
2. Treat "SUCCESS"/`All Finished Successfully` as "the XML parser did not fail", not as "the device was written".
3. Do not run two host tools against the same 9008 session. Re-enter EDL (unplug/replug) between tools.
4. `target not stable`, a port that takes 10 s to open, or programmer upload failures are session-level symptoms: restart from a cold EDL, do not keep retrying the same XML.
5. If a script exits abnormally, `fh_loader.exe` may still hold COM3: kill `fh_loader`/`QSaharaServer` before the next run.

### 2.5 Reading `misc` / `logdump` / `metadata` with EDL

```powershell
# sizes: misc = 1 MiB (LUN0 LBA 8456, 256 sectors)
#        logdump = 512 MiB (LUN4 LBA 735255)
#        metadata = 64 MiB (LUN0 LBA 5251880)
# Read, then inspect contents; do not assume the file is non-zero.
```

A large read may fail halfway while still producing a file. Always check the first bytes for an expected marker (`"IL13"` control block for the wrapper, `==== INITLOG13` header for logdump, `AERA_...` markers for the logcat service) before trusting the content.

---

## 3. fastbootd — the fast, EDL-free channel

### 3.1 How to enter and what works

- Entry: from a bootable system `adb reboot fastboot`, or from stock recovery `adb shell reboot bootloader` then `fastboot reboot fastboot`.
- `fastboot getvar is-userspace` = `yes` confirms fastbootd.
- Writes: physical partitions (`boot_b`, `init_boot_b`, `vbmeta_b`, `vbmeta_system_b`, …) and logical partitions (`system`, `system_ext`, `product`), `set_active`, `resize-logical-partition`.
- Reads: platform-tools 37+ supports `fastboot fetch <partition> <out_file>`; this was the fastest way to pull `misc`, `logdump` and `metadata` when the device could reach fastbootd.
- Throttling: a 20 GiB `super` (~13 GiB used payload) took about 20 s; a 2.2 GiB `vendor` took ~8 s over EDL; USB stability is usually the limiting factor.

### 3.2 Partition naming rule (costly mistake)

fastbootd expects **no slot suffix**: `fastboot flash vendor ...`, `fastboot flash vendor_boot ...`, `fastboot flash system_ext ...`, `fastboot flash init_boot ...`, `fastboot flash vbmeta_system ...`. Writing `vendor_b` fails with `unknown partition` (observed: `system_ext_b` happened to be accepted, but do not rely on the exception).

### 3.3 `fastboot -w` is not a formatter

On Windows platform-tools without host `mke2fs`/`make_f2fs`, `fastboot -w` performs **erase only** and prints:

```
Erase successful, but not automatically formatting.
File system type raw not supported.
```

Consequence: after `fastboot -w`, the next boot can see a raw/empty `metadata`/`userdata` and fail (`init_user0_failed`). The reliable way to format is the stock recovery **Factory data reset** (it runs the real `make_f2fs`), or an explicitly verified `fastboot format`.

### 3.4 Limits

- `fastboot reboot fastboot` fails when the slot is unbootable: `Failed to boot into userspace fastboot; one or more components might be unbootable.`
- Bootloader fastboot is read-only for this device; `set_active`/`flash`/`oem edl` all return `remote: 'unknown command'`.

---

## 4. Stock recovery — recovery-mode debugging and a critical semantic trap

- Stock recovery exposes adb (`<SN-REDACTED> recovery` appears in `adb devices`), and `dd` can read/write raw partitions (used historically for `init_boot_b` writes).
- **Trap:** when the bootloader falls back to recovery, `IsRecoveryMode()` is true, first-stage mounting is **skipped entirely** (`First stage mount skipped (recovery mode)`), and the root filesystem comes from the recovery ramdisk with a **monolithic `/sepolicy`**. A log taken in this state cannot be used to judge first-stage or userspace behavior: there are no `EXT4-fs (dm-…)` mount lines and no `Opening SELinux policy` from the split-policy path, and a `2.7 s` death is expected (recovery init aborts).
- Use recovery for: factory reset, `dd`, and as an entry point to fastbootd. Do not use a recovery boot as evidence that "the ROM is broken".

---

## 5. System `adb` — what it can tell you when the UI is up

- Authorization state lives in `/data/misc/adb/adb_keys`; `ro.adb.secure=1` on this ROM, so after a data wipe the host must re-authorize (`adb devices` shows `unauthorized`, shell reports `device unauthorized`).
- `adb shell` returning `FAIL closed` with a live transport is usually an authorization/`adbd` state problem, not a ROM bug; check `getprop init.svc.adbd` and the state in `adb devices`.
- Useful one-shot gathers:

```bash
adb shell getprop sys.boot_completed
adb shell getprop init.svc.bootanim
adb shell getprop ro.crypto.state
adb shell getprop ro.boot.verifiedbootstate
adb shell cat /proc/mounts
adb shell dmesg
adb logcat -b all -d
adb shell ps -A
```

- The `adb_root` service on this ROM is a passive AIDL service (it does **not** restart `adbd`); deleting its `.rc` is safe but does not fix authorization problems.

---

## 6. Boot-time capture wrappers (init_boot) — earliest reliable evidence

### 6.1 Why a wrapper

When the device dies before userspace (first-stage mount failure, early init fatal), `adb`/`logcat` do not exist and `misc`/`logfs`/pstore do not help. The only channel that starts early enough is a **modified `init_boot` ramdisk**: move the stock `/init` to `/init.real`, add a small wrapper as `/init`, fork, `execv("/init.real")` in the parent, and let the child read `/dev/kmsg` and persist it.

### 6.2 Hard design constraints (learned the hard way)

| Constraint | Reason |
|---|---|
| `kernel_size = 0` in the `init_boot` header | A 1-byte kernel makes the device reboot-loop so fast that the wrapper never runs |
| Parent must `execv("/init.real")` immediately | The wrapper cannot sleep or wait for block devices: UFS module probing takes ~1.16 s and only happens once real init proceeds |
| Child must open `/dev/kmsg` itself (mknod 1:11) | `/proc/kmsg` is not guaranteed readable; `/dev/kmsg` is the documented interface |
| Child must flush immediately after opening its target | Waiting to accumulate logs means nothing is persisted when the kernel panics |
| Target block device must be located via GPT, not a hard-coded number | `misc` LBA 8456 is valid for the stock GPT only; parse the GPT or use `/dev/block/by-name/` alternatives |
| Wrapper must not break PID 1 semantics | The parent must remain the init process that execs `/init.real` |

### 6.3 Implementations used in this project (in order of usefulness)

| Wrapper | Target | Layout | When to use |
|---|---|---|---|
| `initlog9` / `logging4` | `misc` | stream from 0x81000 | Legacy; first proof that the wrapper executes (its capture ended at the kernel death point, not by design) |
| `initlog10` / `logging10` | `misc` | 508 KiB stream from 0x81000; fills at ~1.5 s | Early-stage capture only; cannot see userspace |
| `initlog12` / `logging12` | `misc` | ring buffer + latest-snapshot rewrite every ~1 s at 0x81000 | Better for long hangs; ring bug produced interleaved text (split by `ctl.snap_len`) |
| `initlog13` / `logging13` | `logdump` (512 MiB) | continuous raw `/dev/kmsg` bytes + header + wrap marker; misc control block heartbeat | **Recommended**; survives long boots and cannot damage `metadata` |

### 6.4 `misc` control-block layout (verified field offsets)

`misc` byte offset `0x80000`:

| Offset | Type | Meaning |
|---|---|---|
| +0 | u32 | boot counter |
| +4 | char[4] | magic: `IL9\0`, `IL10`, `IL12`, `IL13` |
| +8 | u32 | stage: 1 = kmsg opened, 2 = logdump opened, 5 = streaming, 9 = DONE (stream ended and wrapper asked for reboot) |
| +12 | u32 | ticks (10 ms units) |
| +16 | u32 | bytes written to the log target |
| +20 | u32 | bytes read from kmsg (IL13) / total captured (IL12) |
| +24 | u32 | uptime seconds |
| +28 | u32 | wrap count (IL13) / snapshot count (IL12) |
| +64 | char[] | `/proc/cmdline` |

Read and sanity-check it with a tiny script:

```python
import struct
d = open("misc_fetched.bin", "rb").read()
o = 0x80000
print("counter", struct.unpack_from("<I", d, o+0)[0])
print("magic  ", d[o+4:o+8])
print("stage  ", struct.unpack_from("<I", d, o+8)[0])
print("ticks  ", struct.unpack_from("<I", d, o+12)[0])
print("written", struct.unpack_from("<I", d, o+16)[0])
print("uptime ", struct.unpack_from("<I", d, o+24)[0])
print("cmdline", d[o+64:o+64+256].split(b"\x00")[0])
```

Reading rules: a `stage=5` with tiny `ticks`, or a log that stops after the UFS `sd 0:0:0:5` line, means the kernel died during first-stage mount. A `stage=9` plus `DONE-EDL` at the end of the log means the wrapper completed its capture window and requested the reboot itself (not a boot failure).

### 6.5 `logdump` partition (INITLOG13) format

- 512 MiB at LUN4 LBA 735255; **not referenced by any vbmeta descriptor**, so writing it cannot break AVB.
- Start of partition: `==== INITLOG13 boot=<N> uptime=<S> ====\n`, then raw kmsg bytes (each record is `pri,seq,ts;message`, long messages wrapped).
- When the partition is full: wraps to offset 0 and writes `==== LOGWRAP ====`, increments the wrap counter. Parse from the last `==== INITLOG13` header to get the most recent boot segment.
- `printk` ratelimiting can still drop lines **at the producer**; `printk.devkmsg=on` helps but does not disable ratelimits. For full first-stage logs, also consider writing `printk_ratelimit=0` / `printk_ratelimit_burst=9999` once `/proc` is mounted (next-round item; not yet part of the default wrapper).

---

## 7. Userspace capture: logcat to `rawdump`

### 7.1 Working design

A `system_ext` init service (`class core`/`post-fs-data`) that:

1. waits for `logd.ready=true` (bounded retries),
2. writes a header (`==== AERA_LOGCAT2_BEGIN uptime=… ====`), `getprop`, and `dmesg`,
3. runs `logcat -b all -v threadtime` into `/dev/block/by-name/rawdump` (or the `rawdump` block device found via sysfs).

`rawdump` is 512 MiB and is not AVB-covered; writing it is safe. The vendor kernel ramdump path also uses `rawdump`, so an extreme kernel panic can overwrite the log — acceptable for system_server crashes.

### 7.2 Two bugs that silently produced empty captures (do not repeat)

| Symptom | Cause | Fix |
|---|---|---|
| `logdump` contains only the `AERA_LOGCAT_BEGIN` header, no logcat lines | `logcat -v pid` is not a valid format (`logcat: Invalid -v 'pid'`, process exits) | use `-v threadtime` (optionally `,usec`) |
| `logdump` contains header/getprop/dmesg but the logcat section is empty | `exec logcat -G 16M ...` — `-G` only sets the buffer size and then **returns EXIT_SUCCESS immediately** (`system/logging/logcat/logcat.cpp:1165`), so no log stream is opened | split it: `logcat -b all -G 16M >/dev/null 2>&1` then `exec logcat -b all -v threadtime` |

### 7.3 Capture-health verdicts

| Signature | Verdict |
|---|---|
| `==== INITLOG13` header present | kmsg capture valid |
| `AERA_LOGCAT2_BEGIN` / `AERA_DIAG_BEGIN` header present but no content after it | `CAPTURE-FAILED` |
| target partition is 64 MiB of zeros / all zeros | `CAPTURE-NOT-RUN` (service never executed) |
| `logcat: Invalid -v '...'` | `CAPTURE-FAILED` |
| log ends abruptly without reaching userspace | capture truncated — **do not** conclude "F0 not effective"; mark F0 status unknown |
| `==== LOGDUMP3` / `AERA_DMESG` found in a `metadata` dump | `PRE-F0-DIAG`: the old `logdump.sh` was active (this is the pre-F0 behavior, not a boot-stage log) |

> **Rule:** the pre-F0 `logdump.sh` wrote snapshots into the `metadata` partition by raw `dd`. That destroyed the f2fs superblock and caused the reboot → `init_user0_failed` → clear-data loop. It was removed from the shipped `system` in F0. Never write to `metadata` for diagnostics; use `logdump` (kmsg) and `rawdump` (logcat).

---

## 8. Reading and judging a capture

### 8.1 Stage criteria (independent of any tool)

| Stage | Positive evidence | Negative evidence |
|---|---|---|
| S0 first-stage | `init first stage started!`, `EXT4-fs (dm-…)` ×7+, `Opening SELinux policy` / `Compiling SELinux policy` | `Failed to mount required partitions`, `[libfs_avb] Device path not found: /dev/block/by-name/…`, `ELOOP`, `fs_mgr_create_canonical_mount_point` |
| S1a metadata | `F2FS-fs (sda10): Mounted with checkpoint version = …` | `vold: Failed to create /metadata/vold: Read-only file system`, no `sda10` line |
| S1b init_user0 | no failure lines, boot continues to zygote | `vdc: Command: cryptfs init_user0 Failed: Status(-8, EX_SERVICE_SPECIFIC)`, `vdc call failed with error code: 25`, `Failed to mkdir(/data/misc/vold/user_keys)`, `Reason: init_user0_failed` |
| S2 system_server | `starting service 'zygote'` repeatedly at ~5 s intervals, `Exit zygote because system server (pid …) has terminated` (logcat), `*** FATAL EXCEPTION IN SYSTEM PROCESS` (logcat crash buffer) | one-shot zygote start then silence (capture truncated) |
| S3 success | `sys.boot_completed=1`, `init.svc.bootanim=stopped`, `Boot completed` in logcat | — |
| F0 effective | shipped `system` has no `logdump.sh`/`logdump.rc`; current boot's kmsg has no `starting service 'exec … logdump.sh` and no `avc: denied { execute_no_trans } … path="/system/bin/logdump.sh"`; `F2FS-fs (sda10)` present | any `logdump.sh` exec/avc line → **F0 not effective** |

Device block mapping (stock GPT): `sda10 = metadata`, `sda14 = userdata`. If the GPT changes, re-derive this from a GPT dump.

### 8.2 Grep one-liners

```bash
# first stage
grep -aE "init first stage started|Failed to mount required partitions|libfs_avb|ELOOP|EXT4-fs|Opening SELinux policy" logdump.bin

# metadata / FBE chain
grep -aE "F2FS-fs \(sda10\)|Failed to create /metadata/vold|read_key failed|encryptFstab|make_f2fs" logdump.bin

# init_user0 chain
grep -aE "init_user0|user_keys|mount_all /vendor/etc/fstab.qcom|queue_fs_event|vdc call failed" logdump.bin

# zygote / system_server (kmsg side)
grep -aE "starting service 'zygote'|received SIGKILL|Sending SIGKILL|updatable_crashing" logdump.bin

# logcat side (rawdump or live adb)
grep -aE "Exit zygote because system server|FATAL EXCEPTION IN SYSTEM PROCESS|WATCHDOG KILLING|AndroidRuntime" rawdump.bin

# capture health
grep -aE "INITLOG13|AERA_LOGCAT|Invalid -v|LOGWRAP" logdump.bin
```

### 8.3 `boot-doctor` automation

`boot-doctor.py` (reviewed version) turns the criteria above into a verdict. Usage:

```bash
python3 boot-doctor-reviewed.py <dump.bin> --tag <label> --out <outdir>
# directory mode: one verdict per file, never mix evidence from different boots
python3 boot-doctor-reviewed.py <evidence_dir> --out <outdir>
```

Verdicts: `S0-first-stage`, `S1-metadata-missing`, `S1-init_user0-failed`, `S2-system_server`, `S3-success`, `S3-indirect (device alive N s, capture truncated)`, `CAPTURE-FAILED`, `CAPTURE-NOT-RUN`, `PRE-F0-DIAG`, `STALE-PREV-BOOT`, `F0-likely-effective`, `F0-NOT-EFFECTIVE`, `F0-unknown`.

Rules baked into the reviewed version:

- classify by **file name first**, then magic, then size (the 64 MiB logdump must not be mistaken for `metadata`);
- never feed `metadata` snapshot text into the boot-stage verdict; use it only for `PRE-F0-DIAG`;
- `sys.boot_completed` must match the strict regex `sys\.boot_completed[=:\s]+1` (a bare `=1` anywhere in the text is a false positive);
- use the `misc` control block's uptime for `S3-indirect` when the capture is truncated;
- split `misc` streaming regions by `ctl.snap_len` before analysis (a 7 s failed boot file also contained the previous boot's init_user0 failure chain; mixing the two produces a wrong timeline).

### 8.4 Failure-capture SOP

1. Reproduce the failure with the diagnostic set (recommended: `vendor_boot_diag2` + `init_boot_logging13` + matching `vbmeta_system`), never leaving `metadata` as a capture target.
2. Wait for the device to either boot or fall back (recovery / fastboot). Note the mode and the wait time.
3. Enter fastbootd (if bootable) and `fastboot fetch misc logdump metadata`; otherwise cold-enter EDL and read the same partitions.
4. Sanity-check capture health (headers/all-zero) before analysis.
5. Run `boot-doctor` or the greps above; record the verdict, the evidence lines, and the exact image/partition list used for the boot (record `vendor_boot` SHA-256 — cmdline alone cannot distinguish diagnostic variants).
6. Only then change one variable and repeat.

---

## 9. Pitfalls (quick list)

1. Do not trust EDL's SUCCESS; read back and hash.
2. Do not use soft EDL; cold 9008 only.
3. One tool per 9008 session; kill stale `fh_loader` before retrying.
4. `misc` logs must be split by `snap_len` before mixing.
5. `metadata` is not a capture target (pre-F0 lesson) — use `logdump`/`rawdump`.
6. `logcat -G` alone exits immediately; `logcat -v pid` is invalid — both silently produce empty captures.
7. fastbootd partition names have no `_b` suffix.
8. `fastboot -w` only erases; use recovery factory reset to format.
9. A recovery-mode boot has no first-stage mounts — do not analyze it as a normal boot.
10. Changing `vendor_boot` variants without recording their SHA makes results non-reproducible (`printk.devkmsg=on` etc. are not visible from the booted system).
11. Record `misc`/`logdump` fetch sizes and first bytes; a truncated fetch can look like a short capture.
12. `misc` device block numbers (`sda10`/`sda14`) depend on the GPT; re-derive after any GPT change.
13. The wrapper sees only kernel `printk`; Java/crash logs require logcat (`rawdump`).

---

## 10. UNVERIFIED items

1. `fastboot fetch` works in fastbootd on this device in principle (platform-tools 37+), but the 512 MiB `logdump` fetch itself was not completed end-to-end during the recorded rounds.
2. The `printk_ratelimit=0` + `printk_ratelimit_burst=9999` addition to the wrapper (to stop producer-side dropping) is proposed and **not yet built/verified**.
3. The `rawdump` logcat service was validated structurally (script/init/sha) but its on-device output under a genuine system_server crash loop is not recorded.
4. The exact memory/device-tree reason why some `init_boot` variants run faster than others is not characterized.
5. Whether the recovery fallback in a specific failure was driven by ABL retry logic, BCB, or a key/volume sequence is not fully closed (in one recorded case `misc` BCB was empty and the fallback still happened).

---

## 11. References (evidence files, relative to `<PROJECT_ROOT>`)

- `out/2026-11-11-los24-bootfix/BOOT-DOCTOR-REVIEW.md` — the full stage criteria table, `boot-doctor` rule mapping, verdict matrix, reviewed tool usage.
- `out/2026-11-11-los24-bootfix/REBUILD-ZYGOTE-TIMELINE.md` — kmsg judgement table, `snap_len` split rule, `libfs_avb` evidence.
- `out/2026-11-11-los24-bootfix/ADB-ROOT-ANALYSIS.md` — adb authorization analysis, recovery-mode/SELinux evidence, `logcat` service feasibility.
- `out/2026-11-11-los24-bootfix/INITLOG12-BUILD-REPORT.md`, `INITLOG13-BUILD-REPORT.md` — wrapper design, `misc` control layout, `logdump` format.
- `out/2026-11-11-los24-bootfix/SYSTEMEXT-LOGCAT2-REPORT.md`, `SYSTEMEXT-LOGCAT3-REPORT.md` — logcat-to-rawdump service and its two bugs.
- `out/2026-11-11-los24-bootfix/SYSTEM_SERVER_CRASH-HYPOTHESES.md` §5 — metadata-write failure chain and capture plan.
- `out/2026-11-11-los24-bootfix/SESSION-20261112-FBE-ROOTCAUSE-LOG.md` §5 — capture-tool inventory and fastboot-fetch discovery.
- `out/2026-11-10-los24-logdump/RECOVERY-PLAYBOOK.md`, `LOS24-PLAYBOOK-CONSOLIDATED.md` §3.6/§3.7 — channel capability matrix and pstore/logfs failure history.
- `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` §3/§7 — F0 acceptance evidence (boot_completed, metadata/data mounts, 3× reboot regression).
