Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0 (original text)

# 09 — AVB Chain Notes (Lenovo Legion Y700 5th Gen, TB323FU, LineageOS 24)

| Item | Value |
|---|---|
| Document status | 2026-11-12; boot-time behavior verified on hardware (F0 acceptance PASS) |
| Applicable device | Lenovo Legion Y700 5th Gen **TB323FU** (SM8850P, canoe/kaanapali), unlocked bootloader (verified-boot state = orange), active slot = B |
| Scope | Android Verified Boot (AVB) topology of the stock firmware, the tested chain that lets LineageOS 24 boot, what may/must not be modified, how to re-sign images, dm-verity coupling, slot state storage, verification commands |
| Out of scope | Kernel/DTB changes, firmware flashing rules, SELinux policy content, recovery image internals |
| Related docs | [01 — Device Facts](01-DEVICE-FACTS.md) (identity/partition geometry), [03 — Flash](03-FLASH.md) (write sets and rollback), [05 — Root cause: /vendor ELOOP](05-ROOTCAUSE-VENDOR-SYMLINK.md), [08 — SELinux](08-SELINUX-POLICY.md), [11 — Error Catalog](11-ERROR-CATALOG.md), [12 — Experiment Log](12-EXPERIMENT-LOG.md) |
| Evidence policy | Every number is copied from offline image analysis or on-device logs. Claims that were not closed are explicitly marked **UNVERIFIED**. Nothing in this document is a "should work" guess presented as fact. |

> **Path convention.** Evidence paths are written relative to the project root, which is redacted as `<PROJECT_ROOT>`. The build tree is a WSL Ubuntu tree at `/root/los24` (LineageOS 24.0 / Android 17). Serial numbers are shown as `<SN-REDACTED>` and MAC addresses as `<MAC>` throughout this repository.

---

## 1. TL;DR

1. The stock chain is **hash-pinned, not fully replaceable**: root `vbmeta_b` is signed with the OEM key and pins `boot_b`, `recovery_b` (chain partitions) and `dtbo_b`, `vendor_boot_b` (hash descriptors).
2. The only part of the chain proven compatible with self-built content is the **AOSP testkey** subtree: root `vbmeta_b` re-signed with AOSP testkey + `vbmeta_system_b` re-signed with AOSP testkey + **stock** `boot_b`/`recovery_b`/`dtbo_b`/`vendor_boot_b` + stock partition content boots to `sys.boot_completed=1` (experiment E12). Self-generated non-testkey keys fail.
3. The root `vbmeta_b` is the **only** place where dm-verity can be globally disabled (`flags=1/2`). A per-partition digest mismatch is **not** excused by an unlocked bootloader; it produces dm-verity I/O errors (EIO) at mount time.
4. Changing `vendor_boot_b` (fstab flags) is tolerated by the unlocked ABL: the device shows "orange" and may stop at the first screen, but it does **not** fall back to the bootloader. Changing `init_boot_b` to a non-OEM, non-hash-pinned image has always been observed to return to bootloader fastboot within ~8–12 s.
5. `slot-unbootable` lives in the **GPT partition attributes** (LUN4, `boot_b`, entry 53, attribute byte 54): `0x6F` = active + successful + bootable, `0xEF` = unbootable bit (0x80) set. It is not in `misc`, `devinfo`, `efisp` or `uefivarstore`.
6. The F0 booting set is deliberately **verity-off**: `vendor_boot_diag2` (all `avb=` flags removed from the first-stage fstab) + `vbmeta_system_v10` (system digest `2a3c7c06…`) + a `system_b` whose AVB footer is still the old one. This is safe only because verity is off; restoring verity requires a recomputed hashtree and the matching `vbmeta_system` (see §8.4).

---

## 2. Terminology used in this note

| Term | Meaning here |
|---|---|
| root vbmeta | The top-level `vbmeta` (on this device: partition `vbmeta_b`, LUN4 LBA 513634, 65,536 B) |
| chain partition | A partition whose own vbmeta is loaded **because** the root vbmeta contains a `chain` descriptor pointing at it (`chain_partition`), e.g. `vbmeta_system_b` |
| hash descriptor | Root vbmeta pins the exact bytes of a partition (`dtbo_b`, `vendor_boot_b`, `init_boot_b`) as `sha256(salt ‖ data[0:image_size])` |
| hashtree descriptor | dm-verity tree/FEC layout for a filesystem image (`system`, `system_ext`, `product`, `vendor`, `odm`, …) |
| rollback index (RI) | Anti-rollback counter; must never decrease |
| RI location | Which rollback-index slot in the bootloader store the value uses; stock `vbmeta_system` uses location **2** |
| footer | AVB metadata appended to the image itself; its `Algorithm` is `NONE` for `init_boot`/`dtbo`/`vendor_boot` (they are hash-only, not signed) |
| first-stage fstab | `first_stage_ramdisk/fstab.qcom` inside the **stock** `vendor_boot_b` ramdisk; it decides which partitions are mounted by first-stage init and whether dm-verity is used |
| orange / verified-boot state | `ro.boot.verifiedbootstate=orange` = unlocked bootloader; AVB verification errors are tolerated by ABL |

---

## 3. Partition/LUN facts needed to reason about AVB

All LBAs use **4 KiB sectors**. Only the sections relevant to AVB are listed.

| Object | LUN | Start LBA | Size |
|---|---|---|---|
| `super` (physical) | 0 | 8968 | 20 GiB (21,474,836,480 B) |
| `vbmeta_system_b` | 0 | 5,251,864 | 16 sectors (65,536 B) |
| `misc` | 0 | 8456 | 256 sectors (1 MiB) |
| `metadata` | 0 | 5,251,880 | 64 MiB (block device `sda10`) |
| `userdata` | 0 | — | `sda14` |
| `vbmeta_b` | 4 | 513,634 | 16 sectors (65,536 B) |
| `boot_b` | 4 | 489,006 | 24,576 sectors (100,663,296 B) |
| `vendor_boot_b` | 4 | 672,238 | 24,576 sectors |
| `init_boot_b` | 4 | 722,990 | 2,048 sectors (8,388,608 B) |
| `dtbo_b` / `recovery_b` / `pvmfw_b` | 4 | 513,650 / 696,878 / 725,054 | — |
| `logdump` (diagnostic target, not AVB-covered) | 4 | 735,255 | 512 MiB |

Logical partitions of `super` are mapped by liblp; `system_b` is the only logical partition rewritten by this port. Physical LBA of `system_b` = 620,062 (super start 8968 + 611,094), length 2,498,804 sectors (10,235,101,184 B).

---

## 4. Stock AVB topology (as shipped by the OEM)

```
root vbmeta_b   (OEM key 8fcb864f…, flags=0, rollback_index=0)
 ├─ CHAIN  boot_b            → OEM key 8fcb864f…          (do not replace)
 ├─ CHAIN  recovery_b        → OEM key 8fcb864f…          (do not replace; replacing it risks red-screen / unbootable)
 ├─ CHAIN  vbmeta_system_b   → testkey is accepted after re-signing (E12 form)
 ├─ HASH   dtbo_b            (sha256(salt‖content); footer Algorithm=NONE)
 ├─ HASH   vendor_boot_b     (same; footer Algorithm=NONE)
 └─ TREE   dataext_b, odm_b, system_dlkm_b, vendor_b, vendor_dlkm_b

vbmeta_system_b  (stock: OEM key, flags=0, RI=1788566400, RI-location=2)
 ├─ HASH   init_boot_b       (stock: image_size=2,555,904 / salt 99caf6df… / digest dcf52c78…)
 ├─ HASH   pvmfw_b           (761,856 B / digest 847e80aa…)
 └─ TREE   product, system, system_ext   (hashtree root must equal the image footer)
```

Stock reference hashes (SHA-256, verified against the full readback set):

| Partition | SHA-256 |
|---|---|
| `vbmeta_b` | `ae4ebd619bb57c0d4f50e6619d1a5937bc805b8eaff90f83becdf2631dbf54d7` |
| `vbmeta_system_b` | `493448e6…` |
| `boot_b` | `2731d62ca182c811ed51e4c4e33fe22da4191218569499cdb7debf793c072bec` |
| `init_boot_b` | `a31072c0b26f5df8581e2f23e9a39cb8476c00b2b9f251c701db433141653e68` |
| `vendor_boot_b` | `9349137dc262ab61508014275b623f4d39e5b14bc55c77082848d63a28f381b2` |
| `dtbo_b` | `6cdc8d3bbf2ff9123ad303db9837e666c5f7a1da4a0654a5799439aba239db49` |
| `recovery_b` | `a3b34a80b8e15a9ef6f66831b64d6f10f4a37ad2676b4102eb43e529862acea0` |
| `pvmfw_b` | `d24b59dc…` |
| `dataext_b` | `e231c8c7…` |
| `super` | `78e54bd36dc1d6971d338ffb49670c6809cad36ca16f6004d0b281af331cf4e5` |

The first-stage fstab (extracted from the stock `vendor_boot_b` ramdisk, 7,374 B) contains 13 mount lines with `first_stage_mount`: `system`, `system_ext`, `product`, `vendor`, `vendor_dlkm`, `system_dlkm`, `odm` (all `avb=…,logical,first_stage_mount`), plus the physical boot-chain partitions. Only the `system` line additionally carries seven GSI `avb_keys=/avb/*-gsi.avbpubkey` entries; `/dataext` is second-stage only.

---

## 5. The chain that was actually proven to boot LineageOS 24 content

**E12 configuration (stock content, proves the signing model):**

```
root vbmeta_b      = AOSP testkey re-sign   (pubkey sha1 2597c218aae470a130f61162feaae70afd97f011)
 ├─ CHAIN boot_b     → OEM key 8fcb864f…    (stock boot image kept)
 ├─ CHAIN recovery_b → OEM key 8fcb864f…    (stock recovery kept)
 ├─ CHAIN vbmeta_system_b → testkey 2597c218…
 └─ HASH/HASH/TREE  dtbo_b / vendor_boot_b / dataext,odm,system_dlkm,vendor,vendor_dlkm
vbmeta_system_b    = AOSP testkey re-sign, flags=0, RI=1788566400, RI-location=2
 ├─ HASH init_boot_b  (stock or diagnostic wrapper, digest recomputed)
 ├─ HASH pvmfw_b      (stock digest)
 └─ TREE product / system / system_ext (digests recomputed from the actual images)
```

Result: `sys.boot_completed=1` with the stock fingerprint. The decisive detail is that a **custom signing key is rejected**, while the **AOSP testkey is accepted** by this ABL; only `boot`/`recovery` must stay OEM-signed because they are *chain* partitions of the OEM root.

The LineageOS booting set used for this port keeps the root `vbmeta_b` in this testkey form (`7ed20919…`, `vbmeta_b_testkey_E12.img`) and re-signs `vbmeta_system_b` whenever `system`/`product`/`system_ext`/`init_boot` change.

---

## 6. Why AVB self-consistency is a hard prerequisite (dm-verity coupling)

- First-stage init reads its fstab from the **stock** `vendor_boot_b` ramdisk (`first_stage_ramdisk/fstab.qcom`); this cannot be changed by editing `system` content. Logical partitions are resolved to `*_b` by `slotselect`.
- For each `avb=` partition, `fs_avb` builds a dm-verity device from the embedded hashtree (for `system`: via the GSI `avb_keys` first, then falling back to the `avb=vbmeta_system` descriptor). **The actual verification happens when the filesystem reads blocks, not when the dm table is created.** Whether the mount succeeds is decided by `sha256` of the data blocks against the tree/FEC built earlier.
- Therefore a content/footer mismatch shows up later as **EIO while reading `system`**, not as a friendly "verification failed" message. This is why `avbtool verify_image` (offline) is mandatory before flashing a new `system`/`product`/`system_ext`.
- A digest mismatch is **not** excused by `unlocked`/orange. Unlocking only tolerates signature-verification errors (`ERROR_VERIFICATION`, `PUBLIC_KEY_REJECTED`); a structurally invalid chained vbmeta (`ERROR_INVALID_METADATA`) and a data-hashtree mismatch still fail (EIO / `AvbHandle::Open()` returning null).
- The **only** global "off" switch is `flags=1/2` in the top-level root vbmeta. A per-partition `vbmeta_system flags=1` does not help. That experiment was run (E7) and did not change the failure.
- Diagnostic shortcut used by this port: `vendor_boot` variants whose first-stage fstab has **all `avb=`/`avb_keys=` flags removed** (plus `no_fail`) mount the logical partitions without dm-verity. This is a diagnostic/bring-up configuration, not a release configuration.

---

## 7. What may be changed (and what it costs)

| Component | Mechanism | Can it be changed? | Observed consequence |
|---|---|---|---|
| `system`, `system_ext`, `product` (logical) | hashtree descriptors in `vbmeta_system` | **Yes**, but `vbmeta_system_b` must be re-signed with the new root digests and flashed in the same transaction | Verity-off: any content boots. Verity-on: a stale digest → dm-verity EIO at mount |
| `init_boot` | hash descriptor in `vbmeta_system` | **Yes** — re-hash it in `vbmeta_system` (stock `image_size` 2,555,904 → wrapper images are larger, e.g. 2,736,128) | A custom init_boot (non-OEM signature or unbounded chain) was observed to return to bootloader fastboot in ~8–12 s |
| `vbmeta_system` | chain partition → must be signed by a key the root trusts | **Yes with testkey** (AOSP testkey pubkey must be the chain target in root) | Works (E12 and all later builds) |
| root `vbmeta_b` | top-level vbmeta | **Yes with AOSP testkey**; **never with a privately generated key** | Custom key → 8 s to fastboot. Testkey → boots. |
| `boot`, `recovery` | chain partitions → OEM key | **No, keep stock** | Replacing/re-signing them to testkey was never observed to boot cleanly (one attempt returned to fastboot in 12 s while the slot was also unbootable, so the experiment is inconclusive) |
| `vendor_boot` | hash descriptor in root vbmeta | **Tolerated by unlocked ABL** even when the hash does not match | Orange state; device may hang at the first screen; does not by itself fall to fastboot |
| `dtbo` | hash descriptor in root vbmeta | Not changed in this port | If changed, must be re-hashed in root vbmeta |
| `dataext`, `odm`, `vendor`, `vendor_dlkm`, `system_dlkm` (physical/logical content) | hashtree descriptors in root vbmeta | Only by re-signing root vbmeta with a key the device accepts | `dataext_b` content is assumed stock; `vold` warnings only if corrupted (not fatal) |
| `super` LP metadata | not covered by AVB | Must not be hand-edited | Use liblp tools/fastbootd; hand-written LP metadata risks unbootable super |

---

## 8. Signing recipes (commands actually used)

`avbtool` is the AOSP copy from the LineageOS tree: `/root/los24/external/avb/avbtool.py`. The testkey used here is the public AOSP `testkey_rsa4096.pem` (`<PROJECT_ROOT>/tmp/recon/testkey_rsa4096.pem`, SHA-256 `6a224754880a57ab9cbd308267cd157d94cf05a1c8cb851aec4090e045d24121`); its public key SHA-1 is `2597c218aae470a130f61162feaae70afd97f011`. **AOSP testkey is publicly known — never use it as a production security anchor.**

### 8.1 `system` hashtree footer (after fixing content)

```bash
export PATH=/root/los24/out/host/linux-x86/bin:$PATH   # host 'fec' binary is required
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
python3 /root/los24/external/avb/avbtool.py verify_image \
  --image system_work.raw --key /root/los24/external/avb/test/data/testkey_rsa4096.pem
```

`--calc_max_image_size` must report 10,073,513,984 B (exactly the ext4 data area). The resulting footer must be compared field-by-field with the original LOS footer: `Image Size`, `Original image size`, `salt`, `Tree offset/size`, `FEC offset/size`, `FEC roots`, `Partition Name`, `Algorithm: NONE`, and the three `com.android.build.system.*` props. For the boot-fix image the numbers were: original image size 10,235,101,184 B, AVB image size 10,073,513,984 B, salt `2b92bdc7…`, tree 79,331,328 B @ 10,073,513,984, FEC 80,265,216 B @ 10,152,845,312, FEC roots 2, old root digest `37cc913b…` → new root digest `2a3c7c06…`.

### 8.2 `init_boot` hash footer (diagnostic wrapper or stock)

```bash
avbtool add_hash_footer \
  --image payload.img \
  --partition_size 8388608 \
  --partition_name init_boot \
  --hash_algorithm sha256 \
  --algorithm SHA256_RSA4096 \
  --key testkey_rsa4096.pem \
  --rollback_index 1788566400
```

`mkbootimg` must produce header v4 with **`kernel_size=0`** (a 1-byte kernel makes the wrapper never execute), `--os_version 17.0.0 --os_patch_level 2026-09`, page size 4096. For `init_boot_logging13.img`: payload 2,736,128 B, footer digest `4bf06b0c…`, salt `c1250c11…`, total 8,388,608 B, `verify_image` PASS.

### 8.3 `vbmeta_system` (testkey, all descriptors from actual images)

```bash
avbtool make_vbmeta_image \
  --output vbmeta_system_v10.img \
  --algorithm SHA256_RSA4096 --key testkey_rsa4096.pem \
  --flags 0 --rollback_index 1788566400 --rollback_index_location 2 \
  --padding_size 65536 \
  --include_descriptors_from_image init_boot_logging13.img \
  --include_descriptors_from_image stock_product.raw \
  --include_descriptors_from_image stock_system_ext.raw \
  --include_descriptors_from_image system_raw_fixed.raw \
  --include_descriptors_from_image pvmfw_b.img
```

Resulting header for `v10`: pubkey sha1 `2597c218…`, `SHA256_RSA4096`, RI 1788566400, RI location **2**, flags 0, 65,536 B, sha256 `2b52e26b9c1bc8f15562d5e22a1fc2eced0d5721a432e15846ee26901fce4afc`. Staged `verify_image` must be run with the real partition images available in the same directory (avbtool resolves partition names to files).

### 8.4 Restoring dm-verity after the F0 boot set (recipe, not applied in production flow)

1. Take the F0 content (F0 = logdump removal; system root digest changed because files were deleted), rebuild the hashtree/FEC and sign it:
   - new verity-ready `system` raw: SHA-256 `29ad60fb…` (10,235,101,184 B), new root digest `9103aeb9…`;
   - rebuild `vbmeta_system` with that digest → `vbmeta_system_f0_v11.img`, SHA-256 `66e20599…`, all other descriptors unchanged (`init_boot` 2,736,128/`4bf06b0c…`, `pvmfw` 761,856/`847e80aa…`, `product` `8a8c821e…`, `system_ext` `c7980e63…`, `system` `9103aeb9…`).
2. Flash the **full** verity-ready `system` image (the 9-block incremental patch leaves the old footer and is verity-off only).
3. Replace the diagnostic `vendor_boot` with an AVB-enabled variant whose first-stage fstab keeps `avb=` flags.
4. Only then enable verity. **Never** enable verity with F0's current `vendor_boot_diag2` + `vbmeta_system_v10`: the system digest does not match the modified content → dm-verity EIO.
5. `vbmeta_b` (testkey root) does **not** need to change for this.

---

## 9. Pairing matrix (the most common source of "it flashed but does not boot")

| Boot set | `system` content | `vbmeta_system` | `init_boot` | `vendor_boot` | Notes |
|---|---|---|---|---|---|
| `super_v7` | `system_raw_fixed.raw` (`1e7ec2d1…`) | `vbmeta_system_v7` (`6b11d5e4…`, system `2a3c7c06…`) / `v8` (`bfd496d9…`) | stock or `logging4`/`logging10` | stock, `vendor_boot_nofail`, `diag2` | The first booting set |
| F0 ready (verity-off) | `system_raw_nologdump.raw` (`b6ca50f5…`) or its 9-block patch | `vbmeta_system_v10` (`2b52e26b…`, system digest `2a3c7c06…`) | `init_boot_logging13` (`baf1133d…`) | `vendor_boot_diag2` (`40623569…`) | Boot verified 2026-11-12 (3/3 reboots) |
| F0 + verity-on (future) | `system_verity.raw` (`29ad60fb…`, root digest `9103aeb9…`) | `vbmeta_system_f0_v11` (`66e20599…`) | `init_boot_logging13` | AVB-enabled `vendor_boot` | **UNVERIFIED on hardware** |
| Stock content control | stock `super` | stock `vbmeta_system_b` (`493448e6…`) | stock | stock | Boots (E12 used this content with testkey vbmeta) |

**Hard rule:** `system` content digest, `vbmeta_system` system descriptor and the actual image footer must all agree; `init_boot` content must match its hash descriptor; and `vbmeta_system` must be signed by the key the root vbmeta trusts. Mixing items from different rows is the classic "flashes OK, dies at first screen / EIO" failure.

---

## 10. `slot-unbootable` and other slot state (GPT attributes)

Qualcomm's bootctrl HAL stores A/B slot metadata in the **GPT partition attributes** of LUN4, not in `misc`:

- `AB_FLAG_OFFSET = 54` inside each 128-byte GPT entry (attributes bits 48–55);
- `AB_PARTITION_ATTR_SLOT_ACTIVE = 0x04`, `BOOT_SUCCESSFUL = 0x40`, `UNBOOTABLE = 0x80`;
- `boot_b` is GPT entry #53 on LUN4. Observed values: stock/healthy `byte54 = 0x6F`; unbootable `0xEF`.
- Repair = write the stock `gpt_main4` (LBA 0, 6 sectors) **and** `gpt_backup4` (LBA 1,048,571, 5 sectors) pair, then reset. Both tables must be written together.
- Every failed boot can set the unbootable bit again; clear/fix content **before** the next boot attempt, and never use a failed boot as a test result while `slot-unbootable:b=yes`.

Quick read of the attribute (after pulling the GPT with EDL):

```python
# gpt_main4.bin = 6 sectors at LUN4 LBA0; boot_b entry #53
d = open("gpt_main4.bin", "rb").read()
byte54 = d[2*4096 + 53*128 + 54]
print(hex(byte54))            # 0x6F = active+successful+bootable; 0xEF = unbootable set
```

---

## 11. Rollback index, flags, and ABL behavior

- Root `vbmeta_b`: `flags=0`, rollback index 0, RI location 0. `vbmeta_system_b`: `flags=0`, RI `1788566400`, RI location **2**. A repacked `vbmeta_system` must keep these values (never lower the RI).
- `vendor_boot` repacks in this project sometimes lowered `os_version/os_patch_level` to 15.0.0 / 2025-07 (stock 17.0.0 / 2026-09). AVB does not verify those fields, but whether the Qualcomm anti-rollback logic reads them is **UNVERIFIED**. Keep stock values when possible.
- ABL strings found in the stock `abl_b` image document the behavior: `State: Unlocked, AvbSlotVerify returned %a, continue boot`, `Device is unlocked, Skipping boot verification`, `Reset unbootable slots failed enter fastboot mode`, `No bootable slots found enter fastboot mode`. This is why unlocked boot with a mismatched hash still continues to the kernel, while a missing bootable slot falls to fastboot.
- The 8 s / 12 s "fall back to fastboot" symptom is **not** uniquely caused by AVB. It is also produced by AOSP init reaching a fatal condition and requesting a reboot to bootloader. Treat it as "boot chain or early userspace fatal", not automatically "signature rejected".

---

## 12. Verification checklist (run before and after flashing)

```bash
# 1. Offline: does the image signature/hashtree verify?
avbtool info_image   --image system_work.raw
avbtool verify_image --image system_work.raw --key testkey_rsa4096.pem

# 2. Offline: does the descriptor in vbmeta_system match the image footer?
avbtool info_image --image vbmeta_system_v10.img | grep -A8 "system"
avbtool info_image --image system_work.raw          | grep -E "Root Digest|Image Size|Salt"

# 3. On device: slot / boot state
fastboot getvar current-slot
fastboot getvar slot-unbootable:b        # must be no
fastboot getvar is-userspace             # yes = fastbootd, no = bootloader fastboot
fastboot getvar unlocked                 # yes = unlocked
adb shell getprop ro.boot.verifiedbootstate   # orange = unlocked, green = locked

# 4. On device: dm-verity really active?
adb shell getprop ro.boot.veritymode
adb shell dmesg | grep -Ei "dm-verity|avb|verification"
adb shell cat /proc/mounts | grep -E "system|vendor|product"

# 5. After EDL writes: read back and hash
certutil -hashfile <readback>.bin SHA256    # or Get-FileHash on Windows
# Compare against the expected sha256 recorded in the flash checklist.
```

Acceptance criteria for "AVB chain is correct": (a) `avbtool verify_image` PASS on every re-signed image; (b) `vbmeta_system` descriptor equals the image footer; (c) read-back hash equals the flashed image; (d) device boots with no dm-verity EIO; (e) `slot-unbootable:b=no`.

---

## 13. Known pitfalls

1. **Descriptor/image mismatch**: re-signing `vbmeta_system` with the *old* system digest is the single most common error. Always take `Root Digest` from the actual image footer.
2. **Stale pairing**: a `vbmeta_system` built for `init_boot_logging10` (image size 2,732,032 / digest `a87adf96…`) does not describe `init_boot_logging13` (2,736,128 / `4bf06b0c…`). Flash the matching pair.
3. **`verify_image` needs the partition files**: avbtool resolves `--include_descriptors_from_image` and staged verification by partition name; run it in a directory containing `system`, `product`, `system_ext`, `init_boot`, `pvmfw` or use the `verify_image --image <file>` form with the key only.
4. **FEC tool required**: `add_hashtree_footer` with FEC needs the host `fec` binary from the build tree (`out/host/linux-x86/bin/fec`); without it generation fails or silently differs.
5. **Stock `vbmeta_system` is stale after any content change**, e.g. the `product`/`system_ext` that were replaced by LOS builds. That is why the booting set always re-signs `vbmeta_system`.
6. **`dataext_b` content was never read back**; the root vbmeta hashtree for `dataext` assumes stock content. If it was ever formatted, second-stage `/dataext` mount produces dm-verity EIO (not fatal, but `vold`/data-extension breakage).
7. **Changing `recovery_b` to a non-stock recovery** can make `AvbHandle::Open()` return null because chained vbmeta metadata becomes invalid (`ERROR_INVALID_METADATA` is not tolerated even when unlocked). Keep stock `recovery_b`, or verify its AVB metadata first.
8. **Never hand-edit GPT/LP metadata** to "fix" a slot; write the stock table pair instead.
9. **AOSP testkey is public.** For anything distributed, re-think the security model; this repository documents bring-up, not a production signing service.

---

## 14. Open questions / UNVERIFIED items

1. Clean-state behavior of a `boot→testkey` chain: the single experiment that tried it returned to fastboot in 12 s, but the slot was already marked unbootable at that time, so the result is **inconclusive**.
2. OEM re-signing of `init_boot`/`boot` is impossible without the OEM private key; whether the ABL would accept an OEM-signed custom boot image is unknown.
3. Whether the bootloader's rollback-index storage reads `os_version/os_patch_level` from `vendor_boot` (the repacked values were 15.0.0/2025-07) — unknown.
4. `dataext_b`, `pvmfw_b` and `recovery_b` physical contents were never read back in the boot-fix round (assumed stock). Reading them back and checking their AVB digests is a pending task.
5. Verity-on operation of the F0 content (`system_verity.raw` + `vbmeta_system_f0_v11` + AVB-enabled `vendor_boot`) is prepared offline but **not yet hardware-verified**.
6. Whether a second, redundant slot-state store exists (RPMB or other persistent region) is not proven; all byte-level comparisons covered only plaintext partitions.

---

## 15. References (evidence files, relative to `<PROJECT_ROOT>`)

- `out/2026-11-11-los24-bootfix/VERIFY-REPORT.md` — independent byte-level verification of the chain, digests, root digest pairing, ELOOP root cause (§1–§3), and the "if booting still fails" analysis (§4).
- `out/2026-11-11-los24-bootfix/IMAGE-FIX-REPORT.md` — full `avbtool` command lines, footer parameters, staged `verify_image` outputs.
- `out/2026-11-11-los24-bootfix/INITLOG13-BUILD-REPORT.md`, `INITLOG12-BUILD-REPORT.md` — `init_boot` hash-footer and `vbmeta_system` pairing values.
- `out/2026-11-11-los24-bootfix/F0-SIDE-EFFECT-AUDIT.md` §3 — verity-restore recipe (`system_verity.raw`, `vbmeta_system_f0_v11.img`).
- `out/2026-11-11-los24-bootfix/FLASH-CHECKLIST.md` — minimal single-variable flash set, LUN/sector/expected sha.
- `out/2026-11-11-los24-bootfix/F0-FLASH-BUNDLE.md` — rollback anchors and stock hashes.
- `out/2026-11-10-los24-logdump/LOS24-PLAYBOOK-CONSOLIDATED.md` §3.3 — stock chain ownership and change boundaries; §3.2 — slot state in GPT attributes.
- `out/2026-11-10-los24-logdump/RECOVERY-PLAYBOOK.md` §"Problem 3" — chain topology and AVB bypass routes.
- `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` — the booted set and its hashes.
