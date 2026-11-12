Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0 (original text)

# 08 — SELinux: precompiled-policy checksum mismatch and the 4 KiB policy-sector patch

| Field | Value |
|---|---|
| Status | 2026-11-12 — resolved. The accepted flashing set no longer depends on the 4 KiB sector patch (it is currently inert); a policy decision on reverting that block is still open (§7). |
| Device | Lenovo Legion Y700 Gen 5 **TB323FU**, SN `<SN-REDACTED>`, SM8850P (canoe / kaanapali), A/B, 4 KiB pages, unlocked (`vbs=orange`), B slot active |
| Applies to | the LineageOS 24.0 (Android 17) port's `system_b` (LOS platform policy) combined with the stock `vendor_b`/`odm_b` (stock vendor/ODM policy) inside `super`; `/system/etc/selinux/plat_sepolicy_and_mapping.sha256` in `system_b` |
| Evidence sources | `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SELINUX-COMPILE-ANALYSIS.md`, `…\F0-SIDE-EFFECT-AUDIT.md`, `…\BOOTFIX-FACTS.md`, `…\SYSTEM-LOGDUMP-REMOVAL-REPORT.md`; `<PROJECT_ROOT>\out\2026-11-10-los24-logdump\LOS-SYSTEM-ANALYSIS.md`; `<PROJECT_ROOT>\out\2026-11-12-edl-f0\F0-ACCEPTANCE-REPORT.md` |

---

## 1. Where it shows up in the boot flow

Once first stage passes (doc 05), the kernel log reaches the second stage:

```
init: Opening SELinux policy
init: Compiling SELinux policy
```

(`device/kmsg_20261111_223511.txt:2193` / `:2195`; `…230836.txt:2175/2177`). "Compiling" means init decided **not** to use a precompiled policy and is running `secilc` on the device. If the CIL inputs are inconsistent, that compile fails at runtime and the boot dies a few milliseconds after `Using genfs …` — with the error text swallowed by the panic/ratelimit, which explains "silent reboot after ~20 ms into the SELinux step".

## 2. How init chooses precompiled vs. runtime compile

`system/core/init/selinux.cpp` (LOS 24 tree):

- `FindPrecompiledSplitPolicy()` `:133-185` — the precompiled policy (`/odm/etc/selinux/precompiled_sepolicy`, or `/vendor`'s) is used **only if three sha256 pairs all match**:
  - `/system/etc/selinux/plat_sepolicy_and_mapping.sha256` ↔ `precompiled_sepolicy.plat_sepolicy_and_mapping.sha256`
  - `/system_ext/etc/selinux/system_ext_sepolicy_and_mapping.sha256` ↔ `…system_ext…`
  - `/product/etc/selinux/product_sepolicy_and_mapping.sha256` ↔ `…product…`
  - Only the **first line** of each file is compared as a string; there is no signature or content verification.
- `GetVendorMappingVersion()` `:187-197` — the mapping version comes from `/vendor/etc/selinux/plat_sepolicy_vers.txt` (here `202504`).
- `GetUserdebugPlatformPolicyFile()` `:205-222` — debug policy only when `INIT_FORCE_DEBUGGABLE` and unlocked; this device has **no `/force_debuggable` and no `/userdebug_plat_sepolicy.cil`** (confirmed with debugfs), so the normal platform policy is used.
- genfs selection `:333-347` — `get_genfs_labels_version()`; vendor `genfs_labels_version.txt = 202504`, so `/system/etc/selinux/plat_sepolicy_genfs_202504.cil` is used (device log agrees).
- `compile_args` order `:349-392` (matches the device's actual invocation):
  ```
  /system/bin/secilc
    <plat_policy.cil>            # /system/etc/selinux/plat_sepolicy.cil
    -m -M true -G -N -v -c <SEPOLICY_VERSION>
    <plat_mapping.cil>           # /system/etc/selinux/mapping/202504.cil
    -o <compiled_sepolicy>       # /dev/sepolicy.XXXXXX
    -f <filecontext out>         # /sys/fs/selinux/null
    [<plat_compat.cil>]          # /system/etc/selinux/mapping/202504.compat.cil
    [<system_ext_policy.cil>]    # /system_ext/etc/selinux/system_ext_sepolicy.cil
    [<system_ext_mapping.cil>]   # /system_ext/etc/selinux/mapping/202504.cil
    [<system_ext_compat.cil>]    # /system_ext/etc/selinux/mapping/202504.compat.cil
    [<product_policy.cil>]       # /product/etc/selinux/product_sepolicy.cil
    [<product_mapping.cil>]      # /product/etc/selinux/mapping/202504.cil
    [<plat_pub_versioned.cil>]   # /vendor/etc/selinux/plat_pub_versioned.cil
    [<vendor_policy.cil>]        # /vendor/etc/selinux/vendor_sepolicy.cil
    [<odm_policy.cil>]           # /odm/etc/selinux/odm_sepolicy.cil
    [<genfs_cil>]                # /system/etc/selinux/plat_sepolicy_genfs_202504.cil
  ```

`-c` comes from the init build macro: AOSP `system/core/init/Android.bp` sets `-DSEPOLICY_VERSION=30`; the stock `/odm/etc/selinux/precompiled_sepolicy` binary header also reports policyvers `0x1e` (= 30). Offline testing with `-c 30/31/32/33` gave the same results (§5), so that value is not a risk factor.

## 3. The mismatch on the device

- The stock `/odm/etc/selinux/precompiled_sepolicy` was built against the **stock platform policy**, and its three recorded hashes are: plat `2fc99e11d7b3fb553103a4b77e3df001d0b64dc3cd741fab3c7b3c8a40582f2e`, system_ext `50cb98e2…`, product `4ae60473…`.
- The LOS `system` image ships a different platform policy, whose `plat_sepolicy_and_mapping.sha256` first line is `bb683371…`. The plat pair therefore **mismatches**, `FindPrecompiledSplitPolicy()` returns nothing, and init falls back to compiling `secilc` on the device.
- With **stock product/system_ext** still installed (their hash files do match the precompiled values), the runtime compile **fails** because the stock OEM `system_ext_sepolicy.cil` / `product_sepolicy.cil` reference types that exist only in the stock platform policy. The offline reproduction with the real image inputs (`_tmp/selinux`, host `secilc` from the LOS 24 build):

```
$ secilc <LOS plat> -m -M true -G -N -v -c 30 <LOS mapping/202504.cil> \
    -o actual.policy -f <fc> <LOS mapping/202504.compat.cil> \
    <stock system_ext/system_ext_sepolicy.cil> <stock se mapping/202504.cil> <stock se mapping/202504.compat.cil> \
    <stock product/product_sepolicy.cil> <stock product mapping/202504.cil> \
    <stock vendor/plat_pub_versioned.cil> <stock vendor/vendor_sepolicy.cil> <stock odm/odm_sepolicy.cil> \
    <LOS plat_sepolicy_genfs_202504.cil>
rc=254
Failed to resolve typeattributeset statement at .../stock_system_ext/etc/selinux/system_ext_sepolicy.cil:2
Failed to resolve AST
Failed to compile cildb: -2
```

- Root cause: stock OEM policy references OEM-platform-only types (e.g. `mediaserverwrapper`; stock plat declares it once, LOS plat zero times, vendor/odm never). `(typeattributeset domain (... mediaserverwrapper ...))` cannot resolve, so `secilc` fails immediately — consistent with the observed device behaviour (death ~20 ms after the genfs line). Adding a stub `(type mediaserverwrapper)` to the LOS plat only moved the error to `system_ext_sepolicy.cil:3` (next OEM-only type) ⇒ **not a single-symbol problem; stub patching is not viable**.

## 4. The 4 KiB policy-sector patch (the workaround used at 22:39)

Idea: make `FindPrecompiledSplitPolicy()` believe the precompiled policy matches by replacing the LOS plat hash line with the stock value — while stock `product`/`system_ext` (whose hash files already matched the precompiled values) were still installed. Then init loads `/odm`'s precompiled policy and **skips the failing runtime `secilc`**.

### 4.1 Target

- ext4 **block 81,367** of `system_b` — file offset 333,279,232 (= 81,367 × 4,096); absolute 4 KiB LBA **701,429** (= `system_b` base 620,062 + 81,367).
- The block belongs to inode 1043 = `/system/etc/selinux/plat_sepolicy_and_mapping.sha256` (65 B text file; original content = LOS plat policy sha).
- Patch file: `selinux_hash_sector.bin`, **4,096 B**, sha256 `d05ef83d3abc4e01ae19aefb446a5412653e9c29c63fdcb8d68b5abc5015f615`.
- New file content (first line): `2fc99e11d7b3fb553103a4b77e3df001d0b64dc3cd741fab3c7b3c8a40582f2e` (stock precompiled plat hash); verified with `debugfs cat` after the write.

### 4.2 Write and effect

- Written by EDL at LBA 701,429 during the 22:39 flashing step (together with `vendor_boot_diag2.img`); recorded in the flashing fact table (`BOOTFIX-FACTS.md`). This changed `system_b` content by exactly one 4 KiB sector, so `system_b` no longer equals `super_v7.img`'s replacement image as a whole (the whole-`super` SHA `5779a9a5…` no longer applies once this sector is patched).
- After the write and `power reset`, at **22:40** adb first enumerated the LineageOS user space (`watch-boot.log:131`, 18.4 s after watch start). The boot log of the previous attempt (22:35) had stopped at `Compiling SELinux policy`, i.e. the compile step was the last observed activity; with the patch the boot went past it.
- At **22:48–22:50**, after flashing LOS `product_b`/`system_ext_b` (22:45/22:46) and `fastboot -w`, the user visually reached the LineageOS welcome screen.
- **Honest caveat**: the 22:39 step changed more than one variable (`vendor_boot_diag2` + policy sector + subsequent product/system_ext replacement). The patch's causal role (skip the failing compile) is supported by offline compile data and by the 22:35 vs. 22:40 boot logs, but it was not isolated as a single-variable on-device test.

## 5. The proper fix: flash LOS `product`/`system_ext`

Offline reproduction with the LOS three-piece set (`system` = fixed LOS, `product`/`system_ext` = LOS raw images, `vendor`/`odm` = stock) compiled successfully:

| `policyvers` (-c) | rc | output |
|---|---|---|
| 30 (AOSP actual value) | **0** | 1,485,976 B, sha256 `3b337c371881a106bf19f2fe718d06a48c5cb13c8915f37f3bca921a243a27d7` |
| 31 | **0** | 1,485,984 B |
| 32 | **0** | 1,485,984 B |
| 33 | **0** | 1,489,704 B |

No stdout/stderr errors; host compile time 0.62 s (x86), estimated ~2–5 s on the device's ARM cores. Because LOS `product`/`system_ext` policy files are self-consistent with the LOS platform policy, the runtime compile succeeds and the precompiled-policy detour is unnecessary.

On the device this was done at **22:45/22:46**: flash `product_b` (sha `8624234c…`) and `system_ext_b` (sha `68b48149…`) + `fastboot -w`; the user reached the welcome screen at 22:48. The same change also removed the `com.motorola.android.providers.settings` signature conflict (that stock Moto app came from the stock `system_ext`).

Relevant input hashes (from the actual images):
- LOS `product/etc/selinux/product_sepolicy.cil`: empty policy, sha256 `01ba4719…daca546b` (1 B, normal); `product_sepolicy_and_mapping.sha256` = `75a11da4…`.
- LOS `system_ext/etc/selinux/system_ext_sepolicy.cil`: sha256 `ef46d746…`; `system_ext_sepolicy_and_mapping.sha256` = `71cdbbf6…`.
- Stock `vendor_sepolicy.cil` = `1862deda…`, `plat_pub_versioned.cil` = `e0996b2d…` (both from the stock `vendor_b`), stock `odm_sepolicy.cil` empty (1 B).

**Important consequence:** after LOS `product`/`system_ext` are installed, their hash files (`75a11da4…` / `71cdbbf6…`) no longer match the stock precompiled values (`4ae60473…` / `50cb98e2…`), so `FindPrecompiledSplitPolicy()` fails again and init goes back to the compile path — the 4 KiB policy-sector patch is now **inert** (it only changed the plat pair, which is irrelevant when the other two pairs mismatch).

## 6. Why not force the precompiled policy path

Forcing the precompiled policy would require rewriting all three hash files to the stock values (the plat one was done by the sector patch; product/system_ext would need further rewrites). Assessed risks:

1. init only does string comparison; there is no signature check — so it is technically possible.
2. The stock `precompiled_sepolicy` binary was compiled against the **stock platform policy**, while the LOS system user-space configuration is LOS: `plat_file_contexts`, `plat_property_contexts`, `plat_service_contexts`, `seclabel` entries in `.rc` files and xattrs on system files reference LOS-plat-only types (46 types/attributes exist in LOS plat but not in stock plat, measured offline). Loading the stock policy makes those labels/domains unresolvable → `avc denied` / invalid-context storms, and `system_server`/services will most likely fail to start.
3. It is forging AOSP consistency metadata (the hash files are the contract that the precompiled binary matches the installed policy); unsupported, and fragile across upgrades/rollbacks.
4. The three hash files live on verity-protected partitions, so changing them still requires rebuilding `super` and re-signing `vbmeta_system` — the cost is **no smaller** than flashing LOS `product`/`system_ext`, which was verified to compile with rc=0.
5. Fallback only (not used): offline-compile the policy and inject it as `/odm/etc/selinux/precompiled_sepolicy` (odm is a logical partition in `super`), rewriting the three hash files accordingly; this also requires rebuilding the odm hashtree descriptor in `vbmeta_b` and re-signing. This guarantees the policy matches the LOS three-piece set (equivalent to runtime compilation), but is a much wider change.

## 7. Current status in the accepted (F0) set

- The F0 `system` image still contains the 4 KiB policy block (block 81,367 → LBA 701,429): the 9-block diff relative to the pre-fix image includes it (`bb683371…` → `2fc99e11…`).
- It is **inert**: the F0 set uses LOS `product`/`system_ext` (`system_ext_f0diag`, `product_b`), so all three precompiled checks fail and init compiles at boot. Confirmed indirectly by normal boot + permissive SELinux and no policy-related failure.
- **Open decision** (recorded, not yet executed): either (a) revert that block to the LOS value (then the F0 diff becomes 8 blocks and the patch cannot silently activate), or (b) keep it and add an explicit constraint to the flashing set: "do not combine with stock `product`/`system_ext` unless the stock `/odm` precompiled policy is intended". Option (a) is recommended for a clean publishable image.
- Verity-on restoration recipe (independent of this doc): recompute the system hashtree → new root digest `9103aeb99e58b9356d7f6d1b7a629a148798926a7206ab9cc4dd978beedd5887`, new raw SHA `29ad60fb…`, `vbmeta_system_f0_v11.img` (`66e20599…`, staged verify PASS), and an avb-enabled `vendor_boot`. **Never** switch verity on with the current `system` + `vbmeta_system_v10` (whose system digest is the old `2a3c7c06…`): dm-verity would fail with EIO.

## 8. Unverified / limitations

1. The actual ARM `secilc` execution on the device was never captured: the analysis statically confirmed that `/system/bin/secilc` exists and is executable (aarch64 ELF, mode 0700, sha256 `11f25d00…`) and reproduced the compile on the host; device-side exec/memory/path failure was not observed.
2. The number of runtime SELinux denials with the LOS three-piece set was not quantified; the bring-up runs with `androidboot.selinux=permissive` (`avc denied … permissive=1` observed, e.g. 3,541 such lines in the last F0 boot), so denials did not block boot and were used as diagnostics only. Enforcing requires a separate policy pass.
3. The decision on reverting the 4 KiB policy block (§7) is still pending.
4. `llndk.libraries.txt` content was never diffed line by line (only sizes matched), and secondary mount points under `/mnt/vendor` were not audited one by one; neither is related to the SELinux compile path.

## 9. Evidence index

| Path | Content |
|---|---|
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SELINUX-COMPILE-ANALYSIS.md` | init compile path with line numbers, real input hashes, rc=254 failure text, LOS three-piece rc=0 matrix, assessment of forging precompiled hashes, fallback plan |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\SYSTEM-LOGDUMP-REMOVAL-REPORT.md` §3 | exact policy block (81,367 / LBA 701,429 / offset 333,279,232 / inode 1043), patch file SHA, post-write `debugfs cat` assertion |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\BOOTFIX-FACTS.md` | record of the 22:39 policy-sector write, flashing fact table, known-good boot configurations |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\F0-SIDE-EFFECT-AUDIT.md` §4#5, §5 | policy patch inertia analysis, revert recommendation, verity restore recipe |
| `<PROJECT_ROOT>\out\2026-11-10-los24-logdump\LOS-SYSTEM-ANALYSIS.md` §2-① | stock `/odm` precompiled policy hashes and the mismatch that forces runtime compilation |
| `<PROJECT_ROOT>\out\2026-11-11-los24-bootfix\device\kmsg_20261111_223511.txt` | `Opening SELinux policy` / `Compiling SELinux policy` at second stage (`:2193/:2195`) |
