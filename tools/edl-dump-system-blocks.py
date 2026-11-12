#!/usr/bin/env python3
"""edl-dump-system-blocks.py — EDL preflight: read the F0 changed blocks from the device
(LUN0, LBA = 620062 + block_index), print each block's sha16 and classify device state
against blocks.tsv old/new hashes.

Device state verdict:
  OLD    all blocks still have old content        -> F0 block patch NOT applied (safe to write)
  NEW    all blocks already have new content      -> F0 block patch already applied (nothing to do)
  MIXED  some old, some new                       -> previous write interrupted; re-run block flash
  OTHER  at least one block matches neither hash  -> device system_b base differs; DO NOT flash --
                                                      investigate (full-image route or restore anchor)

Usage:
  python edl-dump-system-blocks.py --dry-run      # no device needed: print LBA list + exit 0
  python edl-dump-system-blocks.py                # device must be in EDL/firehose (9008)
Options:
  --tsv PATH      default: blocks.tsv next to this script
  --lba-base N    default 620062 (super LBA 8968 + system_b offset 2503041024/4096)
  --out PATH      optional JSON result file
  --no-reset      keep device in firehose after readback (default: power reset at end)

The tool NEVER writes to the device: it only issues EDL <read> commands (1 sector each).
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

# ---- EDL toolchain constants (same as flash-system-blocks.py, verified in this project) ----
WIN = r'<USER_HOME>\Downloads\高通工具箱-2026.9.28-1\bin\tool\Win'
FH = os.path.join(WIN, 'fh_loader.exe')
QS = os.path.join(WIN, 'QSaharaServer.exe')
PROG = (r'<USER_HOME>\Downloads\高通工具箱-2026.9.28-1\bin\tool\qctool'
        r'\lenovo\devprg_legion-y700-5-2.0.11.043\prog_firehose_ddr.elf')
WORK = r'<WORKSPACE>'

LUN = 0
SECTOR = 4096
LBA_BASE = 620062          # super start LBA 8968 + system_b offset 2,503,041,024/4096 = 611094
EXTENT_BLOCKS = 2498804    # 10,235,101,184 / 4096

_log_file = None


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    if _log_file:
        _log_file.write(s + '\n')
        _log_file.flush()


def run(cmd, timeout=300):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors='replace',
                           cwd=WIN, timeout=timeout)
        return (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def fh(xml, timeout=300):
    return run([FH, '--port=\\\\.\\COM3', '--memoryname=ufs', '--search_path=' + WORK,
                '--sendxml=' + xml, '--mainoutputdir=' + WORK, '--skip_configure',
                '--noprompt', '--zlpawarehost=1'], timeout=timeout)


def firehose():
    xml = os.path.join(WORK, 'probe.xml')
    open(xml, 'w').write('<?xml version="1.0" ?><data><read SECTOR_SIZE_IN_BYTES="4096" '
                         'physical_partition_number="0" start_sector="%d" '
                         'num_partition_sectors="1" filename="probe.bin" /></data>'
                         % LBA_BASE)
    for attempt in range(2):
        if 'All Finished Successfully' in fh(xml, 90):
            log('firehose ok')
            return True
        log('firehose probe failed; try to start programmer (QSaharaServer) ...')
        out = run([QS, '-p', r'\\.\COM3', '-s', '13:' + PROG], timeout=120)
        log('\n'.join([l for l in out.splitlines() if l.strip()][-2:]))
        time.sleep(2)
    return False


def read_block(lba):
    fn = 'blk_%d.bin' % lba
    p = os.path.join(WORK, fn)
    if os.path.exists(p):
        os.remove(p)
    xml = os.path.join(WORK, 'read_%d.xml' % lba)
    open(xml, 'w').write('<?xml version="1.0" ?><data><read SECTOR_SIZE_IN_BYTES="4096" '
                         'physical_partition_number="%d" start_sector="%d" '
                         'num_partition_sectors="1" filename="%s" /></data>'
                         % (LUN, lba, fn))
    out = fh(xml, 120)
    if 'All Finished Successfully' not in out or not os.path.exists(p):
        return None
    data = open(p, 'rb').read()
    os.remove(p)
    return data


def load_tsv(path):
    rows = []
    for ln in open(path, encoding='utf-8', errors='replace'):
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        p = ln.split('\t')
        rows.append({'block': int(p[0]), 'old': p[1], 'new': p[2]})
    return rows


def main():
    global WORK, _log_file, LBA_BASE
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = r'<PROJECT_ROOT>\out\2026-11-11-los24-bootfix'
    # prefer blocks.tsv next to this script, else the canonical copy in the F0 output dir
    default_tsv = os.path.join(here, 'blocks.tsv')
    if not os.path.exists(default_tsv):
        default_tsv = os.path.join(out_dir, 'blocks.tsv')
    ap = argparse.ArgumentParser()
    ap.add_argument('--tsv', default=default_tsv)
    ap.add_argument('--lba-base', type=int, default=LBA_BASE)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out', default=None)
    ap.add_argument('--no-reset', action='store_true')
    args = ap.parse_args()
    LBA_BASE = args.lba_base

    if not os.path.exists(args.tsv):
        log('FATAL: blocks.tsv not found:', args.tsv)
        return 2
    rows = load_tsv(args.tsv)
    if not rows:
        log('FATAL: empty blocks.tsv'); return 2
    log('blocks.tsv:', args.tsv, '| blocks:', len(rows), '| lba base:', LBA_BASE)
    log('target LBAs:')
    for r in rows:
        lba = LBA_BASE + r['block']
        if lba < LBA_BASE or lba >= LBA_BASE + EXTENT_BLOCKS:
            log('FATAL: LBA %d outside system_b extent' % lba); return 2
        log('  block %-8d -> LBA %d   (old %s / new %s)'
            % (r['block'], lba, r['old'], r['new']))

    if args.dry_run:
        log('DRY-RUN OK: printed %d target LBAs; device NOT touched' % len(rows))
        return 0

    os.makedirs(WORK, exist_ok=True)
    _log_file = open(os.path.join(WORK, 'dump_%s.log' % time.strftime('%Y%m%d_%H%M%S')),
                     'w', encoding='utf-8')
    log('=== EDL preflight dump (LUN%d, %d blocks)' % (LUN, len(rows)))
    if not firehose():
        log('ERROR: device not reachable in EDL/firehose (9008). Put device into EDL and retry.')
        log('       (dry-run works without device: --dry-run)')
        return 3

    results = []
    n_old = n_new = n_other = 0
    for r in rows:
        lba = LBA_BASE + r['block']
        data = read_block(lba)
        if data is None or len(data) != SECTOR:
            log('  block %-8d LBA %-9d READ FAILED' % (r['block'], lba))
            results.append({'block': r['block'], 'lba': lba, 'state': 'READ_FAIL'})
            n_other += 1
            continue
        h = hashlib.sha256(data).hexdigest()[:16]
        if h == r['old']:
            st = 'OLD'; n_old += 1
        elif h == r['new']:
            st = 'NEW'; n_new += 1
        else:
            st = 'OTHER'; n_other += 1
        cur = data[:32]
        log('  block %-8d LBA %-9d sha16=%s  old=%s new=%s  => %s'
            % (r['block'], lba, h, r['old'], r['new'], st))
        results.append({'block': r['block'], 'lba': lba, 'sha16': h,
                        'old': r['old'], 'new': r['new'], 'state': st})
    if n_other == 0 and n_new == 0:
        verdict = 'OLD (block patch NOT applied) -> safe to run flash-system-blocks.py'
    elif n_other == 0 and n_old == 0:
        verdict = 'NEW (block patch already applied) -> nothing to write'
    elif n_other == 0:
        verdict = 'MIXED (old+new) -> interrupted write; re-run flash-system-blocks.py'
    else:
        verdict = ('OTHER (%d block(s) match neither hash) -> DO NOT flash block patch; '
                   'device system_b differs. Use full-image route or restore anchor.' % n_other)
    log('=== VERDICT: %s   (OLD=%d NEW=%d OTHER=%d total=%d)'
        % (verdict, n_old, n_new, n_other, len(rows)))
    res = {'tsv': args.tsv, 'lba_base': LBA_BASE, 'blocks': len(rows),
           'old_count': n_old, 'new_count': n_new, 'other_count': n_other,
           'verdict': verdict, 'per_block': results}
    if args.out:
        json.dump(res, open(args.out, 'w', encoding='utf-8'), indent=1)
        log('result ->', args.out)
    if not args.no_reset:
        xml = os.path.join(WORK, 'reset.xml')
        open(xml, 'w').write('<?xml version="1.0" ?><data><power value="reset"/></data>')
        out = run([FH, '--port=\\\\.\\COM3', '--search_path=' + WORK, '--sendxml=' + xml,
                   '--noprompt', '--zlpawarehost=1', '--memoryname=ufs'], timeout=120)
        log('reset:', 'All Finished Successfully' in out)
    # exit codes: 0=OLD/NEW (consistent), 5=MIXED (interrupted block patch),
    #             4=OTHER (unexpected content -> never flash the block patch)
    if n_other:
        rc = 4
    elif n_old and n_new:
        rc = 5
    else:
        rc = 0
    log('EXIT_CODE', rc)
    return rc


if __name__ == '__main__':
    try:
        rc = main()
    finally:
        if _log_file:
            _log_file.close()
    print('EXIT', rc)
    sys.exit(rc)
