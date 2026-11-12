#!/usr/bin/env python3
"""edl-write-f0.py — Device-writer for the F0 flash set over EDL/firehose (9008).

Writes (LUN, 4KiB-LBA, sectors) — geometry cross-verified 2026-11-12 20:19 by the maintainer from
GPT refs gpt_main0/gpt_main4 + restore-map LP extents + regions.json:
  vbmeta_system_b   LUN0  lba 5,251,864  16      vbmeta_system_v10.img
  init_boot_b       LUN4  lba   722,990   2,048   init_boot_logging13.img
  vendor_boot_b     LUN4  lba   672,238  24,576   vendor_boot_diag2.img
  system_ext_b      LUN0  lba 3,122,496 137,444   system_ext_f0diag.img
  vendor_b          LUN0  lba 3,259,940 537,797   vendor_b_full_stock.img
(system_b is handled by flash-system-blocks.py: 9 blocks @ lba 620062+block)

Usage:
  python edl-write-f0.py --dry-run                    # offline: verify files/size/sha, print plan
  python edl-write-f0.py --verify-only                # device: read back head/tail (+full small) and compare
  python edl-write-f0.py --no-reset                   # write all, keep device in firehose
  python edl-write-f0.py --no-reset --only vbmeta_system,init_boot
  python edl-write-f0.py --reset --only vendor        # write one, then power reset
Exit: 0 ok, 1 write/verify failure, 2 offline precondition failure, 3 firehose unreachable.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time

WIN = r'<USER_HOME>\Downloads\高通工具箱-2026.9.28-1\bin\tool\Win'
FH = os.path.join(WIN, 'fh_loader.exe')
QS = os.path.join(WIN, 'QSaharaServer.exe')
PROG = (r'<USER_HOME>\Downloads\高通工具箱-2026.9.28-1\bin\tool\qctool'
        r'\lenovo\devprg_legion-y700-5-2.0.11.043\prog_firehose_ddr.elf')
BT = r'<PROJECT_ROOT>\out\2026-11-11-los24-bootfix'
OUT = r'<PROJECT_ROOT>\out\2026-11-12-edl-f0'
WORK = os.path.join(OUT, 'work')
STAMP = time.strftime('%Y%m%d_%H%M%S')
SECTOR = 4096

# name -> (lun, lba, sectors, image filename, expected sha256)
TARGETS = {
    'vbmeta_system': (0, 5251864, 16, 'vbmeta_system_v10.img',
                      '2b52e26b9c1bc8f15562d5e22a1fc2eced0d5721a432e15846ee26901fce4afc'),
    'init_boot': (4, 722990, 2048, 'init_boot_logging13.img',
                  'baf1133d9699240dd64b069d5792a7b21348121d1b16d53f14b405d8c5ff0c78'),
    'vendor_boot': (4, 672238, 24576, 'vendor_boot_diag2.img',
                    '406235697d5df9a95a5425b6ddeed26413cda11da41a88c5612317909345f969'),
    'system_ext': (0, 3122496, 137444, 'system_ext_f0diag.img',
                   'e1addc293fedcf5ace231636f7da04495b4d3243035ca6c52789c0c4b49f5945'),
    'vendor': (0, 3259940, 537797, 'vendor_b_full_stock.img',
               '08caa9a653332bc2e86063f4dd7f545b7760cc83524a68713b6df1eea6897957'),
}
ORDER = ['vbmeta_system', 'init_boot', 'vendor_boot', 'system_ext', 'vendor']
# sanity: these extents must not overlap each other (all are disjoint partitions in GPT/super)
_lf = None


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    if _lf:
        _lf.write(s + '\n')
        _lf.flush()


def run(args, timeout=3600):
    try:
        p = subprocess.run(args, capture_output=True, text=True, errors='replace',
                           cwd=WIN, timeout=timeout)
        return (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def fh(xml, timeout=3600):
    return run([FH, '--port=\\\\.\\COM3', '--memoryname=ufs', '--search_path=' + WORK,
                '--sendxml=' + xml, '--mainoutputdir=' + WORK, '--skip_configure',
                '--noprompt', '--zlpawarehost=1'], timeout=timeout)


def firehose():
    xml = os.path.join(WORK, 'probe.xml')
    open(xml, 'w').write('<?xml version="1.0" ?><data><read SECTOR_SIZE_IN_BYTES="4096" '
                         'physical_partition_number="0" start_sector="620062" '
                         'num_partition_sectors="1" filename="probe.bin" /></data>')
    for i in range(3):
        out = fh(xml, 120)
        if 'All Finished Successfully' in out:
            log('firehose OK (attempt %d)' % (i + 1))
            return True
        log('probe failed; starting programmer via QSaharaServer ...')
        lo = run([QS, '-p', r'\\.\COM3', '-s', '13:' + PROG], timeout=180)
        lines = [l for l in lo.splitlines() if l.strip()]
        log('QSahara tail:', lines[-2:] if lines else '(empty)')
        time.sleep(3)
    return False


def sha_file(path, block=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(block)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def resolve(name):
    lun, lba, sectors, fn, want = TARGETS[name]
    return lun, lba, sectors, os.path.join(BT, fn), want


def dry_run():
    bad = 0
    log('=== F0 EDL WRITE PLAN (dry-run) %s ===' % STAMP)
    log('%-14s %-4s %-10s %-9s %-14s %-17s %s' %
        ('name', 'LUN', 'lba', 'sectors', 'bytes', 'sha256', 'state'))
    for name in ORDER:
        lun, lba, sectors, img, want = resolve(name)
        if not os.path.exists(img):
            log('%-14s MISSING %s' % (name, img)); bad += 1; continue
        sz = os.path.getsize(img)
        ok = sz == sectors * SECTOR
        sha = sha_file(img)
        shaok = sha == want
        log('%-14s %-4d %-10d %-9d %-14d %-17s size=%s sha=%s' %
            (name, lun, lba, sectors, sectors * SECTOR, sha[:16],
             'OK' if ok else 'SIZE-MISMATCH', 'OK' if shaok else 'SHA-MISMATCH'))
        if not ok or not shaok:
            bad += 1
    # blocks.tsv / changed-bin inputs for system patch
    for fn in ('blocks.tsv', 'system_b_changed_blocks.bin', 'flash-system-blocks.py'):
        p = os.path.join(BT, fn)
        log('%-14s %s  %s' % ('aux', fn, 'present' if os.path.exists(p) else 'MISSING'))
        if not os.path.exists(p):
            bad += 1
    log('--- planned order:', ' -> '.join(ORDER), '(system block patch via flash-system-blocks.py first/last)')
    log('DRY-RUN RESULT: %s' % ('OK' if not bad else 'FAIL (%d)' % bad))
    return 0 if not bad else 2


def read_sectors(lun, lba, cnt, tag):
    fn = 'rb_%s_%d_%d.bin' % (tag, lba, cnt)
    p = os.path.join(WORK, fn)
    if os.path.exists(p):
        os.remove(p)
    xml = os.path.join(WORK, 'read_%s.xml' % tag)
    open(xml, 'w').write('<?xml version="1.0" ?><data><read SECTOR_SIZE_IN_BYTES="4096" '
                         'physical_partition_number="%d" start_sector="%d" '
                         'num_partition_sectors="%d" filename="%s" /></data>'
                         % (lun, lba, cnt, fn))
    out = fh(xml, 900)
    if 'All Finished Successfully' not in out or not os.path.exists(p):
        log('  READBACK FAILED %s (%s)' % (tag, [l for l in out.splitlines() if 'ERROR' in l][-2:]))
        return None
    return open(p, 'rb').read()


def write_one(name):
    lun, lba, sectors, img, want = resolve(name)
    link = os.path.join(WORK, 'w_%s.img' % name)
    if os.path.exists(link):
        os.remove(link)
    try:
        os.link(img, link)
    except OSError:
        shutil.copyfile(img, link)
    xml = os.path.join(WORK, 'write_%s.xml' % name)
    open(xml, 'w').write(
        '<?xml version="1.0" ?><data><program start_sector="%d" size_in_KB="%.1f" '
        'physical_partition_number="%d" partofsingleimage="false" file_sector_offset="0" '
        'num_partition_sectors="%d" readbackverify="false" filename="%s" sparse="false" '
        'start_byte_hex="0x%X" SECTOR_SIZE_IN_BYTES="4096" label="%s"/></data>'
        % (lba, sectors * SECTOR / 1024.0, lun, sectors, os.path.basename(link),
           lba * SECTOR, name))
    log('--- WRITE %-14s LUN%d lba=%d sectors=%d (%.1f MiB) ---'
        % (name, lun, lba, sectors, sectors * SECTOR / 1048576.0))
    t0 = time.time()
    out = fh(xml)
    ok = 'All Finished Successfully' in out
    dt = time.time() - t0
    log('    write ok=%s  %.1fs  (%.1f MiB/s)' % (ok, dt, sectors * SECTOR / 1048576.0 / max(dt, 1e-6)))
    if not ok:
        errs = [l for l in out.splitlines() if 'ERROR' in l.upper()][-6:]
        log('    errors:', errs)
        return False
    # verify head+tail 4KiB
    with open(img, 'rb') as f:
        head = f.read(SECTOR)
        f.seek((sectors - 1) * SECTOR)
        tail = f.read(SECTOR)
    got_h = read_sectors(lun, lba, 1, '%s_h' % name)
    got_t = read_sectors(lun, lba + sectors - 1, 1, '%s_t' % name)
    hok = got_h == head
    tok = got_t == tail
    log('    readback head=%s tail=%s' % ('MATCH' if hok else 'MISMATCH', 'MATCH' if tok else 'MISMATCH'))
    if os.path.exists(link):
        os.remove(link)
    return hok and tok


def verify_all(names):
    allok = True
    for name in names:
        lun, lba, sectors, img, want = resolve(name)
        full = sectors * SECTOR <= 8 * 1048576   # full read for small partitions (<=8MiB)
        if full:
            got = read_sectors(lun, lba, sectors, '%s_full' % name)
            exp = open(img, 'rb').read()
            ok = got == exp
            log('VERIFY %-14s FULL %d B MATCH=%s' % (name, len(exp), ok))
        else:
            with open(img, 'rb') as f:
                head = f.read(SECTOR)
                f.seek((sectors - 1) * SECTOR)
                tail = f.read(SECTOR)
            gh = read_sectors(lun, lba, 1, '%s_vh' % name)
            gt = read_sectors(lun, lba + sectors - 1, 1, '%s_vt' % name)
            ok = gh == head and gt == tail
            log('VERIFY %-14s head/tail MATCH=%s' % (name, ok))
        allok = allok and ok
    return allok


def main():
    global WORK, _lf
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--verify-only', action='store_true')
    ap.add_argument('--only', default=None)
    ap.add_argument('--no-reset', action='store_true')
    ap.add_argument('--reset', action='store_true')
    args = ap.parse_args()

    if args.dry_run:
        return dry_run()

    names = [n for n in ORDER if (not args.only or n in [x.strip() for x in args.only.split(',')])]
    if not names:
        log('FATAL: --only selected nothing'); return 2
    for n in names:
        _, _, sectors, img, want = resolve(n)
        if not os.path.exists(img):
            log('FATAL: missing', img); return 2
        if os.path.getsize(img) != sectors * SECTOR:
            log('FATAL: size mismatch', n, os.path.getsize(img)); return 2
        # verify written bytes match the expected sha BEFORE touching the device
        # (verifier task-3 recommendation: write path must not trust a stale file)
        got = sha_file(img)
        if got != want:
            log('FATAL: sha mismatch', n, 'got', got[:16], 'want', want[:16]); return 2
        log('pre-write sha OK %-14s %s' % (n, got[:16]))

    os.makedirs(WORK, exist_ok=True)
    _lf = open(os.path.join(OUT, 'edl-write-f0-%s.log' % STAMP), 'w', encoding='utf-8')
    log('=== edl-write-f0 %s  targets=%s  reset=%s ===' % (STAMP, names, args.reset and not args.no_reset))
    if not firehose():
        log('FATAL: firehose not reachable'); return 3
    if args.verify_only:
        return 0 if verify_all(names) else 1
    for n in names:
        if not write_one(n):
            log('RESULT: FAIL at', n)
            return 1
    if not verify_all(names):
        log('RESULT: FAIL verification')
        return 1
    if args.reset and not args.no_reset:
        xml = os.path.join(WORK, 'reset.xml')
        open(xml, 'w').write('<?xml version="1.0" ?><data><power value="reset"/></data>')
        out = run([FH, '--port=\\\\.\\COM3', '--search_path=' + WORK, '--sendxml=' + xml,
                   '--noprompt', '--zlpawarehost=1', '--memoryname=ufs'], timeout=180)
        log('reset:', 'All Finished Successfully' in out)
    log('RESULT: ALL OK (%d partitions written+verified)' % len(names))
    return 0


if __name__ == '__main__':
    try:
        rc = main()
    finally:
        if _lf:
            _lf.close()
    print('EXIT', rc)
    sys.exit(rc)
