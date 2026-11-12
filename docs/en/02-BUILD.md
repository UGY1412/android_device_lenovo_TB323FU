Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0 (original text)

# 02 · Build — LineageOS 24.0 (Android 17) for TB323FU

| Field | Value |
|---|---|
| Status | 2026-11-12 — build recipe validated; final images used by the 2026-11-12 acceptance run were produced on 2026-11-11 and are reproducible with the steps below |
| Applies to | Lenovo Legion Y700 Gen 5, model **TB323FU**; LineageOS 24.0 / Android 17, product `lineage_TB323FU-cp2a-userdebug` |
| Scope | Build host, source tree, device-tree configuration, lunch/build commands, the build-tree `/vendor` symlink root-fix, batch/pairing discipline, known build failures |
| Evidence sources | `out/2026-11-11-los24-bootfix/BUILD-FIX-REPORT.md`; `out/2026-11-11-los24-bootfix/BUILD-FIX-MANIFEST.json`; `<WORKSPACE>/research/a17-rom-survey/BUILD-LOG.md`; `<PROJECT_ROOT>/tmp/aera-recovery/ENV.md`; device-tree `BoardConfig.mk`/`device.mk`; `out/2026-11-11-los24-bootfix/SELINUX-COMPILE-ANALYSIS.md` |

> Design premise (**minimal content replacement**): this port compiles only `system`, `system_ext`, `product`, and the `vbmeta_system` signature. `vendor`, `odm`, `vendor_dlkm`, `system_dlkm`, the kernel, and the whole boot chain (`boot` / `init_boot` / `vendor_boot` / `dtbo` / `recovery`) remain stock Lenovo images. The kernel is not compiled; a prebuilt stock kernel is used only for the build-time VINTF kernel check.

## 1. Build host

| Item | Value |
|---|---|
| Host OS | Windows 10.0.19045.5856 + WSL2 |
| WSL release | Ubuntu 24.04.5 LTS (`VERSION_ID="24.04"`) |
| WSL version / kernel | WSL 3.0.1.0 / `6.18.40.1-microsoft-standard-WSL2` |
| CPU | Intel Xeon E5-2666 v3 @ 2.90 GHz; host 20 logical cores, WSL limited to **18** (`processors=18`) |
| RAM / swap | 47 GiB / 16 GiB (`memory=48GB`, `swap=16GB`) |
| Root FS | ext4 on `/dev/sdd`; `rw,relatime,discard,errors=remount-ro` |
| Build user | root inside WSL (no desktop user required) |
| JDK | **21.0.12.1 default** (`openjdk-21-jdk-headless`), 17.0.20.1 also installed; switch with `update-alternatives --set java /usr/lib/jvm/java-17-openjdk-amd64/bin/java` (and `javac`) |
| repo launcher | `/root/bin/repo` launcher **v2.71**; offline repo source at `/opt/aera-repo-src` (`REPO_URL=/opt/aera-repo-src`) |

### 1.1 Dependency baseline

Dependencies were audited against the AOSP Ubuntu 24.04 list and completed to `dpkg` 697 → 853 packages. The 25 packages installed in that round:

`cpio`, `device-tree-compiler`, `python3-venv`, `zstd`, `pigz`, `diffstat`, `jq`, `ninja-build`, `cmake`, `p7zip-full`, `android-sdk-libsparse-utils`, `android-sdk-platform-tools`, `dosfstools`, `f2fs-tools`, `libelf-dev`, `dwarves` (pahole), `libncurses-dev`, `libncurses6`, `libxml2-dev`, `libbz2-dev`, `libreadline-dev`, `libwxgtk3.2-dev`, `libsdl1.2-dev`, `moreutils`, `openjdk-21-jdk-headless`.

`mkbootimg` / `avbtool` are **not** installed system-wide on purpose: AOSP builds them from the source tree (`system/tools/mkbootimg`, `external/avb`) and this device tree also ships `prebuilts/` copies.

### 1.2 Network / mirrors

| Target | State | Notes |
|---|---|---|
| AOSP via USTC mirror | reachable (~0.1 s) | `~/.gitconfig` rewrites `https://android.googlesource.com/` → `https://mirrors.ustc.edu.cn/aosp/` |
| LineageOS Gerrit | via TUNA mirror | `https://review.lineageos.org/` → `https://mirrors.tuna.tsinghua.edu.cn/git/lineageOS/` |
| Gerrit LFS | direct | LFS blobs must come from Gerrit directly; the mirror rewrite is intentionally removed for LFS |
| `github.com` git protocol | reachable | used for donor trees |
| `gitlab.com` | **unreachable** | only relevant if an OrangeFox-era tree is to be reused |
| `raw.githubusercontent.com` | unreachable | not needed for this build |

## 2. Source tree

```bash
repo init -u https://github.com/LineageOS/android -b lineage-24.0 \
  --git-lfs --no-repo-verify --repo-rev main --depth=1
repo sync
```

- Tree location: `/root/los24`.
- Final size: `.repo` 70 GB, working tree total 105 GB.
- Missing projects after sync: 3 darwin-host prebuilts (disabled group; irrelevant on Linux).
- WebView prebuilt LFS artifacts for all four architectures were present (260/98/157/359 MB).
- Practical sync note: shallow `--depth=1` only works for brand-new projects; a reset of partially fetched projects was needed, and the successful full-tree fetch ran at `-j3` after USTC returned HTTP 429 for ~550 projects at higher parallelism.

## 3. Device tree configuration (key values)

The device tree in this repository is placed at `device/lenovo/TB323FU`. The values below are the ones that materially affect the build:

| Setting | Value | Reason |
|---|---|---|
| `TARGET_BOARD_PLATFORM` / `TARGET_BOOTLOADER_BOARD_NAME` | `canoe` | `ro.board.platform=canoe` on the device |
| `TARGET_ARCH` / `TARGET_ARCH_VARIANT` | `arm64` / `armv8-2a-dotprod` | 64-bit only SoC (`arm64-v8a`, empty 32-bit ABI list) |
| `TARGET_CPU_VARIANT_RUNTIME` | `oryon` | `ro.bionic.cpu_variant=oryon` |
| `TARGET_KERNEL_VERSION` | `6.12` | stock kernel `6.12.69-android16-6`; required because the tree compiles no kernel but `kernel.mk` still compares versions |
| `TARGET_PREBUILT_KERNEL` | `device/lenovo/TB323FU/prebuilt/Image` | stock kernel extracted from `boot_b.img`; SHA-256 `bb251454…`; used **only** for the VINTF kernel-version check |
| `BOARD_SYSTEMIMAGE_PARTITION_SIZE` | `10235101184` | stock `system` extent length |
| `BOARD_SYSTEM_EXTIMAGE_PARTITION_SIZE` | `562970624` | stock `system_ext` length |
| `BOARD_PRODUCTIMAGE_PARTITION_SIZE` | `2167775232` | stock `product` length |
| `BOARD_SUPER_PARTITION_SIZE` | `21474836480` | stock `super` (20 GiB) |
| `BOARD_QTI_DYNAMIC_PARTITIONS_SIZE` | `21470642176` | LP group maximum |
| `BOARD_SUPER_PARTITION_GROUPS` | `qti_dynamic_partitions` | group name has **no** slot suffix |
| `BOARD_*IMAGE_FILE_SYSTEM_TYPE` | `ext4` (system, system_ext, product, vendor, odm, vendor_dlkm, system_dlkm) | stock fstab declares ext4 for all seven logical partitions; magic check confirms |
| `TARGET_COPY_OUT_SYSTEM` / `_SYSTEM_EXT` / `_PRODUCT` | `system` / `system_ext` / `product` | full-userspace layout |
| `BOARD_AVB_ENABLE` | `true` | AVB v2 |
| `BOARD_AVB_ALGORITHM` | `SHA256_RSA4096` | device accepts AOSP testkey as the root of trust |
| `BOARD_AVB_KEY_PATH` | `external/avb/test/data/testkey_rsa4096.pem` | AOSP testkey (`pubkey sha1 2597c218…`) |
| `BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS` | `--flags 0` | chained vbmeta must use flags 0 |
| `BOARD_AVB_VBMETA_SYSTEM` | `system system_ext product` | one `vbmeta_system` signs all three |
| `BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX` / `_LOCATION` | `1788566400` / `2` | stock value; must not decrease |
| `TARGET_SCREEN_DENSITY` | `440` | `ro.sf.lcd_density=440` |
| `TARGET_FS_CONFIG_GEN` | `device/lenovo/TB323FU/config.fs` | 17 Qualcomm vendor AIDs (GID 2901–2917) needed by init/soong |
| `PRODUCT_SHIPPING_API_LEVEL` | `37` | LOS24 `cp2a` = SDK 37 / board API 202604; `COMMON_LUNCH_CHOICES` changed from `bp2a` to `cp2a` |
| `TARGET_COPY_OUT_VENDOR` + `BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE` | `vendor` + `ext4` | full-userspace build since 2026-11-09; this is also why the stale `/vendor` symlink issue below appeared |

Full files: `BoardConfig.mk`, `device.mk`, `lineage_TB323FU.mk`, `AndroidProducts.mk`, `config.fs`.

## 4. Lunch and build commands

```bash
cd /root/los24
export REPO_URL=/opt/aera-repo-src
export PATH=/root/bin:$PATH
export USE_CCACHE=false
export ALLOW_MISSING_DEPENDENCIES=true
export LC_ALL=C
source build/envsetup.sh
lunch lineage_TB323FU-cp2a-userdebug
mka systemimage out/target/product/TB323FU/vbmeta_system.img
```

Notes, all measured on this tree:

1. **Build `system` and `vbmeta_system` in the same `mka` invocation.** A second `mka` refresh can rebuild `system`/`system_ext`/`product` staging and change the AVB root digests, which silently breaks the pairing with an older `vbmeta_system`.
2. `mka vbmeta_systemimage` (phony target) **does not exist** in this tree: `Schedule Failure: unknown target "vbmeta_systemimage"`. Use the file path target as shown above.
3. In Android 17 / LOS24 the make target for `system_ext` lost its underscore: use `systemextimage`, not `system_extimage`. Full four-artifact command used on 2026-11-07:
   ```bash
   mka systemimage systemextimage productimage vbmetasystemimage -j12
   ```
   (`vbmetasystemimage` worked there as part of the same invocation, but the file-path form above is the documented-safe form for rebuilds.)
4. `ALLOW_MISSING_DEPENDENCIES=true` must be set **before** `source build/envsetup.sh`; the first build with this env triggers a one-off Soong full re-analysis (4 m 16.94 s). Keep the env stable afterwards or every build pays that cost again.
5. `lunch` identity check:

   | Variable | Value |
   |---|---|
   | `PLATFORM_VERSION` | 17 |
   | `LINEAGE_VERSION` | `24.0-20261106-UNOFFICIAL-TB323FU` |
   | `TARGET_PRODUCT` | `lineage_TB323FU` |
   | `TARGET_BUILD_VARIANT` | `userdebug` |
   | `BUILD_ID` | `CP2A.260605.016` |
   | `WITH_GMS` | false |

## 5. Build-tree `/vendor` symlink root-fix (the "stuck on first screen" build-side defect)

**Symptom.** The produced `system.img` had a self-referencing symlink ring at its root: `/vendor → /system/vendor` while `/system/vendor → /vendor`. At first-stage mount, `fs_mgr_create_canonical_mount_point()` calls `realpath()` on the mount point, hits `ELOOP`, `DoFirstStageMount()` returns false, and `first_stage_init` logs `LOG(FATAL)` — the device never reaches the second stage.

**Mechanism (source-level, AOSP + device-tree config).**

1. With full-userspace (`BOARD_USES_VENDORIMAGE=true`), `system/core/rootdir/create_root_structure.mk` is supposed to create a **directory** `root/vendor` (lines 54–55: `mkdir -p $(TARGET_ROOT_OUT)/vendor`).
2. The old 2026-11-07 `out/` was built while `TARGET_COPY_OUT_VENDOR` was still legacy `system/vendor`, so it contained `root/vendor -> /system/vendor`. After switching the tree to full-userspace on 2026-11-09 that symlink became stale.
3. Recreation of the root structure only happens inside `init.environ.rc`'s `LOCAL_POST_INSTALL_CMD`; if `out/.../root/init.environ.rc` already exists and is newer than its deps, ninja does not re-run the rule. Even when it does run, `mkdir -p …/vendor` on a dangling symlink fails, but the command is chained with `;` and the last `ln -sf` returns 0 → make sees success and the bad link survives.
4. `build_image.py` copies `out/.../root` into the image root (`shutil.copytree(root_dir)`), carrying the bad symlink into `system.img`.

**Fix actually used (2026-11-11, no source/device-tree changes, no `make clean`):**

```bash
cd /root/los24
P=out/target/product/TB323FU

# 0) preserve evidence of the broken staging
mkdir -p /root/buildfix/bak
cp -a $P/root/vendor /root/buildfix/bak/root-vendor.symlink
stat $P/root/vendor > /root/buildfix/bak/root-vendor.before.txt
readlink $P/root/vendor >> /root/buildfix/bak/root-vendor.before.txt
sha256sum $P/system.img > /root/buildfix/bak/old-system-img.sha256

# 1) delete the stale symlink FIRST
rm -f $P/root/vendor

# 2) force the root-structure post-install to re-run (delete the tracked carrier file)
rm -f $P/root/init.environ.rc

# 3) incremental rebuild (do NOT clean out/)
source build/envsetup.sh
export ALLOW_MISSING_DEPENDENCIES=true
export LC_ALL=C
lunch lineage_TB323FU-cp2a-userdebug
mka systemimage 2>&1 | tee /root/buildfix/build-$(date +%Y%m%d-%H%M%S).log

# 4) staging assertion
test -d $P/root/vendor && echo "OK: root/vendor is a directory"
```

**Proof after the rebuild:**

- staging: `root/vendor` = directory 0755, mtime 2026-11-11 21:40:19 (before: `lrwxrwxrwx … root/vendor -> /system/vendor`, mtime 2026-11-07 12:36:52).
- final image (`debugfs -R "stat /vendor" new-system.img`): `Type: directory Mode: 0755 User: 0 Group: 2000`, xattr `security.selinux = "u:object_r:vendor_file:s0"`.
- `/system/vendor` remains a symlink to `/vendor`; `/vendor` itself is an empty mount-point directory.
- `e2fsck -fn` clean: `2900/615296 files (0.7% non-contiguous), 254287/2459354 blocks`.
- AVB root digest changed as expected: `37cc913b3c2dc6813b454abaea1b347db0779665b256a88d1fa8ef5621af1553` (old) → `ba9495595acfaab2a99c9da6acd6fee65b8ab5b7d73b5afc57f126bb5e52046f` (final).
- `/dataext` is still absent from the image (see §7).

**Recurrence prevention.** The fix only holds while `root/init.environ.rc` is not rolled back independently. Recurrence happens if (1) `out/.../root/` is restored from a pre-2026-11-07 snapshot, (2) the tree flips between legacy and full-userspace again, or (3) a script drops a symlink into `root/` without forcing the `init.environ.rc` reinstall. Suggested wrapper hardening:

```bash
# self-heal before build
if [ -L out/target/product/TB323FU/root/vendor ]; then
  rm -f out/target/product/TB323FU/root/vendor
  rm -f out/target/product/TB323FU/root/init.environ.rc
fi
# assertion after build
test -d out/target/product/TB323FU/root/vendor || { echo "FATAL: root/vendor not dir"; exit 1; }
```

## 6. Final artifacts of the fixed batch (2026-11-11 21:49–21:50)

| Artifact | Size (B) | SHA-256 | AVB root digest |
|---|---|---|---|
| `out/target/product/TB323FU/system.img` (sparse) | 1,043,829,244 | `331acc2b17cfc421cbabd61eb1d7933b1f9d88c2d2c7a81571da9568d6922db2` | `ba9495595acfaab2a99c9da6acd6fee65b8ab5b7d73b5afc57f126bb5e52046f` |
| `system_ext.img` (sparse) | 465,404,172 | `d86e4b4d358dd940cfdea19f2fa06c29fb9f92de389c04bc2d344e6b0b149e35` | `b687aa29a164de7cd699aece4c4a64b84f577f06dba431b71fd9658a3d8d569c` |
| `product.img` (sparse) | 533,258,592 | `1e9ac21f3b21e046724633d006768c2d7705aa5cad22fe6bdbeac52df1c6a658` | `34610c0793381e170016db9fa01323397ffbdee48dfddbde52f6ef63ed490741` |
| `vbmeta_system.img` | 65,536 | `b8fa5f4dbfd6f69b75aa2f9f8dece8cd40a60c0545aff35fa78352b5ea94b946` | `SHA256_RSA4096`, pubkey sha1 `2597c218aae470a130f61162feaae70afd97f011`, rollback index `1788566400`, flags 0 |
| raw for `super` packaging: `new-system.img` | 10,235,101,184 | `f716cfe5c7f5827b12b64bdf7dc782a20d7ad9b4622e40381f39b2124a2e0b7f` | matches `BOARD_SYSTEMIMAGE_PARTITION_SIZE` exactly |
| raw `new-system_ext.img` | 562,970,624 | `af79baa59f367b4c788c1d9f4bf976e6ff94aa04459518bac6e92313a6998c51` | matches board size |
| raw `new-product.img` | 2,167,775,232 | `38af4ee21e5c8c4cf49e18a499d61bc70e0ab1f5ef4525f2b877eeeff3034a82` | matches board size |

`vbmeta_system.img` embeds hashtree descriptors equal to the three images above (`system ba949559…`, `system_ext b687aa29…`, `product 34610c07…`), verified with `avbtool info_image` — the AVB chain is self-consistent.

Earlier batch (2026-11-07) artifacts, still useful for history: `system c7caea7d…`, `system_ext 488c5815…`, `product 3c732a7c…`, `vbmeta_system 37f16224…`.

## 7. Known gap: `/dataext`

The stock system-as-root image has a `/dataext` directory; the LineageOS image does not (`debugfs -R "stat /dataext"` → File not found). It is **not** the cause of the first-screen failure and was intentionally excluded from the minimal fix set. Correct future patch:

```make
# device/lenovo/TB323FU/BoardConfig.mk, near the full-userspace section
BOARD_ROOT_EXTRA_FOLDERS += dataext
```

plus a SELinux `file_contexts` mapping (currently no `dataext` label exists in the tree's sepolicy; the AOSP mechanism is `create_root_structure.mk:29-31` `mkdir -p … $(BOARD_ROOT_EXTRA_FOLDERS)`). Without a context the new directory may fall back to `rootfs` or fail the build; do it in a dedicated round and verify with `debugfs -R "stat /dataext"`.

Impact: first-stage init comes from the stock `vendor_boot` ramdisk; if its init mounts `/dataext` with a `mkdir` fallback, the missing directory does not block boot — only services that depend on that mount may be affected. This is why the omission did not block the acceptance run.

## 8. Packaging the new images into `super`

`vbmeta_system` is a **physical** partition on LUN0 (not inside `super`); `system`/`system_ext`/`product` are LP regions inside `super`. The project tool `superkit.py` (regions / audit / build / compare subcommands) patches only the three regions:

```bash
cd <WORKSPACE>/_tmp/super    # WSL view of the project workspace

# (a) derive region map from stock lpdump (skip if regions.json exists)
python3 superkit.py regions --lpdump lpdump_stock_all.txt --size 21474836480 --out regions.json

# (b) patch the three regions of a base super with this batch's raw images
python3 superkit.py build \
  --src  <base_super.img> \
  --dst  /root/buildfix/super_systemfix-20261111.img \
  --regions regions.json \
  --patch system=/root/buildfix/new-system.img,system_ext=/root/buildfix/new-system_ext.img,product=/root/buildfix/new-product.img \
  --out  /root/buildfix/super-build-20261111.json

# (c) audit: only system/system_ext/product region SHAs change; LP metadata untouched
python3 superkit.py audit --file /root/buildfix/super_systemfix-20261111.img \
  --regions regions.json --out /root/buildfix/super-audit-20261111.json --lp
python3 superkit.py compare --a <base_audit.json> --b /root/buildfix/super-audit-20261111.json \
  --out /root/buildfix/super-compare-20261111.json
```

Expected: `compare` shows changes only for `system`, `system_ext`, `product`; `audit --lp` keeps the stock first-64-KiB SHA-256 `fc0163625355ffd46479d9a6c671187a3879954d43cb3c2cf46407dc3b68c573`.

**Pairing rules (hard):**

- `vbmeta_system` must be built/flashed with the same batch as `system` + `system_ext` + `product`; mixed batches break dm-verity.
- The offline-patched `system` route produces a different root digest and its `vbmeta_system` is **not** interchangeable with the build-header-produced one.
- `fastboot flash super` rejects sparse images: always package a raw `super`.
- Always re-extract raw images with `simg2img`, re-record `avbtool info_image` root digests, and re-check the `vbmeta_system` descriptors before packaging.

## 9. Known build failures and fixes

| Error / symptom | Root cause | Fix |
|---|---|---|
| `prebuilt_libbundleaidl` (vendor/lenovo/TB323FU/Android.bp:32469) depends on `android.media.audio.common.types` **V4 and V5** two versions | a stale 3 GB A16-era vendor-blobs tree had been placed under `/root/los24/vendor/lenovo/TB323FU`; Soong scans it and its 4800 prebuilt modules referenced AIDL V4 | delete that vendor-blobs tree (the minimal-content design compiles no vendor blobs; `inherit` in `device.mk` is commented out) |
| `ninja: unknown target "system_extimage"` | Android 17 renamed the target (underscore removed) | use `systemextimage`; `mka systemimage systemextimage productimage vbmetasystemimage` |
| `vendor/lineage/build/tasks/kernel.mk:122: error: Argument missing.` | no kernel source present, so `TARGET_KERNEL_VERSION` degrades to `.` | set `TARGET_KERNEL_VERSION := 6.12` (major.minor only; `kernel.mk:123` compares against 6.1) |
| `ninja: 'out/target/product/TB323FU/kernel' … missing and no known rule to make it` | `TARGET_PREBUILT_KERNEL` empty → `NEEDS_KERNEL_COPY` false → no rule for the kernel stub | point `TARGET_PREBUILT_KERNEL` at `device/lenovo/TB323FU/prebuilt/Image` (stock kernel, 42,097,152 B, SHA-256 `bb251454…`) |
| Build killed with exit 143 (`Got signal: terminated`) | a second (recovery) build ran concurrently inside the same WSL instance | serialize builds, or reduce jobs and `nice` the build |
| Build killed with exit 137 (`Killed`) | 47 GiB RAM exhausted at `-j16/-j18` while another build was running | tune jobs down (`-j8` succeeded); the final full build ran with `-j8` after earlier attempts at `-j12/-j18/-j16` |
| First build with `ALLOW_MISSING_DEPENDENCIES=true` takes +4 m 17 s | Soong full re-analysis, one-off | keep the env stable across builds |
| Runtime `secilc` fails `rc=254` (`Failed to resolve typeattributeset` in `system_ext_sepolicy.cil:2`) with LOS `system` + stock `product`/`system_ext` | OEM `product`/`system_ext` policies reference OEM-only types absent from the LOS platform policy | flash LOS `product` and `system_ext` as well; then runtime secilc compiles `rc=0` (host-side reproduction, `-c 30/31/32/33` all pass). Details in `08-SELINUX-POLICY.md` |

## 10. Build-time reference

| Run | Result |
|---|---|
| 2026-11-07 first full build | started 04:40:21, `build completed successfully (57:52)` at 12:59:05, `BUILD_EXIT=0`; four artifacts + `avbtool verify_image rc=0` |
| 2026-11-11 root-fix `mka systemimage` | 9 m 18 s total = Soong re-analysis 4 m 16.94 s (one-off) + kati + ninja `1m52.06s`; `build completed successfully (09:18)` |
| 2026-11-11 second `mka` (rebuilt `vbmeta_system` + three images) | 5 m 40 s |
| Routine incremental build with stable env | ≈ 5 min |

## 11. Verification commands (run before any flashing)

```bash
# extract raw from sparse
simg2img out/target/product/TB323FU/system.img /root/buildfix/new-system.img

# filesystem sanity
e2fsck -fn /root/buildfix/new-system.img

# mount-point assertions
debugfs -R "stat /vendor" /root/buildfix/new-system.img
debugfs -R "stat /system/vendor" /root/buildfix/new-system.img
debugfs -R "stat /dataext" /root/buildfix/new-system.img

# AVB identity
out/host/linux-x86/bin/avbtool info_image --image out/target/product/TB323FU/system.img | grep "Root Digest"
out/host/linux-x86/bin/avbtool verify_image --image out/target/product/TB323FU/vbmeta_system.img \
  --key external/avb/test/data/testkey_rsa4096.pem

# pairing: listed root digests must equal the three image root digests
out/host/linux-x86/bin/avbtool info_image --image out/target/product/TB323FU/vbmeta_system.img

# hashes
sha256sum out/target/product/TB323FU/system.img out/target/product/TB323FU/system_ext.img \
  out/target/product/TB323FU/product.img out/target/product/TB323FU/vbmeta_system.img
```

## 12. Evidence sources

| Topic | Evidence |
|---|---|
| Host/deps/JDK/repo/network | `<PROJECT_ROOT>/tmp/aera-recovery/ENV.md` (§1–§3) |
| Source tree / lunch / build timeline / failure log | `<WORKSPACE>/research/a17-rom-survey/BUILD-LOG.md` |
| `/vendor` symlink root-fix, artifact table, `/dataext` | `out/2026-11-11-los24-bootfix/BUILD-FIX-REPORT.md`, `BUILD-FIX-MANIFEST.json` |
| BoardConfig values | device-tree `BoardConfig.mk` |
| Runtime `secilc` failure analysis | `out/2026-11-11-los24-bootfix/SELINUX-COMPILE-ANALYSIS.md` |
| super packaging tooling | `_tmp/super/superkit.py` + `regions.json` + `lpdump_stock_all.txt` |
