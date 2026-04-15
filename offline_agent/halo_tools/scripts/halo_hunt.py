"""
KEN HALO HUNT — delta-scanning memory hunter for MCC-Win64-Shipping.exe

Implements the core Cheat Engine workflow in Python:

  1. First pass: scan MCC's writable memory for every float
     in a plausible health range (0.0 - 200.0). Remember every
     (address, value) pair found.
  2. Every N seconds, re-read those addresses. Keep only
     addresses where the value CHANGED since last read
     (meaning the value is live game state, not a constant).
  3. Further narrow: apply "increased" / "decreased" / "any
     change" filters to shrink the candidate set.
  4. After enough iterations, 1-5 addresses remain — those
     are the live game-state values. Write them all to
     hunt_results.jsonl for inspection.

Ken's workflow:
  - Start MCC, get into a mission with a health bar visible.
  - Run HALO_HUNT.bat. It watches stdout for commands.
  - While it's running, take damage in-game. Every ~2s it
    re-scans and narrows the candidate set based on
    "decreased" values.
  - After a few damage events, check hunt_results.jsonl —
    the remaining addresses are health / shield candidates.
  - Use them with a write tool to set invincibility.

This is essentially a headless mini Cheat Engine. Requires
admin privileges (PROCESS_VM_READ + PROCESS_VM_WRITE +
PROCESS_VM_OPERATION).

Commands (type into the console while running):
  i    — rescan, keep only INCREASED values
  d    — rescan, keep only DECREASED values
  c    — rescan, keep only CHANGED values
  u    — rescan, keep only UNCHANGED values
  r    — reset, start a fresh first-pass scan
  w N  — write value N to all remaining candidates
  s    — status (candidate count + top 20)
  q    — quit
"""

import sys
import os
import ctypes
import struct
import json
import time
import threading
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

# ─── Config ──────────────────────────────────────────────
PROCESS_NAME = "mcc-win64-shipping.exe"
SCAN_MIN = 0.0
SCAN_MAX = 200.0
MAX_FIRST_PASS = 5_000_000     # safety cap
SCAN_INTERVAL_SEC = 2.0

# ─── Windows API ─────────────────────────────────────────
PROCESS_VM_READ            = 0x0010
PROCESS_VM_WRITE           = 0x0020
PROCESS_VM_OPERATION       = 0x0008
PROCESS_QUERY_INFORMATION  = 0x0400

MEM_COMMIT              = 0x1000
PAGE_READWRITE          = 0x04
PAGE_EXECUTE_READWRITE  = 0x40

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


def find_pid():
    arr = (wintypes.DWORD * 4096)()
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
            if buf.value.lower() == PROCESS_NAME:
                kernel32.CloseHandle(h)
                return pid
        kernel32.CloseHandle(h)
    return None


def enum_rw_regions(h):
    mbi = MBI()
    addr = 0
    out = []
    while kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        if (mbi.State == MEM_COMMIT and
            (mbi.Protect & (PAGE_READWRITE | PAGE_EXECUTE_READWRITE))):
            out.append((mbi.BaseAddress or 0, mbi.RegionSize))
        addr = (mbi.BaseAddress or 0) + mbi.RegionSize
        if addr > (1 << 47):
            break
    return out


def read_float(h, addr):
    buf = (ctypes.c_float * 1)()
    nread = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, 4, ctypes.byref(nread))
    if ok and nread.value == 4:
        return buf[0]
    return None


def write_float(h, addr, val):
    buf = ctypes.c_float(val)
    nwrit = ctypes.c_size_t(0)
    ok = kernel32.WriteProcessMemory(h, ctypes.c_void_p(addr), ctypes.byref(buf), 4, ctypes.byref(nwrit))
    return bool(ok and nwrit.value == 4)


# ─── Scanner state ───────────────────────────────────────
candidates = {}   # addr → last_value
pid = None
h_proc = None
lock = threading.Lock()
scan_in_progress = False


def open_proc():
    global pid, h_proc
    pid = find_pid()
    if not pid:
        print(f"[halo_hunt] {PROCESS_NAME} not running")
        return False
    flags = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
    h_proc = kernel32.OpenProcess(flags, False, pid)
    if not h_proc:
        err = ctypes.get_last_error()
        print(f"[halo_hunt] OpenProcess failed: {err} (need to run as admin)")
        return False
    print(f"[halo_hunt] attached to pid {pid}")
    return True


def first_pass():
    """Scan all writable regions, collect every float in
    [SCAN_MIN, SCAN_MAX]. Fills `candidates`."""
    global candidates, scan_in_progress
    with lock:
        scan_in_progress = True
        regions = enum_rw_regions(h_proc)
        # Skip huge regions (>256MB — textures)
        regions = [r for r in regions if 4096 < r[1] < 256 * 1024 * 1024]
        regions.sort(key=lambda r: r[1])

        print(f"[halo_hunt] first pass — scanning {len(regions)} regions")
        found = {}
        total_bytes = 0
        t0 = time.time()
        for base, size in regions:
            if len(found) >= MAX_FIRST_PASS:
                break
            buf = (ctypes.c_ubyte * size)()
            nread = ctypes.c_size_t(0)
            if not kernel32.ReadProcessMemory(h_proc, ctypes.c_void_p(base), buf, size, ctypes.byref(nread)):
                continue
            total_bytes += nread.value
            raw = bytes(buf[:nread.value])
            # Walk 4 bytes at a time
            for offset in range(0, len(raw) - 3, 4):
                val = struct.unpack_from('<f', raw, offset)[0]
                if SCAN_MIN <= val <= SCAN_MAX and not (val != val):  # not NaN
                    found[base + offset] = val
                    if len(found) >= MAX_FIRST_PASS:
                        break
        elapsed = time.time() - t0
        candidates = found
        scan_in_progress = False
        print(f"[halo_hunt] first pass done: {len(candidates):,} candidates in {elapsed:.1f}s, {total_bytes//(1024*1024)}MB scanned")


def rescan(mode):
    """mode: 'increased' | 'decreased' | 'changed' | 'unchanged'"""
    global candidates
    with lock:
        kept = {}
        for addr, prev in candidates.items():
            cur = read_float(h_proc, addr)
            if cur is None:
                continue
            if mode == 'increased' and cur > prev:
                kept[addr] = cur
            elif mode == 'decreased' and cur < prev:
                kept[addr] = cur
            elif mode == 'changed' and cur != prev:
                kept[addr] = cur
            elif mode == 'unchanged' and cur == prev:
                kept[addr] = cur
        before = len(candidates)
        candidates = kept
        print(f"[halo_hunt] {mode}: {before:,} → {len(kept):,}")


def status(n=20):
    with lock:
        print(f"[halo_hunt] candidates: {len(candidates):,}")
        items = list(candidates.items())[:n]
        for addr, val in items:
            cur = read_float(h_proc, addr)
            print(f"  0x{addr:016x}: stored={val:.3f} now={cur:.3f}" if cur is not None else f"  0x{addr:016x}: stored={val:.3f} now=<read fail>")


def write_all(value):
    with lock:
        written = 0
        for addr in list(candidates.keys()):
            if write_float(h_proc, addr, value):
                written += 1
        print(f"[halo_hunt] wrote {value} to {written:,} addresses")


def dump_results():
    """Write current candidate set to hunt_results.jsonl."""
    out = Path(__file__).resolve().parent / "hunt_results.jsonl"
    try:
        with open(out, 'w', encoding='utf-8') as f:
            f.write(json.dumps({
                'at': datetime.now(timezone.utc).isoformat(),
                'pid': pid,
                'count': len(candidates),
            }) + '\n')
            for addr, val in candidates.items():
                f.write(json.dumps({
                    'addr': hex(addr),
                    'addr_int': addr,
                    'value': val,
                }) + '\n')
        print(f"[halo_hunt] dumped {len(candidates):,} candidates to {out.name}")
    except Exception as e:
        print(f"[halo_hunt] dump failed: {e}")


def command_loop():
    print()
    print("[halo_hunt] commands:")
    print("  i   — rescan, keep only INCREASED values")
    print("  d   — rescan, keep only DECREASED values")
    print("  c   — rescan, keep only CHANGED values")
    print("  u   — rescan, keep only UNCHANGED values")
    print("  r   — reset, start a fresh first-pass scan")
    print("  s   — show status + top 20 candidates")
    print("  w N — write value N to every candidate")
    print("  x   — dump candidates to hunt_results.jsonl")
    print("  q   — quit")
    print()
    while True:
        try:
            line = input("hunt> ").strip().lower()
        except EOFError:
            break
        if not line:
            continue
        cmd = line[0]
        arg = line[1:].strip()
        if cmd == 'q':
            dump_results()
            break
        elif cmd == 'i':
            rescan('increased')
        elif cmd == 'd':
            rescan('decreased')
        elif cmd == 'c':
            rescan('changed')
        elif cmd == 'u':
            rescan('unchanged')
        elif cmd == 'r':
            first_pass()
        elif cmd == 's':
            status()
        elif cmd == 'w' and arg:
            try: write_all(float(arg))
            except ValueError: print("[halo_hunt] w needs a number, e.g. 'w 9999'")
        elif cmd == 'x':
            dump_results()
        else:
            print(f"[halo_hunt] unknown: {line}")


def main():
    if not open_proc():
        return 1
    try:
        first_pass()
        dump_results()
        command_loop()
    finally:
        if h_proc:
            kernel32.CloseHandle(h_proc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
