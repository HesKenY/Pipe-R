/* ══════════════════════════════════════════════════════
   CHERP / Pipe-R — Halo MCC learning agent
   ──────────────────────────────────────────────────────
   Gives Ken AI a closed game loop against Halo MCC:

     screenshot + HUD OCR  →  state JSON
     state + history       →  prompt Ken AI (ollama run)
     parse action          →  fire keypress
     log state+action+when →  halo-log.jsonl (under ken-ai
                              memory dir so dreams.js can
                              reflect on it later)
     wait N seconds        →  repeat

   The loop is explicit start/stop/tick only — never fires on
   boot. 4-second default tick so Ken can `/api/halo/stop`
   faster than the agent can do damage. Model inference alone
   takes ~8-12 s on a 14B Ollama model so effective rate is
   ~one action every 10-15 s. Plenty slow for "learning" but
   nowhere near realtime.

   Action vocabulary (single word per turn, case-insensitive):
     move_fwd    move_back    strafe_left   strafe_right
     jump        crouch       sprint        reload
     interact    grenade      melee         swap_weapon
     fire        ads          look_left     look_right
     look_up     look_down    noop          pause

   ══════════════════════════════════════════════════════ */

import { spawn, spawnSync } from 'node:child_process';
import { readFileSync, existsSync, mkdirSync, appendFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEMORIES_DIR = join(__dirname, '..', 'memories');
const KEN_AI_SLUG = 'ken-ai-latest';
const HALO_LOG    = join(MEMORIES_DIR, KEN_AI_SLUG, 'halo-log.jsonl');
const TICK_PY     = join(__dirname, 'halo_tick.py');
const DO_PY       = join(__dirname, 'halo_do.py');

const VALID_ACTIONS = new Set([
  'move_fwd', 'move_back', 'strafe_left', 'strafe_right',
  'jump', 'crouch', 'sprint', 'reload', 'interact', 'grenade',
  'melee', 'swap_weapon', 'fire', 'ads', 'look_left', 'look_right',
  'look_up', 'look_down', 'noop', 'pause'
]);

let _loopTimer = null;
let _running = false;
let _history = [];
let _pythonBin = process.env.PYTHON || 'python';
let _model = 'ken-ai:latest';
let _tickMs = 4000;
let _stats = { ticks: 0, startedAt: null, lastAction: null, lastState: null, lastTickMs: null };

function ensureLogDir() {
  const dir = join(MEMORIES_DIR, KEN_AI_SLUG);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

function stripAnsi(s) {
  return String(s || '')
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '');
}

/* ── Pull a fresh state snapshot via halo_tick.py ── */
function captureState() {
  const res = spawnSync(_pythonBin, [TICK_PY], {
    encoding: 'utf8',
    timeout: 12000,
    maxBuffer: 8 * 1024 * 1024,
  });
  if (res.status !== 0) {
    return { error: 'halo_tick.py exit ' + res.status, stderr: (res.stderr || '').slice(0, 400) };
  }
  try {
    const line = (res.stdout || '').split('\n').find(l => l.trim().startsWith('{'));
    if (!line) return { error: 'no json from halo_tick.py' };
    return JSON.parse(line);
  } catch (e) {
    return { error: 'parse: ' + e.message };
  }
}

/* ── Build the ollama prompt for one tick.
   Includes the last 3 (state, action) pairs for context so
   the agent can chain thinking across ticks. The system line
   is injected by the model's SYSTEM profile + notes.md (which
   got the Halo coaching addendum 2026-04-13). ── */
function buildPrompt(state, history) {
  const stateStr = JSON.stringify({
    ammo: state.ammo, shield: state.shield,
    radar: state.radar, center: state.center,
    screen: `${state.w}x${state.h}`,
  });

  const historyBlock = history.slice(-3).map((h, i) =>
    `turn ${i + 1}: you did ${h.action} — after: ammo=${h.stateAfter?.ammo || '?'} shield=${h.stateAfter?.shield || '?'}`
  ).join('\n');

  return (
    'you are playing halo mcc. the hud OCR below is your only eyes.\n' +
    'respond with EXACTLY one action word from this list — no prose, no punctuation, no explanation:\n' +
    '  move_fwd move_back strafe_left strafe_right jump crouch sprint\n' +
    '  reload interact grenade melee swap_weapon fire ads\n' +
    '  look_left look_right look_up look_down noop pause\n\n' +
    (historyBlock ? 'recent history:\n' + historyBlock + '\n\n' : '') +
    'current state (HUD text from OCR — may be noisy):\n' + stateStr + '\n\n' +
    'your one-word action:'
  );
}

/* ── Ask ken-ai what to do. Parses to a known action or falls
   back to "noop" so the loop never crashes on bad output. ── */
function askAgent(prompt) {
  const t0 = Date.now();
  const res = spawnSync('ollama', ['run', _model], {
    input: prompt,
    encoding: 'utf8',
    timeout: 60000,
    maxBuffer: 4 * 1024 * 1024,
  });
  const elapsed = Date.now() - t0;
  if (res.status !== 0) {
    return { action: 'noop', raw: '', elapsed, error: 'ollama exit ' + res.status };
  }
  const raw = stripAnsi(res.stdout || '').trim();
  // Extract the first valid action word anywhere in the response.
  const tokens = raw.toLowerCase().split(/[^a-z_]+/).filter(Boolean);
  const hit = tokens.find(t => VALID_ACTIONS.has(t));
  return { action: hit || 'noop', raw, elapsed };
}

/* ── Fire the chosen action via halo_do.py ── */
function fireAction(action, durationMs = 150) {
  if (!VALID_ACTIONS.has(action)) action = 'noop';
  const res = spawnSync(_pythonBin, [DO_PY, action, String(durationMs)], {
    encoding: 'utf8',
    timeout: 4000,
  });
  if (res.status !== 0) return { ok: false, stderr: (res.stderr || '').slice(0, 300) };
  try {
    const line = (res.stdout || '').split('\n').find(l => l.trim().startsWith('{'));
    return Object.assign({ ok: true }, line ? JSON.parse(line) : {});
  } catch (e) {
    return { ok: false, parseError: e.message };
  }
}

/* ── Log one full tick to halo-log.jsonl.
   Shape: { at, state, prompt_len, action, action_detail, elapsedMs } ── */
function logTick(entry) {
  ensureLogDir();
  try { appendFileSync(HALO_LOG, JSON.stringify(entry) + '\n', 'utf8'); }
  catch (e) { /* best-effort */ }
}

/* ── Run exactly one tick end-to-end. Exported so an /api/halo/tick
   endpoint can fire a single step for testing without starting the
   whole loop. ── */
export async function tickOnce() {
  const t0 = Date.now();
  const state = captureState();
  if (state.error) {
    const entry = { at: new Date().toISOString(), error: state.error, stage: 'capture' };
    logTick(entry);
    return entry;
  }

  const prompt = buildPrompt(state, _history);
  const decision = askAgent(prompt);
  const firing = fireAction(decision.action, 160);

  // Second state snapshot after the action so ken-ai can see
  // the outcome in its next turn's history block.
  const stateAfter = captureState();

  const entry = {
    at: new Date().toISOString(),
    model: _model,
    stateBefore: state,
    stateAfter: stateAfter.error ? null : stateAfter,
    promptLen: prompt.length,
    rawResponse: (decision.raw || '').slice(0, 240),
    action: decision.action,
    actionDetail: firing.detail || null,
    inferenceMs: decision.elapsed,
    totalMs: Date.now() - t0,
    error: decision.error || firing.parseError || null,
  };

  _history.push({ action: entry.action, stateBefore: state, stateAfter: entry.stateAfter });
  if (_history.length > 16) _history = _history.slice(-16);
  _stats.ticks += 1;
  _stats.lastAction = entry.action;
  _stats.lastState = state;
  _stats.lastTickMs = entry.totalMs;

  logTick(entry);
  return entry;
}

export function startLoop(opts = {}) {
  if (_running) return { ok: false, reason: 'already running' };
  _tickMs = Math.max(2000, Math.min(30000, opts.tickMs || 4000));
  _model = opts.model || 'ken-ai:latest';
  _running = true;
  _stats.startedAt = new Date().toISOString();
  _stats.ticks = 0;
  _history = [];
  const fire = async () => {
    if (!_running) return;
    try { await tickOnce(); }
    catch (e) { logTick({ at: new Date().toISOString(), error: 'loop: ' + e.message }); }
    if (_running) _loopTimer = setTimeout(fire, _tickMs);
  };
  fire();
  return { ok: true, tickMs: _tickMs, model: _model };
}

export function stopLoop() {
  if (!_running) return { ok: false, reason: 'not running' };
  _running = false;
  if (_loopTimer) { clearTimeout(_loopTimer); _loopTimer = null; }
  return { ok: true, ranTicks: _stats.ticks, startedAt: _stats.startedAt };
}

export function status() {
  return {
    running: _running,
    tickMs: _tickMs,
    model: _model,
    stats: _stats,
    historyLength: _history.length,
  };
}

export function readRecentLog(limit = 50) {
  if (!existsSync(HALO_LOG)) return [];
  try {
    const raw = readFileSync(HALO_LOG, 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    const out = [];
    for (let i = lines.length - 1; i >= 0 && out.length < limit; i--) {
      try { out.push(JSON.parse(lines[i])); }
      catch (e) { /* skip */ }
    }
    return out;
  } catch (e) { return []; }
}
