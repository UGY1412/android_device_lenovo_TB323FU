# Documentation / 文档索引

Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017  
作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017

Every document exists in English (`docs/en/`) and Chinese (`docs/zh-CN/`)
with the same structure and data. / 每篇文档都有英文（`docs/en/`）和中文
（`docs/zh-CN/`）两个版本，结构与数据一致。

| # | English | 中文 | Topic / 主题 |
|---|---|---|---|
| 01 | [01-DEVICE-FACTS](en/01-DEVICE-FACTS.md) | [01-DEVICE-FACTS](zh-CN/01-DEVICE-FACTS.md) | Partitions, LUN map, super layout, kernel, slots / 分区、LUN、super 布局、内核、槽位 |
| 02 | [02-BUILD](en/02-BUILD.md) | [02-BUILD](zh-CN/02-BUILD.md) | Build environment, repo/lunch, blobs, build errors / 构建环境、blobs、构建错误 |
| 03 | [03-FLASH](en/03-FLASH.md) | [03-FLASH](zh-CN/03-FLASH.md) | EDL / fastbootd flashing, wipe, rollback / 刷写、清数据、回退 |
| 04 | [04-HARDWARE-SUPPORT](en/04-HARDWARE-SUPPORT.md) | [04-HARDWARE-SUPPORT](zh-CN/04-HARDWARE-SUPPORT.md) | Verified / unverified functions / 已验证与未验证功能 |
| 05 | [05-ROOTCAUSE-VENDOR-SYMLINK](en/05-ROOTCAUSE-VENDOR-SYMLINK.md) | [05-ROOTCAUSE-VENDOR-SYMLINK](zh-CN/05-ROOTCAUSE-VENDOR-SYMLINK.md) | `/vendor` self-referential symlink → first-stage FATAL |
| 06 | [06-ROOTCAUSE-LOGDUMP-METADATA](en/06-ROOTCAUSE-LOGDUMP-METADATA.md) | [06-ROOTCAUSE-LOGDUMP-METADATA](zh-CN/06-ROOTCAUSE-LOGDUMP-METADATA.md) | logdump corrupting `/metadata` → `init_user0_failed` |
| 07 | [07-FBE-INIT-USER0](en/07-FBE-INIT-USER0.md) | [07-FBE-INIT-USER0](zh-CN/07-FBE-INIT-USER0.md) | FBE / `init_user0` analysis & dual-fstab fix |
| 08 | [08-SELINUX-POLICY](en/08-SELINUX-POLICY.md) | [08-SELINUX-POLICY](zh-CN/08-SELINUX-POLICY.md) | Precompiled SELinux policy mismatch & 4 KiB policy patch |
| 09 | [09-AVB-CHAIN-NOTES](en/09-AVB-CHAIN-NOTES.md) | [09-AVB-CHAIN-NOTES](zh-CN/09-AVB-CHAIN-NOTES.md) | ABL / vbmeta / test-key / 8 s-to-fastboot semantics |
| 10 | [10-DEBUG-CHANNELS](en/10-DEBUG-CHANNELS.md) | [10-DEBUG-CHANNELS](zh-CN/10-DEBUG-CHANNELS.md) | Capturing first-stage logs without pstore |
| 11 | [11-ERROR-CATALOG](en/11-ERROR-CATALOG.md) | [11-ERROR-CATALOG](zh-CN/11-ERROR-CATALOG.md) | 40+ real error messages → meaning → fix |
| 12 | [12-EXPERIMENT-LOG](en/12-EXPERIMENT-LOG.md) | [12-EXPERIMENT-LOG](zh-CN/12-EXPERIMENT-LOG.md) | Failed experiments and ruled-out hypotheses |

## Other documents / 其它文档

- [ATTRIBUTION.md](ATTRIBUTION.md) — per-path provenance map / 逐目录来源映射
- [COMPLIANCE.md](COMPLIANCE.md) — inclusion/exclusion policy & takedown / 合规与下架
- [ECOSYSTEM.md](ECOSYSTEM.md) — reusing this tree for other AOSP ROMs / 复用与移植指引
- `screenshots/` — device evidence screenshots / 真机证据截图
