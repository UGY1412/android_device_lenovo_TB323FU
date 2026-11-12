# Tools / 工具说明

Author/Maintainer: krollv, @DeepSeek V4.1 Flash 1017  
作者/维护者：自恋也是种美，@DeepSeek V4.1 Flash 1017

Reference scripts used during the TB323FU LineageOS 24 bring-up. They are
provided for study and reuse; **paths were sanitized** and must be adapted.

TB323FU LineageOS 24 bring-up 期间使用的参考脚本，供学习与复用；**路径已脱敏**，
使用前需按本机环境修改。

## Files / 文件

| File | Purpose / 用途 |
|---|---|
| `edl-precheck.py` | Read-only preflight over EDL (9008): GPT, misc/BCB, partition hashes, block classification / EDL 只读预检：GPT、misc、分区哈希、块分类 |
| `edl-write-f0.py` | Write the F0 partition set over EDL, with head/tail read-back verification / 经 EDL 写 F0 分区集并回读校验 |
| `flash-system-blocks.py` | Flash only the changed 4 KiB blocks of a system image via EDL (byte-exact, fast) / 只写 system 镜像变化的 4 KiB 块（精确、快速） |
| `edl-dump-system-blocks.py` | Read back changed blocks and classify OLD/NEW/MIXED/OTHER / 回读变化块并分类 |
| `boot-doctor.py` | Classify captured boot logs (misc/logdump/metadata) into failure stages / 对抓取的启动日志做阶段判定 |
| `superkit.py` | Assemble/audit a 20 GiB `super.img` from raw partition images / 由 raw 分区拼装/审计 20 GiB super 镜像 |
| `regions.json`, `audit_v6.json` | Partition-region geometry used by the scripts / 脚本使用的分区几何数据 |

## Path placeholders / 路径占位符

After sanitization, project paths appear as:

- `<PROJECT_ROOT>` — the original Windows project directory (sanitized)
- `<WORKSPACE>` — the agent/workspace directory
- `<USER_HOME>` — the user profile (only in a few comments)

Replace them with your own absolute paths before running.
运行前请替换为你自己的绝对路径。

## Requirements / 依赖

- Python 3.9+ (Windows or Linux)
- A Qualcomm **firehose** loader and EDL tool `fh_loader`/`QSaharaServer`
  (not included — obtain them from public flashing-tool packages for your
  platform; the loader must match SM8850)
- A USB cable and the device in EDL (9008) or fastbootd mode
- **fastboot/platform-tools** for the fastbootd routes

## Safety / 安全

These scripts write boot-critical partitions. Before any write:

1. Read a full backup of the partitions you intend to modify.
2. Verify the target partition name/LUN/sector and the image SHA-256.
3. Keep the device connected to a stable USB port and power.
4. Never run a write without a read-back verification.

The authors accept no responsibility for bricked devices or data loss.

## License / 许可

Original scripts in this directory: Apache-2.0 (see the repository `LICENSE`).
No proprietary tool binaries are included.
