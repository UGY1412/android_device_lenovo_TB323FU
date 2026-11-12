Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
License: Apache-2.0

# 04 · Hardware Support Matrix — TB323FU

| Field | Value |
|---|---|
| Status | 2026-11-12 — **boot-level verification only**: the system boots to the Launcher, all major vendor HAL processes start, and the UI is interactive. Functional testing of individual hardware features (Wi-Fi, camera, audio, sensors, brightness, touch gestures, fingerprint, OTA) has **not** been performed yet |
| Applies to | Lenovo Legion Y700 Gen 5, model **TB323FU** (SM8850P / `canoe`), LineageOS 24.0 userdebug with stock `vendor`/`odm`/`vendor_dlkm`/`system_dlkm` and stock boot chain |
| Scope | Per-subsystem hardware inventory (measured / declared), HAL service state on the current build, known boot-log findings, and the pending verification matrix |
| Evidence sources | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` (§3, §5); `out/2026-11-12-edl-f0/device/postflash-final/ps-A.txt`; `.../logcat-all.txt`; `.../getprop-final.txt`; `.../dmesg.txt`; `.../mounts.txt`; `work/research/B-tb323fu-hardware.md` (§1, §3, §4); stock `dmesg` capture `handoff/2026-10-12-flash1/grab/dmesg.txt` |

> **Status legend**
> - **Measured** — observed working on the current build (device log / property / user-visible behaviour).
> - **HAL present, function untested** — service/process is running or the kernel driver probed, but no feature-level test has been performed (待验证).
> - ⚪ **Declared only** — appears in vendor properties/manifests but no runtime evidence yet.
> - **Hardware model names for sensors/cameras are partially unknown**; where the vendor package contains a generic QTI library set, this document says so instead of guessing.

## 1. Display

| Parameter | Value | Status / evidence |
|---|---|---|
| Panel resolution | **1904 × 3040** | measured in the current build: `DisplayDeviceInfo … 1904 x 3040`; `msm-dsi-info: hactive=1904, vactive=3040` |
| Panel identity | CSOT panel, Novatek **NT36523N** controller, node `qcom,mdss_dsi_baldur_nt36523_csot_3k_dsc_vid` | stock dmesg panel probe (panel model is hardware, unchanged) |
| DSI topology | dual DSI (2 LM / 2 interfaces), DSI PHY `9ac1000` / `9ac4000` | stock dmesg |
| Refresh rates | 30 / 60 / 90 / 120 / 144 / **165** Hz | current build: `supportedRefreshRates [165.0, 144.00002, 120.00001, 90.0, 60.000004, 30.000002]`; default mode = 165 Hz |
| Density | 440 dpi (scale 2.75; logic ≈ 692 × 1105 dp portrait, ≈ 1105 × 692 dp landscape) | current build: `density 440, 409.84406 x 406.4 dpi`; also `ro.sf.lcd_density=440` |
| Screen size | 8.8 inch | vendor property `ro.vendor.config.lgsi.screen_size=8.8` |
| HDR / wide color | Dolby Vision + HDR10 + HLG (`supportedHdrTypes=[1,2,3]`), max/average luminance 750 nits; wide color gamut | current build `DisplayDeviceInfo` |
| Composition | QTI display composer service (`vendor.qti.hardware.display.composer-service`, AIDL v4) | process running |
| Panel calibration | P3 / sRGB calibration files in stock `vendor` (`/etc/display/panel_baldur_nt36523_csot_3k_dsc_vid_C3D_cali_{p3,srgb}.txt`) | declared / file presence |
| Brightness | stock backlight calibration; `persist.sys.max_screen_brightness_backlight=191`; CABC + SVI display features | ⚪ declared; brightness curve not yet tuned for LineageOS (待验证) |
| Color-temperature sensor | **absent** — current build logs `failed to set up display white-balance: … cannot find color temperature sensor: com.google.sensor.color` | measurement of absence; behaviour impact (auto white balance unavailable) **待验证** |

## 2. Touch and pen

| Parameter | Value | Status / evidence |
|---|---|---|
| Touch controller | Novatek **NVT** capacitive touch, SPI, cascade ("Cascade Chip"), PID `0x609F` (stock log), IRQ 394 | current build: `input: NVTCapacitiveTouchScreen as /devices/virtual/input/input6`; `proc/NVTSPI` created |
| Touch report size | 19041 × 30401 at reconfigure, then 1904 × 3040 in DIRECT mode | current build `InputReader` |
| Pen input | `NVTCapacitivePen` input device; `novatek,pen-support=1`; Lenovo Tab Pen Plus (`pen_info=0x617F:0x17EF:Lenovo Tab Pen Plus`) | input device registered; pen function **待验证** |
| Touch firmware | `/vendor/firmware/novatek_ts_fw.bin` (+ MP test bin) from stock vendor | declared / not re-flashed |
| Gestures / touch features | NVT proc nodes for gesture, game mode, edge suppression, haptics, pen state | ⚪ presented by the driver; LineageOS-side configuration not yet tested |

## 3. SoC, memory, storage

| Parameter | Value | Status / evidence |
|---|---|---|
| SoC | Qualcomm SM8850P (Snapdragon 8 Elite Gen 5 class), platform `canoe` | `ro.soc.model=SM8850P`, `ro.board.platform=canoe` |
| CPU | Oryon cores, runtime variant `oryon`, arm64 only | properties |
| GPU | Adreno (`ro.hardware.egl=adreno`, `ro.hardware.vulkan=adreno`, GLES 3.2) | properties; UI composition works |
| RAM / storage SKU | 12 GB + 256 GB (`hqsysfs.pcba_hwid=SM8850P_12+256_11`) | stock cmdline |
| UFS | `1d84000.ufshc`, UFS ICE v4.0.3, MCQ 9 queues / 8 I/O queues, depth 64 | stock dmesg |
| Internal storage | `/data` on `dm-49` f2fs with inlinecrypt, 213 GB visible, 1.8 GB used after first boot | current build `mounts.txt` / `df` |
| External SD | `8804000.sdhci` → `/storage/sdcard1` (voldmanaged) | ⚪ stock fstab; no card test (待验证) |
| USB-OTG storage | `*.dwc3/xhci-hcd.*` → `/storage/usbotg` | ⚪ stock fstab; no OTG test (待验证) |
| Boot storage | A/B slots, virtual A/B (snapshots/compression/batch writes/io_uring all enabled) | properties + partition layout |

## 4. Audio

| Parameter | Value | Status / evidence |
|---|---|---|
| Audio HAL | `audiohalservice.qti` with `android.hardware.audio.core` AIDL v3 | process running |
| Audio DSP path | AGM / PAL streams (`vendor.qti.hardware.agm`, `pal`); AGM activity in the boot log | AGM stream opened |
| Playback codecs | Codec2 AIDL preferred (`debug.stagefright.ccodec=4`, `vendor.audio.c2.preferred=true`), Dolby DAX3 declared (`ro.vendor.dolby.dax.version=DAX3_3.14.0.10_r1`) | not audibly tested |
| Speaker/mic topology | canoe-SKU mixer profiles in vendor: `/etc/audio/sku_canoe/mixer_paths_canoe_*` (9 variants) + `audio_effects*.xml`; which one is loaded is **unknown** | ⚪ vendor config; audio function **待验证** |
| USB audio | `ro.usb.uvc.enabled=true`, `snd_usb_audio_qmi` module | ⚪ declared |
| Bluetooth audio | A2DP offload + LE Audio profiles declared (`persist.vendor.bt.a2dp_offload_cap=sbc-aptx-aptxtws-aptxhd-aac-ldac`) | ⚪ declared; **待验证** |
| Voice / telephony audio | RIL audio HAL present in vendor manifest; device is Wi-Fi SKU (`device.nettype=wifi`) | ⚪ composite vendor package; relevance **待验证** |

## 5. Camera

| Parameter | Value | Status / evidence |
|---|---|---|
| Camera HAL | `vendor.qti.camera.provider-service_64` (`android.hardware.camera.provider` AIDL v3, `ICameraProvider/vendor_qti/0`); CamX provider starts | process running (`CameraProvider service is starting`) |
| CameraService | `CameraService started (pid=1982)` | framework camera service up |
| ADSP / fastrpc | camera provider initializes fastrpc domains; boot log contains fastrpc `Error 0x39: apps_std_get_search_paths_with_env failed` lines during provider start | not blocking service start; impact **待验证** |
| Actual sensors | **unknown** — the stock vendor package ships a generic QTI camera library set (40+ `com.qti.sensor.*.so`); which sensors are physically installed cannot be determined from that list. Stock dmesg stops before camera probe completes | **待验证** (`dumpsys media.camera` on device) |
| Aux/offline features | `vendor.camera.aux.packagelist=org.codeaurora.snapcam`, AON (screen-off) camera + offline camera HAL declared | ⚪ declared |
| Front camera / face unlock | face HAL is present (`android.hardware.biometrics.face@4.0`), but no camera test has been run | **待验证** |

## 6. Wi-Fi, Bluetooth, GNSS, NFC

| Subsystem | Evidence on current build | Status |
|---|---|---|
| Wi-Fi | `android.hardware.wifi-service` running; supplicant AIDL v4 + hostapd v3 + QTI vendor supplicant declared; `wifi.interface=wlan0`, `wifi.aware.interface=wifi-aware0` | HAL running, **no scan/connect test**; early boot logs one `wlc: Could not read interface wlan0 flags: No such device` (driver not up yet at that instant) — recheck at F1 |
| Wi-Fi Display / Miracast | `vendor.qti.hardware.wifidisplaysession_aidl` v1 (4 instances), `sigma_miracast_aidl` declared | ⚪ declared |
| Bluetooth | `android.hardware.bluetooth@aidl-service-qti` running; HCI/BT stack init in log; A2DP/LE-Audio/Channel-Sounding services registered | HAL running, **no pairing test** |
| GNSS | `android.hardware.gnss-aidl-service-qti` running (GNSS AIDL v4, QTI loc v8); `persist.vendor.data.mutualex.mode=wifipreferred` | HAL running; fix acquisition **待验证** |
| NFC | Stock dmesg probes an **NXP NFC I²C driver**; properties `ro.nfc.port=I2C`, `persist.nfc.secure_nfc=true` exist; however the `canoe` SKU manifest does **not** declare NFC/secure-element (only the unrelated `alor` manifest does), and no NFC HAL process is present in the current boot | **待验证** — possibly SKU variance; treat as unsupported until tested |
| Cellular / modem | Full modem partitions (`modem_a/b`, 367 MB each), Radio HAL set, TME firmware, `modemst1/2` partitions exist; but device properties declare `device.nettype=wifi` and there is no SIM-slot evidence in the current boot | ⚪ **待验证** — vendor package appears to be multi-SKU; do not assume cellular works |

## 7. Sensors

| Sensor | Evidence | Status |
|---|---|---|
| Sensor HAL | `android.hardware.sensors-service.multihal` (`android.hardware.sensors` AIDL v3) | process running |
| Accelerometer / gyroscope | SensorService registers `lsm6dsv` gyroscope (+ uncalibrated), `gravity`, `linear_acceleration` | registered; values **待验证** |
| Magnetometer / compass | SensorService registers `mmc56x3x` magnetometer (+ uncalibrated) | registered; **待验证** |
| Ambient light | SensorService registers `stk_stk3acx` ambient light (+ wakeup variant) | registered; **待验证** |
| Barometer | `sensor.barometer.high_quality.implemented=true`; `lps22df` config present in vendor | ⚪ declared / driver config; runtime registration **待验证** |
| Proximity / step counter | `sku_canoe` permission XMLs list proximity, stepcounter, stepdetector, head-tracker | ⚪ declared; actual sensor set **待验证** |
| Sensor calibration | `vendor.qti.hardware.sensorscalibrate` + `libsensorcal.so` | ⚪ declared |
| Color-temperature sensor | not found at runtime (see §1) | absent / **待验证** |

## 8. Biometrics and security

| Feature | Evidence | Status |
|---|---|---|
| Face biometrics | `android.hardware.biometrics.face@4.0-service.face` running | HAL running; unlock **待验证** |
| Fingerprint | No dedicated fingerprint HAL process is present in the current boot; only AOSP "virtual fingerprint" apex data and the `fingerprint` feature flag appear. Stock vendor contains `com.qualcomm.qti.biometrics.fingerprint.service` app (process observed) | **待验证 / likely not populated on this SKU** — do not claim fingerprint support |
| Gatekeeper | `android.hardware.gatekeeper-service-spu-qti`, `android.hardware.security.gatekeeper` | running (device credential path used by FBE) |
| KeyMint / TEE | `android.hardware.security.onekeymint-service-qti`, `keymint-service-spu-qti`, StrongBox profile declared; `vendor.qti.hardware.spu-service` | running |
| Weaver / Secretkeeper | `weaver-service-spu-qti`, `secretkeeper-service-qti` | running |
| FBE v2 | `ro.crypto.state=encrypted`, `ro.crypto.type=file`, `ro.crypto.metadata.enabled=true`, `sys.user.0.ce_available=true`; `/data` dm-49 f2fs inlinecrypt; `/metadata` sda10 f2fs | measured |
| Verified boot | unlocked, `verifiedbootstate=orange`; verity currently off (diagnostic state) | measured (diagnostic; see `03-FLASH.md` §8) |
| DRM | `android.hardware.drm-service.clearkey` + `widevine`, CAS service | HAL running; Widevine L1 playback **待验证** |

## 9. Power, battery, thermal, haptics, LED

| Feature | Evidence | Status |
|---|---|---|
| Battery HAL | `vendor.lenovo.hardware.battery-service` (v5) starts; `android.hardware.health-service.qti` opens `battery/capacity` after 3 retries; healthd warns several optional sysfs paths missing (`batteryCapacityLevelPath`, `chargingStatePath`, …) | running; charge/level display **待验证** (warnings are non-fatal) |
| Charger | `BATTERY_CHG` logs report USB type and Lenovo thermal charge-current limits; charge current limiting active | measured at boot; charging curve **待验证** |
| Thermal | `android.hardware.thermal-service.qti` v3; ThermalEngine loads `/vendor/etc/thermal-engine_battery_0.conf`; one warning `No thermal zone for sensor: battery, ret:-1` | running with a minor sensor warning; throttling **待验证** |
| Power HAL | `android.hardware.power-service` (v6) + `powerstats-service.qti` + QTI `perf2` HAL | running |
| Haptics | Dual Awinic **AW86937** motors, both detected (`<left>` and `<right>` `qualified chip`), firmware `haptic_ram.bin` | driver ready; vibration strength/pattern **待验证** |
| LED | Awinic **AW22127**, chip detected (`chipid: aw22127`); the post-flash device log shows `aw22xxx_fw.bin` loading successfully (`fw customer: awinic_baldur`, 17,542 B) | driver ready; notification LED behaviour **待验证** |
| Fan (if present) | ThermalEngine user cases include `fan_0`; stock hardware research has no fan data | **待验证** |
| RTC / timezone | device RTC runs GMT (`persist.sys.timezone=GMT`), 8 h behind local time | measured — expected, not a defect |

## 10. USB and connectivity

| Feature | Evidence | Status |
|---|---|---|
| USB device mode | `android.hardware.usb-service.qti` + `usb.gadget-service.qti` + `vendor.lenovo.hardware.usb` running; `persist.sys.usb.config=adb` | running |
| adb | adb online after first boot, USB debugging authorised; serial number redacted in this repo | measured |
| MTP | MTP enumerated ~1 min after first boot (during F0 acceptance) | measured |
| USB-OTG host | DWC3 controller `a600000.dwc3`; fstab USB-OTG storage entry | ⚪ declared; host-mode test **待验证** |
| DisplayPort / video out | not documented in the sources used here | **待验证** |
| Wireless display | `vendor.qti.hardware.wifidisplaysession_aidl` (4 instances) + Miracast HAL declared | ⚪ declared |

## 11. Summary matrix

| Subsystem | Hardware present | HAL/service at boot | Function measured |
|---|---|---|---|
| Display panel + composer | CSOT/NT36523N, 1904×3040, 165 Hz | Yes | UI rendering |
| Touch + pen | Novatek NVT | Yes | Touch: (UI interaction). Pen: 待验证 |
| Storage (UFS /data /metadata) | Yes | | mounted + FBE |
| FBE / keymint / gatekeeper | TEE-backed | Yes | encrypted userdata |
| USB adb / MTP | Yes | | Yes |
| Wi-Fi | (QTI WLAN, wlan0) | Yes | 待验证 |
| Bluetooth | Yes | | 待验证 |
| Audio (speaker/mic) | Yes | | 待验证 |
| Camera(s) | (models unknown) | Yes | 待验证 |
| Sensors (accel/gyro/mag/light) | Yes | | 待验证 |
| GNSS | Yes | | 待验证 |
| Face biometrics | Yes | | 待验证 |
| Fingerprint | 待验证 (likely absent) | ✗ not observed | 待验证 |
| NFC | 待验证 (SKU variance) | ✗ not observed | 待验证 |
| Cellular | 待验证 (Wi-Fi SKU) | partial vendor HALs | 待验证 |
| Battery / charger / thermal | Yes | | 待验证 |
| Haptics (dual AW86937) | Yes | driver | 待验证 |
| LED (AW22127) | Yes | driver + firmware | 待验证 |
| External SD / USB-OTG storage | (fstab) | — | 待验证 |
| OTA / A/B update | virtual A/B | boot control HAL | 待验证 (not required for the diagnostic build) |

## 12. VINTF generational gap (porting risk)

Measured on the stock images: the stock Lenovo **system** libraries expect `android.hardware.graphics.composer3` **V5**, while the stock Lenovo **vendor** provides only **V4** (`vendor.qti.hardware.display.composer-service3_v4.xml`, `aidl 4`). AOSP logs this mismatch as `Slog.e` and does **not** block boot — this is why the stock firmware boots anyway.

Implications for this port:

- The LineageOS build replaces only `system`/`system_ext`/`product`; the vendor side stays at composer3 V4. LineageOS framework must not require a composer3 interface newer than V4 — the accepted build boots and renders, so this condition currently holds.
- If a future LineageOS update raises the composer3 requirement above V4, display bring-up can regress; check `frameworks/native` / `hardware/interfaces/graphics/composer` requirements before updating.

Other key vendor HAL versions (for framework compatibility checks): `android.hardware.power` 6, `sensors` 3, `health` 4, `audio.core` 3, `camera.provider` 3, `bluetooth.audio` 5, `wifi` 3 / `wifi.supplicant` 4, `thermal` 3, `gatekeeper` 1, `keymint` 4/3, `drm` 1, `usb` 3, `gnss` 4.

## 13. Pending verification plan (F1)

Run on the device (adb), capture output under `out/<date>-f1-hardware/`:

```bash
# system state
adb shell getprop | grep -E 'ro\.(soc|board|hardware|product)|sys\.boot_completed'
adb shell dumpsys display          | head -80      # modes / HDR / density
adb shell dumpsys input            | head -120     # touch + pen devices
adb shell dumpsys sensorservice    | head -80      # actual sensor list + rates
adb shell dumpsys media.camera     | head -80      # camera count / characteristics
adb shell dumpsys wifi             | head -80      # wifi enabled/scan
adb shell dumpsys bluetooth_manager| head -80
adb shell dumpsys audio            | head -100
adb shell dumpsys battery          | head -40
adb shell dumpsys thermalservice   | head -60
adb shell cmd vibrator vibrate 200 # haptics (if service allows)
adb shell dmesg | grep -iE 'aw8693|aw22xxx|NVT-ts|camera|soundwire|wsa88|wcd93'
```

Feature test matrix to fill in: Wi-Fi scan/connect/throughput, Bluetooth pair + A2DP, speaker/mic/USB-C audio, front/rear camera capture, sensor values (accel/gyro/mag/light/baro/proximity), GPS fix outdoors, face unlock enrolment, brightness curve + auto-brightness, 30/60/90/120/144/165 Hz switching, pen input, haptics strength, LED behaviour, charging curve, SD card, USB-OTG host, Widevine playback, OTA updater path.

Known issues to watch during F1 (already observed in boot logs):

1. `DisplayPowerController: failed to set up display white-balance: … cannot find color temperature sensor` — auto white balance will be unavailable.
2. `android.hardware.thermal-service.qti: No thermal zone for sensor: battery, ret:-1` — thermal HAL may miss the battery zone.
3. `healthd: …Path not found` warnings for optional battery sysfs nodes — cosmetic, but battery UI may show reduced detail.
4. Camera provider logs fastrpc `0x39` search-path errors at start-up (service still starts) — watch for camera-open failures.
5. One early `wlc: Could not read interface wlan0 flags: No such device` — check whether Wi-Fi comes up cleanly once the WLAN driver loads.
6. Diagnostic state: SELinux permissive produces large `avc denied` counts (permissive=1); these are not feature failures. `init_boot_logging13` continuously writes kernel logs to the `logdump` partition by design.

## 14. Evidence sources

| Topic | Evidence |
|---|---|
| HAL processes running, per-subsystem PIDs | `out/2026-11-12-edl-f0/device/postflash-final/ps-A.txt` |
| Display modes / density / HDR / touch input devices / sensor registrations | `.../postflash-final/logcat-all.txt` (display lines at `DisplayDeviceInfo`, `InputReader`, `SensorService`) |
| Boot properties (crypto, SoC, display flags, Wi-Fi interface) | `.../postflash-final/getprop-final.txt` |
| Mounts, /data usage | `.../postflash-final/mounts.txt`, `data-fs.txt` |
| Kernel probes (panel, touch, haptics, LED, camera region, UFS, PMIC) | stock `dmesg` capture `handoff/2026-10-12-flash1/grab/dmesg.txt`; `.../postflash-final/dmesg.txt` |
| Hardware inventory, HAL/manifest versions, panel/sensor/audio camera clues | `work/research/B-tb323fu-hardware.md` §1/§3/§4 |
| Boot acceptance / feature-test scope | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` §3/§5 |
