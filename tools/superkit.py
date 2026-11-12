#!/usr/bin/env python3
"""superkit.py - inspect / verify / assemble Android Logical Partition (LP) super images.

Native Windows IO (no WSL 9p bottleneck). Subcommands:
  regions  --lpdump <txt> --size <bytes> --out <json>
  audit    --file <img> [--regions <json>] --out <json> [--lp]
  build    --src <img> --dst <img> --regions <json> --patch name=path[,...] --out <json>
  compare  --a <json> --b <json> [--ignore name,name] [--out json]
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

BLOCK = 512
BUF = 8 * 1024 * 1024          # 8 MiB IO buffer
GIB = 1 << 30
LP_SIZE = 21474836480
EXPECT_FIRST64K = 'fc0163625355ffd46479d9a6c671187a3879954d43cb3c2cf46407dc3b68c573'

LAYOUT_RE = re.compile(r'^super:\s+(\d+)\s+\.\.\s+(\d+):\s+(\S+)\s+\((\d+) sectors\)$')


def log(msg):
    print(msg, flush=True)


class Progress:
    def __init__(self, label, total):
        self.label = label
        self.total = total
        self.done = 0
        self.t0 = time.time()
        self.next_report = GIB

    def add(self, n):
        self.done += n
        if self.done >= self.next_report or self.done >= self.total:
            el = time.time() - self.t0
            rate = self.done / el / (1 << 20) if el > 0 else 0.0
            log('  %s: %.2f/%.2f GiB  %.0f MB/s  %.1fs'
                % (self.label, self.done / GIB, self.total / GIB, rate, el))
            while self.next_report <= self.done:
                self.next_report += GIB


def read_layout(lpdump_path):
    parts = []
    with open(lpdump_path, 'r', encoding='utf-8', errors='replace') as f:
        for ln in f:
            m = LAYOUT_RE.match(ln.strip())
            if not m:
                continue
            start, end, name, nsect = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
            parts.append({'name': name, 'start_sector': start, 'end_sector': end, 'sectors': nsect})
    if not parts:
        raise SystemExit('ERROR: no "super: a .. b: name (n sectors)" layout lines in %s' % lpdump_path)
    parts.sort(key=lambda p: p['start_sector'])
    for p in parts:
        if p['end_sector'] - p['start_sector'] != p['sectors']:
            raise SystemExit('ERROR: inconsistent sectors for %s' % p['name'])
    return parts


def build_regions(parts, total_size):
    regions = []
    pos = 0
    for p in parts:
        start_b = p['start_sector'] * BLOCK
        end_b = p['end_sector'] * BLOCK
        if start_b < pos:
            raise SystemExit('ERROR: overlapping partition %s' % p['name'])
        if start_b > pos:
            regions.append({'name': 'header' if pos == 0 else ('gap_at_%d' % pos),
                            'offset': pos, 'length': start_b - pos, 'kind': 'gap'})
        regions.append({'name': p['name'], 'offset': start_b, 'length': end_b - start_b,
                        'kind': 'partition', 'start_sector': p['start_sector'],
                        'sectors': p['sectors']})
        pos = end_b
    if pos < total_size:
        regions.append({'name': 'tail', 'offset': pos, 'length': total_size - pos, 'kind': 'gap'})
    if pos > total_size:
        raise SystemExit('ERROR: layout exceeds file size')
    total = sum(r['length'] for r in regions)
    if total != total_size:
        raise SystemExit('ERROR: region coverage %d != file size %d' % (total, total_size))
    return regions


def cmd_regions(args):
    parts = read_layout(args.lpdump)
    regions = build_regions(parts, args.size)
    out = {'lpdump': args.lpdump, 'size': args.size, 'regions': regions}
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    log('regions: %d regions, coverage %d bytes (%.2f GiB) -> %s'
        % (len(regions), args.size, args.size / GIB, args.out))
    for r in regions:
        log('  %-18s off=%12d len=%12d %s' % (r['name'], r['offset'], r['length'],
                                             ('sectors=%d' % r['sectors']) if 'sectors' in r else ''))


def sha256_region(path, offset, length):
    h = hashlib.sha256()
    with open(path, 'rb', buffering=0) as f:
        f.seek(offset)
        left = length
        while left > 0:
            chunk = f.read(min(BUF, left))
            if not chunk:
                raise SystemExit('ERROR: short read in %s at %d' % (path, offset + length - left))
            h.update(chunk)
            left -= len(chunk)
    return h.hexdigest()


def cmd_audit_threaded(args, size, regions):
    """Full-file sha256 on the main thread while region hashes run in a thread pool."""
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [ex.submit(sha256_region, args.file, r['offset'], r['length']) for r in regions]
        h_full = hashlib.sha256()
        prog = Progress('full-sha', size)
        with open(args.file, 'rb', buffering=0) as f:
            pos = 0
            while True:
                buf = f.read(BUF)
                if not buf:
                    break
                h_full.update(buf)
                pos += len(buf)
                prog.add(len(buf))
        if pos != size:
            raise SystemExit('ERROR: read %d != size %d' % (pos, size))
        for r, fut in zip(regions, futs):
            r['sha256'] = fut.result()
    return h_full.hexdigest(), time.time() - t0


def cmd_audit(args):
    path = args.file
    size = os.path.getsize(path)
    regions = []
    if args.regions:
        regions = json.load(open(args.regions, encoding='utf-8'))['regions']
        cov = sum(r['length'] for r in regions)
        if cov != size:
            raise SystemExit('ERROR: regions coverage %d != file size %d' % (cov, size))
        if args.parallel_regions:
            full_sha, el = cmd_audit_threaded(args, size, regions)
            res = {'file': path, 'size': size, 'elapsed_s': round(el, 2),
                   'full_sha256': full_sha,
                   'regions': [{'name': r['name'], 'offset': r['offset'],
                                'length': r['length'], 'sha256': r['sha256']} for r in regions]}
            if args.lp and size >= 208896 + 196608:
                res['lp_meta'] = {
                    'first_64KiB_sha256': sha256_region(path, 0, 65536),
                    'primary_208896_sha256': sha256_region(path, 0, 208896),
                    'backup_196608_sha256': sha256_region(path, size - 196608, 196608),
                }
            with open(args.out, 'w', encoding='utf-8') as f:
                json.dump(res, f, indent=1)
            log('audit %s: size=%d (%.2f GiB) elapsed=%.2fs sha256=%s'
                % (os.path.basename(path), size, size / GIB, el, res['full_sha256']))
            if 'lp_meta' in res:
                for k, v in res['lp_meta'].items():
                    log('  LP %s = %s' % (k, v))
                if res['lp_meta']['first_64KiB_sha256'] != EXPECT_FIRST64K:
                    log('  WARNING: LP first64KiB sha256 != expected stock %s' % EXPECT_FIRST64K)
            log('  -> %s' % args.out)
            return
        for r in regions:
            r['_h'] = hashlib.sha256()
    h_full = hashlib.sha256()
    idx = 0
    pos = 0
    prog = Progress(os.path.basename(path), size)
    t0 = time.time()
    with open(path, 'rb', buffering=0) as f:
        while True:
            buf = f.read(BUF)
            if not buf:
                break
            n = len(buf)
            h_full.update(buf)
            if regions:
                m = 0
                while m < n:
                    r = regions[idx]
                    r_end = r['offset'] + r['length']
                    take = min(n - m, r_end - (pos + m))
                    r['_h'].update(buf[m:m + take])
                    m += take
                    if pos + m >= r_end:
                        idx += 1
                        if idx >= len(regions) and pos + m < size:
                            raise SystemExit('ERROR: region table exhausted early')
            pos += n
            prog.add(n)
    if pos != size:
        raise SystemExit('ERROR: read %d != size %d' % (pos, size))
    el = time.time() - t0
    res = {'file': path, 'size': size, 'elapsed_s': round(el, 2),
           'full_sha256': h_full.hexdigest(), 'regions': []}
    for r in regions:
        res['regions'].append({'name': r['name'], 'offset': r['offset'], 'length': r['length'],
                               'sha256': r['_h'].hexdigest()})
    if args.lp and size >= 208896 + 196608:
        res['lp_meta'] = {
            'first_64KiB_sha256': sha256_region(path, 0, 65536),
            'primary_208896_sha256': sha256_region(path, 0, 208896),
            'backup_196608_sha256': sha256_region(path, size - 196608, 196608),
        }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    log('audit %s: size=%d (%.2f GiB) elapsed=%.2fs sha256=%s'
        % (os.path.basename(path), size, size / GIB, el, res['full_sha256']))
    if 'lp_meta' in res:
        for k, v in res['lp_meta'].items():
            log('  LP %s = %s' % (k, v))
        if res['lp_meta']['first_64KiB_sha256'] != EXPECT_FIRST64K:
            log('  WARNING: LP first64KiB sha256 != expected stock %s' % EXPECT_FIRST64K)
    log('  -> %s' % args.out)


def write_zeros(fo, n):
    zero = bytes(min(BUF, max(n, 1)))
    while n > 0:
        k = min(n, len(zero))
        fo.write(zero[:k])
        n -= k


def copy_n(fin, fout, n, prog):
    left = n
    while left > 0:
        chunk = fin.read(min(BUF, left))
        if not chunk:
            raise SystemExit('ERROR: unexpected EOF in source')
        fout.write(chunk)
        left -= len(chunk)
        prog.add(len(chunk))


def cmd_build(args):
    regions = json.load(open(args.regions, encoding='utf-8'))['regions']
    region_map = {r['name']: r for r in regions}
    patches = []
    for spec in args.patch.split(','):
        if not spec.strip():
            continue
        name, ppath = spec.split('=', 1)
        name = name.strip()
        if name not in region_map:
            raise SystemExit('ERROR: unknown region %r' % name)
        r = region_map[name]
        psize = os.path.getsize(ppath)
        patches.append({'name': name, 'offset': r['offset'], 'length': r['length'],
                        'source': ppath, 'source_size': psize})
    patches.sort(key=lambda p: p['offset'])
    total = os.path.getsize(args.src)
    prev_end = 0
    for p in patches:
        if p['offset'] < prev_end:
            raise SystemExit('ERROR: overlapping patch regions')
        prev_end = p['offset'] + p['length']
    free = None
    try:
        st = os.statvfs(args.dst) if hasattr(os, 'statvfs') else None
    except Exception:
        st = None
    log('build: %s -> %s  total=%.2f GiB  patches=%s'
        % (os.path.basename(args.src), os.path.basename(args.dst), total / GIB,
           [(p['name'], p['source_size'], p['length']) for p in patches]))
    prog = Progress('build', total)
    t0 = time.time()
    with open(args.src, 'rb', buffering=0) as fi, open(args.dst, 'wb', buffering=0) as fo:
        pos = 0
        for p in patches:
            copy_n(fi, fo, p['offset'] - pos, prog)
            pos = p['offset']
            pwrite = 0
            zero_pad = 0
            with open(p['source'], 'rb', buffering=0) as fp:
                left = p['length']
                while left > 0:
                    chunk = fp.read(min(BUF, left))
                    if not chunk:
                        break
                    fo.write(chunk)
                    left -= len(chunk)
                    pwrite += len(chunk)
                if left > 0:
                    write_zeros(fo, left)
                    zero_pad = left
            p['bytes_from_source'] = pwrite
            p['zero_padded_bytes'] = zero_pad
            p['truncated_source_bytes'] = p['source_size'] - pwrite
            p['action'] = ('exact' if pwrite == p['length'] else
                           ('padded' if zero_pad else 'truncated'))
            prog.add(p['length'])
            pos += p['length']
            # Skip the patched range in the source as well; otherwise every
            # subsequent copy would be shifted by the patch length (bug fixed
            # in v2 of this script).
            if fi.tell() != p['offset'] + p['length']:
                fi.seek(p['offset'] + p['length'])
            log('  patch %-16s off=%12d len=%12d source=%12d bytes -> %s (pad=%d, trunc=%d); src_pos=%d'
                % (p['name'], p['offset'], p['length'], p['source_size'],
                   p['action'], zero_pad, p['truncated_source_bytes'], fi.tell()))
        copy_n(fi, fo, total - pos, prog)
        fo.flush()
        os.fsync(fo.fileno())
    dsize = os.path.getsize(args.dst)
    el = time.time() - t0
    if dsize != total:
        raise SystemExit('ERROR: dst size %d != src size %d' % (dsize, total))
    res = {'src': args.src, 'dst': args.dst, 'size': dsize,
           'elapsed_s': round(el, 2), 'patches': patches}
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    log('build done: %s size=%d (%.2f GiB) in %.1fs' % (args.dst, dsize, dsize / GIB, el))


def cmd_compare(args):
    a = json.load(open(args.a, encoding='utf-8'))
    b = json.load(open(args.b, encoding='utf-8'))
    ignore = set(x.strip() for x in (args.ignore or '').split(',') if x.strip())
    ra = {r['name']: r for r in a.get('regions', [])}
    rb = {r['name']: r for r in b.get('regions', [])}
    res = {'a': a['file'], 'b': b['file'],
           'size_a': a['size'], 'size_b': b['size'],
           'full_sha_a': a['full_sha256'], 'full_sha_b': b['full_sha256'],
           'full_sha_match': a['full_sha256'] == b['full_sha256'],
           'regions': [], 'matches': 0, 'diffs': 0, 'ignored': sorted(ignore)}
    for name in sorted(set(ra) | set(rb)):
        if name in ignore:
            continue
        ha = ra.get(name, {}).get('sha256')
        hb = rb.get(name, {}).get('sha256')
        same = ha is not None and ha == hb
        res['regions'].append({'name': name, 'sha_a': ha, 'sha_b': hb, 'match': same})
        if same:
            res['matches'] += 1
        else:
            res['diffs'] += 1
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    log('compare %s vs %s: size %d/%d, full_sha_match=%s, regions match=%d diff=%d ignored=%s'
        % (os.path.basename(a['file']), os.path.basename(b['file']),
           a['size'], b['size'], res['full_sha_match'], res['matches'], res['diffs'],
           res['ignored']))
    for r in res['regions']:
        if not r['match']:
            log('  DIFF region %-18s a=%s b=%s'
                % (r['name'], (r['sha_a'] or '')[:16], (r['sha_b'] or '')[:16]))
    log('  -> %s' % args.out)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('regions')
    p.add_argument('--lpdump', required=True)
    p.add_argument('--size', type=int, required=True)
    p.add_argument('--out', required=True)
    p.set_defaults(func=cmd_regions)

    p = sub.add_parser('audit')
    p.add_argument('--file', required=True)
    p.add_argument('--regions', default=None)
    p.add_argument('--out', required=True)
    p.add_argument('--lp', action='store_true')
    p.add_argument('--parallel-regions', action='store_true')
    p.add_argument('--workers', type=int, default=9)
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser('build')
    p.add_argument('--src', required=True)
    p.add_argument('--dst', required=True)
    p.add_argument('--regions', required=True)
    p.add_argument('--patch', required=True)
    p.add_argument('--out', required=True)
    p.set_defaults(func=cmd_build)

    p = sub.add_parser('compare')
    p.add_argument('--a', required=True)
    p.add_argument('--b', required=True)
    p.add_argument('--ignore', default='')
    p.add_argument('--out', required=True)
    p.set_defaults(func=cmd_compare)

    args = ap.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
