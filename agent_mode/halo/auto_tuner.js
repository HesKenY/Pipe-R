/* ══════════════════════════════════════════════════════
   Halo auto-tuner — squad assist that adjusts aimbot live
   ──────────────────────────────────────────────────────
   Reads aim-loop stats every N seconds and nudges the aimbot
   config based on observed hit rate. Pure rules, no LLM —
   runs fast and never blocks the game loop.

   Rules:

     hit_rate < 10%  → loosen: lower minConfidence, widen palette
     hit_rate > 40%  → tighten: raise minConfidence, reduce burst
     shots = 0 in 90s → widen palette to 'all', floor confidence
     shots > 50 in 90s → reduce burst size to 2, shorter cooldown

   Each tune writes the new config via the same endpoint Ken
   would call manually. So the aimbot keeps running — this
   just restarts it with new params.

   Also stamps a tuning log bullet into halo-memory.md so the
   driver prompt sees "auto-tuner raised burst to 4 at 00:12".
   ══════════════════════════════════════════════════════ */

import { appendLesson } from './memory.js';

let _timer = null;
let _running = false;
let _intervalMs = 60000;
let _lastStats = null;
let _stats = { tunes: 0, startedAt: null, lastTuneAt: null, lastChange: null };

// Runtime-mutable tuning state. Seeded on first pass from
// the live aim config so the tuner respects whatever profile
// Ken started the aimbot with instead of clobbering it.
let _tuning = {
  intervalMs: 60,
  palette: 'all',
  minConfidence: 0.015,
  burstSize: 5,
  shotDelay: 85,
  maxShots: 7,
};
let _seeded = false;

// Aggression floors — tuner may walk values UP from here but
// never back below. Ken's "DIAL IT IN" directive: headhunt hard.
const FLOORS = {
  burstSize: 4,
  maxShots: 5,
  minConfidenceMax: 0.035, // never tighten past this
  intervalMsMax: 90,       // never slow past this
};

export function getTuning() { return { ..._tuning }; }

/* ── Core tuning logic. Takes current aim stats + delta
   vs last cycle, returns a new tuning config. ── */
function computeNextTuning(currentStats, prevStats) {
  // First pass: seed _tuning from whatever config is live so we
  // don't stomp Ken's initial aggressive profile.
  if (!_seeded && currentStats) {
    _tuning = {
      intervalMs:    currentStats.intervalMs    || _tuning.intervalMs,
      palette:       currentStats.palette       || _tuning.palette,
      minConfidence: currentStats.minConfidence != null ? currentStats.minConfidence : _tuning.minConfidence,
      burstSize:     currentStats.burstSize     || _tuning.burstSize,
      shotDelay:     currentStats.shotDelay     || _tuning.shotDelay,
      maxShots:      currentStats.maxShots      || _tuning.maxShots,
    };
    _seeded = true;
  }
  const next = { ..._tuning };
  if (!currentStats || !currentStats.stats) return null;
  const s = currentStats.stats;

  // Compute DELTA since last tune so we measure only recent
  // performance, not lifetime.
  let scansDelta = s.scans;
  let hitsDelta = s.hits;
  let shotsDelta = s.shots;
  if (prevStats && prevStats.stats) {
    scansDelta  = Math.max(0, s.scans  - prevStats.stats.scans);
    hitsDelta   = Math.max(0, s.hits   - prevStats.stats.hits);
    shotsDelta  = Math.max(0, s.shots  - prevStats.stats.shots);
  }

  if (scansDelta < 3) return null; // not enough data to tune
  const hitRate = hitsDelta / scansDelta;

  let changed = false;
  let reason = '';

  // Starved rule — no shots fired in the whole window
  if (shotsDelta === 0 && scansDelta >= 15) {
    if (next.minConfidence > 0.015) {
      next.minConfidence = Math.max(0.015, next.minConfidence - 0.01);
      changed = true;
      reason += `lower min_conf → ${next.minConfidence.toFixed(3)}; `;
    }
    if (next.palette !== 'all') {
      next.palette = 'all';
      changed = true;
      reason += 'palette → all; ';
    }
  }

  // Low hit rate — loosen
  if (hitRate < 0.10 && shotsDelta < 5) {
    if (next.minConfidence > 0.02) {
      next.minConfidence = Math.max(0.02, next.minConfidence - 0.005);
      changed = true;
      reason += `lower min_conf → ${next.minConfidence.toFixed(3)}; `;
    }
  }

  // High hit rate — tighten a hair to favor quality, but
  // never past the aggression floor.
  if (hitRate > 0.40 && scansDelta >= 20) {
    if (next.minConfidence < FLOORS.minConfidenceMax) {
      next.minConfidence = Math.min(FLOORS.minConfidenceMax, next.minConfidence + 0.003);
      changed = true;
      reason += `raise min_conf → ${next.minConfidence.toFixed(3)}; `;
    }
  }

  // Quiet period — widen burst for punchy engagements
  if (shotsDelta > 0 && shotsDelta < 10 && scansDelta > 30) {
    if (next.burstSize < 6) {
      next.burstSize = Math.min(6, next.burstSize + 1);
      changed = true;
      reason += `burst → ${next.burstSize}; `;
    }
  }

  // Hard clamps against the aggression floors — tuner may NEVER
  // walk below these regardless of what rules fired above.
  if (next.burstSize < FLOORS.burstSize) {
    next.burstSize = FLOORS.burstSize;
    changed = true;
  }
  if (next.maxShots < FLOORS.maxShots) {
    next.maxShots = FLOORS.maxShots;
    changed = true;
  }
  if (next.intervalMs > FLOORS.intervalMsMax) {
    next.intervalMs = FLOORS.intervalMsMax;
    changed = true;
  }

  if (!changed) return null;
  _tuning = next;
  return { next, reason: reason.trim(), hitRate, scansDelta, hitsDelta, shotsDelta };
}

async function runTunePass() {
  try {
    // Fetch current aim status via local HTTP
    const res = await fetch('http://127.0.0.1:7777/api/halo/aim/status');
    if (!res.ok) return;
    const current = await res.json();
    if (!current || !current.running) return;

    const change = computeNextTuning(current, _lastStats);
    _lastStats = current;

    if (!change) return;

    // Restart aim loop with new params
    await fetch('http://127.0.0.1:7777/api/halo/aim/stop', { method: 'POST' });
    await fetch('http://127.0.0.1:7777/api/halo/aim/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        intervalMs:    _tuning.intervalMs,
        palette:       _tuning.palette,
        minConfidence: _tuning.minConfidence,
        engage:        true,
        burstSize:     _tuning.burstSize,
        shotDelay:     _tuning.shotDelay,
        maxShots:      _tuning.maxShots,
        daemon:        false,
      }),
    });

    _stats.tunes += 1;
    _stats.lastTuneAt = new Date().toISOString();
    _stats.lastChange = change.reason;

    try {
      appendLesson('tactics_learned',
        `auto-tuner: ${change.reason} (hitrate=${(change.hitRate*100).toFixed(0)}%, scans=${change.scansDelta}, shots=${change.shotsDelta})`);
    } catch (e) { /* best-effort */ }
  } catch (e) { /* swallow */ }
}

export function startAutoTuner(opts = {}) {
  if (_running) return { ok: false, reason: 'already running' };
  _intervalMs = Math.max(20000, Math.min(600000, opts.intervalMs || 60000));
  _running = true;
  _stats = { tunes: 0, startedAt: new Date().toISOString(), lastTuneAt: null, lastChange: null };
  const tick = async () => {
    if (!_running) return;
    try { await runTunePass(); }
    catch (e) { /* swallow */ }
    if (_running) _timer = setTimeout(tick, _intervalMs);
  };
  _timer = setTimeout(tick, 5000); // first pass after 5s warmup
  return { ok: true, intervalMs: _intervalMs };
}

export function stopAutoTuner() {
  if (!_running) return { ok: false, reason: 'not running' };
  _running = false;
  if (_timer) { clearTimeout(_timer); _timer = null; }
  return { ok: true, stats: _stats };
}

export function tunerStatus() {
  return {
    running: _running,
    intervalMs: _intervalMs,
    tuning: _tuning,
    stats: _stats,
  };
}
