"""
VISION-ASSISTED HALO HUNT — use llama3.2-vision to READ Halo's
HUD, feed the observed values into the memory delta scanner to
find the exact health offset in 2-4 iterations.

Workflow:

  1. Attach to MCC-Win64-Shipping.exe (requires admin)
  2. Ask vision: "what's the shield value shown on the HUD right now?"
  3. Vision returns a number (e.g. "45")
  4. Scan process memory for all floats matching that value
  5. Wait ~3 seconds for player to take damage
  6. Ask vision again — shield is now 30
  7. Rescan: keep only addresses that went from 45 → 30
  8. Usually lands 1-10 candidates after 2-3 rounds
  9. Write 9999 to all remaining candidates → god mode

No generic delta scanning — the vision model provides ground-
truth HUD readings so each scan is targeted. Converges
dramatically faster than the blind workflow.

Requires:
  - admin (for ReadProcessMemory / WriteProcessMemory)
  - llama3.2-vision installed via ollama
  - MCC running in a mission with shield HUD visible
  - pyautogui for screenshots
"""

import sys
import os
import ctypes
import struct
import subprocess
import tempfile
import time
import json
import re
import threading
from ctypes import wintypes
from pathlib import Path
from datetime import datetime, timezone

# health pin thread state — continuously rewrites max-health
# into every candidate address so shields/health never drop
# while the aimbot is being dialed in.
_pin_stop = threading.Event()
_pin_thread = None

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception as e:
    print("pyautogui required:", e)
    sys.exit(2)

from PIL import Image

# ── Windows API ──────────────────────────────────────────
PROCESS_VM_READ           = 0x0010
PROCESS_VM_WRITE          = 0x0020
PROCESS_VM_OPERATION      = 0x0008
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


def find_pid(name='mcc-win64-shipping.exe'):
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
            if buf.value.lower() == name:
                kernel32.CloseHandle(h)
                return pid
        kernel32.CloseHandle(h)
    return None


def open_proc(pid):
    flags = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
    h = kernel32.OpenProcess(flags, False, pid)
    return h or None


def enum_rw_regions(h):
    mbi = MBI()
    addr = 0
    out = []
    while kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        if (mbi.State == MEM_COMMIT and
            (mbi.Protect & (PAGE_READWRITE | PAGE_EXECUTE_READWRITE)) and
            4096 < mbi.RegionSize < 256 * 1024 * 1024):
            out.append((mbi.BaseAddress or 0, mbi.RegionSize))
        addr = (mbi.BaseAddress or 0) + mbi.RegionSize
        if addr > (1 << 47):
            break
    return out


def scan_for_float(h, target, epsilon=0.5):
    """Return dict of {addr: value} for every float in the
    process close to the target value (within epsilon)."""
    regions = enum_rw_regions(h)
    found = {}
    for base, size in regions:
        buf = (ctypes.c_ubyte * size)()
        nread = ctypes.c_size_t(0)
        if not kernel32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(nread)):
            continue
        raw = bytes(buf[:nread.value])
        for offset in range(0, len(raw) - 3, 4):
            val = struct.unpack_from('<f', raw, offset)[0]
            if val != val:  # NaN
                continue
            if abs(val - target) <= epsilon:
                found[base + offset] = val
                if len(found) >= 2_000_000:
                    return found
    return found


def rescan(h, candidates, new_target, epsilon=0.5):
    """Keep only candidates whose current value is close to
    new_target."""
    kept = {}
    for addr in list(candidates.keys()):
        buf = (ctypes.c_float * 1)()
        nread = ctypes.c_size_t(0)
        if not kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, 4, ctypes.byref(nread)):
            continue
        if nread.value != 4:
            continue
        val = buf[0]
        if val != val:
            continue
        if abs(val - new_target) <= epsilon:
            kept[addr] = val
    return kept


def write_float(h, addr, value):
    buf = ctypes.c_float(value)
    nwrit = ctypes.c_size_t(0)
    return bool(kernel32.WriteProcessMemory(h, ctypes.c_void_p(addr),
                ctypes.byref(buf), 4, ctypes.byref(nwrit))) and nwrit.value == 4


# ── Vision via ollama ────────────────────────────────────
VISION_MODEL = "llama3.2-vision"

VISION_PROMPT = (
    "You are looking at a Halo 2 MCC gameplay screenshot. "
    "Read the SHIELD bar value + HEALTH value shown on the HUD. "
    "The shield bar is a horizontal meter in the top-left of the screen. "
    "Respond with EXACTLY this format on ONE line:\n\n"
    "  SHIELD:<int> HEALTH:<int>\n\n"
    "If you can't see a value, use -1. No prose, no prefix, no markdown. "
    "Example valid responses:\n"
    "  SHIELD:45 HEALTH:100\n"
    "  SHIELD:-1 HEALTH:-1\n"
    "  SHIELD:22 HEALTH:85"
)


def vision_read_hud():
    """Screenshot + ask llama3.2-vision for the current shield/
    health values. Returns (shield, health) ints or (None, None)."""
    shot = pyautogui.screenshot()
    w, h = shot.size
    # Downsample to 896 wide for vision speed
    target_w = 896
    if w > target_w:
        scale = target_w / w
        shot = shot.resize((target_w, int(h * scale)), Image.BILINEAR)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        shot.save(path, "PNG")
        input_blob = f"{path}\n{VISION_PROMPT}"
        res = subprocess.run(
            ["ollama", "run", VISION_MODEL],
            input=input_blob,
            capture_output=True,
            text=True,
            timeout=40,
            encoding="utf-8",
        )
        if res.returncode != 0:
            return None, None, res.stderr[:100]
        raw = re.sub(r"\x1b\[\??[0-9;]*[a-zA-Z]", "", res.stdout or "").strip()
        # Parse "SHIELD:N HEALTH:M" from any line
        shield = health = None
        for line in raw.splitlines():
            m = re.search(r"SHIELD\s*:\s*(-?\d+)", line, re.I)
            if m: shield = int(m.group(1))
            m = re.search(r"HEALTH\s*:\s*(-?\d+)", line, re.I)
            if m: health = int(m.group(1))
            if shield is not None and health is not None:
                break
        return shield, health, raw[:120]
    finally:
        try: os.unlink(path)
        except Exception: pass


# ── Main hunt loop ───────────────────────────────────────
def main():
    pid = find_pid()
    if not pid:
        print("[vh] MCC-Win64-Shipping.exe not running")
        return 1
    print(f"[vh] attaching to pid {pid}")
    h = open_proc(pid)
    if not h:
        err = ctypes.get_last_error()
        print(f"[vh] OpenProcess failed: {err} (run as admin)")
        return 1

    print()
    print("="*60)
    print("VISION-ASSISTED HALO HUNT")
    print("="*60)
    print()
    print("Workflow: vision reads the HUD, memory scanner searches")
    print("for that exact value, ken takes damage, repeat until")
    print("we have < 20 candidates, then write 9999 for god mode.")
    print()

    candidates = {}

    try:
        while True:
            cmd = input("hunt> ").strip().lower()
            if not cmd: continue
            if cmd == 'q':
                break
            if cmd == 'r':
                # Read HUD via vision
                print("[vh] asking vision to read HUD...")
                t0 = time.time()
                shield, health, raw = vision_read_hud()
                elapsed = time.time() - t0
                print(f"[vh] vision: shield={shield}, health={health} ({elapsed:.1f}s)")
                if shield is None or shield < 0:
                    print("[vh] vision couldn't read HUD — try a different angle / clearer shot")
                    continue
                # First pass: scan for all floats matching shield
                if not candidates:
                    print(f"[vh] first pass: scanning memory for floats == {shield}")
                    t0 = time.time()
                    candidates = scan_for_float(h, float(shield), epsilon=0.5)
                    print(f"[vh] found {len(candidates):,} candidates in {time.time()-t0:.1f}s")
                else:
                    # Rescan: keep candidates that moved to new value
                    print(f"[vh] rescan: keeping candidates now == {shield}")
                    t0 = time.time()
                    before = len(candidates)
                    candidates = rescan(h, candidates, float(shield), epsilon=0.5)
                    print(f"[vh] {before:,} → {len(candidates):,} in {time.time()-t0:.1f}s")
            elif cmd == 's':
                print(f"[vh] candidates: {len(candidates):,}")
                for i, (addr, val) in enumerate(list(candidates.items())[:20]):
                    buf = (ctypes.c_float * 1)()
                    nread = ctypes.c_size_t(0)
                    kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, 4, ctypes.byref(nread))
                    cur = buf[0] if nread.value == 4 else None
                    print(f"  0x{addr:016x}: stored={val:.2f} now={cur:.2f}" if cur is not None else f"  0x{addr:016x}: stored={val:.2f}")
            elif cmd.startswith('w'):
                arg = cmd[1:].strip()
                try: val = float(arg) if arg else 9999.0
                except ValueError:
                    print("[vh] usage: w [value] (default 9999)")
                    continue
                wrote = 0
                for addr in candidates:
                    if write_float(h, addr, val):
                        wrote += 1
                print(f"[vh] wrote {val} to {wrote:,} addresses")
            elif cmd.startswith('p'):
                global _pin_thread
                if _pin_thread and _pin_thread.is_alive():
                    _pin_stop.set()
                    _pin_thread.join(timeout=1.5)
                    _pin_thread = None
                    print("[vh] pin: STOPPED")
                    continue
                if not candidates:
                    print("[vh] pin: no candidates yet — run 'r' first")
                    continue
                arg = cmd[1:].strip()
                try: pin_val = float(arg) if arg else 9999.0
                except ValueError:
                    print("[vh] usage: p [value] (default 9999)")
                    continue
                addrs = list(candidates.keys())
                _pin_stop.clear()
                def _pin_loop(handle, addr_list, value, stop):
                    buf = ctypes.c_float(value)
                    nwrit = ctypes.c_size_t(0)
                    while not stop.is_set():
                        for a in addr_list:
                            kernel32.WriteProcessMemory(handle, ctypes.c_void_p(a),
                                ctypes.byref(buf), 4, ctypes.byref(nwrit))
                        stop.wait(0.08)
                _pin_thread = threading.Thread(
                    target=_pin_loop, args=(h, addrs, pin_val, _pin_stop), daemon=True)
                _pin_thread.start()
                print(f"[vh] pin: WRITING {pin_val} to {len(addrs):,} addrs every 80ms — type 'p' again to stop")
            elif cmd == 'x':
                out = Path(__file__).resolve().parent / "vision_hunt_results.jsonl"
                with open(out, 'w', encoding='utf-8') as f:
                    f.write(json.dumps({
                        'at': datetime.now(timezone.utc).isoformat(),
                        'pid': pid,
                        'count': len(candidates),
                    }) + '\n')
                    for addr, val in candidates.items():
                        f.write(json.dumps({'addr': hex(addr), 'value': val}) + '\n')
                print(f"[vh] dumped {len(candidates):,} candidates to {out.name}")
            elif cmd == 'h' or cmd == '?':
                print("""
commands:
  r     — read HUD via vision + scan/rescan memory
  s     — show status + top 20 candidates
  w [N] — write value N (default 9999) to all candidates
  p [N] — PIN value N forever (80ms loop) — type 'p' again to stop
  x     — export candidates to vision_hunt_results.jsonl
  q     — quit

workflow:
  1. type 'r' — vision reads HUD, first memory pass
  2. take damage in Halo
  3. type 'r' — vision reads new HUD, rescan narrows candidates
  4. repeat 2-3 times until candidates < 20
  5. type 'w' — write 9999 to all, god mode active
  6. type 'x' to save results, 'q' to quit
""")
            else:
                print("[vh] unknown. type h for help")
    finally:
        _pin_stop.set()
        kernel32.CloseHandle(h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
