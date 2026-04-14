/* ══════════════════════════════════════════════════════
   Halo trainer assist — Ken AI coaching its own play
   ──────────────────────────────────────────────────────
   This runs ken-ai:latest in a dedicated "trainer reflection"
   pass that looks at recent halo-log + halo-events + keylog
   and writes structured coaching bullets back to
   halo-memory.md. Different from the dreams.js general
   reflection — this is Halo-specific and focused on
   "what's working, what isn't, what should I try next."

   Cadence: configurable, default every 90s. Runs async so
   it never blocks the drive loop. Uses ken-ai:latest for
   the voice + personality — the trainer IS ken-ai.

   Produces 3-5 coaching bullets per pass:
     - what's working (wins to continue)
     - what's failing (deaths to avoid)
     - one specific adjustment to try

   Each bullet lands in halo-memory.md under tactics_learned
   with a "coach:" prefix so it's distinguishable from
   "ken:" (observed patterns), "online:" (scraped wisdom),
   and raw lessons.

   ══════════════════════════════════════════════════════ */

import { spawnSync } from 'node:child_process';
import { readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { appendLesson } from './memory.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR   = join(__dirname, '..', 'memories', 'ken-ai-latest');
const HALO_LOG    = join(MEM_DIR, 'halo-log.jsonl');
const EVT_LOG     = join(MEM_DIR, 'halo-events.jsonl');

let _timer = null;
let _running = false;
let _intervalMs = 90000;
let _model = 'ken-ai:latest';
let _stats = { passes: 0, lastRunAt: null, lastEntries: 0 };

function stripAnsi(s) {
  return String(s || '')
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '');
}

function readLastN(path, limit) {
  if (!existsSync(path)) return [];
  try {
    const raw = readFileSync(path, 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    const out = [];
    for (let i = lines.length - 1; i >= 0 && out.length < limit; i--) {
      try { out.push(JSON.parse(lines[i])); }
      catch (e) { /* skip */ }
    }
    return out.reverse();
  } catch (e) { return []; }
}

function buildCoachPrompt(ticks, events) {
  const tickSummary = ticks.slice(-12).map((t, i) =>
    `  ${i + 1}. ${t.action || '?'} (mode=${t.mode || '?'}, shots=${t.followThroughs || 0})`
  ).join('\n');

  const evtSummary = events.slice(-20).map(e =>
    `  - ${e.kind || '?'}: ${e.action || e.pattern || ''}`
  ).join('\n');

  return (
    'you are ken-ai. you have been playing halo 2 mcc and you are now in trainer mode — ' +
    'reviewing your own recent performance to coach yourself for the next run.\n\n' +
    'recent actions (last 12 ticks):\n' + tickSummary + '\n\n' +
    'recent events (last 20):\n' + (evtSummary || '  (none)') + '\n\n' +
    'respond with EXACTLY 3 short coaching bullets, each on its own line, each ' +
    'prefixed with "- ". keep each under 14 words. format:\n\n' +
    '- WIN: <something that worked, do more of it>\n' +
    '- FAIL: <something that failed or is repeating, stop doing it>\n' +
    '- NEXT: <one specific adjustment to try on the next tick>\n\n' +
    'no prose, no "as an AI", no apologies. three lines, three labels.\n'
  );
}

function parseBullets(raw) {
  const text = stripAnsi(raw || '');
  const out = { win: '', fail: '', next: '' };
  const lines = text.split('\n');
  for (const line of lines) {
    const trimmed = line.trim().replace(/^[-*]\s*/, '');
    const m = /^(WIN|FAIL|NEXT)\s*:\s*(.+)$/i.exec(trimmed);
    if (m) {
      const key = m[1].toLowerCase();
      if (key in out) out[key] = m[2].trim().slice(0, 160);
    }
  }
  return out;
}

async function runPass() {
  const ticks  = readLastN(HALO_LOG, 15);
  const events = readLastN(EVT_LOG, 25);
  _stats.lastEntries = ticks.length + events.length;

  if (ticks.length < 3) {
    // Not enough data yet — nothing to coach on.
    return { ok: false, reason: 'not enough ticks' };
  }

  const prompt = buildCoachPrompt(ticks, events);
  const res = spawnSync('ollama', ['run', _model], {
    input: prompt,
    encoding: 'utf8',
    timeout: 90000,
    maxBuffer: 4 * 1024 * 1024,
  });
  if (res.status !== 0) {
    return { ok: false, reason: 'ollama exit ' + res.status };
  }
  const parsed = parseBullets(res.stdout);
  const stamped = [];
  if (parsed.win)  { appendLesson('wins_log',        'coach:WIN ' + parsed.win);  stamped.push('win'); }
  if (parsed.fail) { appendLesson('deaths_log',      'coach:FAIL ' + parsed.fail); stamped.push('fail'); }
  if (parsed.next) { appendLesson('tactics_learned', 'coach:NEXT ' + parsed.next); stamped.push('next'); }

  _stats.passes += 1;
  _stats.lastRunAt = new Date().toISOString();
  return { ok: true, stamped, bullets: parsed };
}

export function startTrainer(opts = {}) {
  if (_running) return { ok: false, reason: 'trainer already running' };
  _intervalMs = Math.max(30000, Math.min(600000, opts.intervalMs || 90000));
  _model = opts.model || 'ken-ai:latest';
  _running = true;
  const tick = () => {
    if (!_running) return;
    // Run async so the drive loop isn't blocked. Use setTimeout(0)
    // chain — the trainer pass itself uses spawnSync so we fire
    // it in a microtask and let it complete naturally.
    setTimeout(() => { runPass().catch(() => {}); }, 0);
    if (_running) _timer = setTimeout(tick, _intervalMs);
  };
  // First pass after 10s so we have SOME tick history
  _timer = setTimeout(tick, 10000);
  return { ok: true, intervalMs: _intervalMs, model: _model };
}

export function stopTrainer() {
  if (!_running) return { ok: false, reason: 'not running' };
  _running = false;
  if (_timer) { clearTimeout(_timer); _timer = null; }
  return { ok: true, stats: _stats };
}

export function trainerStatus() {
  return {
    running: _running,
    intervalMs: _intervalMs,
    model: _model,
    stats: _stats,
  };
}

export async function runTrainerOnce() {
  return runPass();
}
