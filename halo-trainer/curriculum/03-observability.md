# Curriculum 03 — observability: reading the game state

## why this matters

the aimbot, the drive loop, and the patcher all depend on
ONE thing: seeing what's happening on screen right now. HUD
reads tell us shield + health + ammo. motion diff tells us
whether the scene changed. vision model readings give us
ground-truth numbers we can feed the memory scanner.

if observability is broken, the aimbot fires at nothing, the
drive loop issues noops, and the patcher tunes based on
phantom stats. this curriculum drills agents on parsing noisy
data fast + accurately.

## the failure modes

- OCR sees "0" as "O" and "1" as "l" — must be tolerated
- 5120x1440 ultrawide has the HUD in the far-left 25% — the
  center crop misses it
- motion detection at 320-wide grayscale diff is enough for a
  binary "something happened" signal — do not over-engineer
- vision models take 5-15s per frame — cannot be in the hot
  loop, must be a side channel

## drills in this track

- `observability-101-hud-parse` — llama3.1 parses a noisy OCR
  line into structured state JSON
- `observability-102-motion-label` (TODO) — classify activity
  from motion + brightness + ocr
- `observability-103-vision-plausibility` (TODO) — given a
  vision read of SHIELD:45, estimate confidence
