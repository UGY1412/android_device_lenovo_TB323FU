#!/usr/bin/env python3
"""flash-system-blocks.py — write the changed 4 KiB blocks of system_b (LOS system,
logdump-removal patch) to the device over EDL/firehose, WITHOUT writing the full 10 GiB.

Target geometry (TB323FU, from verified flash logs):
  super physical partition, LUN0, starts at 4 KiB LBA 8968
  system_b extent offset inside super = 2,503,041,024 B = 611,094 4KiB-blocks
  => system_b absolute 4KiB LBA = 8968 + 611094 = 620,062  (maintainer-verified)
  changed block `b` (index into system_b raw, 4 KiB units) -> LBA 620062 + b

Inputs (same directory by default):
  blocks.tsv                     # col1 block_index, then old/new sha16 (from blockdiff.py)
  system_b_changed_blocks.bin    # new content, concatenated in ascending block order

Usage (run on Windows where fh_loader/QT toolchain exists; device in EDL/9008):
  python flash-system-blocks.py --dry-run
  python flash-system-blocks.py            # write + readback verify of sampled ranges + reset probe
  python flash-system-blocks.py --no-reset # leave device in firehose after writing

Safety:
  * refuses to run if any target LBA falls outside the system_b extent;
  * --dry-run prints LBA ranges and first/last LBA (to cross-check before writing);
  * verifies total bin size == n_blocks * 4096;
  * after writing, reads back the first changed range and the last changed block and compares;
  * prints a summary table; non-zero exit on any failure.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time

# ---- device/toolchain constants (verified in earlier EDL runs of this project) ----
WIN = r'<USER_HOME>\Downloads\高通工具箱-2026.9.28-1\bin\tool\Win'
FH = os.path.join(WIN, 'fh_loader.exe')
QS = os.path.join(WIN, 'QSaharaServer.exe')
PROG = (r'<USER_HOME>\Downloads\高通工具箱-2026.9.28-1\bin\tool\qctool'
        r'\lenovo\devprg_legion-y700-5-2.0.11.043\prog_firehose_ddr.elf')
WORK = r'<WORKSPACE>'

SYS_B_START_LBA = 620062          # absolute 4 KiB LBA of system_b block 0 (maintainer-verified)
SYS_B_BLOCKS = 2498804            # 10,235,101,184 / 4096
SYS_B_LAST_LBA = SYS_B_START_LBA + SYS_B_BLOCKS - 1
LUN = 0
SECTOR = 4096

BLOCK = 4096


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    if _lf:
        _lf.write(s + '\n'); _lf.flush()


def run(cmd, timeout=1800):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors='replace',
                           cwd=WIN, timeout=timeout)
        return (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def fh(xml, timeout=1800):
    return run([FH, '--port=\\\\.\\COM3', '--memoryname=ufs', '--search_path=' + WORK,
                '--sendxml=' + xml, '--mainoutputdir=' + WORK, '--skip_configure',
                '--noprompt', '--zlpawarehost=1'], timeout=timeout)


def firehose():
    xml = os.path.join(WORK, 'probe.xml')
    open(xml, 'w').write('<?xml version="1.0" ?><data><read SECTOR_SIZE_IN_BYTES="4096" '
                         'physical_partition_number="0" start_sector="%d" '
                         'num_partition_sectors="1" filename="probe.bin" /></data>'
                         % (SYS_B_START_LBA,))
    for _ in range(3):
        if 'All Finished Successfully' in fh(xml, 120):
            log('firehose ok'); return True
        log('probe fail; start programmer')
        out = run([QS, '-p', r'\\.\COM3', '-s', '13:' + PROG], timeout=120)
        log([l for l in out.splitlines() if l.strip()][-2:])
        time.sleep(2)
    return False


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_blocks(lba, count):
    fn = 'rb_%d_%d.bin' % (lba, count)
    xml = os.path.join(WORK, 'rb.xml')
    p = os.path.join(WORK, fn)
    if os.path.exists(p):
        os.remove(p)
    open(xml, 'w').write('<?xml version="1.0" ?><data><read SECTOR_SIZE_BYTES_PLACEHOLDER '
                         'SECTOR_SIZE_IN_BYTES="4096" physical_partition_number="%d" '
                         'start_sector="%d" num_partition_sectors="%d" filename="%s" />'
                         '</data>'.replace('SECTOR_SIZE_BYTES_PLACEHOLDER ', '')
                         % (LUN, lba, count, fn))
    out = fh(xml, 300)
    if 'All Finished Successfully' not in out or not os.path.exists(p):
        log('readback FAILED at LBA %d' % lba)
        return None
    d = open(p, 'rb').read()
    os.remove(p)
    return d


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--blocks', default=os.path.join(here, 'blocks.tsv'))
    ap.add_argument('--bin', dest='binfile',
                    default=os.path.join(here, 'system_b_changed_blocks.bin'))
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-reset', action='store_true')
    args = ap.parse_args()

    blocks = []
    for ln in open(args.blocks, encoding='utf-8', errors='replace'):
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        blocks.append(int(ln.split('\t')[0]))
    if not blocks:
        log('FATAL: no blocks in', args.blocks); return 2
    if blocks != sorted(set(blocks)):
        log('FATAL: blocks.tsv not strictly ascending/unique'); return 2
    nbytes = os.path.getsize(args.binfile) if os.path.exists(args.binfile) else -1
    if nbytes != len(blocks) * BLOCK:
        log('FATAL: bin size %d != n_blocks(%d)*4096' % (nbytes, len(blocks))); return 2

    # merge into contiguous ranges
    ranges = []
    for b in blocks:
        if ranges and b == ranges[-1][1] + 1:
            ranges[-1][1] = b
        else:
            ranges.append([b, b])
    first_lba = SYS_B_START_LBA + blocks[0]
    last_lba = SYS_B_START_LBA + blocks[-1]
    log('changed blocks: %d (%d B); ranges: %d' % (len(blocks), len(blocks) * BLOCK, len(ranges)))
    log('system_b extent LBA range: %d .. %d (blocks %d)' % (SYS_B_START_LBA, SYS_B_LAST_LBA, SYS_B_BLOCKS))
    log('target LBA range      : %d .. %d' % (first_lba, last_lba))
    if first_lba < SYS_B_START_LBA or last_lba > SYS_B_LAST_LBA:
        log('FATAL: target outside system_b extent'); return 2
    for (a, b) in ranges:
        if SYS_B_START_LBA + a < SYS_B_START_LBA or SYS_B_START_LBA + b > SYS_B_LAST_LBA:
            log('FATAL: range outside extent', a, b); return 2
    if args.dry_run:
        idx = 0
        for (a, b) in ranges:
            log('  range: blocks %d..%d  count=%d  LBA %d..%d  bin_off=%d'
                % (a, b, b - a + 1, SYS_B_START_LBA + a, SYS_B_START_LBA + b, idx * BLOCK))
            idx += b - a + 1
        log('DRY-RUN OK: nothing written')
        return 0

    os.makedirs(WORK, exist_ok=True)
    log('=== inputs')
    log('blocks.tsv      sha256 =', hashlib.sha256(open(args.blocks, 'rb').read()).hexdigest())
    log('changed bin     sha256 =', hashlib.sha256(open(args.binfile, 'rb').read()).hexdigest())
    log('changed bin     size   =', nbytes)

    if not firehose():
        log('FATAL: firehose not reachable'); return 2

    # write ranges: one temp file per range + one XML with all programs
    binfile = open(args.binfile, 'rb')
    entries = []
    idx = 0
    for i, (a, b) in enumerate(ranges):
        cnt = b - a + 1
        fn = 'rng_%d.bin' % i
        p = os.path.join(WORK, fn)
        binfile.seek(idx * BLOCK)
        data = binfile.read(cnt * BLOCK)
        assert len(data) == cnt * BLOCK
        open(p, 'wb').write(data)
        entries.append((SYS_B_START_LBA + a, cnt, fn, a, b))
        idx += cnt
    binfile.close()
    xml = os.path.join(WORK, 'write_blocks.xml')
    parts = ['<?xml version="1.0" ?><data>']
    for (lba, cnt, fn, a, b) in entries:
        parts.append('<program start_sector="%d" size_in_KB="%.1f" '
                     'physical_partition_number="%d" partofsingleimage="false" '
                     'file_sector_offset="0" num_partition_sectors="%d" '
                     'readbackverify="false" filename="%s" sparse="false" '
                     'start_byte_hex="0x%X" SECTOR_SIZE_IN_BYTES="4096" label="sysb_blk_%d"/>'
                     % (lba, cnt * BLOCK / 1024.0, LUN, cnt, fn, lba * BLOCK, a))
    parts.append('</data>')
    open(xml, 'w').write(''.join(parts))
    log('XML entries:', len(entries))
    t0 = time.time()
    out = fh(xml)
    ok = 'All Finished Successfully' in out
    log('WRITE ok=%s  %.1fs' % (ok, time.time() - t0))
    if not ok:
        log([l for l in out.splitlines() if 'ERROR' in l.upper()][-8:])
        return 1

    # readback verify: first range, middle range, last range
    allok = True
    for tag, ri in (('first', 0), ('mid', len(entries) // 2), ('last', len(entries) - 1)):
        lba, cnt, fn, a, b = entries[ri]
        exp = open(os.path.join(WORK, fn), 'rb').read()
        got = read_blocks(lba, cnt)
        same = got is not None and got[:len(exp)] == exp
        log('READBACK %-5s LBA %d..%d MATCH=%s' % (tag, lba, lba + cnt - 1, same))
        allok = allok and same
    log('=== RESULT: %s' % ('ALL OK' if allok else 'FAILED'))
    if allok and not args.no_reset:
        xml = os.path.join(WORK, 'reset.xml')
        open(xml, 'w').write('<?xml version="1.0" ?><data><power value="reset"/></data>')
        out = run([FH, '--port=\\\\.\\COM3', '--search_path=' + WORK, '--sendxml=' + xml,
                   '--noprompt', '--zlpawarehost=1', '--memoryname=ufs'], timeout=120)
        log('reset:', 'All Finished Successfully' in out)
    return 0 if allok else 1


if __name__ == '__main__':
    _lf = None
    try:
        if '--dry-run' not in sys.argv:
            os.makedirs(WORK, exist_ok=True)
            _lf = open(os.path.join(WORK, 'flash_blocks_%s.log'
                                    % time.strftime('%Y%m%d_%H%M%S')), 'w', encoding='utf-8')
        rc = main()
    finally:
        if _lf:
            _lf.close()
    print('EXIT', rc)
    sys.exit(rc)
