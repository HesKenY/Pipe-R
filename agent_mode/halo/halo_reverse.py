"""
Halo MCC reverse-engineering indexer.

Catalogs everything observable about a running + installed
Halo MCC — install tree, save files, loaded DLLs, module
list in the live process, memory region summary, and a
histogram of float patterns in executable writable regions.

Goal: find entry points + interesting offsets so we can
later hook / patch in-process.

Outputs a structured report to stdout (JSON) AND a human-
readable report to agent_mode/memories/ken-ai-latest/halo-reverse.md.

Usage:
    python halo_reverse.py                    # full scan
    python halo_reverse.py --quick            # process-only, skip disk walk
    python halo_reverse.py --float-target 1.0 # scan for specific float

Requires admin for memory scans. Disk walk works unprivileged.
"""

import sys
import os
import json
import struct
import ctypes
import argparse
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

# Process flags
PROCESS_VM_READ           = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

MEM_COMMIT             = 0x1000
PAGE_READWRITE         = 0x04
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READONLY          = 0x02

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
psapi    = ctypes.WinDLL('psapi',    use_last_error=True)


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('BaseAddress',       ctypes.c_void_p),
        ('AllocationBase',    ctypes.c_void_p),
        ('AllocationProtect', wintypes.DWORD),
        ('RegionSize',        ctypes.c_size_t),
        ('State',             wintypes.DWORD),
        ('Protect',           wintypes.DWORD),
        ('Type',              wintypes.DWORD),
    ]


class MODULEINFO(ctypes.Structure):
    _fields_ = [
        ('lpBaseOfDll', ctypes.c_void_p),
        ('SizeOfImage', wintypes.DWORD),
        ('EntryPoint',  ctypes.c_void_p),
    ]


# ── Disk walker ──────────────────────────────────────────
INTERESTING_EXT = {
    '.exe', '.dll', '.pak', '.map', '.yaml', '.json', '.xml',
    '.txt', '.log', '.lua', '.cfg', '.ini', '.bin', '.dat',
    '.module', '.tags', '.cache',
}

def find_mcc_install():
    candidates = [
        'C:\\Program Files (x86)\\Steam\\steamapps\\common\\Halo The Master Chief Collection',
        'D:\\SteamLibrary\\steamapps\\common\\Halo The Master Chief Collection',
        'E:\\SteamLibrary\\steamapps\\common\\Halo The Master Chief Collection',
        'C:\\XboxGames\\Halo- The Master Chief Collection',
        'C:\\XboxGames\\Halo-The Master Chief Collection',
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


def walk_install(root, limit=4000):
    """Walk the MCC install tree, catalog interesting files."""
    files = []
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                ext = os.path.splitext(name)[1].lower()
                full = os.path.join(dirpath, name)
                try:
                    st = os.stat(full)
                except Exception:
                    continue
                rec = {
                    'path': full,
                    'size': st.st_size,
                    'ext':  ext,
                    'rel':  os.path.relpath(full, root),
                }
                if ext in INTERESTING_EXT or st.st_size > 100 * 1024 * 1024:
                    rec['interesting'] = True
                files.append(rec)
                if len(files) >= limit:
                    return files
    except Exception as e:
        return files
    return files


# ── Process enumeration ──────────────────────────────────
def find_pid(name_lower='mcc-win64-shipping.exe'):
    arr = (wintypes.DWORD * 2048)()
    cb = wintypes.DWORD(0)
    psapi.EnumProcesses(ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(cb))
    count = cb.value // ctypes.sizeof(wintypes.DWORD)
    for i in range(count):
        pid = arr[i]
        if not pid: continue
        h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not h: continue
        buf = ctypes.create_unicode_buffer(512)
        if psapi.GetModuleBaseNameW(h, None, buf, 512) > 0:
            if buf.value.lower() == name_lower:
                kernel32.CloseHandle(h)
                return pid
        kernel32.CloseHandle(h)
    return None


def enum_modules(h_proc, limit=256):
    """Return list of (name, base, size) for every loaded DLL in
    the target process. This is the ASLR-randomized map — every
    session has different base addresses."""
    needed = wintypes.DWORD(0)
    arr = (ctypes.c_void_p * limit)()
    ok = psapi.EnumProcessModulesEx(h_proc, arr, ctypes.sizeof(arr), ctypes.byref(needed), 0x03)
    if not ok:
        return []
    count = min(limit, needed.value // ctypes.sizeof(ctypes.c_void_p))
    mods = []
    for i in range(count):
        base = arr[i]
        if not base: continue
        name_buf = ctypes.create_unicode_buffer(512)
        psapi.GetModuleBaseNameW(h_proc, ctypes.c_void_p(base), name_buf, 512)
        info = MODULEINFO()
        psapi.GetModuleInformation(h_proc, ctypes.c_void_p(base), ctypes.byref(info), ctypes.sizeof(info))
        mods.append({
            'name': name_buf.value,
            'base': hex(base),
            'size': info.SizeOfImage,
            'entry': hex(info.EntryPoint or 0),
        })
    return mods


def enum_regions(h_proc, cap=10000):
    """Summarize committed memory regions. Useful for spotting
    big RW blocks where game state lives."""
    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0
    regions = []
    while kernel32.VirtualQueryEx(h_proc, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        if mbi.State == MEM_COMMIT:
            regions.append({
                'base': hex(mbi.BaseAddress or 0),
                'size': mbi.RegionSize,
                'protect': hex(mbi.Protect),
                'type': hex(mbi.Type),
                'rw': bool(mbi.Protect & (PAGE_READWRITE | PAGE_EXECUTE_READWRITE)),
            })
            if len(regions) >= cap:
                break
        addr = (mbi.BaseAddress or 0) + mbi.RegionSize
        if addr > (1 << 47):
            break
    return regions


def float_histogram(h_proc, regions, target_floats, max_bytes=128 * 1024 * 1024):
    """Count how often each target float appears in writable
    regions. Capped at max_bytes total bytes scanned."""
    targets = {struct.pack('<f', t): (t, 0) for t in target_floats}
    scanned = 0
    regions_scanned = 0
    # Use mid-sized regions — skip < 4KB (probably stacks/TLS)
    # and > 256MB (textures/heaps). The sweet spot for game
    # state is 64KB-16MB heap blocks.
    rw = [r for r in regions if r['rw'] and 4096 < r['size'] < 256 * 1024 * 1024]
    rw.sort(key=lambda r: r['size'])  # smallest first so we see variety
    for region in rw[:200]:
        base = int(region['base'], 16)
        size = region['size']
        if scanned + size > max_bytes:
            break
        buf = (ctypes.c_ubyte * size)()
        nread = ctypes.c_size_t(0)
        ok = kernel32.ReadProcessMemory(h_proc, ctypes.c_void_p(base), buf, size, ctypes.byref(nread))
        if not ok:
            continue
        raw = bytes(buf[:nread.value])
        for tb, (val, count) in list(targets.items()):
            c = 0
            off = 0
            while True:
                i = raw.find(tb, off)
                if i < 0: break
                c += 1
                off = i + 4
            targets[tb] = (val, count + c)
        scanned += size
        regions_scanned += 1
    return [{'value': v, 'count': c} for (v, c) in targets.values()], scanned, regions_scanned


# ── Main ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true',
                        help='skip disk walk, only process snapshot')
    parser.add_argument('--float-target', type=float, action='append',
                        help='additional float to histogram (repeat)')
    parser.add_argument('--no-memory', action='store_true',
                        help='skip process memory scan')
    args = parser.parse_args()

    report = {
        'at': datetime.now(timezone.utc).isoformat(),
        'install': None,
        'process': None,
    }

    # Disk walk
    if not args.quick:
        install = find_mcc_install()
        report['install_path'] = install
        if install:
            files = walk_install(install)
            report['install'] = {
                'file_count': len(files),
                'total_bytes': sum(f['size'] for f in files),
                'by_ext': {},
                'interesting': [f for f in files if f.get('interesting')][:50],
            }
            for f in files:
                report['install']['by_ext'][f['ext']] = report['install']['by_ext'].get(f['ext'], 0) + 1

    # Process snapshot
    if not args.no_memory:
        pid = find_pid()
        if pid:
            PROCESS_ACCESS = PROCESS_VM_READ | PROCESS_QUERY_INFORMATION
            h = kernel32.OpenProcess(PROCESS_ACCESS, False, pid)
            if h:
                try:
                    mods = enum_modules(h)
                    regions = enum_regions(h)
                    rw_regions = [r for r in regions if r['rw']]
                    process = {
                        'pid': pid,
                        'module_count': len(mods),
                        'modules': mods[:32],
                        'region_count': len(regions),
                        'rw_region_count': len(rw_regions),
                        'total_rw_bytes': sum(r['size'] for r in rw_regions),
                    }
                    # Float histogram — common Halo health values
                    targets = [1.0, 45.0, 100.0, 75.0, 70.0, 0.0, 0.5]
                    if args.float_target:
                        targets.extend(args.float_target)
                    hist, scanned, regions_scanned = float_histogram(h, regions, targets)
                    process['float_histogram'] = {
                        'targets': hist,
                        'bytes_scanned': scanned,
                        'regions_scanned': regions_scanned,
                    }
                    report['process'] = process
                finally:
                    kernel32.CloseHandle(h)
        else:
            report['process'] = {'error': 'MCC-Win64-Shipping.exe not running'}

    # Write human-readable to memory folder
    try:
        mem_dir = Path(__file__).resolve().parent.parent / 'memories' / 'ken-ai-latest'
        mem_dir.mkdir(parents=True, exist_ok=True)
        out_path = mem_dir / 'halo-reverse.md'
        stamp = report['at']
        lines = [f'\n# Halo MCC reverse snapshot — {stamp}\n']
        if report.get('install'):
            ins = report['install']
            lines.append(f"**Install:** {report.get('install_path')}")
            lines.append(f"files: {ins['file_count']}, total: {ins['total_bytes'] // (1024*1024)}MB")
            lines.append('top extensions:')
            top_ext = sorted(ins['by_ext'].items(), key=lambda x: -x[1])[:10]
            for ext, count in top_ext:
                lines.append(f"  {ext or '<none>'}: {count}")
            lines.append('')
        if report.get('process'):
            p = report['process']
            if p.get('error'):
                lines.append(f"**Process:** {p['error']}")
            else:
                lines.append(f"**Process:** pid {p['pid']}, {p['module_count']} modules, {p['rw_region_count']} RW regions, {p['total_rw_bytes'] // (1024*1024)}MB writable")
                lines.append('top modules:')
                for m in p['modules'][:10]:
                    lines.append(f"  {m['name']} @ {m['base']} size={m['size']//1024}KB")
                hist = p.get('float_histogram', {})
                if hist.get('targets'):
                    lines.append('float histogram:')
                    for h in hist['targets']:
                        lines.append(f"  {h['value']}: {h['count']} matches")
                    lines.append(f"  (scanned {hist['bytes_scanned']//(1024*1024)}MB across {hist['regions_scanned']} regions)")
        with open(out_path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    except Exception as e:
        pass

    # JSON to stdout
    sys.stdout.write(json.dumps(report, default=str))
    sys.stdout.write('\n')
    sys.stdout.flush()


if __name__ == '__main__':
    main()
