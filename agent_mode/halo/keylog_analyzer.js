/* ══════════════════════════════════════════════════════
   Halo learning agent — live keylog analyzer
   ──────────────────────────────────────────────────────
   Tails halo-keylog.jsonl while Ken is playing and detects
   combat patterns from his actual key+mouse presses. Every
   recognized pattern gets stamped into halo-memory.md under
   ken_patterns so the drive loop prompt sees them.

   Patterns detected:

     rapid_fire         5+ LMB clicks within 3 seconds
     reload_after_fire  R key within 1s of a rapid_fire window
     grenade_throw      F key press
     melee_strike       Q key press
     strafe_shoot       A or D held + LMB overlapping
     sprint_jump        LShift held + Space tap within 400ms
     ads_fire           RMB + LMB overlapping (aimed shot)
     swap_weapon        1 key press
     noob_combo         RMB hold + release + LMB within 800ms
                        (plasma pistol overcharge → BR headshot
                         — THE Halo 2 signature combo)

   Each pattern, when detected, emits one entry to the
   ken_patterns section of halo-memory.md + an event row to
   halo-events.jsonl for downstream dream reflection.

   The analyzer reads the tail of halo-keylog.jsonl on a
   ~2-second cadence. Cheap because the file is line-buffered
   and we only scan the last ~40 events.

   ══════════════════════════════════════════════════════ */

import { existsSync, readFileSync, appendFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { appendLesson } from './memory.js';
import { refreshJumpstartSnapshot } from './jumpstart.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const KEYLOG_PATH = join(__dirname, '..', 'memories', 'ken-ai-latest', 'halo-keylog.jsonl');
const EVENTS_PATH = join(__dirname, '..', 'memories', 'ken-ai-latest', 'halo-events.jsonl');

let _timer = null;
let _running = false;
let _intervalMs = 2000;
let _lastProcessedAt = 0; // ms since epoch — only process events newer
let _detectedRecent = new Map(); // debounce so the same pattern doesn't
                                  // spam the memory every tick.

// Debounce window per pattern name (ms). A pattern only gets
// recorded at most once per window to keep halo-memory.md from
// filling up on repeat combos.
const DEBOUNCE_MS = {
  rapid_fire:        8000,
  reload_after_fire: 8000,
  grenade_throw:     6000,
  melee_strike:      6000,
  strafe_shoot:     10000,
  sprint_jump:       8000,
  ads_fire:          6000,
  swap_weapon:       8000,
  noob_combo:       10000,
};

function readTail(limit = 80) {
  if (!existsSync(KEYLOG_PATH)) return [];
  try {
    const raw = readFileSync(KEYLOG_PATH, 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    const out = [];
    for (let i = lines.length - 1; i >= 0 && out.length < limit; i--) {
      try { out.push(JSON.parse(lines[i])); } catch (e) { /* skip */ }
    }
    return out.reverse(); // oldest first for sequence analysis
  } catch (e) { return []; }
}

function toMs(iso) {
  try { return new Date(iso).getTime(); }
  catch (e) { return 0; }
}

function shouldRecord(pattern, nowMs) {
  const last = _detectedRecent.get(pattern) || 0;
  const window = DEBOUNCE_MS[pattern] || 6000;
  if (nowMs - last < window) return false;
  _detectedRecent.set(pattern, nowMs);
  return true;
}

function emit(pattern, detail, nowMs) {
  if (!shouldRecord(pattern, nowMs)) return false;
  const entry = {
    at: new Date(nowMs).toISOString(),
    kind: 'ken_pattern',
    pattern,
    detail,
  };
  try { appendFileSync(EVENTS_PATH, JSON.stringify(entry) + '\n', 'utf8'); }
  catch (e) { /* best-effort */ }
  try { appendLesson('tactics_learned', `ken:${pattern} — ${detail}`); }
  catch (e) { /* best-effort */ }
  return true;
}

/* ── Detect patterns in the tail. Receives events in time order. ── */
function detect(events) {
  if (!events.length) return;
  // Only look at events newer than our last processed watermark
  const fresh = events.filter(e => toMs(e.at) > _lastProcessedAt);
  if (!fresh.length) return;
  _lastProcessedAt = toMs(fresh[fresh.length - 1].at);

  // Build a compact timeline: [{t, kind, id}] — kind is 'key' or
  // 'mouse', id is key name or button name.
  const timeline = fresh.map(e => ({
    t: toMs(e.at),
    kind: e.kind,
    id: e.kind === 'key' ? (e.key || '') : (e.button || ''),
    dir: e.dir || '',
  })).filter(e => e.dir === 'down' || e.dir === '');

  // 1. rapid_fire — 5+ LMB clicks within 3 seconds
  const lmbs = timeline.filter(e => e.kind === 'mouse' && e.id === 'left');
  if (lmbs.length >= 5) {
    const span = lmbs[lmbs.length - 1].t - lmbs[0].t;
    if (span <= 3000) {
      emit('rapid_fire', `${lmbs.length} lmb clicks in ${span}ms`, lmbs[lmbs.length - 1].t);
    }
  }

  // 2. reload_after_fire — r key within 1s after ≥3 LMB clicks
  const reloads = timeline.filter(e => e.kind === 'key' && e.id === 'r');
  for (const r of reloads) {
    const priorLMBs = lmbs.filter(l => l.t < r.t && r.t - l.t < 3000);
    if (priorLMBs.length >= 3) {
      emit('reload_after_fire', `r pressed after ${priorLMBs.length} lmbs`, r.t);
    }
  }

  // 3. grenade_throw — f key
  for (const e of timeline) {
    if (e.kind === 'key' && e.id === 'f') {
      emit('grenade_throw', 'f pressed', e.t);
    }
  }

  // 4. melee_strike — q key
  for (const e of timeline) {
    if (e.kind === 'key' && e.id === 'q') {
      emit('melee_strike', 'q pressed', e.t);
    }
  }

  // 5. strafe_shoot — a or d within 600ms of an lmb
  const strafes = timeline.filter(e =>
    e.kind === 'key' && (e.id === 'a' || e.id === 'd'));
  for (const s of strafes) {
    const nearLMB = lmbs.find(l => Math.abs(l.t - s.t) < 600);
    if (nearLMB) {
      emit('strafe_shoot', `${s.id} + lmb within 600ms`, Math.max(s.t, nearLMB.t));
      break;
    }
  }

  // 6. sprint_jump — left shift + space within 400ms
  const shifts = timeline.filter(e => e.kind === 'key' && e.id === 'left shift');
  const jumps  = timeline.filter(e => e.kind === 'key' && e.id === 'space');
  for (const s of shifts) {
    const nearJump = jumps.find(j => Math.abs(j.t - s.t) < 400);
    if (nearJump) {
      emit('sprint_jump', 'shift + space within 400ms', Math.max(s.t, nearJump.t));
      break;
    }
  }

  // 7. ads_fire — rmb + lmb overlapping (within 300ms of each other)
  const rmbs = timeline.filter(e => e.kind === 'mouse' && e.id === 'right');
  for (const r of rmbs) {
    const nearLMB = lmbs.find(l => Math.abs(l.t - r.t) < 300);
    if (nearLMB) {
      emit('ads_fire', 'rmb + lmb within 300ms', Math.max(r.t, nearLMB.t));
      break;
    }
  }

  // 8. swap_weapon — 1 key press
  for (const e of timeline) {
    if (e.kind === 'key' && e.id === '1') {
      emit('swap_weapon', '1 pressed', e.t);
    }
  }

  // 9. noob_combo — rmb press+release, then lmb within 800ms
  //    (the classic plasma-pistol overcharge + BR headshot)
  for (let i = 0; i < rmbs.length; i++) {
    const r = rmbs[i];
    const followUpLMB = lmbs.find(l => l.t > r.t && l.t - r.t < 800);
    if (followUpLMB) {
      emit('noob_combo', `rmb → lmb in ${followUpLMB.t - r.t}ms`, followUpLMB.t);
      break;
    }
  }
}

export function startKeylogAnalyzer(opts = {}) {
  if (_running) return { ok: false, reason: 'already running' };
  _intervalMs = Math.max(500, Math.min(10000, opts.intervalMs || 2000));
  _running = true;
  _lastProcessedAt = Date.now() - 5000; // start 5s ago so first pass sees recent events
  const tick = () => {
    if (!_running) return;
    try {
      detect(readTail(80));
      refreshJumpstartSnapshot({ minimumIntervalMs: 20000 });
    }
    catch (e) { /* swallow */ }
    if (_running) _timer = setTimeout(tick, _intervalMs);
  };
  tick();
  return { ok: true, intervalMs: _intervalMs };
}

export function stopKeylogAnalyzer() {
  if (!_running) return { ok: false, reason: 'not running' };
  _running = false;
  if (_timer) { clearTimeout(_timer); _timer = null; }
  return { ok: true };
}

export function analyzerStatus() {
  return {
    running: _running,
    intervalMs: _intervalMs,
    lastProcessedAt: _lastProcessedAt ? new Date(_lastProcessedAt).toISOString() : null,
    patternsDetected: _detectedRecent.size,
  };
}
