# Curriculum 04 — quality: verifying our work doesn't break the game

## why this matters

everything we build writes to a live process. one bad pointer,
one race, one clamp we didn't see — and Halo crashes, taking
the training session with it. quality is the track that grinds
the "measure twice, cut once" instinct into the squad.

## three hard rules

1. **reads before writes** — every write is preceded by a read
   of the current value, saved as rollback state. no exceptions.
2. **verify-after** — every write is followed within 250ms by a
   re-read. if the read doesn't match, the write didn't land or
   the game clamped it.
3. **watchdog everything** — any loop that writes memory has a
   co-running watchdog that can set a stop event and kill the
   pin thread. no unsupervised writers.

## the failure taxonomy

- **silent no-op**: WriteProcessMemory returns true but the
  page was copy-on-write and the kernel wrote a private copy
  you can't see. cure: verify-after.
- **clamp**: you wrote 9999, game clamped to 100 on next
  access. cure: AOB-patch the clamp instruction, or pin at
  80ms so the clamp doesn't get a chance to run.
- **wrong struct**: you found a float that changes under
  damage. it was a shield regen timer, not HP. cure: always
  confirm with a SECOND delta scan on a different event.
- **handle death**: the process got restarted. your PID is
  dead. cure: detect on next write failure, rehunt.
- **PID collision**: new process reused the PID. you're now
  writing to excel. cure: cache the process start time.

## drills in this track

- `quality-101-write-verify` — jefferyjefferferson designs a
  read-back verification plan
- `quality-102-regression-risks` — enumerate the regression
  surface when writing to game memory
- `quality-103-rollback-proof` (TODO) — prove a rollback
  restores the original bytes exactly
