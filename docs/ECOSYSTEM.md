# Ecosystem & reuse guide / 生态与复用指南

Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017  
作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017

Goal: nobody should have to re-solve the TB323FU bring-up problems documented
in this repository. The device tree is written so it can be reused for other
AOSP-based ROMs on the same device.

目标：后来者不必重复解决本项目已经踩完的 TB323FU 移植问题；本设备树可直接复用到
同机型的其他 AOSP 系 ROM。

## 1. Reuse for other AOSP ROMs / 复用到其他 AOSP 系 ROM

LineageOS 24.0 is the validated base. Sibling projects that consume the same
device tree (crDroid, PixelOS, AviumUI, ...) can reuse it as follows.

已验证基线是 LineageOS 24.0；crDroid、PixelOS、AviumUI 等同源项目可直接复用。

```xml
<!-- .repo/local_manifests/tb323fu.xml -->
<manifest>
  <remote name="krollv" fetch="https://github.com/UGY1412" />
  <project name="android_device_lenovo_TB323FU"
           path="device/lenovo/TB323FU"
           remote="krollv" revision="main" />
  <!-- recovery trees are optional; see the companion repositories -->
</manifest>
```

Then / 然后：

```bash
repo init -u <target-rom-manifest> -b <a17-branch> --git-lfs --no-repo-verify
repo sync -c -j"$(nproc)"
source build/envsetup.sh
lunch <target>_TB323FU-<variant>-userdebug   # target product name per ROM
mka systemimage
```

Notes / 注意:

- The product name (`lineage_TB323FU`) is Lineage-specific. Other ROMs either
  add a small product include (`vendor/<rom>/config/...`) that inherits
  `device/lenovo/TB323FU/device.mk`, or override `AndroidProducts.mk`.
- The stock kernel/vendor are used; no kernel source is required. Do not
  replace the kernel unless you have a validated build for this board.
- The two root causes in docs 05/06 are **not** Lineage-specific. Any ROM
  reusing the stock vendor/recovery chain will hit them if the images are
  built the same way.

## 2. What you must redo per ROM / 每个 ROM 需要重做的部分

| Item | Why |
|---|---|
| Extract blobs from your own firmware | We cannot redistribute Lenovo/Qualcomm files |
| Verify `vbmeta_system` / AVB pairing | Test-key chains and rollback indexes are per-image |
| Re-run first-boot acceptance (boot + ≥3 reboots) | Settings/props differ per ROM |
| Re-check SELinux policy | Different platform policy releases |
| Hardware bring-up checks | See [04-HARDWARE-SUPPORT](en/04-HARDWARE-SUPPORT.md) |

## 3. Contributing back / 回馈

- Fix a generic issue in `device/lenovo/TB323FU` → PR here.
- Recovery-specific changes → PR in the corresponding recovery repository
  (`...-orangefox` / `...-aera`).
- If you add a document that helps others, keep bilingual parity
  (`docs/en/` + `docs/zh-CN/`) and cite your evidence.

## 4. Cross-device reuse / 跨机型复用

Different SoC/panel/HAL → do **not** copy the tree. Use it as a reference for:
partition/LUN layout method, EDL/fastbootd flashing workflow, AVB/test-key
semantics, first-stage mount debugging, FBE/`init_user0` analysis, and the
error catalog (docs/11). / 不同 SoC/面板/HAL 的机型不要直接搬树，可参考其方法学。

## 5. Avoid duplicate work / 避免重复劳动

If you are about to debug "stuck at first screen", "boot-loop after reboot",
"SELinux policy compile fails", or "flash succeeds but device boots recovery",
read docs 05, 06, 08, 11 first — each of these has a validated, evidence-based
answer for this device.
