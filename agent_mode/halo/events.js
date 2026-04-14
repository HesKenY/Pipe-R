/* ══════════════════════════════════════════════════════
   Halo learning agent — event extractor
   ──────────────────────────────────────────────────────
   Compares stateBefore + stateAfter on each drive-mode tick
   and emits structured events the memory module + post-mortem
   system can use for learning.

   Events detected (best-effort — HUD OCR is noisy so we rely
   on gross string-length and zero-state heuristics):

     died            — shield text went non-empty → empty AND
                       center text contains "died" / "respawn"
                       / "checkpoint" OR shield stayed empty
                       across 3 consecutive ticks
     damage_taken    — shield text changed (any mutation) AND
                       the change isn't a swap to all-empty
                       (which = scene transition, not damage)
     shield_regen    — shield was empty in prev tick and has
                       content now
     ammo_changed    — ammo text differs between states
     scene_change    — ALL four HUD fields went from non-empty
                       to empty or vice versa in one tick
                       (menu / cutscene / reload screen)
     idle            — nothing changed at all

   Each event is appended to halo-events.jsonl in the ken-ai
   memory dir. Callers can subscribe to the returned event for
   side-effects (post-mortem on death, win-stamp on regen).

   ══════════════════════════════════════════════════════ */

import { existsSync, mkdirSync, appendFileSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR   = join(__dirname, '..', 'memories', 'ken-ai-latest');
const EVT_LOG   = join(MEM_DIR, 'halo-events.jsonl');

// Tracking: multi-tick history so we can detect "shield stayed
// empty for 3 ticks" which is a reliable death signal even when
// the center text doesn't say "died".
let _shieldEmptyStreak = 0;
const DEATH_SCREEN_WORDS = ['died', 'respawn', 'checkpoint', 'failed', 'mission'];

function ensureDir() {
  if (!existsSync(MEM_DIR)) mkdirSync(MEM_DIR, { recursive: true });
}

function isBlank(s) { return !s || !String(s).trim(); }

function allBlank(state) {
  return isBlank(state?.ammo) && isBlank(state?.shield) &&
         isBlank(state?.radar) && isBlank(state?.center);
}

function containsAny(haystack, needles) {
  if (!haystack) return false;
  const lower = String(haystack).toLowerCase();
  return needles.some(n => lower.includes(n));
}

/* ── Run on one complete tick entry { stateBefore, stateAfter,
   action, mode }. Returns the primary event object or null. ── */
export function extractFromTick(entry) {
  if (!entry || entry.mode !== 'drive') return null;
  const before = entry.stateBefore || {};
  const after  = entry.stateAfter  || {};
  if (!entry.stateBefore || !entry.stateAfter) return null;

  const now = new Date().toISOString();
  let event = null;

  // Scene change — both fully blank or both fully filled.
  if (allBlank(after) && !allBlank(before)) {
    event = { at: now, kind: 'scene_change', direction: 'to_blank' };
  } else if (!allBlank(after) && allBlank(before)) {
    event = { at: now, kind: 'scene_change', direction: 'to_filled' };
  }

  // Shield tracking for death / regen.
  const shieldBefore = String(before.shield || '').trim();
  const shieldAfter  = String(after.shield  || '').trim();

  if (!shieldAfter) {
    _shieldEmptyStreak += 1;
  } else {
    if (_shieldEmptyStreak > 0 && shieldAfter) {
      // Regen detected after at least one empty tick
      event = { at: now, kind: 'shield_regen', streak: _shieldEmptyStreak };
    }
    _shieldEmptyStreak = 0;
  }

  // Death detection:
  //   (a) center text matches any death-screen keyword, OR
  //   (b) shield stayed empty for 3+ consecutive ticks
  if (containsAny(after.center, DEATH_SCREEN_WORDS) ||
      containsAny(after.radar, DEATH_SCREEN_WORDS)) {
    event = { at: now, kind: 'died', cause: 'death_screen_text' };
  } else if (_shieldEmptyStreak >= 3) {
    event = { at: now, kind: 'died', cause: 'shield_empty_3_ticks' };
    _shieldEmptyStreak = 0; // reset after reporting
  }

  // Damage taken — shield text mutated but not to empty and not
  // from empty.
  if (!event && shieldBefore && shieldAfter && shieldBefore !== shieldAfter) {
    event = { at: now, kind: 'damage_taken',
              before: shieldBefore.slice(0, 20),
              after: shieldAfter.slice(0, 20) };
  }

  // Ammo change — more informational than actionable, logged at
  // low priority if nothing else happened.
  if (!event) {
    const ammoB = String(before.ammo || '').trim();
    const ammoA = String(after.ammo  || '').trim();
    if (ammoB && ammoA && ammoB !== ammoA) {
      event = { at: now, kind: 'ammo_changed',
                before: ammoB.slice(0, 20),
                after: ammoA.slice(0, 20) };
    }
  }

  // Default — nothing interesting this tick
  if (!event) event = { at: now, kind: 'idle' };

  // Stamp the action + agent context on every event row
  event.action = entry.action;
  event.tickAt = entry.at;
  event.model  = entry.model;

  // Persist everything except 'idle' (we don't need to spam disk
  // with thousands of identical idle entries).
  if (event.kind !== 'idle') {
    try {
      ensureDir();
      appendFileSync(EVT_LOG, JSON.stringify(event) + '\n', 'utf8');
    } catch (e) { /* best-effort */ }
  }
  return event;
}

/* ── Read last N events for post-mortem / dream input. ── */
export function readRecentEvents(limit = 40) {
  if (!existsSync(EVT_LOG)) return [];
  try {
    const raw = readFileSync(EVT_LOG, 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    const out = [];
    for (let i = lines.length - 1; i >= 0 && out.length < limit; i--) {
      try { out.push(JSON.parse(lines[i])); }
      catch (e) { /* skip */ }
    }
    return out;
  } catch (e) { return []; }
}
