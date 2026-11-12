Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0 (original text)

# 05 — Root cause: `/vendor` self-referencing symlink loop breaks first-stage mount (ELOOP → `LOG(FATAL)`)

| Field | Value |
|---|---|
| Status | 2026-11-12 — root cause closed on 2026-11-11; the fixed `system` image has been in the flashing set ever since (including the F0 repair set, §8) |
| Device | Lenovo Legion Y700 Gen 5 **TB323FU**, SN `<SN-REDACTED>`, SoC SM8850P (canoe / kaanapali), A/B + dedicated recovery, virtual A/B, 4 KiB pages, super 20 GiB, unlocked bootloader (`vbs=orange`), slot B active |
| Applies to | LineageOS 24.0 (Android 17) port; `system_b` ext4 image inside `super` (logical partition size 10,235,101,184 B) |
| Evidence sources | `<PROJECT_ROOT>\out\2026-11-10-los24-logdump\LOS-SYSTEM-ANALYSIS.md` (root-cause analysis); `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\IMAGE-FIX-REPORT.md` (offline patch production); `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\VERIFY-REPORT.md` (independent re-derivation); `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\BOOTFIX-FACTS.md` (fact table) |

---

## 1. Symptom

- The device stopped changing state after the first splash screen: it either rebooted in a loop or hung hard. **USB never enumerated** (no adb, no MTP), so no userspace log could be collected.
- First-stage kernel log (initlog wrapper capture from `misc`, `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\device\kmsg_full.txt`) cuts off at **~0.48–0.50 s**:
  - `Run /init as init process` at t≈264 ms
  - `init: init first stage started!` at t≈265 ms
  - `/lib/modules/*.ko` loaded, then UFS LUN0–LUN5 enumerated (`sd 0:0:0:0..5`) at t≈480–500 ms
  - last line `sd 0:0:0:5 Optimal transfer size` → **log ends, no FATAL text reached the log buffer**
- The second stage was never executed: no `exec /system/bin/init selinux_setup`, no `Opening SELinux policy`, no framebuffer/boot animation progress.
- Consequently, every earlier hypothesis that blamed a *later* boot phase (dm-verity digest, SELinux policy compile, VINTF matrix, `/data` encryption/format) could not have been the blocker in those experiments — those code paths were never reached.

## 2. Structural root cause (byte-level)

The LineageOS-built `system.img` root directory contained a **self-referencing symlink loop** where the stock image has a mount point directory:

| Path | Stock A17 `system_b` (original super extent) | LOS `raw_system_v3.raw` (= `out/system.img`, footer root digest `37cc913b…`) |
|---|---|---|
| `/vendor` | **directory**, inode 4466, mode 0755 (pre-created mount point) | **symlink**, inode 2898, size 14, fast-link dest `"/system/vendor"` |
| `/system/vendor` | symlink → `"/vendor"` | symlink → `"/vendor"` (inode 2892, size 7) |
| `/dataext` | directory (mount point) | **missing** (`File not found by ext2_lookup`) |
| `/mnt`, `/metadata`, `/product`, `/system_ext`, `/odm`, `/vendor_dlkm`, `/system_dlkm` | directories | directories (identical) |
| `/system` | real directory | real directory |

`/vendor → /system/vendor → /vendor` is a two-hop cycle. Any lookup of `/vendor` therefore returns `ELOOP`:

```
/vendor          Inode 2898  Type: symlink  Size 14  Fast link dest: "/system/vendor"
/system/vendor   Inode 2892  Type: symlink  Size 7   Fast link dest: "/vendor"
```

Why this is fatal (and not merely cosmetic): the `system` partition is mounted **read-only** (`ro,barrier=1,discard`), so a mount point cannot be created at runtime; AOSP therefore requires `system`'s root directory to ship the mount point as a real directory. The stock image does exactly that; the LOS build did not.

## 3. Failure path in source code (file:line)

1. The first-stage fstab comes from the **stock `vendor_boot` ramdisk** (`first_stage_ramdisk/fstab.qcom`, 7,374 B; device read-back `vendor_boot_b` sha256 `9349137dc262ab61508014275b623f4d39e5b14bc55c77082848d63a28f381b2` = stock reference image). The `vendor` line is present in the first-stage set and has no `no_fail` / `formattable` flag:
   ```
   vendor  /vendor  ext4  ro,barrier=1,discard  wait,slotselect,avb=vbmeta,logical,first_stage_mount
   ```
2. `system/core/init/first_stage_mount_android.cpp:48-62` — `FirstStageMount::Create()` reads the default fstab and filters with `std::erase_if(fstab, !first_stage_mount)`; `/vendor` stays in the first-stage list.
3. `system/core/init/first_stage_mount.cpp:283-308` — `TrySwitchSystemAsRoot()`: mount `/system`, then `SwitchRoot("/system")`.
4. `system/core/init/first_stage_mount.cpp:343-394` — the remaining partitions are mounted in fstab order (`/system_ext`, `/product`, `/vendor`, …); `first_stage_mount.cpp:186-195` calls `fs_mgr_create_canonical_mount_point(mount_point)` first and returns false on failure.
5. `system/fs/fs_mgr/fs_mgr.cpp:2363-2381` — `fs_mgr_create_canonical_mount_point()`:
   - `mkdir("/vendor")` fails with `EEXIST` (the symlink already exists) → `created_mount_point=false`;
   - `Realpath("/vendor")` fails with **ELOOP** → `ok=false` → returns `false`.
6. `first_stage_mount.cpp:376-387` — a failed mount is ignored only when the entry carries `no_fail` or `formattable`; `/vendor` has neither → `PLOG(ERROR) << "Failed to mount …"` and `return false`.
7. `system/core/init/first_stage_init.cpp:551-553` — `DoFirstStageMount()` returning false triggers `LOG(FATAL) << "Failed to mount required partitions early …"`. init is PID 1 → abort → kernel panic / hard hang / reboot-loop, depending on the kernel–init combination.
8. There is **no tolerance branch** on this path: `SkipMountingPartitions()` only takes effect when `/system/system_ext/etc/init/config/skip_mount.cfg` exists (it does not in this image, and its patterns would not match `/vendor`); the same-mount-point retry branch (`first_stage_mount.cpp:217-226`) does not apply because there is exactly one `/vendor` entry.

Because the failure happens *before* the FATAL message can be flushed, the captured kmsg ends at ~500 ms without the `Failed to mount /vendor` string. The partition-level attribution is instead proven by elimination: every other first-stage precondition was byte-checked and passed (`/system` digest `37cc913b…`, `/product` `e746c5ea…`, `/system_ext` `24deae32…`, vendor/odm/dlkm descriptors equal to stock, LP metadata identical to stock, unlocked/permissive AVB, `/metadata` has `formattable` and is ignored) — the only structural defect left is the `/vendor` loop.

## 4. ELOOP reproduced with the real kernel resolver (not a theoretical claim)

A directory tree with the identical two-hop loop was assembled and resolved through the kernel inside a chroot (`_tmp/verify/08_src_more.log`):

```
os.open   /vendor          => 40 ELOOP Too many levels of symbolic links
realpath  /vendor          => 40 ELOOP Too many levels of symbolic links
os.stat   /vendor          => 40 ELOOP Too many levels of symbolic links
os.open   /system/vendor   => 40 ELOOP Too many levels of symbolic links
realpath  /system/vendor   => 40 ELOOP Too many levels of symbolic links
```

## 5. Why the loop existed: a stale build-tree artifact

- The AOSP rule that creates `system`'s root directory is `system/core/rootdir/create_root_structure.mk:54-59`:
  ```
  ifdef BOARD_USES_VENDORIMAGE
    LOCAL_POST_INSTALL_CMD += ; mkdir -p $(TARGET_ROOT_OUT)/vendor
  else
    LOCAL_POST_INSTALL_CMD += ; ln -sf /system/vendor $(TARGET_ROOT_OUT)/vendor
  endif
  ```
- The port's `BoardConfig.mk` already satisfied `BOARD_USES_VENDORIMAGE=true` (derived by `build/make/core/board_config.mk:703-717` from `BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE`, set at `device/lenovo/TB323FU/BoardConfig.mk:251`), so the rule *should* have produced `mkdir -p $OUT/root/vendor`.
- However the actual out state was: `out/target/product/TB323FU/root/vendor` was still the **old symlink created 2026-11-07 12:36:52** (i.e. before `vendor` was built as a separate image), while the full-userspace `BoardConfig.mk` was modified 2026-11-09 21:35 and `out/system/vendor` was regenerated 2026-11-10 19:38. `mkdir -p` against a dangling symlink fails but **does not stop `make`**, so the stale symlink survived and was packed into every rebuilt `system.img`.
- Conclusion of the analysis: no amount of rebuilding would fix the image until `out/target/product/TB323FU/root` was cleaned. Once done, `mka systemimage` produces the correct layout. The `/dataext` absence was a second, independent build-configuration gap (stock system ships `/dataext`; AOSP supports `BOARD_ROOT_EXTRA_FOLDERS += dataext`, `create_root_structure.mk:29-31`) — a non-fatal second-stage mount-point issue.

## 6. Why earlier "already excluded" conclusions were invalid

Experiments E6/E7/E8/E9/E13 (verity off, SELinux changes, VINTF patch, `/data` wipe, etc.) all used `system` images built from the same bad tree. `raw_system_v3.raw`, the `system` content of `super_test5` and of `super_los_v6` all carry the **same AVB root digest `37cc913b…`** — i.e. the same broken image. Those experiments therefore never reached the verity/SELinux/VINTF/`/data` code paths, and conclusions such as "verity already excluded", "SELinux already excluded", "VINTF already excluded", "`/data` already excluded" do not hold for that period. The only conclusion that survived is that the E12 set (stock `super` + AOSP testkey boot chain) boots, because the stock system root has `/vendor` as a directory and is not affected.

## 7. Fix: offline raw patch of `system.img` (P0-A)

The `system` logical partition is a plain ext4 image; the fix rewrites only ext4 metadata/root-directory blocks, then recomputes the AVB hashtree/FEC with the *original* footer parameters so the result stays a byte-valid AVB partition.

### 7.1 Strip the old AVB tail

```bash
cp raw_system_v3.raw system_work.raw
truncate -s 10073513984 system_work.raw     # = footer "Original image size" (not a guess)
```

### 7.2 debugfs: before → patch → after

Before:
```
/vendor         Inode 2898  Type: symlink  Mode 0644 Size 14  Fast link dest: "/system/vendor"
/system/vendor  Inode 2892  Type: symlink  Mode 0644 Size 7   Fast link dest: "/vendor"
/dataext        File not found by ext2_lookup
```

Patch commands (`debugfs -w -f`, command file `logs/debugfs_cmds.txt`):
```
unlink /vendor
mkdir /vendor
sif /vendor mode 040755
sif /vendor uid 0
sif /vendor gid 0
mkdir /dataext
sif /dataext mode 040755
sif /dataext uid 0
sif /dataext gid 0
```

After (assertions PASS):
```
/vendor         Inode 2901  Type: directory  Mode 0755  User 0 Group 0  Size 4096  Links 2  EXTENTS (0):219224
/system/vendor  Inode 2892  Type: symlink    Mode 0644  Size 7   Fast link dest: "/vendor"   (unchanged)
/dataext        Inode 2902  Type: directory  Mode 0755  User 0 Group 0  Size 4096  Links 2  EXTENTS (0):219225
```

### 7.3 Filesystem check

```
e2fsck -f -y system_work.raw   → pass 1 rc=1  (fix: orphan inode 2898 moved to /lost+found; inode 2898 refcount 2→1)
e2fsck -f -y system_work.raw   → pass 2 rc=0  (clean; 2902/615296 files, 254290/2459354 blocks)
```

### 7.4 Recompute hashtree + FEC with the original parameters

```bash
export PATH=/root/los24/out/host/linux-x86/bin:$PATH   # host 'fec' tool is required by avbtool
python3 /root/los24/external/avb/avbtool.py add_hashtree_footer \
  --image system_work.raw \
  --partition_size 10235101184 \
  --partition_name system \
  --hash_algorithm sha256 \
  --salt 2b92bdc70f0956d0b3a1100c51d7bde331ea21642661b0b1a9e79c27d5febfd0 \
  --fec_num_roots 2 \
  --algorithm NONE \
  --prop com.android.build.system.os_version:17 \
  --prop com.android.build.system.fingerprint:Lenovo/TB323FU/TB323FU:17/CP2A.260605.016/eng.root:userdebug/test-keys \
  --prop com.android.build.system.security_patch:2026-11-01
```

Result: size exactly **10,235,101,184 B**; `Tree Offset 10073513984 / size 79331328`; `FEC Offset 10152845312 / size 80265216 / num roots 2`; `VBMeta Offset 10233110528 / size 832`; new **root digest `2a3c7c069c1dd825ff6c797ff920dca6c5df65dc1c066356936d910350682d4f`**. `avbtool verify_image`: `Successfully verified footer and NONE vbmeta struct` + `Successfully verified sha256 hashtree`.

### 7.5 Re-sign `vbmeta_system`

Same testkey chain as the rest of the bring-up (AOSP testkey, public-key sha1 `2597c218aae470a130f61162feaae70afd97f011`), same rollback index/location, only the `system` descriptor changes:

```bash
python3 /root/los24/external/avb/avbtool.py make_vbmeta_image \
  --output vbmeta_system_v7.img \
  --algorithm SHA256_RSA4096 --key testkey_rsa4096.pem \
  --flags 0 --rollback_index 1788566400 --rollback_index_location 2 \
  --padding_size 65536 \
  --include_descriptors_from_image system_raw_fixed.raw \
  --include_descriptors_from_image stock_product.raw \
  --include_descriptors_from_image stock_system_ext.raw \
  --include_descriptors_from_image pvmfw_b.img \
  --include_descriptors_from_image init_boot_logging4.img
```

Descriptor set (staged `verify_image` = 6/6 PASS): system `2a3c7c06…`, product `8a8c821e…` (stock), system_ext `c7980e63…` (stock), init_boot `a87adf96…` (the init_boot variant actually flashed), pvmfw `847e80aa…` (stock).

### 7.6 Rebuild `super`

`super_v7.img` = stock `super` with **only** the `system_b` extent replaced at offset **2,503,041,024 B**, length **10,235,101,184 B**:

```bash
python superkit.py build --src super_stock.img --dst super_v7.img --regions regions.json \
  --patch system_b=system_raw_fixed.raw --out build_v7.json
python superkit.py audit --lp --parallel-regions
python superkit.py compare --a audit_stock.json --b audit_v7.json
```

Audit result: 9 segments, **8 byte-identical to stock**, only `system_b` changed; LP metadata (first 64 KiB, primary 208,896 B, backup 196,608 B) byte-identical to stock.

### 7.7 Artifacts

| Artifact | Size (B) | SHA-256 |
|---|---|---|
| `system_raw_fixed.raw` | 10,235,101,184 | `1e7ec2d126d2889340578182b78121af7b39dbd1bc2165f39852cf4453673ff8` |
| `vbmeta_system_v7.img` | 65,536 | `6b11d5e4a83318f6ff95128404b59a1890b33b167c04806d974feb0b76c04616` |
| `super_v7.img` | 21,474,836,480 | `5779a9a5e73ddcdecea245fc65ad8cc9e398de4a1ab889d8656e8f3b335823bf` |

## 8. Verification on the device

- **2026-11-11 22:35 (first-stage fully passes)** — with the 22:18 diagnostic set (stock GPT + `vendor_boot_nofail` + `init_boot_logging10` + `vbmeta_system_v8`), the `misc`-captured kmsg (`device/kmsg_20261111_223511.txt`) shows: `:1234 init: init first stage started!`; `:2172-2190` **7 EXT4 partitions mounted** (`EXT4-fs (dm-7 … dm-13): mounted filesystem … ro without journal`); `:2193 init: Opening SELinux policy`; `:2195 init: Compiling SELinux policy` — i.e. first-stage now passes and the kernel reaches second stage, which never happened before.
- **22:40** — first adb user-space enumeration of LineageOS: `Lenovo/lineage_TB323FU/TB323FU:17/CP2A.260605.016/eng.root:userdebug/test-keys`, `slot=_b`, `vbs=orange`.
- **22:48–22:50** — user visually reaches the LineageOS welcome screen.
- **2026-11-12 F0 repair set** — the `system` image in the finally accepted set carries the same fixed root layout (plus the logdump removal of doc 06). Final acceptance: `sys.boot_completed=1`, boot animation stopped, FBE `file/encrypted`, `/metadata` and `/data` mounted, and 3/3 consecutive `adb reboot` rounds PASS.
- Honest caveat: the 22:18 set changed several variables at once (stock GPT restore, `no_fail` fstab, logging wrapper, `vbmeta_system_v8`); no single-variable control was run, so "the `/vendor` fix alone" was not isolated on-device. The structural proof is byte- and source-level, and the fix direction is additionally confirmed by the fact that the stock layout (with `/vendor` as a directory) is exactly what boots. Reproduce with the full known-good set described in the project state notes.

## 9. Known caveats / unverified

1. The new `/vendor` and `/dataext` directories **have no `security.selinux` xattr**; stock `/vendor` has `u:object_r:vendor_file:s0` and gid 2000, stock `/dataext` has `u:object_r:dataext_file:s0`. This does not block first stage (SELinux is not loaded yet; the directories are covered by their mounted filesystems afterwards), but if a `u:object_r:rootfs`-related denial appears later, add the xattrs.
2. `/lost+found/2898` keeps the old `/vendor` symlink inode; `e2fsck -fn` reports the filesystem clean, and the directory does not participate in boot.
3. `vbmeta_system_v7.img` is paired with the init_boot variant that was on the device at signing time; swapping init_boot requires re-signing the descriptor (a `…_stockib` variant was also produced).
4. The `hashtree`/FEC was recomputed, but no on-device dm-verity-enabled run was done at that time (the bring-up set was verity-off). Any future verity-on run must use a `vbmeta_system` whose system descriptor matches the shipped system image.
5. Not validated on-device at the time: whether the `/vendor` fix *alone* (with the old diagnostic set) would boot — see caveat in §8.

## 10. Reproduction summary

1. Check the LOS `system` raw image: `debugfs -R "stat /vendor"` must print `Type: directory`. If it prints `Type: symlink` with dest `/system/vendor`, the image has the loop.
2. Fix offline: strip footer → `unlink /vendor` + `mkdir /vendor` + `mkdir /dataext` (mode 040755, uid/gid 0) → `e2fsck -f -y` twice (rc=1 then rc=0) → `avbtool add_hashtree_footer` (original partition size/salt/FEC props) → `avbtool make_vbmeta_image` with the testkey chain.
3. Rebuild `super` replacing only the `system_b` extent; verify 8/9 other segments are byte-identical to stock.
4. Flash the coherent set and verify first stage from kmsg: `init: init first stage started!` → 7× `EXT4-fs (dm-…)` → `init: Opening SELinux policy`.

## 11. Evidence index

| Path | Content |
|---|---|
| `<PROJECT_ROOT>\out\2026-11-10-los24-logdump\LOS-SYSTEM-ANALYSIS.md` | first root-cause analysis: debugfs layout comparison, build-rule timestamps, source path, ELOOP semantics |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\IMAGE-FIX-REPORT.md` | offline patch production, avbtool parameters, super audit, artifact SHAs |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\VERIFY-REPORT.md` | independent re-derivation of the root cause (R1–R4) and independent verification of the three artifacts (R5–R9) |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\BOOTFIX-FACTS.md` | fact table: artifact mtimes, flashing set, boot evidence excerpts |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\device\kmsg_20261111_223511.txt` | first stage fully passing (7 EXT4 mounts; second stage start) |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\device\kmsg_20261111_230836.txt` | same boot family after 22:46: `Opening SELinux policy` → `Compiling` → `Loading SELinux policy` |
