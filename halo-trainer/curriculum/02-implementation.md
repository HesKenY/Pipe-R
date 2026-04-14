# Curriculum 02 — implementation: writing the hunters

## why this matters

reverse engineering only gets us a list of offsets. the
hunters are the scripts that actually attach to MCC, read
memory, delta-scan, and write values. every hunter we build
here lives permanently in the toolkit. this curriculum drills
the students on writing CORRECT hunters on the first try —
the ctypes prototype mistakes (OverflowError on HMODULE,
missing argtype prototypes, buffer sizes wrong) are the class
of bugs we grind out here.

## the shape of a hunter

```
attach:   find pid → OpenProcess(VM_READ|VM_WRITE|VM_OPERATION)
enumerate: VirtualQueryEx loop → list of committed RW regions
scan:      ReadProcessMemory → struct.unpack floats → filter
rescan:    same regions, keep only matching current value
write:     WriteProcessMemory on each surviving address
verify:    re-read immediately + after 250ms + after damage
```

## the gotchas this curriculum grinds

- **HMODULE is u64 on x64** — do not use ctypes.c_void_p for
  module arrays, use `wintypes.HMODULE`
- **psapi functions need explicit argtypes** — without them,
  ctypes will call them with the default C ABI which mangles
  pointer arguments
- **MBI uses c_size_t not DWORD** — the regionsize field is
  64-bit on x64
- **huge regions — gate the scanner at 256MB** — MCC has a
  600MB region that will OOM a naive scanner
- **epsilon on floats** — never compare floats with ==, always
  abs(val - target) <= epsilon

## drills in this track

- `implementation-101-health-scanner` — qwen2.5-coder writes a
  full ctypes delta scanner
- `implementation-102-pin-thread` (TODO) — background thread
  that writes a value every 80ms
- `implementation-103-aob-scan` (TODO) — scan a region for a
  specific byte pattern
