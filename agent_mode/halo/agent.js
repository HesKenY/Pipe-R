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
const HALO_LOG        = join(MEMORIES_DIR, KEN_AI_SLUG, 'halo-log.jsonl');
const HALO_WATCH_LOG  = join(MEMORIES_DIR, KEN_AI_SLUG, 'halo-watch-log.jsonl');
const NOTES_PATH      = join(MEMORIES_DIR, KEN_AI_SLUG, 'notes.md');
const GUIDE_PATH      = join(__dirname, 'halo2-guide.md');
const TICK_PY         = join(__dirname, 'halo_tick.py');
const DO_PY           = join(__dirname, 'halo_do.py');

// Cache notes.md + guide contents on first read. Both are large
// files that bloat the prompt; we read them once per process and
// let a restart pick up edits.
let _notesCache = null;
let _guideCache = null;
function readKenNotes() {
  if (_notesCache != null) return _notesCache;
  try { _notesCache = existsSync(NOTES_PATH) ? readFileSync(NOTES_PATH, 'utf8') : ''; }
  catch (e) { _notesCache = ''; }
  return _notesCache;
}
function readHaloGuide() {
  if (_guideCache != null) return _guideCache;
  try { _guideCache = existsSync(GUIDE_PATH) ? readFileSync(GUIDE_PATH, 'utf8') : ''; }
  catch (e) { _guideCache = ''; }
  return _guideCache;
}

const VALID_ACTIONS = new Set([
  'move_fwd', 'move_back', 'strafe_left', 'strafe_right',
  'jump', 'crouch', 'sprint', 'reload', 'interact', 'grenade',
  'melee', 'weapon_slot_1', 'switch_grenade', 'flashlight',
  'dual_wield', 'scoreboard', 'fire', 'ads',
  'look_left', 'look_right', 'look_up', 'look_down',
  'noop', 'pause'
]);

let _loopTimer = null;
let _running = false;
let _mode = 'observe'; // 'observe' | 'drive'
let _history = [];
let _pythonBin = process.env.PYTHON || 'python';
let _model = 'ken-ai:latest';
let _tickMs = 4000;
let _stats = { ticks: 0, startedAt: null, lastAction: null, lastState: null, lastTickMs: null, mode: 'observe', observeTicks: 0, handoffAt: null };
let _dreamEveryTicks = 20;
let _ticksSinceDream = 0;
// Auto-handoff thresholds: after N observations the agent is
// allowed to flip itself from observe → drive, but only if the
// last K observations show it has real intent (not noop spam).
let _handoffMinObserveTicks = 25;
let _handoffWindow = 10;
let _handoffNonNoopRate = 0.5;

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

/* ── Format the current HUD state as compact JSON. ── */
function stateStr(state) {
  return JSON.stringify({
    ammo: state.ammo, shield: state.shield,
    radar: state.radar, center: state.center,
    screen: `${state.w}x${state.h}`,
  });
}

/* ── DRIVE-mode prompt: the agent is in control, must pick
   exactly one action token from the vocabulary. ── */
function buildDrivePrompt(state, history) {
  const notes = readKenNotes();
  const guide = readHaloGuide();
  const historyBlock = history.slice(-3).map((h, i) =>
    `turn ${i + 1}: you did ${h.action} — after: ammo=${h.stateAfter?.ammo || '?'} shield=${h.stateAfter?.shield || '?'}`
  ).join('\n');

  const stateIsEmpty = !state.ammo && !state.shield && !state.radar && !state.center;
  const antiNoopHint = stateIsEmpty
    ? '\n\nHUD OCR is empty this tick. PICK A MOVEMENT ACTION (move_fwd, strafe_left, strafe_right, look_left, or look_right). DO NOT pick noop.'
    : '\n\nPick the most useful action for what you can see. noop is only correct if you are in a menu or cutscene.';

  return (
    (notes ? notes + '\n\n---\n\n' : '') +
    (guide ? '# HALO 2 REFERENCE\n\n' + guide + '\n\n---\n\n' : '') +
    'you are playing halo mcc right now, live. the HUD OCR below is your only eyes (tesseract cropped on a 5120x1440 ultrawide — it is noisy and will often be empty). trust the history and the reference guide more than the raw OCR.\n\n' +
    'respond with EXACTLY one action word from this list — nothing else, no prose, no punctuation:\n' +
    '  move_fwd move_back strafe_left strafe_right jump crouch sprint\n' +
    '  reload interact grenade melee weapon_slot_1 switch_grenade\n' +
    '  fire ads look_left look_right look_up look_down\n' +
    '  dual_wield flashlight scoreboard noop pause\n\n' +
    (historyBlock ? 'recent history (last 3 turns):\n' + historyBlock + '\n\n' : '') +
    'current hud state:\n' + stateStr(state) +
    antiNoopHint + '\n\n' +
    'your one-word action:'
  );
}

/* ── OBSERVE-mode prompt: the agent is WATCHING Ken play. It
   does NOT fire actions. Its job is to describe what it sees
   and what it would do, so every observation becomes training
   data for a future handoff to drive mode. ── */
function buildObservePrompt(state, history) {
  const notes = readKenNotes();
  const guide = readHaloGuide();
  const historyBlock = history.slice(-3).map((h, i) =>
    `turn ${i + 1}: state=${JSON.stringify({ammo:h.stateBefore?.ammo,shield:h.stateBefore?.shield})} → you_would_have: ${h.action}`
  ).join('\n');

  return (
    (notes ? notes + '\n\n---\n\n' : '') +
    (guide ? '# HALO 2 REFERENCE\n\n' + guide + '\n\n---\n\n' : '') +
    'OBSERVE MODE — ken is playing halo mcc right now, you are watching over his shoulder. you do NOT control the game. your job is to study his play so you can take over later.\n\n' +
    'given the HUD OCR state below, respond with a SINGLE LINE in this exact format:\n' +
    '  ACTION|NOTE\n\n' +
    'where ACTION is the ONE action word from the vocabulary that YOU would fire if you were driving right now (same 20-word list as drive mode: move_fwd, strafe_left, fire, ads, reload, grenade, melee, look_left, etc.), and NOTE is a 5-12 word observation about what ken seems to be doing + what the situation is.\n\n' +
    'examples:\n' +
    '  look_right|shield bar visible, ken advancing down corridor\n' +
    '  fire|center has weapon model, target in frame\n' +
    '  move_fwd|empty hud, probably transition between rooms\n' +
    '  grenade|red blip center, enemy group visible\n\n' +
    (historyBlock ? 'recent observations (last 3 turns):\n' + historyBlock + '\n\n' : '') +
    'current hud state:\n' + stateStr(state) + '\n\n' +
    'your ACTION|NOTE line:'
  );
}

/* ── Ask ken-ai (or whatever model is set) what to do. Parses
   to a known action or falls back to noop so the loop never
   crashes on bad output. Works for both drive and observe mode
   — observe replies look like "ACTION|note" which we split. ── */
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
    return { action: 'noop', note: '', raw: '', elapsed, error: 'ollama exit ' + res.status };
  }
  const raw = stripAnsi(res.stdout || '').trim();

  // Observe-mode format: ACTION|note. Split on the pipe.
  let actionPart = raw;
  let notePart = '';
  const pipeIdx = raw.indexOf('|');
  if (pipeIdx > 0) {
    actionPart = raw.slice(0, pipeIdx);
    notePart = raw.slice(pipeIdx + 1).trim();
  }

  // Extract the first valid action word anywhere in actionPart.
  const tokens = actionPart.toLowerCase().split(/[^a-z_]+/).filter(Boolean);
  const hit = tokens.find(t => VALID_ACTIONS.has(t));
  return { action: hit || 'noop', note: notePart, raw, elapsed };
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

/* ── Append one row to the watch log (observe mode). ── */
function logWatch(entry) {
  ensureLogDir();
  try { appendFileSync(HALO_WATCH_LOG, JSON.stringify(entry) + '\n', 'utf8'); }
  catch (e) { /* best-effort */ }
}

/* ── Run exactly one tick end-to-end. Mode decides whether the
   chosen action is actually fired (drive) or only logged as an
   observation of what the agent WOULD have done (observe). ── */
export async function tickOnce(forceMode) {
  const t0 = Date.now();
  const mode = forceMode || _mode;
  const state = captureState();
  if (state.error) {
    const entry = { at: new Date().toISOString(), error: state.error, stage: 'capture', mode };
    if (mode === 'observe') logWatch(entry); else logTick(entry);
    return entry;
  }

  const prompt = mode === 'observe'
    ? buildObservePrompt(state, _history)
    : buildDrivePrompt(state, _history);
  const decision = askAgent(prompt);

  let firing = { ok: true, detail: null };
  if (mode === 'drive') {
    firing = fireAction(decision.action, 160);
  }

  // Second state snapshot after the action (drive) or after the
  // same delay (observe, so the watch log captures a realistic
  // state pair for future imitation-learning).
  const stateAfter = captureState();

  const entry = {
    at: new Date().toISOString(),
    mode,
    model: _model,
    stateBefore: state,
    stateAfter: stateAfter.error ? null : stateAfter,
    promptLen: prompt.length,
    rawResponse: (decision.raw || '').slice(0, 280),
    action: decision.action,
    note: decision.note || null,
    actionDetail: firing.detail || null,
    fired: mode === 'drive',
    inferenceMs: decision.elapsed,
    totalMs: Date.now() - t0,
    error: decision.error || firing.parseError || null,
  };

  _history.push({
    action: entry.action,
    mode,
    stateBefore: state,
    stateAfter: entry.stateAfter,
  });
  if (_history.length > 16) _history = _history.slice(-16);
  _stats.ticks += 1;
  _stats.lastAction = entry.action;
  _stats.lastState = state;
  _stats.lastTickMs = entry.totalMs;
  _stats.mode = mode;

  if (mode === 'observe') {
    logWatch(entry);
    _stats.observeTicks += 1;
    // Auto-handoff check: once the agent has watched enough and
    // its recent observations show real intent, it flips itself
    // to drive mode and takes control. No manual button press.
    if (_stats.observeTicks >= _handoffMinObserveTicks && _mode === 'observe') {
      const recent = _history.slice(-_handoffWindow);
      const nonNoop = recent.filter(h => h.action && h.action !== 'noop').length;
      if (recent.length >= _handoffWindow && (nonNoop / recent.length) >= _handoffNonNoopRate) {
        _mode = 'drive';
        _stats.mode = 'drive';
        _stats.handoffAt = new Date().toISOString();
        const handoffEntry = {
          at: _stats.handoffAt,
          kind: 'handoff',
          from: 'observe',
          to: 'drive',
          reason: 'observeTicks=' + _stats.observeTicks +
                  ' nonNoopRate=' + (nonNoop / recent.length).toFixed(2),
          model: _model,
        };
        logTick(handoffEntry);
        logWatch(handoffEntry);
      }
    }
  } else {
    logTick(entry);
  }

  // Auto-dream hook: every N ticks, fire a reflection pass so
  // ken-ai consolidates its own recent halo attempts into notes.md.
  // Runs non-blocking so the next tick fires on schedule.
  _ticksSinceDream += 1;
  if (_ticksSinceDream >= _dreamEveryTicks) {
    _ticksSinceDream = 0;
    queueAutoDream();
  }

  return entry;
}

/* ── Fire a dream pass for the current model in the background.
   Best-effort — any failure is logged but doesn't stop the loop. ── */
function queueAutoDream() {
  setTimeout(async () => {
    try {
      const { dreamAgent } = await import('../core/dreams.js');
      const { AgentRegistry } = await import('../core/registry.js');
      const reg = new AgentRegistry();
      const agent = (reg.agents || []).find(a => (a.base || a.id) === _model);
      if (!agent) return;
      await dreamAgent(agent, { windowSize: 12 });
    } catch (e) { /* silent */ }
  }, 50);
}

export function startLoop(opts = {}) {
  if (_running) return { ok: false, reason: 'already running' };
  _tickMs = Math.max(2000, Math.min(30000, opts.tickMs || 4000));
  _model = opts.model || 'ken-ai:latest';
  _mode = opts.mode === 'drive' ? 'drive' : 'observe'; // safe default
  _running = true;
  _stats.startedAt = new Date().toISOString();
  _stats.ticks = 0;
  _stats.observeTicks = 0;
  _stats.handoffAt = null;
  _stats.mode = _mode;
  _history = [];
  _ticksSinceDream = 0;
  const fire = async () => {
    if (!_running) return;
    try { await tickOnce(); }
    catch (e) { logTick({ at: new Date().toISOString(), error: 'loop: ' + e.message }); }
    if (_running) _loopTimer = setTimeout(fire, _tickMs);
  };
  fire();
  return { ok: true, tickMs: _tickMs, model: _model, mode: _mode };
}

export function stopLoop() {
  if (!_running) return { ok: false, reason: 'not running' };
  _running = false;
  if (_loopTimer) { clearTimeout(_loopTimer); _loopTimer = null; }
  return { ok: true, ranTicks: _stats.ticks, startedAt: _stats.startedAt, handoffAt: _stats.handoffAt };
}

/* ── Manual mode flip — useful if Ken wants to force handoff
   now without waiting for the auto-threshold. ── */
export function setMode(mode) {
  if (mode !== 'observe' && mode !== 'drive') {
    return { ok: false, reason: 'invalid mode' };
  }
  _mode = mode;
  _stats.mode = mode;
  if (mode === 'drive' && !_stats.handoffAt) _stats.handoffAt = new Date().toISOString();
  return { ok: true, mode: _mode };
}

export function status() {
  return {
    running: _running,
    mode: _mode,
    tickMs: _tickMs,
    model: _model,
    stats: _stats,
    historyLength: _history.length,
    handoffThresholds: {
      minObserveTicks: _handoffMinObserveTicks,
      window: _handoffWindow,
      nonNoopRate: _handoffNonNoopRate,
    },
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

export function readRecentWatchLog(limit = 50) {
  if (!existsSync(HALO_WATCH_LOG)) return [];
  try {
    const raw = readFileSync(HALO_WATCH_LOG, 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    const out = [];
    for (let i = lines.length - 1; i >= 0 && out.length < limit; i--) {
      try { out.push(JSON.parse(lines[i])); }
      catch (e) { /* skip */ }
    }
    return out;
  } catch (e) { return []; }
}
