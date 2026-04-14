# Curriculum 01 — reverse engineering halo2.dll

## why this matters

halo 2 mcc's entire campaign runtime lives in `halo2.dll`. the
launcher (`mcc-win64-shipping.exe`) hosts it and wires up d3d +
input, but every enemy AI tick, every damage calculation, every
weapon reload is code inside halo2.dll. reverse-engineering it
is the difference between "we can scan for floats" and "we can
flip a single byte to turn off enemy fire."

## vocabulary

| term | meaning |
|---|---|
| PE | Portable Executable — windows binary format |
| .text | code section — CPU instructions |
| .rdata | read-only data — string literals, const arrays |
| .data | mutable globals — the interesting stuff for cheaters |
| AOB | array of bytes — a unique opcode pattern used to locate a function |
| RVA | relative virtual address — offset from module base |
| base | the absolute address the module was loaded at |
| struct | a fixed-layout blob in memory — biped, weapon, ai_squad |

## the loop a reverse-engineer runs

1. **get the base address** — ask the game dumper which gives
   `halo2.dll @ 0x7ff6xxxx`
2. **find the .data section** — PE header + IMAGE_SECTION_HEADER
   parsing gives offset + size
3. **dump .data** — ReadProcessMemory the whole section
4. **scan for patterns** — floats in HP range, strings like
   "biped", AOB patterns for known opcodes
5. **cross-reference** — the address you find at step 4 should
   change on damage (confirm with delta scan), live near other
   floats that also change (health + shield usually adjacent)
6. **patch or pin** — write over the value or NOP out the
   clamping instruction

## drills in this track

- `reverse-101-dll-base` — find halo2.dll base from the game
  dump. cherp-piper.
- `reverse-102-section-layout` (TODO) — identify .text vs .data
  offsets
- `reverse-103-aob-hunt` (TODO) — propose 6 AOB patterns for
  damage-apply

## reference material

- community halo 2 modding docs (mccm, assembly.cefclient)
- ghidra / IDA docs on PE parsing
- microsoft's PE format spec
