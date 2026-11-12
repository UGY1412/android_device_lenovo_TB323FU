#!/usr/bin/env python3
"""boot-doctor-reviewed.py — independent reviewer build of boot-doctor (task-17).

Fixes vs bootfix/boot-doctor.py (see BOOT-DOCTOR-REVIEW.md):
  * classification by NAME first, then magic, then size (logdump fetches are often
    exactly 64 MiB and were misclassified as metadata in the original).
  * supports IL9 (+ IL10/IL11/IL12/IL13); per-boot CURRENT vs STALE split for IL12.
  * metadata dumps (LOGDUMP3/AERA_DMESG) are graded on their own ("PRE-F0 diag"),
    and NEVER pollute the boot-stage verdict.
  * F0 effectiveness is a first-class verdict (logdump.sh exec/avc evidence in the
    current-boot log; stale LOGDUMP3 in metadata only => "stale pre-F0 artifact").
  * boot_completed is matched with a strict regex; indirect success is reported
    from the misc ctl (uptime/stage) when the capture is truncated.
  * zygote/system_server: counts + "received before Sending => Reap cleanup"
    ordering check + 5 s periodicity detection (from kmsg timestamps).
  * init_user0 chain: vdc/mkdir/user_keys/reboot_into_recovery/Reason patterns.
  * directory mode reports one table row per file and only combines dumps that
    belong to the same capture set (by filename signature), never mixes boots.
"""
import glob
import json
import os
import re
import struct
import sys

PRINTABLE = set(range(32, 127)) | {9, 10, 13}
CTL, MAGIC_OFF, LOG = 0x80000, 0x80004, 0x81000
LOG_CAP = 520192
MAGICS = (b'IL9\0', b'IL10', b'IL11', b'IL12', b'IL13')

SDA10 = 'F2FS-fs (sda10)'          # metadata (GPT LUN0 mapping)
SDA14 = 'F2FS-fs (sda14)'          # userdata
KMSG_REC = re.compile(r'(\d{1,2}),(\d{1,6}),(\d{6,9}),[-c],caller=(T\d+);')


def to_text(b):
    return ''.join(chr(x) if x in PRINTABLE else ('\n' if x == 0 else ' ') for x in b)


def grep(text, pat, limit=5):
    out = [ln.strip() for ln in text.split('\n') if pat in ln]
    return out[:limit]


def strip_records(text):
    """Return list of (ts_us or None, message) when text contains kmsg records."""
    out = []
    for m in KMSG_REC.finditer(text):
        start = m.end()
        nxt = KMSG_REC.search(text, start)
        end = nxt.start() if nxt else len(text)
        out.append((int(m.group(3)), text[start:end].strip('\n')))
    return out


# ---------------------------------------------------------------- misc parsing

def parse_misc(path, data):
    ctr = struct.unpack_from('<I', data, CTL)[0]
    magic = data[MAGIC_OFF:MAGIC_OFF + 4]
    u = struct.unpack_from('<8I', data, CTL)
    stage, ticks, f16, f20, f24, f28 = u[2], u[3], u[4], u[5], u[6], u[7]
    r = dict(file=os.path.basename(path), kind='misc', counter=ctr,
             magic=magic.decode('latin1').rstrip('\0'), stage=stage, ticks=ticks,
             f16=f16, f20=f20, f24=f24, f28=f28, text='', stale_text='',
             uptime_s=None, note='', capture_quality='')
    if magic in (b'IL10', b'IL11'):
        written = f16 or f20
        written = min(written, LOG_CAP)
        r['text'] = to_text(data[LOG:LOG + written])
        r['written'] = written
        r['uptime_s'] = f24 if 0 < f24 < 10 ** 6 else (ticks // 100)
        r['note'] = f'IL{magic[2:].decode()}: streamed current-boot log = first {written} B of 0x81000 area'
    elif magic == b'IL9\0':
        written = max(f16, f20)
        written = min(written, LOG_CAP)
        r['text'] = to_text(data[LOG:LOG + written])
        r['written'] = written
        r['note'] = f'IL9 (legacy): heuristic log = first {written} B'
    elif magic == b'IL12':
        snap = min(f16, LOG_CAP)
        r['text'] = to_text(data[LOG:LOG + snap])
        r['stale_text'] = to_text(data[LOG + snap:LOG + LOG_CAP])
        r['uptime_s'] = f24
        r['note'] = f'IL12 current-boot snapshot = first {snap} B (rest={LOG_CAP-snap} B is STALE from a previous boot)'
    elif magic == b'IL13':
        r['uptime_s'] = f24
        r['note'] = (f'IL13: misc ctl only (written={f16} read={f20} uptime={f24}s wraps={f28}); '
                     'kmsg is streamed to the logdump partition')
    else:
        r['note'] = f'unknown misc magic {magic!r}'
    # capture quality: for streamed logs, full buffer means early truncation
    written = r.get('written')
    if written is not None and written >= LOG_CAP:
        r['capture_quality'] = 'misc 508 KiB log area FULL (userspace logs likely truncated)'
    return r


# ---------------------------------------------------------------- logdump parsing

def parse_logdump(path, data):
    r = dict(file=os.path.basename(path), kind='logdump', text='', markers=[], note='')
    last = max((i for i, b in enumerate(data) if b), default=-1)
    r['last_nonzero'] = last
    if last < 0:
        r['all_zero'] = True
        r['note'] = 'logdump partition is ALL ZEROS -> capture never ran'
        return r
    txt = to_text(data[:last + 1])
    hdrs = [
        ('INITLOG13', re.compile(r'==== INITLOG13[^\n]*')),
        ('AERA_LOGCAT2', re.compile(r'==== AERA_LOGCAT2_BEGIN[^\n]*')),
        ('AERA_DIAG', re.compile(r'==== AERA_DIAG_BEGIN[^\n]*')),
        ('AERA_LOGCAT', re.compile(r'==== AERA_LOGCAT_BEGIN[^\n]*')),
    ]
    for name, rx in hdrs:
        for m in rx.finditer(txt):
            r['markers'].append(dict(name=name, header=txt[m.start():m.start() + 160].split('\n')[0]))
    if r['markers']:
        first = min(r['markers'], key=lambda x: txt.find(x['header']))
        start = txt.find('\n', txt.find(first['header'])) + 1
        r['text'] = txt[start:]
        r['note'] = f"capture format={first['name']}; text starts after header"
    else:
        r['text'] = txt
        r['note'] = 'no known capture header; decoding whole region as text'
    return r


# ---------------------------------------------------------------- metadata parsing

def parse_metadata(path, data):
    r = dict(file=os.path.basename(path), kind='metadata', text='', note='',
             logdump3_markers=[], aera_dmesg_markers=0)
    l3 = [m.start() for m in re.finditer(rb'==== LOGDUMP3', data)]
    r['logdump3_markers'] = len(l3)
    r['aera_dmesg_markers'] = len(re.findall(rb'AERA_DMESG', data))
    if l3:
        s = l3[-1]
        end = s
        for e in range(s, min(len(data), s + 2 * 1024 * 1024)):
            if data[e] in PRINTABLE:
                end = e
            elif e - end > 64:
                break
        block = to_text(data[s:end + 1])
        r['text'] = block
        m = re.search(r'LOGDUMP3 mode=(\w+).*?uptime=([\d.]+)\s+([\d.]+)', block)
        r['note'] = (f'f2fs metadata dump: {len(l3)} LOGDUMP3 raw-snapshot markers; last block uptime='
                     f'{m.group(2) if m else "?"}s -> written by logdump.sh (pre-F0 diagnostic artifact)')
    elif r['aera_dmesg_markers']:
        r['note'] = f'f2fs metadata dump: {r["aera_dmesg_markers"]} AERA_DMESG markers'
    else:
        r['note'] = 'f2fs metadata dump: no LOGDUMP3/AERA_DMESG markers (empty or post-F0 clean)'
    return r


# ---------------------------------------------------------------- rules

def analyze(text):
    f = {}
    cnt = text.count
    has = lambda p: p in text
    # S0 first stage
    f['s0_first_stage_started'] = has('init first stage started')
    f['s0_dm_mounts'] = cnt('EXT4-fs (dm-')
    f['s0_ext4_mounted'] = cnt('mounted filesystem')
    f['s0_first_stage_fatal'] = has('Failed to mount required partitions')
    f['s0_avb_missing'] = len(re.findall(r'Device path not found: /dev/block/by-name/\S+', text))
    f['s0_libfs_avb'] = cnt('libfs_avb')
    f['s0_other_mount_fail'] = cnt('Failed to mount /system') + cnt('ELOOP') + cnt('fs_mgr_create_canonical_mount_point')
    f['s0_selinux_open'] = has('Opening SELinux policy')
    f['s0_selinux_compile'] = has('Compiling SELinux policy')
    f['s0_selinux_loaded'] = has('Loading SELinux policy')
    # S1 data / metadata / FBE
    f['s1_metadata_mounted_sda10'] = cnt(SDA10)
    f['s1_metadata_checkpoint'] = len(re.findall(r'F2FS-fs \(sda10\): Mounted with checkpoint version', text))
    f['s1_userdata_mounted_sda14'] = cnt(SDA14)
    f['s1_metadata_ro_error'] = has('Failed to create /metadata/vold: Read-only file system')
    f['s1_read_key_failed'] = has('read_key failed in mountFstab')
    f['s1_encryptfstab_failed'] = has('cryptfs encryptFstab') and has('Failed')
    f['s1_make_f2fs'] = cnt('make_f2fs')
    f['s1_init_user0_failed'] = has('cryptfs init_user0 Failed') or has('init_user0_failed')
    f['s1_user_keys_missing'] = (has('Failed to mkdir(/data/misc/vold/user_keys)')
                                 or has('Failed to prepare /data/misc/vold/user_keys'))
    f['s1_vdc_call_failed'] = has('vdc call failed with error code')
    f['s1_mount_all_failed'] = has('queue_fs_event() failed')
    f['s1_reboot_recovery'] = has('reboot_into_recovery') or has('Reason: init_user0_failed')
    f['s1_fbe_on'] = has('fileencryption') or has('wrappedkey') or has('metadata_encryption')
    # S2 zygote / system_server
    zyg = [ln for ln in text.split('\n') if "starting service 'zygote'" in ln]
    f['s2_zygote_starts'] = len(zyg)
    f['s2_received_sigkill'] = cnt('received SIGKILL')
    f['s2_sending_sigkill_zygote'] = cnt("Sending SIGKILL to service 'zygote'")
    f['s2_exit_zygote_ss'] = cnt('Exit zygote because system server')
    f['s2_fatal_exception_system'] = cnt('FATAL EXCEPTION IN SYSTEM PROCESS')
    f['s2_watchdog'] = cnt('WATCHDOG KILLING SYSTEM PROCESS')
    f['s2_updatable_crashing'] = cnt('updatable_crashing')
    f['s2_flags_health'] = cnt('flags_health_check')
    f['s2_lmkd_oom'] = cnt('lmkd') + cnt('lowmemorykiller') + cnt('Killed process')
    f['s2_system_server_mentions'] = cnt('sid=u:r:system_server')
    # ordering: received SIGKILL followed immediately by Sending SIGKILL to zygote => Reap cleanup
    order_ok = 0
    lines = [ln for ln in text.split('\n') if ln.strip()]
    for i, ln in enumerate(lines[:-1]):
        if "Service 'zygote'" in ln and 'received SIGKILL' in ln and "Sending SIGKILL to service 'zygote'" in lines[i + 1]:
            order_ok += 1
    f['s2_reap_cleanup_pairs'] = order_ok
    # 5 s periodicity from kmsg timestamps
    recs = strip_records(text)
    zts = [ts for ts, msg in recs if "starting service 'zygote'" in msg]
    intervals = [round((b - a) / 1e6, 2) for a, b in zip(zts, zts[1:])]
    f['s2_zygote_intervals_s'] = intervals[:10]
    periodic = [x for x in intervals if 4.5 <= x <= 5.6]
    f['s2_zygote_periodic_5s'] = len(periodic)
    # S3 success
    f['s3_boot_completed'] = bool(re.search(r'sys\.boot_completed[=:\s]+1(?:\D|$)', text))
    f['s3_boot_completed_any'] = cnt('sys.boot_completed')
    f['s3_launcher'] = cnt('Launcher') + cnt('launcher')
    # F0 / capture
    f['f0_logdump_sh_refs'] = cnt('logdump.sh')
    f['f0_logdump_exec_service'] = len(re.findall(r"starting service 'exec [^']*\(/system/bin/logdump\.sh", text))
    f['f0_logdump_avc'] = len(re.findall(r'path="/system/bin/logdump\.sh"', text))
    f['f0_logdump3'] = cnt('LOGDUMP3')
    f['cap_initlog13'] = cnt('==== INITLOG13')
    f['cap_aera_header'] = cnt('AERA_LOGCAT_BEGIN') + cnt('AERA_LOGCAT2_BEGIN') + cnt('AERA_DIAG_BEGIN')
    f['cap_logcat_invalid'] = cnt('Invalid -v')
    f['cap_logcat_lines'] = len([ln for ln in text.split('\n') if re.match(r'^\d\d-\d\d ', ln)])
    return f


def verdict(f, misc_ctl=None, has_bootstage=False):
    A = []
    # capture-health first
    if f['cap_logcat_invalid']:
        return ('CAPTURE-FAILED',
                'logcat capture started but logcat rejected its args ("Invalid -v ...")',
                ['fix capture script: use "-v threadtime" only + wait for logd.ready; or use initlog13 kmsg->logdump.'])
    if not has_bootstage and f['cap_aera_header'] and f['f0_logdump3'] == 0:
        return ('CAPTURE-FAILED', 'AERA logcat header present but no boot-stage lines captured',
                ['check logcat args / logd.ready; capture again.'])
    # first-stage
    if f['s0_first_stage_fatal'] or (f['s0_first_stage_started'] and f['s0_dm_mounts'] == 0
                                    and (f['s0_avb_missing'] or f['s0_other_mount_fail'])):
        if f['s0_avb_missing']:
            A.append('libfs_avb "Device path not found" => first-stage fstab has avb flags while '
                     '/dev/block/by-name/<vbmeta> is unavailable; verify the flashed vendor_boot sha '
                     '(diag2/5/6 have avb removed) and GPT; see "Failed to mount required partitions".')
        if f['s0_other_mount_fail']:
            A.append('mount failure/ELOOP in first stage (fs_mgr_create_canonical_mount_point / '
                     '"Failed to mount /system"); check fstab of the flashed vendor_boot.')
        return ('S0-first-stage', 'died in first-stage mount', A)
    # metadata / init_user0
    if f['s1_metadata_ro_error'] or (f['s1_userdata_mounted_sda14'] and f['s1_metadata_mounted_sda10'] == 0
                                    and (f['s1_init_user0_failed'] or f['s1_read_key_failed'] or f['s1_user_keys_missing'])):
        A.append('metadata (/metadata, sda10) NOT mounted while userdata (sda14) is mounted: '
                 'vold /metadata/vold creation fails, metadata-encryption key unreadable, /data may be '
                 'reformatted, post-fs-data skipped -> init_user0 fails -> recovery.')
        A.append('fix: F0 (no logdump.sh raw dd to metadata) + recovery factory reset to format sda10; '
                 'check metadata with GPT dump (sda10=metadata, sda14=userdata).')
        return ('S1-metadata-missing', 'metadata partition not mounted -> init_user0 chain', A)
    if f['s1_init_user0_failed'] or f['s1_user_keys_missing'] or f['s1_vdc_call_failed']:
        A.append('init_user0 chain failed (FBE vold/keymaster): inspect vold/KeyStorage/KeyMint lines; '
                 'run A (checkpoint) / C (wrappedkey) / D (metadata_encryption) experiments.')
        return ('S1-init_user0-failed', 'init_user0 failed', A)
    # zygote / system_server
    if (f['s2_exit_zygote_ss'] or f['s2_fatal_exception_system'] or f['s2_zygote_starts'] >= 2
            or f['s2_received_sigkill'] >= 2 or f['s2_updatable_crashing']):
        A.append('system_server crashed/restarted -> zygote exit loop (boot-animation hang).')
        if f['s2_reap_cleanup_pairs'] and not f['s2_exit_zygote_ss']:
            A.append(f'{f["s2_reap_cleanup_pairs"]}x "received SIGKILL" followed by "Sending SIGKILL to '
                     'service \'zygote\'": init reaps/cleans; the ORIGINAL kill is not in kmsg '
                     '("Exit zygote because system server" / crash stack are logcat-only).')
        if f['s2_zygote_periodic_5s'] >= 2:
            A.append(f'zygote restarts every ~5 s ({f["s2_zygote_intervals_s"]}): '
                     '== system_server dies + zygote self-kills + init default 5 s restart (init restart_period).')
        A.append('capture logcat (crash buffer) and grep "FATAL EXCEPTION IN SYSTEM PROCESS" / '
                 '"Exit zygote because system server"; check H1 VINTF/H2 keystore2-keymint hypotheses.')
        return ('S2-system_server', 'system_server crash loop (zygote restart)', A)
    # success
    if f['s3_boot_completed']:
        A.append('sys.boot_completed=1 observed; verify F0 reboot survival x3 and metadata sda10 line each boot.')
        return ('S3-success', 'boot completed / desktop reached', A)
    if misc_ctl and misc_ctl.get('uptime_s') and misc_ctl['uptime_s'] >= 120 and f['s2_zygote_starts'] == 0:
        A.append(f'misc ctl says wrapper ran {misc_ctl["uptime_s"]}s (stage={misc_ctl.get("stage")}) '
                 'while the captured log is truncated early -> INDIRECT evidence the device stayed up.')
        A.append('not a failure; capture late stage (initlog13 / logcat->rawdump) for direct proof.')
        return ('S3-indirect (device alive {0}s, capture truncated)'.format(misc_ctl['uptime_s']),
                'boot likely succeeded but the dump ends before userspace', A)
    if f['s0_first_stage_started'] and f['s0_dm_mounts'] > 0 and (f['s0_selinux_open'] or f['s1_metadata_mounted_sda10']):
        A.append('first-stage mounts + selinux/metadata look healthy; capture ends before zygote/system_server '
                 '(typical initlog10 508 KiB overflow or early snapshot). Use initlog13/logcat to get late stage.')
        return ('UPTO-S1-OK (log truncated)', 'no failure found up to S1, late stage not captured', A)
    A.append('capture again with initlog13 (kmsg->logdump) and logcat->rawdump; keep device powered 60-120 s.')
    return ('indeterminate', 'insufficient evidence (truncated/early capture)', A)


# ---------------------------------------------------------------- main

def main():
    argv = sys.argv[1:]
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2
    target = argv[0]
    tag = 'bootdoctor'
    if '--tag' in argv:
        tag = argv[argv.index('--tag') + 1]
    outdir = None
    if '--out' in argv:
        outdir = argv[argv.index('--out') + 1]
    files = sorted(glob.glob(os.path.join(target, '*.bin'))) if os.path.isdir(target) else [target]
    if not files:
        print('no candidate files in', target)
        return 3
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    else:
        outdir = target if os.path.isdir(target) else (os.path.dirname(target) or '.')

    rows, parsed, boot_texts, meta_rows = [], [], [], []
    for p in files:
        data = open(p, 'rb').read()
        name = os.path.basename(p).lower()
        if 'misc' in name or (len(data) >= LOG + 0x100 and data[MAGIC_OFF:MAGIC_OFF + 4] in MAGICS):
            r = parse_misc(p, data)
            kind = 'misc'
        elif 'metadata' in name:
            r = parse_metadata(p, data)
            kind = 'metadata'
        elif 'logdump' in name:
            r = parse_logdump(p, data)
            kind = 'logdump'
        elif len(data) == (64 << 20):
            r = parse_metadata(p, data); kind = 'metadata'
        elif len(data) == (1 << 20):
            r = parse_misc(p, data); kind = 'misc'
        else:
            r = parse_logdump(p, data); kind = 'logdump'
        r['kind'] = kind
        parsed.append(r)
        if kind == 'misc':
            boot_texts.append((r['file'], r.get('text', ''), r))
        elif kind == 'logdump' and not r.get('markers'):
            pass  # unknown text: still allow analysis (could be kmsg)
        elif kind == 'logdump':
            boot_texts.append((r['file'], r.get('text', ''), r))
        elif kind == 'metadata':
            meta_rows.append(r)

    # per-file verdict table
    for r in parsed:
        if r['kind'] == 'misc':
            f = analyze(r.get('text', ''))
            stage, head, acts = verdict(f, misc_ctl=r)
            rows.append(dict(file=r['file'], kind='misc', ctl={'counter': r.get('counter'), 'magic': r.get('magic'),
                            'stage': r.get('stage'), 'ticks': r.get('ticks'), 'uptime_s': r.get('uptime_s'),
                            'f16': r.get('f16'), 'f20': r.get('f20'), 'f28': r.get('f28')},
                            stage=stage, headline=head, actions=acts, findings={k: v for k, v in f.items() if v}))
            st = (r.get('stale_text') or '').strip()
            if st:
                fs = analyze(st)
                s2, h2, a2 = verdict(fs)
                rows.append(dict(file=r['file'], kind='misc-STALE', stage=f'STALE-PREV-BOOT / {s2}',
                                 headline=f'previous boot (STALE segment only, NOT this boot): {h2}',
                                 actions=['stale segment exists -> do NOT confuse with the current boot. It is still '
                                          'useful: it records how the previous boot failed.'] + list(a2),
                                 findings={k: v for k, v in fs.items() if v}))
        elif r['kind'] == 'logdump':
            if r.get('all_zero'):
                rows.append(dict(file=r['file'], kind='logdump', stage='CAPTURE-NOT-RUN',
                                 headline='logdump partition all zeros - capture never ran', findings={}))
                continue
            f = analyze(r.get('text', ''))
            has_stage = f['s0_first_stage_started'] or f['cap_initlog13'] or f['s2_zygote_starts']
            stage, head, acts = verdict(f, has_bootstage=has_stage)
            rows.append(dict(file=r['file'], kind='logdump', stage=stage, headline=head,
                             actions=acts, findings={k: v for k, v in f.items() if v}))
        else:  # metadata
            f = analyze(r.get('text', ''))
            if r.get('logdump3_markers'):
                acts = ['metadata still contains LOGDUMP3 raw snapshots => logdump.sh was ACTIVE on some '
                        'pre-F0 boot (PROOF F0 is not effective for that build); the embedded dmesg is a '
                        'snapshot at uptime<=12 s and cannot be used as a current-boot verdict.',
                        'after F0: bump the boot, then re-dump metadata; LOGDUMP3 must NOT be refreshed '
                        '(only stale raw offsets may remain) and the kmsg must not contain logdump.sh exec/avc lines.']
                rows.append(dict(file=r['file'], kind='metadata', stage='PRE-F0-DIAG',
                                 headline='metadata dump contains LOGDUMP3 (logdump.sh was active / pre-F0)',
                                 actions=acts, findings={'logdump3_markers': r['logdump3_markers'],
                                                         'aera_dmesg_markers': r['aera_dmesg_markers']}))
            else:
                rows.append(dict(file=r['file'], kind='metadata', stage='METADATA-CAPTURE',
                                 headline='no LOGDUMP3/AERA_DMESG markers (clean or post-F0)',
                                 findings={'logdump3_markers': 0, 'aera_dmesg_markers': r['aera_dmesg_markers']}))

    # print
    lines = ['=== dumps ===']
    for r in parsed:
        lines.append(f'- {r["file"]}: kind={r["kind"]} bytes={len(open(os.path.join(os.path.dirname(files[0]), r["file"]), "rb").read()) if False else "?"} note={r.get("note","")}')
    lines = ['=== dumps ===']
    for r in parsed:
        lines.append(f'- {r["file"]}: kind={r["kind"]} note={r.get("note", "")}')
    lines.append('')
    lines.append('=== per-file verdicts ===')
    for row in rows:
        lines.append(f'[{row["kind"]}] {row["file"]}')
        if row.get('ctl'):
            lines.append(f'    ctl: {row["ctl"]}')
        lines.append(f'    VERDICT: {row["stage"]} — {row["headline"]}')
        for a in row.get('actions', []):
            lines.append(f'      -> {a}')
        for k, v in sorted(row.get('findings', {}).items()):
            lines.append(f'      | {k} = {v}')
    # combined verdict only for boot logs (misc+logdump), metadata excluded
    combined = '\n'.join(t for _, t, _ in boot_texts)
    if combined.strip():
        f = analyze(combined)
        stage, head, acts = verdict(f)
        lines.append('')
        lines.append('=== COMBINED (boot logs only; metadata excluded) ===')
        lines.append(f'VERDICT: {stage} — {head}')
        for a in acts:
            lines.append(f'  -> {a}')
    txt_out = os.path.join(outdir, f'{tag}_reviewed_boot_doctor.txt')
    json_out = os.path.join(outdir, f'{tag}_reviewed_boot_doctor.json')
    txt = '\n'.join(lines)
    open(txt_out, 'w', encoding='utf-8', errors='replace').write(txt)
    json.dump({'rows': [{k: v for k, v in row.items()} for row in rows]},
              open(json_out, 'w', encoding='utf-8'), indent=2, ensure_ascii=False, default=str)
    print(txt)
    print(f'\nwritten: {txt_out}\nwritten: {json_out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
