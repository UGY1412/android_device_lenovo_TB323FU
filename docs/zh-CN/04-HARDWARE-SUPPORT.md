作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017
Copyright (C) 2026 自恋也是种美 (krollv)
许可证：Apache-2.0

# 04 · 硬件支持矩阵 —— TB323FU

| 字段 | 内容 |
|---|---|
| 状态 | 2026-11-12 —— **仅完成开机级验证**：系统能启动到桌面，主要 vendor HAL 进程全部启动，UI 可交互。各硬件功能（Wi-Fi、相机、音频、传感器、亮度、触控手势、指纹、OTA）**尚未**做功能实测 |
| 适用设备 | 联想拯救者 Y700 五代，型号 **TB323FU**（SM8850P / `canoe`）；LineageOS 24.0 userdebug，`vendor`/`odm`/`vendor_dlkm`/`system_dlkm` 与启动链均为原厂件 |
| 范围 | 逐子系统硬件清点（实测 / 声明）、当前版本上的 HAL 服务状态、启动日志中的已知发现、待验证矩阵 |
| 证据来源 | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md`（§3、§5）；`out/2026-11-12-edl-f0/device/postflash-final/ps-A.txt`；`.../logcat-all.txt`；`.../getprop-final.txt`；`.../dmesg.txt`；`.../mounts.txt`；`work/research/B-tb323fu-hardware.md`（§1、§3、§4）；原厂 `dmesg` 抓取 `handoff/2026-10-12-flash1/grab/dmesg.txt` |

> **状态图例**
> - **实测** —— 在当前版本上观察到可用（设备日志 / 属性 / 用户可见行为）。
> - **HAL 存在，功能未测** —— 服务/进程在运行或内核驱动已 probe，但尚未做功能级测试（待验证）。
> - ⚪ **仅声明** —— 出现在 vendor 属性/manifest 中，尚无运行期证据。
> - **传感器/相机的具体硬件型号部分未知**；凡是 vendor 包内只是通用 QTI 库集合的，本文档如实说明，不做猜测。

## 1. 显示

| 参数 | 值 | 状态 / 证据 |
|---|---|---|
| 面板分辨率 | **1904 × 3040** | 当前版本实测：`DisplayDeviceInfo … 1904 x 3040`；`msm-dsi-info: hactive=1904, vactive=3040` |
| 面板身份 | CSOT 面板，Novatek **NT36523N** 控制器，节点 `qcom,mdss_dsi_baldur_nt36523_csot_3k_dsc_vid` | 原厂 dmesg 面板 probe（面板属硬件，未改动） |
| DSI 拓扑 | 双 DSI（2 LM / 2 接口），DSI PHY `9ac1000` / `9ac4000` | 原厂 dmesg |
| 刷新率 | 30 / 60 / 90 / 120 / 144 / **165** Hz | 当前版本：`supportedRefreshRates [165.0, 144.00002, 120.00001, 90.0, 60.000004, 30.000002]`；默认模式 = 165 Hz |
| 密度 | 440 dpi（scale 2.75；竖屏逻辑约 692 × 1105 dp，横屏约 1105 × 692 dp） | 当前版本：`density 440, 409.84406 x 406.4 dpi`；另有 `ro.sf.lcd_density=440` |
| 屏幕尺寸 | 8.8 英寸 | vendor 属性 `ro.vendor.config.lgsi.screen_size=8.8` |
| HDR / 广色域 | 支持 Dolby Vision + HDR10 + HLG（`supportedHdrTypes=[1,2,3]`），最大/平均亮度 750 nits；广色域 | 当前版本 `DisplayDeviceInfo` |
| 合成器 | 高通 display composer 服务（`vendor.qti.hardware.display.composer-service`，AIDL v4） | 进程运行中 |
| 面板标定 | 原厂 `vendor` 内含 P3 / sRGB 标定文件（`/etc/display/panel_baldur_nt36523_csot_3k_dsc_vid_C3D_cali_{p3,srgb}.txt`） | 声明 / 文件存在 |
| 亮度 | 原厂背光标定；`persist.sys.max_screen_brightness_backlight=191`；CABC + SVI 显示特性 | ⚪ 仅声明；LineageOS 侧亮度曲线尚未调优（待验证） |
| 色温传感器 | **不存在** —— 当前版本日志：`failed to set up display white-balance: … cannot find color temperature sensor: com.google.sensor.color` | 已实测到「不存在」；行为影响（自动白平衡不可用）**待验证** |

## 2. 触控与笔

| 参数 | 值 | 状态 / 证据 |
|---|---|---|
| 触控控制器 | Novatek **NVT** 电容触控，SPI，级联（"Cascade Chip"），PID `0x609F`（原厂日志），IRQ 394 | 当前版本：`input: NVTCapacitiveTouchScreen as /devices/virtual/input/input6`；已创建 `proc/NVTSPI` |
| 触控上报尺寸 | reconfigure 时 19041 × 30401，DIRECT 模式下 1904 × 3040 | 当前版本 `InputReader` |
| 笔输入 | `NVTCapacitivePen` 输入设备；`novatek,pen-support=1`；联想 Tab Pen Plus（`pen_info=0x617F:0x17EF:Lenovo Tab Pen Plus`） | 输入设备已注册；笔功能**待验证** |
| 触控固件 | 原厂 `vendor` 内 `/vendor/firmware/novatek_ts_fw.bin`（+ MP 测试 bin） | 声明 / 未重新刷写 |
| 手势 / 触控特性 | 驱动提供手势、游戏模式、边缘抑制、触感、笔状态等 NVT proc 节点 | ⚪ 驱动已暴露；LineageOS 侧配置尚未测试 |

## 3. SoC、内存、存储

| 参数 | 值 | 状态 / 证据 |
|---|---|---|
| SoC | 高通 SM8850P（Snapdragon 8 Elite Gen 5 级），平台 `canoe` | `ro.soc.model=SM8850P`、`ro.board.platform=canoe` |
| CPU | Oryon 核心，运行期 variant `oryon`，仅 arm64 | 属性 |
| GPU | Adreno（`ro.hardware.egl=adreno`、`ro.hardware.vulkan=adreno`，GLES 3.2） | 属性；UI 合成正常 |
| 内存 / 存储档位 | 12 GB + 256 GB（`hqsysfs.pcba_hwid=SM8850P_12+256_11`） | 原厂 cmdline |
| UFS | `1d84000.ufshc`，UFS ICE v4.0.3，MCQ 9 队列 / 8 I/O 队列，深度 64 | 原厂 dmesg |
| 内置存储 | `/data` 位于 `dm-49` f2fs + inlinecrypt，首启后可见 213 GB、已用 1.8 GB | 当前版本 `mounts.txt` / `df` |
| 外置 SD | `8804000.sdhci` → `/storage/sdcard1`（voldmanaged） | ⚪ 原厂 fstab；未插卡测试（待验证） |
| USB-OTG 存储 | `*.dwc3/xhci-hcd.*` → `/storage/usbotg` | ⚪ 原厂 fstab；未做 OTG 测试（待验证） |
| 启动存储 | A/B 槽，virtual A/B（snapshots/compression/batch writes/io_uring 全开） | 属性 + 分区布局 |

## 4. 音频

| 参数 | 值 | 状态 / 证据 |
|---|---|---|
| 音频 HAL | `audiohalservice.qti`，`android.hardware.audio.core` AIDL v3 | 进程运行中 |
| 音频 DSP 通路 | AGM / PAL（`vendor.qti.hardware.agm`、`pal`）；启动日志有 AGM 活动 | AGM 流已建立 |
| 播放编解码 | 首选 Codec2 AIDL（`debug.stagefright.ccodec=4`、`vendor.audio.c2.preferred=true`）；声明 Dolby DAX3（`ro.vendor.dolby.dax.version=DAX3_3.14.0.10_r1`） | 未做听感测试 |
| 扬声器/麦克风拓扑 | vendor 内 canoe SKU mixer 配置：`/etc/audio/sku_canoe/mixer_paths_canoe_*`（9 个变体）+ `audio_effects*.xml`；实际加载哪一个**未知** | ⚪ vendor 配置；音频功能**待验证** |
| USB 音频 | `ro.usb.uvc.enabled=true`，`snd_usb_audio_qmi` 模块 | ⚪ 仅声明 |
| 蓝牙音频 | 声明 A2DP offload + LE Audio（`persist.vendor.bt.a2dp_offload_cap=sbc-aptx-aptxtws-aptxhd-aac-ldac`） | ⚪ 仅声明；**待验证** |
| 语音/通话音频 | vendor manifest 内有 RIL audio HAL；设备为 Wi-Fi SKU（`device.nettype=wifi`） | ⚪ 多 SKU 共用 vendor 包；相关性**待验证** |

## 5. 相机

| 参数 | 值 | 状态 / 证据 |
|---|---|---|
| 相机 HAL | `vendor.qti.camera.provider-service_64`（`android.hardware.camera.provider` AIDL v3，`ICameraProvider/vendor_qti/0`）；CamX provider 启动 | 进程运行中（`CameraProvider service is starting`） |
| CameraService | `CameraService started (pid=1982)` | 框架相机服务已起 |
| ADSP / fastrpc | 相机 provider 初始化 fastrpc domain；启动日志中 provider 启动期间出现 fastrpc `Error 0x39: apps_std_get_search_paths_with_env failed` 行 | 未阻塞服务启动；影响**待验证** |
| 实际传感器 | **未知** —— 原厂 vendor 包内含通用 QTI 相机库全集（40+ 个 `com.qti.sensor.*.so`），无法据此判断实机装了哪几颗。原厂 dmesg 在相机 probe 完成前即截断 | **待验证**（设备端 `dumpsys media.camera`） |
| 辅助/离屏特性 | `vendor.camera.aux.packagelist=org.codeaurora.snapcam`，声明 AON（息屏）相机 + 离线相机 HAL | ⚪ 仅声明 |
| 前摄 / 人脸解锁 | 人脸 HAL 存在（`android.hardware.biometrics.face@4.0`），但未做相机测试 | **待验证** |

## 6. Wi-Fi、蓝牙、GNSS、NFC

| 子系统 | 当前版本证据 | 状态 |
|---|---|---|
| Wi-Fi | `android.hardware.wifi-service` 运行；声明 supplicant AIDL v4 + hostapd v3 + QTI vendor supplicant；`wifi.interface=wlan0`、`wifi.aware.interface=wifi-aware0` | HAL 运行中，**未做扫描/连接测试**；启动早期日志有一条 `wlc: Could not read interface wlan0 flags: No such device`（当时驱动尚未就绪）——F1 复测 |
| Wi-Fi Display / Miracast | 声明 `vendor.qti.hardware.wifidisplaysession_aidl` v1（4 实例）、`sigma_miracast_aidl` | ⚪ 仅声明 |
| 蓝牙 | `android.hardware.bluetooth@aidl-service-qti` 运行；日志中 HCI/BT 协议栈初始化；A2DP/LE-Audio/Channel-Sounding 服务注册 | HAL 运行中，**未做配对测试** |
| GNSS | `android.hardware.gnss-aidl-service-qti` 运行（GNSS AIDL v4、QTI loc v8）；`persist.vendor.data.mutualex.mode=wifipreferred` | HAL 运行中；定位**待验证** |
| NFC | 原厂 dmesg probe 了 **NXP NFC I²C 驱动**；属性 `ro.nfc.port=I2C`、`persist.nfc.secure_nfc=true` 存在；但 `canoe` SKU manifest **未**声明 NFC/secure-element（只有无关的 `alor` manifest 声明），当前启动中也没有 NFC HAL 进程 | **待验证** —— 可能是 SKU 差异；测试前按「不支持」对待 |
| 蜂窝 / modem | 存在完整 modem 分区（`modem_a/b` 各 367 MB）、Radio HAL 组、TME 固件、`modemst1/2` 分区；但设备属性声明 `device.nettype=wifi`，当前启动无 SIM 槽证据 | ⚪ **待验证** —— vendor 包看起来是多 SKU 共用；不要假设蜂窝可用 |

## 7. 传感器

| 传感器 | 证据 | 状态 |
|---|---|---|
| Sensor HAL | `android.hardware.sensors-service.multihal`（`android.hardware.sensors` AIDL v3） | 进程运行中 |
| 加速度计 / 陀螺仪 | SensorService 注册了 `lsm6dsv` gyroscope（+ uncalibrated）、`gravity`、`linear_acceleration` | 已注册；数值**待验证** |
| 磁力计 / 罗盘 | SensorService 注册了 `mmc56x3x` magnetometer（+ uncalibrated） | 已注册；**待验证** |
| 环境光 | SensorService 注册了 `stk_stk3acx` ambient light（+ wakeup 变体） | 已注册；**待验证** |
| 气压计 | `sensor.barometer.high_quality.implemented=true`；vendor 内有 `lps22df` 配置 | ⚪ 声明 / 驱动配置；运行期注册**待验证** |
| 接近 / 计步 | `sku_canoe` 权限 XML 列出 proximity、stepcounter、stepdetector、head-tracker | ⚪ 仅声明；实际传感器集**待验证** |
| 传感器校准 | `vendor.qti.hardware.sensorscalibrate` + `libsensorcal.so` | ⚪ 仅声明 |
| 色温传感器 | 运行期未找到（见 §1） | 不存在 / **待验证** |

## 8. 生物识别与安全

| 特性 | 证据 | 状态 |
|---|---|---|
| 人脸识别 | `android.hardware.biometrics.face@4.0-service.face` 运行中 | HAL 运行中；解锁**待验证** |
| 指纹 | 当前启动中**没有**独立的指纹 HAL 进程；只有 AOSP「virtual fingerprint」apex 数据与 `fingerprint` 特性开关。原厂 vendor 内含 `com.qualcomm.qti.biometrics.fingerprint.service` 应用（观察到其进程） | **待验证 / 本 SKU 很可能未配置指纹** —— 不要宣称支持指纹 |
| Gatekeeper | `android.hardware.gatekeeper-service-spu-qti`、`android.hardware.security.gatekeeper` | 运行中（FBE 使用的设备凭据通路） |
| KeyMint / TEE | `android.hardware.security.onekeymint-service-qti`、`keymint-service-spu-qti`，声明 StrongBox；`vendor.qti.hardware.spu-service` | 运行中 |
| Weaver / Secretkeeper | `weaver-service-spu-qti`、`secretkeeper-service-qti` | 运行中 |
| FBE v2 | `ro.crypto.state=encrypted`、`ro.crypto.type=file`、`ro.crypto.metadata.enabled=true`、`sys.user.0.ce_available=true`；`/data` 为 dm-49 f2fs inlinecrypt；`/metadata` 为 sda10 f2fs | 实测 |
| 验证启动 | 已解锁，`verifiedbootstate=orange`；当前 verity 关闭（诊断态） | 实测（诊断态；见 `03-FLASH.md` §8） |
| DRM | `android.hardware.drm-service.clearkey` + `widevine`、CAS 服务 | HAL 运行中；Widevine L1 播放**待验证** |

## 9. 电源、电池、热、触感、LED

| 特性 | 证据 | 状态 |
|---|---|---|
| 电池 HAL | `vendor.lenovo.hardware.battery-service`（v5）启动；`android.hardware.health-service.qti` 重试 3 次后打开 `battery/capacity`；healthd 报多个可选 sysfs 路径缺失（`batteryCapacityLevelPath`、`chargingStatePath` 等） | 运行中；电量/充电显示**待验证**（警告非致命） |
| 充电 | `BATTERY_CHG` 日志报告 USB 类型与联想热限流值；充电限流生效 | 启动实测；充电曲线**待验证** |
| 热管理 | `android.hardware.thermal-service.qti` v3；ThermalEngine 加载 `/vendor/etc/thermal-engine_battery_0.conf`；有一条警告 `No thermal zone for sensor: battery, ret:-1` | 运行中，有轻微传感器警告；温控**待验证** |
| 电源 HAL | `android.hardware.power-service`（v6）+ `powerstats-service.qti` + 高通 `perf2` HAL | 运行中 |
| 触感 | 双 Awinic **AW86937** 马达，左右均检测到（`<left>`/`<right>` `qualified chip`），固件 `haptic_ram.bin` | 驱动就绪；震动强度/波形**待验证** |
| LED | Awinic **AW22127**，芯片检测到（`chipid: aw22127`）；F0 刷后设备日志显示成功加载 `aw22xxx_fw.bin`（`fw customer: awinic_baldur`，17,542 B） | 驱动就绪；通知灯行为**待验证** |
| 风扇（若有） | ThermalEngine 用户场景含 `fan_0`；原厂硬件调研无风扇数据 | **待验证** |
| RTC / 时区 | 设备 RTC 运行 GMT（`persist.sys.timezone=GMT`），比本地时间早 8 小时 | 实测——属预期，非缺陷 |

## 10. USB 与连接

| 特性 | 证据 | 状态 |
|---|---|---|
| USB device 模式 | `android.hardware.usb-service.qti` + `usb.gadget-service.qti` + `vendor.lenovo.hardware.usb` 运行；`persist.sys.usb.config=adb` | 运行中 |
| adb | 首启后 adb 在线，USB 调试已授权；本仓库已对序列号脱敏 | 实测 |
| MTP | F0 验收中首启约 1 分钟后 MTP 枚举 | 实测 |
| USB-OTG host | DWC3 控制器 `a600000.dwc3`；fstab 有 USB-OTG 存储条目 | ⚪ 仅声明；host 模式测试**待验证** |
| DisplayPort / 视频输出 | 本文所用来源未记录 | **待验证** |
| 无线显示 | 声明 `vendor.qti.hardware.wifidisplaysession_aidl`（4 实例）+ Miracast HAL | ⚪ 仅声明 |

## 11. 汇总矩阵

| 子系统 | 硬件存在 | 开机时 HAL/服务 | 功能实测 |
|---|---|---|---|
| 显示面板 + 合成器 | CSOT/NT36523N，1904×3040，165 Hz | Yes | UI 渲染 |
| 触控 + 笔 | Novatek NVT | Yes | 触控：（UI 可交互）。笔：待验证 |
| 存储（UFS / /data / /metadata） | Yes | | 挂载 + FBE |
| FBE / keymint / gatekeeper | TEE 支撑 | Yes | 用户数据加密 |
| USB adb / MTP | Yes | | Yes |
| Wi-Fi | （高通 WLAN，wlan0） | Yes | 待验证 |
| 蓝牙 | Yes | | 待验证 |
| 音频（扬声器/麦克风） | Yes | | 待验证 |
| 相机（数量/型号未知） | Yes | | 待验证 |
| 传感器（加速度/陀螺/磁力/光感） | Yes | | 待验证 |
| GNSS | Yes | | 待验证 |
| 人脸识别 | Yes | | 待验证 |
| 指纹 | 待验证（很可能没有） | ✗ 未观察到 | 待验证 |
| NFC | 待验证（SKU 差异） | ✗ 未观察到 | 待验证 |
| 蜂窝 | 待验证（Wi-Fi SKU） | 部分 vendor HAL | 待验证 |
| 电池 / 充电 / 温控 | Yes | | 待验证 |
| 触感（双 AW86937） | Yes | 驱动 | 待验证 |
| LED（AW22127） | Yes | 驱动 + 固件 | 待验证 |
| 外置 SD / USB-OTG 存储 | （fstab） | — | 待验证 |
| OTA / A/B 更新 | virtual A/B | boot control HAL | 待验证（诊断版本不需要） |

## 12. VINTF 代际落差（移植风险）

实测原厂镜像：联想原厂 **system** 侧库期望 `android.hardware.graphics.composer3` **V5**，而联想自己的 **vendor** 只提供 **V4**（`vendor.qti.hardware.display.composer-service3_v4.xml`，`aidl 4`）。AOSP 对这类不匹配仅 `Slog.e`，**不阻塞**启动——这也是原厂固件仍能开机的原因。

对本移植的影响：

- LineageOS 构建只替换 `system`/`system_ext`/`product`；vendor 侧仍是 composer3 V4。LineageOS framework 不应要求高于 V4 的 composer3 接口——已验收版本能启动并渲染，说明当前满足该条件。
- 若未来 LineageOS 更新把 composer3 要求提到 V4 以上，显示 bring-up 可能回归；升级前先核对 `frameworks/native` / `hardware/interfaces/graphics/composer` 的要求。

其它关键 vendor HAL 版本（用于 framework 兼容性核对）：`android.hardware.power` 6、`sensors` 3、`health` 4、`audio.core` 3、`camera.provider` 3、`bluetooth.audio` 5、`wifi` 3 / `wifi.supplicant` 4、`thermal` 3、`gatekeeper` 1、`keymint` 4/3、`drm` 1、`usb` 3、`gnss` 4。

## 13. 待验证计划（F1）

在设备上用 adb 执行，输出落到 `out/<date>-f1-hardware/`：

```bash
# 系统状态
adb shell getprop | grep -E 'ro\.(soc|board|hardware|product)|sys\.boot_completed'
adb shell dumpsys display          | head -80      # 模式 / HDR / 密度
adb shell dumpsys input            | head -120     # 触控 + 笔设备
adb shell dumpsys sensorservice    | head -80      # 实际传感器列表与速率
adb shell dumpsys media.camera     | head -80      # 相机数量 / 特性
adb shell dumpsys wifi             | head -80      # Wi-Fi 开关/扫描
adb shell dumpsys bluetooth_manager| head -80
adb shell dumpsys audio            | head -100
adb shell dumpsys battery          | head -40
adb shell dumpsys thermalservice   | head -60
adb shell cmd vibrator vibrate 200 # 触感（若服务允许）
adb shell dmesg | grep -iE 'aw8693|aw22xxx|NVT-ts|camera|soundwire|wsa88|wcd93'
```

待填功能测试矩阵：Wi-Fi 扫描/连接/吞吐、蓝牙配对 + A2DP、扬声器/麦克风/USB-C 音频、前/后摄拍照、传感器数值（加速度/陀螺/磁力/光感/气压/接近）、室外 GPS 定位、人脸录入、亮度曲线 + 自动亮度、30/60/90/120/144/165 Hz 切换、笔输入、触感强度、LED 行为、充电曲线、SD 卡、USB-OTG host、Widevine 播放、OTA 升级通路。

F1 期间需重点关注的已知问题（启动日志中已观察到）：

1. `DisplayPowerController: failed to set up display white-balance: … cannot find color temperature sensor` —— 自动白平衡将不可用。
2. `android.hardware.thermal-service.qti: No thermal zone for sensor: battery, ret:-1` —— 热 HAL 可能缺少电池温度区。
3. `healthd: …Path not found` 电池可选 sysfs 节点警告 —— 属外观性警告，但电池 UI 可能显示细节减少。
4. 相机 provider 启动时报 fastrpc `0x39` 搜索路径错误（服务仍能启动）——关注相机打开失败。
5. 启动早期一条 `wlc: Could not read interface wlan0 flags: No such device` —— 待 WLAN 驱动加载后确认 Wi-Fi 是否干净起来。
6. 诊断态：SELinux permissive 会产生大量 `avc denied`（permissive=1），这些不是功能故障。`init_boot_logging13` 会按设计持续把内核日志写入 `logdump` 分区。

## 14. 证据来源

| 主题 | 证据 |
|---|---|
| 运行中的 HAL 进程及各子系统 PID | `out/2026-11-12-edl-f0/device/postflash-final/ps-A.txt` |
| 显示模式 / 密度 / HDR / 触控输入设备 / 传感器注册 | `.../postflash-final/logcat-all.txt`（`DisplayDeviceInfo`、`InputReader`、`SensorService` 相关行） |
| 启动属性（加密、SoC、显示开关、Wi-Fi 接口） | `.../postflash-final/getprop-final.txt` |
| 挂载、/data 占用 | `.../postflash-final/mounts.txt`、`data-fs.txt` |
| 内核 probe（面板、触控、触感、LED、相机保留内存、UFS、PMIC） | 原厂 `dmesg` 抓取 `handoff/2026-10-12-flash1/grab/dmesg.txt`；`.../postflash-final/dmesg.txt` |
| 硬件清点、HAL/manifest 版本、面板/传感器/音频/相机线索 | `work/research/B-tb323fu-hardware.md` §1/§3/§4 |
| 开机验收 / 功能测试范围 | `out/2026-11-12-edl-f0/F0-ACCEPTANCE-REPORT.md` §3/§5 |
