"""
HALO GAME DATA + FILE DUMPER — snapshots MCC's loaded state
for the reverse-engineering index.

Runs from the command line or from a Node spawn. Dumps:

  1. Loaded modules (DLLs) in MCC-Win64-Shipping.exe — base
     address, size, path. The executable + halo2.dll + engine
     DLLs are the first places to hunt for health / AI state.
  2. RW memory region summary — count, total bytes, largest
     single region. Helps agents estimate how much surface
     the scanner is crawling.
  3. Install directory tree — top 120 files by size, mtime,
     relative path. File layout is the schematic: .map files
     hold missions, .fp holds fonts, .bik holds cutscenes,
     .dll holds the native code the reversing is aimed at.
  4. Save directory mtimes — last checkpoint, last config
     edit. Used to correlate memory snapshots with in-game
     progress.

Output is a single JSON object on stdout. Caller parses it
and writes to `halo-game-dump.md` (human-readable) and
`halo-modules.jsonl` (indexable).

No admin required for the install dir walk + save dir scan.
Module + memory enumeration DOES require VM_READ — the script
degrades gracefully if it can't open the process.
"""

import ctypes
import json
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

PROCESS_VM_READ           = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT                = 0x1000
PAGE_READWRITE            = 0x04
PAGE_EXECUTE_READWRITE    = 0x40

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi    = ctypes.WinDLL("psapi",    use_last_error=True)


class MBI(ctypes.Structure):
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


def find_pid(name='mcc-win64-shipping.exe'):
    arr = (wintypes.DWORD * 4096)()
    cb = wintypes.DWORD(0)
    psapi.EnumProcesses(ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(cb))
    count = cb.value // ctypes.sizeof(wintypes.DWORD)
    for i in range(count):
        pid = arr[i]
        if not pid:
            continue
        h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not h:
            continue
        buf = ctypes.create_unicode_buffer(512)
        if psapi.GetModuleBaseNameW(h, None, buf, 512) > 0:
            if buf.value.lower() == name:
                kernel32.CloseHandle(h)
                return pid
        kernel32.CloseHandle(h)
    return None


def enum_modules(h):
    # Explicit prototypes — ctypes defaults mangle HMODULE on x64
    psapi.EnumProcessModules.argtypes = [wintypes.HANDLE,
        ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    psapi.EnumProcessModules.restype = wintypes.BOOL
    psapi.GetModuleBaseNameW.argtypes = [wintypes.HANDLE, wintypes.HMODULE,
        wintypes.LPWSTR, wintypes.DWORD]
    psapi.GetModuleBaseNameW.restype = wintypes.DWORD
    psapi.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE,
        wintypes.LPWSTR, wintypes.DWORD]
    psapi.GetModuleFileNameExW.restype = wintypes.DWORD
    psapi.GetModuleInformation.argtypes = [wintypes.HANDLE, wintypes.HMODULE,
        ctypes.POINTER(MODULEINFO), wintypes.DWORD]
    psapi.GetModuleInformation.restype = wintypes.BOOL

    hmods = (wintypes.HMODULE * 1024)()
    cb_needed = wintypes.DWORD(0)
    if not psapi.EnumProcessModules(h, hmods,
                                    ctypes.sizeof(hmods),
                                    ctypes.byref(cb_needed)):
        return []
    count = cb_needed.value // ctypes.sizeof(wintypes.HMODULE)
    out = []
    for i in range(count):
        hmod = hmods[i]
        if not hmod:
            continue
        name_buf = ctypes.create_unicode_buffer(1024)
        path_buf = ctypes.create_unicode_buffer(1024)
        psapi.GetModuleBaseNameW(h, hmod, name_buf, 1024)
        psapi.GetModuleFileNameExW(h, hmod, path_buf, 1024)
        info = MODULEINFO()
        psapi.GetModuleInformation(h, hmod, ctypes.byref(info), ctypes.sizeof(info))
        out.append({
            'name': name_buf.value,
            'path': path_buf.value,
            'base': info.lpBaseOfDll or 0,
            'size': info.SizeOfImage,
            'entry': info.EntryPoint or 0,
        })
    out.sort(key=lambda m: -m['size'])
    return out


def summarize_rw_regions(h):
    mbi = MBI()
    addr = 0
    count = 0
    total = 0
    largest = 0
    exec_rw = 0
    while kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr),
                                  ctypes.byref(mbi), ctypes.sizeof(mbi)):
        if mbi.State == MEM_COMMIT and (mbi.Protect & (PAGE_READWRITE | PAGE_EXECUTE_READWRITE)):
            count += 1
            total += mbi.RegionSize
            if mbi.RegionSize > largest:
                largest = mbi.RegionSize
            if mbi.Protect & PAGE_EXECUTE_READWRITE:
                exec_rw += 1
        addr = (mbi.BaseAddress or 0) + mbi.RegionSize
        if addr > (1 << 47):
            break
    return {
        'rw_regions': count,
        'rw_total_bytes': total,
        'rw_largest_bytes': largest,
        'rw_exec_regions': exec_rw,
    }


def walk_install_tree(root, max_files=120):
    if not root or not os.path.isdir(root):
        return []
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            full = os.path.join(dirpath, f)
            try:
                st = os.stat(full)
                rows.append({
                    'rel': os.path.relpath(full, root),
                    'size': st.st_size,
                    'mtime': int(st.st_mtime),
                    'ext': os.path.splitext(f)[1].lower(),
                })
            except Exception:
                pass
    rows.sort(key=lambda r: -r['size'])
    return rows[:max_files]


def summarize_tree_by_ext(rows):
    counts = {}
    for r in rows:
        ext = r['ext'] or '(none)'
        if ext not in counts:
            counts[ext] = {'count': 0, 'bytes': 0}
        counts[ext]['count'] += 1
        counts[ext]['bytes'] += r['size']
    return counts


def main():
    pid = find_pid()
    out = {
        'at': int(time.time()),
        'pid': pid,
        'modules': [],
        'memory': None,
        'install_path': None,
        'top_files': [],
        'ext_summary': {},
        'save_dir': None,
        'recent_saves': [],
    }
    if pid:
        h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if h:
            out['modules'] = enum_modules(h)[:40]
            out['memory'] = summarize_rw_regions(h)
            kernel32.CloseHandle(h)

    candidates = [
        r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection',
        r'D:\SteamLibrary\steamapps\common\Halo The Master Chief Collection',
        r'E:\SteamLibrary\steamapps\common\Halo The Master Chief Collection',
        r'C:\XboxGames\Halo- The Master Chief Collection',
    ]
    install = None
    for c in candidates:
        if os.path.isdir(c):
            install = c
            break
    if install:
        out['install_path'] = install
        rows = walk_install_tree(install, 120)
        out['top_files'] = rows
        out['ext_summary'] = summarize_tree_by_ext(rows)

    home = os.environ.get('USERPROFILE', r'C:\Users\Ken')
    save_candidates = [
        os.path.join(home, 'AppData', 'LocalLow', 'MCC', 'Temporary'),
        os.path.join(home, 'AppData', 'LocalLow', 'MCC'),
    ]
    for s in save_candidates:
        if os.path.isdir(s):
            out['save_dir'] = s
            try:
                names = os.listdir(s)
                stamped = []
                for n in names:
                    try:
                        st = os.stat(os.path.join(s, n))
                        if not os.path.isfile(os.path.join(s, n)):
                            continue
                        stamped.append({
                            'name': n,
                            'mtime': int(st.st_mtime),
                            'size': st.st_size,
                        })
                    except Exception:
                        pass
                stamped.sort(key=lambda r: -r['mtime'])
                out['recent_saves'] = stamped[:12]
            except Exception:
                pass
            break

    print(json.dumps(out, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
