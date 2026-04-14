"""
Halo MCC god-mode attempt — in-process memory scanner.

Uses Windows ctypes to attach to MCC-Win64-Shipping.exe, walk
its readable committed memory regions, find candidate player-
health values (common Halo floats: 1.0, 45.0, 100.0 in both
shield + health forms), and overwrite them with large values.

Caveats (read before running):

- Requires admin privileges. Run as administrator.
- MCC uses ASLR so offsets shift every launch. This scanner
  does NOT rely on hardcoded offsets; it scans live memory.
- Single-pass scan can return 10-100k candidates for a value
  like 1.0 because it's everywhere. A better approach is
  Cheat Engine's "scan → take damage → rescan" delta method.
  This script implements a one-shot mass-write of all floats
  matching common health values to 9999.0. Most writes are
  wrong (hit textures/timers/etc) but a few will land on
  real health vars. The game may crash or glitch.
- Known risk: writing to random floats can crash the process.
  This is the "spray and pray" approach. For production, you
  want Cheat Engine's delta-scan UX.

Usage:
    python halo_godmode.py              # scan + write 9999.0 to matches
    python halo_godmode.py --dry-run    # scan only, no writes
    python halo_godmode.py --targets 1.0,45.0,100.0 --write 9999.0
"""

import sys
import ctypes
import struct
import argparse
from ctypes import wintypes

# Process access flags we need
PROCESS_VM_READ            = 0x0010
PROCESS_VM_WRITE           = 0x0020
PROCESS_VM_OPERATION       = 0x0008
PROCESS_QUERY_INFORMATION  = 0x0400

# Memory protection + state
MEM_COMMIT  = 0x1000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

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


def find_pid(name_lower="mcc-win64-shipping.exe"):
    # Enumerate processes via psapi.EnumProcesses
    arr = (wintypes.DWORD * 2048)()
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
            if buf.value.lower() == name_lower:
                kernel32.CloseHandle(h)
                return pid
        kernel32.CloseHandle(h)
    return None


def enum_writable_regions(h_proc):
    """Yield (base, size) tuples for every committed RW region."""
    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0
    while kernel32.VirtualQueryEx(h_proc, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        region_end = (mbi.BaseAddress or 0) + mbi.RegionSize
        if (mbi.State == MEM_COMMIT and
            (mbi.Protect & (PAGE_READWRITE | PAGE_EXECUTE_READWRITE))):
            yield mbi.BaseAddress, mbi.RegionSize
        addr = region_end
        if addr > (1 << 47):
            break


def scan_and_write(pid, targets, write_value, dry_run=False, max_hits=50000):
    PROCESS_ALL = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
    h = kernel32.OpenProcess(PROCESS_ALL, False, pid)
    if not h:
        return {"ok": False, "error": f"OpenProcess failed: {ctypes.get_last_error()}"}

    # Targets are floats. Pre-encode as bytes for fast scanning.
    target_bytes = [struct.pack('<f', t) for t in targets]
    write_bytes = struct.pack('<f', write_value)

    hits_found = 0
    hits_written = 0
    regions_scanned = 0
    bytes_scanned = 0
    try:
        for base, size in enum_writable_regions(h):
            if size > 64 * 1024 * 1024:
                continue  # skip huge regions (likely textures)
            regions_scanned += 1
            bytes_scanned += size
            buf = (ctypes.c_ubyte * size)()
            nread = ctypes.c_size_t(0)
            ok = kernel32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(nread))
            if not ok:
                continue
            raw = bytes(buf[:nread.value])
            for tb in target_bytes:
                offset = 0
                while True:
                    i = raw.find(tb, offset)
                    if i < 0:
                        break
                    hits_found += 1
                    if not dry_run:
                        addr = base + i
                        nwritten = ctypes.c_size_t(0)
                        wrote = kernel32.WriteProcessMemory(
                            h, ctypes.c_void_p(addr),
                            write_bytes, len(write_bytes),
                            ctypes.byref(nwritten)
                        )
                        if wrote and nwritten.value == len(write_bytes):
                            hits_written += 1
                    offset = i + 4
                    if hits_found >= max_hits:
                        return {
                            "ok": True,
                            "pid": pid,
                            "regions_scanned": regions_scanned,
                            "bytes_scanned": bytes_scanned,
                            "hits_found": hits_found,
                            "hits_written": hits_written,
                            "max_hits_reached": True,
                        }
    finally:
        kernel32.CloseHandle(h)

    return {
        "ok": True,
        "pid": pid,
        "regions_scanned": regions_scanned,
        "bytes_scanned": bytes_scanned,
        "hits_found": hits_found,
        "hits_written": hits_written,
        "max_hits_reached": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--targets", default="1.0,45.0,100.0,75.0,70.0",
                        help="comma-separated floats to search for")
    parser.add_argument("--write", type=float, default=9999.0,
                        help="value to write at every hit")
    parser.add_argument("--max-hits", type=int, default=50000)
    args = parser.parse_args()

    pid = find_pid()
    if not pid:
        import json
        print(json.dumps({"ok": False, "error": "MCC-Win64-Shipping.exe not running"}))
        sys.exit(1)

    targets = [float(t.strip()) for t in args.targets.split(",") if t.strip()]
    result = scan_and_write(pid, targets, args.write,
                            dry_run=args.dry_run, max_hits=args.max_hits)
    import json
    print(json.dumps(result))


if __name__ == "__main__":
    main()
