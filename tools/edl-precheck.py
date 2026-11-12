#!/usr/bin/env python3
"""EDL read-only precheck before F0 flashing (device must be in 9008/firehose).

NEVER writes to the device and NEVER resets it (device stays in firehose after run
so the follow-up write session can reuse the loaded programmer).

Reads:
  - GPT LUN0 / LUN4 (6 sectors each) and compares sha256 with refs/readback-full/gpt_main{0,4}.bin
  - misc (LUN0 LBA 8456, 256 sectors, 1 MiB): BCB + initlog counters
  - init_boot_b (LUN4 722990, 2048s = 8 MiB): compare full sha256 with init_boot_logging13.img
  - vbmeta_system_b (LUN0 5251864, 16s = 64 KiB): compare sha with vbmeta_system_v10.img
  - the 9 F0 blocks (LUN0 LBA=620062+block): classify OLD/NEW/OTHER vs blocks.tsv
  - GPT-parsed geometry dump for vendor_b / system_ext_b / super / misc / metadata / userdata
  - vendor_b head/tail + vendor_boot_b head (informational: current experiment images)

Artifacts -> <PROJECT_ROOT>\\out\\2026-11-12-edl-f0\\device\\
"""
import hashlib
import json
import os
import struct
import subprocess
import sys
import time

WIN = r'<USER_HOME>\Downloads\高通工具箱-2026.9.28-1\bin\tool\Win'
FH = os.path.join(WIN, 'fh_loader.exe')
QS = os.path.join(WIN, 'QSaharaServer.exe')
PROG = (r'<USER_HOME>\Downloads\高通工具箱-2026.9.28-1\bin\tool\qctool'
        r'\lenovo\devprg_legion-y700-5-2.0.11.043\prog_firehose_ddr.elf')
WORK = r'<WORKSPACE>'
OUT = r'<PROJECT_ROOT>\out\2026-11-12-edl-f0\device'
REF = r'<PROJECT_ROOT>\refs\readback-full'
BT = r'<PROJECT_ROOT>\out\2026-11-11-los24-bootfix'
STAMP = time.strftime('%Y%m%d_%H%M%S')
os.makedirs(WORK, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, 'edl-precheck-%s.log' % STAMP)
_lf = open(LOG, 'w', encoding='utf-8')
RES = {}


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    _lf.write(s + '\n')
    _lf.flush()


def run(args, timeout=600):
    try:
        p = subprocess.run(args, capture_output=True, text=True, errors='replace',
                           cwd=WIN, timeout=timeout)
        return (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def fh(xml, timeout=600):
    return run([FH, '--port=\\\\.\\COM3', '--memoryname=ufs', '--search_path=' + WORK,
                '--sendxml=' + xml, '--mainoutputdir=' + WORK, '--skip_configure',
                '--noprompt', '--zlpawarehost=1'], timeout=timeout)


def firehose():
    xml = os.path.join(WORK, 'probe.xml')
    open(xml, 'w').write(
        '<?xml version="1.0" ?><data><read SECTOR_SIZE_IN_BYTES="4096" '
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
        log('QSahara tail:', lines[-3:] if lines else '(empty)')
        time.sleep(3)
    return False


def read_ops(ops, tag):
    """ops: list of (name, lun, lba, cnt). One fh batch."""
    xml = os.path.join(WORK, 'read_%s.xml' % tag)
    parts = ['<?xml version="1.0" ?><data>']
    for (n, lun, lba, cnt) in ops:
        fn = '%s_%s.bin' % (tag, n)
        p = os.path.join(WORK, fn)
        if os.path.exists(p):
            os.remove(p)
        parts.append('<read SECTOR_SIZE_IN_BYTES="4096" physical_partition_number="%d" '
                     'start_sector="%d" num_partition_sectors="%d" filename="%s" />'
                     % (lun, lba, cnt, fn))
    parts.append('</data>')
    open(xml, 'w').write(''.join(parts))
    out = fh(xml, 900)
    ok = 'All Finished Successfully' in out
    log('read[%s] ok=%s' % (tag, ok))
    if not ok:
        errs = [l for l in out.splitlines() if 'ERROR' in l]
        log('errors:', errs[-6:])
        return {}
    data = {}
    for (n, lun, lba, cnt) in ops:
        p = os.path.join(WORK, '%s_%s.bin' % (tag, n))
        need = cnt * 4096
        if os.path.exists(p) and os.path.getsize(p) == need:
            data[n] = open(p, 'rb').read()
            dst = os.path.join(OUT, '%s_%s.bin' % (n, STAMP))
            open(dst, 'wb').write(data[n])
        else:
            log('BAD %s got=%s need=%d' % (n, os.path.getsize(p) if os.path.exists(p) else 'none', need))
    return data


def sha(b):
    return hashlib.sha256(b).hexdigest()


def parse_gpt(g, tag, out_lines):
    off = g.find(b'EFI PART')
    if off < 0:
        out_lines.append('%s: no EFI PART' % tag)
        return {}
    h = struct.unpack('<8sIIIIQQQQ16sQIII', g[off:off + 92])
    num, esz = h[11], h[12]
    ent_lba = h[10]   # partition_entry_lba, in 512-byte logical blocks
    log('%s hdr@%d entry_lba=%d num=%d esz=%d' % (tag, off, ent_lba, num, esz))
    # buffer starts at device byte 0; this device's GPT LBA unit is 4 KiB
    # (primary header at 4096, entry array at entry_lba*4096 = 8192). Verified by
    # verifier task-3: previous *512 offset silently shifted LUN4 entries by 56 and
    # produced an empty LUN0 dump. 4 KiB is correct for TB323FU (UFS, 4K LBA).
    ent_off = ent_lba * 4096
    parts = {}
    for i in range(min(num, 128)):
        e = g[ent_off + i * esz: ent_off + (i + 1) * esz]
        if len(e) < 128:
            break
        name = e[56:128].decode('utf-16le', 'replace').rstrip('\x00')
        if not name:
            continue
        first, last, attr = struct.unpack('<QQQ', e[32:56])
        parts[name] = {'entry': i, 'lba': first, 'last': last,
                       'sectors': last - first + 1, 'attr': attr}
        b54 = (attr >> 48) & 0xFF
        if name in ('vendor_b', 'vendor_boot_b', 'init_boot_b', 'vbmeta_system_b',
                    'system_ext_b', 'super', 'misc', 'metadata', 'userdata', 'vbmeta_b'):
            out_lines.append('  %-16s entry#%-3d lba=%-9d sectors=%-8d attr=0x%016X byte54=0x%02X'
                             % (name, i, first, last - first + 1, attr, b54))
    return parts


def main():
    log('=== EDL PRECHECK %s (READ-ONLY, no reset) ===' % STAMP)
    log('device probe: PnP COM3 expected; log ->', LOG)
    if not firehose():
        log('FATAL: firehose not reachable'); return 2

    # ---- phase 1: fixed LBAs ----
    ops1 = [
        ('gpt_main0', 0, 0, 6),
        ('gpt_main4', 4, 0, 6),
        ('misc', 0, 8456, 256),
        ('init_boot_b', 4, 722990, 2048),
        ('vbmeta_system_b', 0, 5251864, 16),
        ('vendor_boot_b_head', 4, 672238, 2),
        ('vendor_boot_b_tail', 4, 672238 + 24576 - 2, 2),
    ]
    d = read_ops(ops1, 'p1')
    if not d:
        log('FATAL: phase1 read failed'); return 3

    # ---- GPT compare with refs ----
    RES['gpt'] = {}
    for tag, refname in (('gpt_main0', 'gpt_main0.bin'), ('gpt_main4', 'gpt_main4.bin')):
        got = d[tag]
        cur = sha(got)
        rp = os.path.join(REF, refname)
        ref = sha(open(rp, 'rb').read()) if os.path.exists(rp) else 'MISSING'
        RES['gpt'][tag] = {'sha256': cur, 'ref_sha256': ref, 'match': cur == ref}
        log('%-10s sha256=%s  ref=%s  MATCH=%s' % (tag, cur, ref, cur == ref))

    # ---- misc ----
    m = d['misc']
    RES['misc'] = {'sha256': sha(m)}
    cmd = m[0:32].split(b'\x00')[0]
    status = m[32:64].split(b'\x00')[0]
    rec = m[64:64 + 768].split(b'\x00')[0]
    log('misc BCB: command=%r status=%r recovery=%r' % (cmd, status, rec[:120]))
    RES['misc'].update({'bcb_command': cmd.decode('latin-1'), 'bcb_status': status.decode('latin-1'),
                        'bcb_recovery': rec.decode('latin-1')})
    nz_pages = [i // 4096 for i in range(0, len(m), 4096) if any(m[i:i + 4096])]
    log('misc nonzero 4k pages: %d first=%s' % (len(nz_pages), nz_pages[:12]))
    RES['misc']['nonzero_pages'] = nz_pages
    # initlog ctl areas (IL10/12/13 style at 0x80000 and 0x100000-0x2000)
    for base in (0x80000, 0x100000 - 0x2000):
        blob = m[base:base + 64]
        log('misc @0x%X head64=%s' % (base, blob.hex()))

    # ---- init_boot / vbmeta_system compare ----
    RES['init_boot_b'] = {'sha256': sha(d['init_boot_b'])}
    ib = os.path.join(BT, 'init_boot_logging13.img')
    ib_ref = sha(open(ib, 'rb').read()) if os.path.exists(ib) else 'MISSING'
    RES['init_boot_b']['want_sha256'] = ib_ref
    RES['init_boot_b']['match_logging13'] = RES['init_boot_b']['sha256'] == ib_ref
    log('init_boot_b sha256=%s  logging13=%s  MATCH=%s'
        % (RES['init_boot_b']['sha256'], ib_ref, RES['init_boot_b']['match_logging13']))

    RES['vbmeta_system_b'] = {'sha256': sha(d['vbmeta_system_b'])}
    vs = os.path.join(BT, 'vbmeta_system_v10.img')
    vs_ref = sha(open(vs, 'rb').read()) if os.path.exists(vs) else 'MISSING'
    RES['vbmeta_system_b']['want_sha256'] = vs_ref
    RES['vbmeta_system_b']['match_v10'] = RES['vbmeta_system_b']['sha256'] == vs_ref
    log('vbmeta_system_b sha256=%s  v10=%s  MATCH=%s'
        % (RES['vbmeta_system_b']['sha256'], vs_ref, RES['vbmeta_system_b']['match_v10']))

    # ---- GPT geometry dump ----
    glines = []
    parts0 = parse_gpt(d['gpt_main0'], 'LUN0', glines)
    parts4 = parse_gpt(d['gpt_main4'], 'LUN4', glines)
    for ln in glines:
        log(ln)
    RES['parts'] = {'lun0': parts0, 'lun4': parts4}

    # ---- super-based system_b extent sanity ----
    sp = parts0.get('super')
    if sp:
        RES['super'] = sp
        log('super: lba=%d sectors=%d size=%d GiB'
            % (sp['lba'], sp['sectors'], sp['sectors'] * 4096 // (1024 ** 3)))

    # ---- phase 2: 9 F0 blocks ----
    tsv = os.path.join(BT, 'blocks.tsv')
    rows = []
    for ln in open(tsv, encoding='utf-8', errors='replace'):
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        p = ln.split('\t')
        rows.append({'block': int(p[0]), 'old': p[1], 'new': p[2]})
    log('blocks.tsv rows:', len(rows), 'lba_base=620062')
    ops2 = []
    for r in rows:
        ops2.append(('blk_%d' % r['block'], 0, 620062 + r['block'], 1))
    d2 = read_ops(ops2, 'blk')
    if not d2:
        log('FATAL: 9-block read failed'); return 4
    n_old = n_new = n_other = 0
    RES['blocks'] = []
    for r in rows:
        data = d2['blk_%d' % r['block']]
        h = sha(data)[:16]
        if h == r['old']:
            st = 'OLD'; n_old += 1
        elif h == r['new']:
            st = 'NEW'; n_new += 1
        else:
            st = 'OTHER'; n_other += 1
        log('  block %-8d lba=%-9d sha16=%s old=%s new=%s => %s'
            % (r['block'], 620062 + r['block'], h, r['old'], r['new'], st))
        RES['blocks'].append({'block': r['block'], 'lba': 620062 + r['block'],
                              'sha16': h, 'old': r['old'], 'new': r['new'], 'state': st})
    log('=== BLOCK VERDICT: OLD=%d NEW=%d OTHER=%d' % (n_old, n_new, n_other))
    log('    expected pre-F0 state: 8x OLD + 1x NEW(block 81367 policy sector)')
    RES['block_summary'] = {'old': n_old, 'new': n_new, 'other': n_other}

    # ---- phase 3: vendor_b head/tail (informational) ----
    vb = parts4.get('vendor_b') or parts0.get('vendor_b')
    if vb:
        log('vendor_b geometry: lba=%d sectors=%d size=%d B'
            % (vb['lba'], vb['sectors'], vb['sectors'] * 4096))
        lun = 4 if 'vendor_b' in parts4 else 0
        ops3 = [('vendor_b_head', lun, vb['lba'], 1),
                ('vendor_b_tail', lun, vb['lba'] + vb['sectors'] - 1, 1)]
        d3 = read_ops(ops3, 'vb')
        if d3:
            RES['vendor_b'] = {'lun': lun, 'lba': vb['lba'], 'sectors': vb['sectors'],
                               'head_sha16': sha(d3['vendor_b_head'])[:16],
                               'tail_sha16': sha(d3['vendor_b_tail'])[:16]}
            log('vendor_b head16=%s tail16=%s'
                % (RES['vendor_b']['head_sha16'], RES['vendor_b']['tail_sha16']))
    se = parts0.get('system_ext_b') or parts4.get('system_ext_b')
    if se:
        log('system_ext_b geometry: lba=%d sectors=%d size=%d B'
            % (se['lba'], se['sectors'], se['sectors'] * 4096))
        RES['system_ext_b_geom'] = se

    json.dump(RES, open(os.path.join(OUT, 'precheck_%s.json' % STAMP), 'w'), indent=1)
    log('=== DONE. device left in firehose (no reset). artifacts:', OUT)
    return 0


if __name__ == '__main__':
    try:
        rc = main()
    finally:
        _lf.close()
    print('EXIT', rc)
    sys.exit(rc)
