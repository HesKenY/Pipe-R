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
import { readFileSync, existsSync, mkdirSync, appendFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { getMemory, appendLesson, stampEvent } from './memory.js';
import { extractFromTick } from './events.js';
import { runPostMortem } from './post_mortem.js';
import { promptBlock as trainingPromptBlock, detectTrainers } from './training_mode.js';
import { rebuildIndex, buildContextBlock } from './index.js';
import { pickTacticalAction, resetTacticalState } from './tactical.js';
import { jumpstartPromptBlock } from './jumpstart.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEMORIES_DIR = join(__dirname, '..', 'memories');
const KEN_AI_SLUG = 'ken-ai-latest';
const HALO_LOG        = join(MEMORIES_DIR, KEN_AI_SLUG, 'halo-log.jsonl');
const HALO_WATCH_LOG  = join(MEMORIES_DIR, KEN_AI_SLUG, 'halo-watch-log.jsonl');
const HALO_KEYLOG     = join(MEMORIES_DIR, KEN_AI_SLUG, 'halo-keylog.jsonl');
const HALO_VISION_CACHE = join(MEMORIES_DIR, KEN_AI_SLUG, 'halo-vision-cache.json');
const NOTES_PATH      = join(MEMORIES_DIR, KEN_AI_SLUG, 'notes.md');
const GUIDE_PATH      = join(__dirname, 'halo2-guide.md');
const TICK_PY         = join(__dirname, 'halo_tick.py');
const DO_PY           = join(__dirname, 'halo_do.py');
const AIM_PY          = join(__dirname, 'aimbot.py');
const KEYLOG_PY       = join(__dirname, 'halo_keylog.py');
const VISION_PY       = join(__dirname, 'halo_vision.py');
const AIM_DAEMON_PY   = join(__dirname, 'halo_aim_daemon.py');

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

/* Read the last N keylog events Ken has produced. Used in
   observe-mode prompts so the agent sees what Ken actually
   pressed, not just what was on screen. Uncached — the
   keylog daemon writes line-buffered, every read is fresh. */
function readRecentKeypresses(limit = 25) {
  if (!existsSync(HALO_KEYLOG)) return [];
  try {
    const raw = readFileSync(HALO_KEYLOG, 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    const out = [];
    for (let i = lines.length - 1; i >= 0 && out.length < limit; i--) {
      try {
        const row = JSON.parse(lines[i]);
        // Skip system lines and key-ups (down events are enough
        // to reconstruct intent — ups double the noise).
        if (row.kind === 'system') continue;
        if (row.dir === 'up') continue;
        out.push(row);
      } catch (e) { /* skip */ }
    }
    return out.reverse();
  } catch (e) { return []; }
}

/* ── Keylog daemon management. Spawn halo_keylog.py as a
   long-lived child process. The process streams events to
   halo-keylog.jsonl and exits on SIGTERM. ── */
let _keylogProc = null;
export function startKeylog(opts = {}) {
  if (_keylogProc && !_keylogProc.killed) {
    return { ok: false, reason: 'already running', pid: _keylogProc.pid };
  }
  const args = [KEYLOG_PY];
  if (opts.stopAfter) args.push('--stop-after', String(opts.stopAfter));
  if (opts.skipMouse) args.push('--skip-mouse');
  try {
    _keylogProc = spawn(_pythonBin, args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });
  } catch (e) {
    return { ok: false, reason: 'spawn failed: ' + e.message };
  }
  _keylogProc.on('exit', (code) => { _keylogProc = null; });
  return { ok: true, pid: _keylogProc.pid };
}
export function stopKeylog() {
  if (!_keylogProc || _keylogProc.killed) {
    return { ok: false, reason: 'not running' };
  }
  try {
    _keylogProc.kill('SIGTERM');
    // Windows: SIGTERM doesn't always deliver, fall back to
    // SIGKILL after a short grace period.
    setTimeout(() => { try { if (_keylogProc && !_keylogProc.killed) _keylogProc.kill('SIGKILL'); } catch (e) {} }, 500);
  } catch (e) {
    return { ok: false, reason: 'kill failed: ' + e.message };
  }
  const pid = _keylogProc.pid;
  _keylogProc = null;
  return { ok: true, pid };
}
export function keylogStatus() {
  return {
    running: !!(_keylogProc && !_keylogProc.killed),
    pid: _keylogProc?.pid || null,
  };
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
let _tickMs = 4000; // base tick — used for observe mode + as a fallback
let _lifelike = true; // drive mode uses per-action timing when true
let _stats = { ticks: 0, startedAt: null, lastAction: null, lastState: null, lastTickMs: null, mode: 'observe', observeTicks: 0, handoffAt: null };
let _dreamEveryTicks = 20;
let _ticksSinceDream = 0;

// Per-action timing table. `nextDelayMs` is the time to wait
// BEFORE the next decision after this action fires — short for
// combat so bursts feel responsive, long for reload/noop which
// would feel mechanical if spammed. `holdMs` is how long the
// primary key is held (for hold-type actions only — taps are
// instant). All values get ±25% jitter in pickDelay/pickHold.
const ACTION_TIMING = {
  fire:          { nextDelayMs: 260,  holdMs: 80,  followThroughs: 2 },
  ads:           { nextDelayMs: 500,  holdMs: 380, followThroughs: 0 },
  reload:        { nextDelayMs: 1500, holdMs: 40,  followThroughs: 0 },
  grenade:       { nextDelayMs: 1100, holdMs: 40,  followThroughs: 0 },
  melee:         { nextDelayMs: 450,  holdMs: 40,  followThroughs: 0 },
  interact:      { nextDelayMs: 600,  holdMs: 40,  followThroughs: 0 },
  move_fwd:      { nextDelayMs: 800,  holdMs: 720, followThroughs: 0 },
  move_back:     { nextDelayMs: 800,  holdMs: 620, followThroughs: 0 },
  strafe_left:   { nextDelayMs: 550,  holdMs: 480, followThroughs: 0 },
  strafe_right:  { nextDelayMs: 550,  holdMs: 480, followThroughs: 0 },
  jump:          { nextDelayMs: 420,  holdMs: 40,  followThroughs: 0 },
  crouch:        { nextDelayMs: 700,  holdMs: 520, followThroughs: 0 },
  sprint:        { nextDelayMs: 900,  holdMs: 800, followThroughs: 0 },
  look_left:     { nextDelayMs: 420,  holdMs: 40,  followThroughs: 1 },
  look_right:    { nextDelayMs: 420,  holdMs: 40,  followThroughs: 1 },
  look_up:       { nextDelayMs: 380,  holdMs: 40,  followThroughs: 0 },
  look_down:     { nextDelayMs: 380,  holdMs: 40,  followThroughs: 0 },
  weapon_slot_1: { nextDelayMs: 700,  holdMs: 40,  followThroughs: 0 },
  switch_grenade:{ nextDelayMs: 550,  holdMs: 40,  followThroughs: 0 },
  dual_wield:    { nextDelayMs: 700,  holdMs: 40,  followThroughs: 0 },
  flashlight:    { nextDelayMs: 350,  holdMs: 40,  followThroughs: 0 },
  scoreboard:    { nextDelayMs: 650,  holdMs: 40,  followThroughs: 0 },
  noop:          { nextDelayMs: 1800, holdMs: 0,   followThroughs: 0 },
  pause:         { nextDelayMs: 2500, holdMs: 40,  followThroughs: 0 },
};

function jitter(base, ratio = 0.25) {
  const delta = base * ratio;
  return Math.max(50, Math.floor(base + (Math.random() * 2 - 1) * delta));
}

function pickNextDelay(action) {
  if (!_lifelike || _mode === 'observe') return _tickMs;
  const t = ACTION_TIMING[action] || ACTION_TIMING.noop;
  return jitter(t.nextDelayMs);
}

function pickHoldMs(action) {
  const t = ACTION_TIMING[action] || { holdMs: 150 };
  return jitter(t.holdMs, 0.2);
}

function pickFollowThroughs(action) {
  const t = ACTION_TIMING[action] || { followThroughs: 0 };
  return t.followThroughs;
}
// Auto-handoff thresholds: after N observations the agent is
// allowed to flip itself from observe → drive, but only if the
// last K observations show it has real intent (not noop spam).
let _handoffMinObserveTicks = 25;
let _handoffWindow = 10;
let _handoffNonNoopRate = 0.5;
// Aim assist — when true, every fire/ads action runs aimbot.py
// first to snap the mouse onto the nearest enemy-signature blob
// before firing. Default on in drive mode; no-op in observe.
let _aimAssist = true;
let _aimPalette = 'all';
let _aimMinConfidence = 0.03;

// Separate aim loop — runs INDEPENDENT of the observe/drive
// game loop so Ken can turn on aimbot assist while he's playing
// himself, no agent required. Tight 250ms cycle. Every cycle
// runs aimbot.py --snap; fire only on explicit opts.
let _aimTimer = null;
let _aimRunning = false;
let _aimIntervalMs = 250;
let _aimFire = false;      // single-shot auto-fire after snap
let _aimEngage = false;    // full engagement burst mode (overrides _aimFire)
let _aimBurstSize = 3;
let _aimShotDelay = 140;
let _aimMaxShots = 5;
let _aimStats = { scans: 0, hits: 0, shots: 0, lastConfidence: 0, startedAt: null };

// Pure reactive tactical loop — zero LLM inference. Runs at
// 150-200ms cadence using tactical.js state machine rules.
// Halo eats the GPU so LLM inference is 15s/tick; tactical
// mode keeps decisions at real frame rate by skipping the LLM
// entirely and using pure state-machine logic.
let _tacticalRunning = false;
let _tacticalTimer = null;
let _tacticalIntervalMs = 180;
let _tacticalPlan = 'advance';
let _tacticalStepIdx = 0;
let _tacticalStats = { ticks: 0, startedAt: null, lastAction: null, fired: 0 };

async function tacticalTick() {
  if (!_tacticalRunning) return;
  try {
    // Capture current state (light touch — just motion / activity)
    const state = captureState();
    if (!state.error) {
      const pick = pickTacticalAction(state, _tacticalPlan, _tacticalStepIdx);
      _tacticalStepIdx += 1;
      const action = pick.action || 'move_fwd';
      // Fire the action via halo_do.py. No LLM, no subprocess
      // for state capture beyond halo_tick.py itself.
      const result = fireAction(action, 400);
      _tacticalStats.ticks += 1;
      _tacticalStats.lastAction = action;
      if (result && result.ok) _tacticalStats.fired += 1;
    }
  } catch (e) { /* swallow */ }
  if (_tacticalRunning) _tacticalTimer = setTimeout(tacticalTick, _tacticalIntervalMs);
}

export function startTacticalLoop(opts = {}) {
  if (_tacticalRunning) return { ok: false, reason: 'tactical loop already running' };
  _tacticalIntervalMs = Math.max(80, Math.min(2000, opts.intervalMs || 180));
  _tacticalPlan = opts.plan || 'advance';
  _tacticalRunning = true;
  _tacticalStepIdx = 0;
  _tacticalStats = { ticks: 0, startedAt: new Date().toISOString(), lastAction: null, fired: 0 };
  resetTacticalState();
  tacticalTick();
  return { ok: true, intervalMs: _tacticalIntervalMs, plan: _tacticalPlan };
}

export function stopTacticalLoop() {
  if (!_tacticalRunning) return { ok: false, reason: 'not running' };
  _tacticalRunning = false;
  if (_tacticalTimer) { clearTimeout(_tacticalTimer); _tacticalTimer = null; }
  return { ok: true, stats: _tacticalStats };
}

export function setTacticalPlan(plan) {
  _tacticalPlan = plan || 'advance';
  _tacticalStepIdx = 0;
  return { ok: true, plan: _tacticalPlan };
}

export function tacticalStatus() {
  return {
    running: _tacticalRunning,
    intervalMs: _tacticalIntervalMs,
    plan: _tacticalPlan,
    stats: _tacticalStats,
  };
}

// Persistent aim daemon for 30fps — skips spawnSync overhead by
// keeping a Python process alive and piping JSON commands.
let _aimDaemonProc = null;
let _aimDaemonReady = false;
let _aimDaemonBuffer = '';
let _aimDaemonWaiter = null;    // { resolve, reject, timeout }
let _aimDaemonInFlight = false;

function startAimDaemon() {
  if (_aimDaemonProc && !_aimDaemonProc.killed) return true;
  try {
    // -u flag forces Python stdout to be unbuffered so the
    // "daemon ready" line reaches Node immediately. Without
    // this, Windows block-buffers stdout when it isn't a TTY
    // and the daemon appears to never respond.
    _aimDaemonProc = spawn(_pythonBin, ['-u', AIM_DAEMON_PY], {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    });
  } catch (e) {
    _aimDaemonProc = null;
    return false;
  }
  _aimDaemonReady = false;
  _aimDaemonBuffer = '';
  _aimDaemonInFlight = false;

  _aimDaemonProc.stdout.on('data', (chunk) => {
    _aimDaemonBuffer += chunk.toString('utf8');
    // Drain any complete JSON lines
    let idx;
    while ((idx = _aimDaemonBuffer.indexOf('\n')) !== -1) {
      const line = _aimDaemonBuffer.slice(0, idx).trim();
      _aimDaemonBuffer = _aimDaemonBuffer.slice(idx + 1);
      if (!line) continue;
      let obj;
      try { obj = JSON.parse(line); }
      catch (e) { continue; }
      if (obj.daemon === 'ready') { _aimDaemonReady = true; continue; }
      if (_aimDaemonWaiter) {
        const w = _aimDaemonWaiter;
        _aimDaemonWaiter = null;
        _aimDaemonInFlight = false;
        clearTimeout(w.timeout);
        w.resolve(obj);
      }
    }
  });

  _aimDaemonProc.stderr.on('data', () => { /* swallow */ });
  _aimDaemonProc.on('exit', () => {
    _aimDaemonProc = null;
    _aimDaemonReady = false;
    if (_aimDaemonWaiter) {
      const w = _aimDaemonWaiter;
      _aimDaemonWaiter = null;
      _aimDaemonInFlight = false;
      clearTimeout(w.timeout);
      w.reject(new Error('daemon exited'));
    }
  });
  return true;
}

function stopAimDaemon() {
  if (!_aimDaemonProc) return;
  try {
    _aimDaemonProc.stdin.write(JSON.stringify({ op: 'quit' }) + '\n');
    setTimeout(() => {
      try { if (_aimDaemonProc && !_aimDaemonProc.killed) _aimDaemonProc.kill('SIGKILL'); }
      catch (e) {}
    }, 500);
  } catch (e) {
    try { _aimDaemonProc.kill('SIGKILL'); } catch (_) {}
  }
  _aimDaemonProc = null;
  _aimDaemonReady = false;
}

function daemonCommand(cmd, timeoutMs = 3000) {
  return new Promise((resolve, reject) => {
    if (!_aimDaemonProc || !_aimDaemonReady) {
      return reject(new Error('daemon not ready'));
    }
    if (_aimDaemonInFlight) {
      // Drop the request silently — keeps the loop non-blocking.
      return resolve({ skipped: true });
    }
    _aimDaemonInFlight = true;
    const timeout = setTimeout(() => {
      if (_aimDaemonWaiter) {
        _aimDaemonWaiter = null;
        _aimDaemonInFlight = false;
        reject(new Error('daemon timeout'));
      }
    }, timeoutMs);
    _aimDaemonWaiter = { resolve, reject, timeout };
    try {
      _aimDaemonProc.stdin.write(JSON.stringify(cmd) + '\n');
    } catch (e) {
      clearTimeout(timeout);
      _aimDaemonWaiter = null;
      _aimDaemonInFlight = false;
      reject(e);
    }
  });
}

// Vision cache — populated by the auto-vision loop using
// halo_vision.py (llama3.2-vision). Runs on a 20s cadence.
// The drive + observe prompts include whatever's in the cache.
let _visionCache = null; // { description, situation, enemies_visible, weapon_hint, at, elapsedMs }
let _visionTimer = null;
let _visionRunning = false;
let _visionIntervalMs = 20000;
let _visionModel = 'llama3.2-vision';

function ensureLogDir() {
  const dir = join(MEMORIES_DIR, KEN_AI_SLUG);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

function writeJsonSnapshot(path, value) {
  ensureLogDir();
  try {
    writeFileSync(path, JSON.stringify(value, null, 2), 'utf8');
  } catch (e) { /* best-effort */ }
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

/* ── Format the current HUD state as compact JSON. Includes
   the motion / brightness / activity fields from halo_tick.py
   v2 so the model has a reliable "something is happening"
   signal even when OCR is garbage. ── */
function stateStr(state) {
  return JSON.stringify({
    ammo:     state.ammo,
    shield:   state.shield,
    radar:    state.radar,
    center:   state.center,
    motion:   state.motion,   // 0..1, pixel-delta vs last frame
    activity: state.activity, // combat | transition | idle | death_screen | exploring
    bright:   state.bright,   // mean screen brightness 0..1
    screen:   `${state.w}x${state.h}`,
  });
}

/* ── Aim-loop stats snapshot for prompt injection. Tells
   the driver / observer how the aim assist has been doing
   recently — shots fired, hit rate, last confidence. ── */
function aimStatsSnapshot() {
  if (!_aimRunning) return null;
  return {
    running: true,
    engage: _aimEngage,
    scans: _aimStats.scans,
    hits: _aimStats.hits,
    shots: _aimStats.shots,
    lastConfidence: _aimStats.lastConfidence,
  };
}

/* ── DRIVE-mode prompt: indexed + slim. Uses the inverted
   keyword index to retrieve the top 6 most relevant memory
   bullets for the current state, instead of dumping the
   entire halo-memory.md + halo2-guide.md (30KB total). Keeps
   the prompt ~1-2KB so llama3.1:8b inference stays under 2s. ── */
function buildDrivePrompt(state, history) {
  const last3 = history.slice(-3).map(h => h.action || '?').join(' → ');
  const activity = state.activity || 'unknown';
  const shortState = `motion=${state.motion || 0} activity=${activity} shield="${(state.shield||'').slice(0,8)}" ammo="${(state.ammo||'').slice(0,8)}"`;

  // Retrieve only relevant context via the index.
  const contextBlock = buildContextBlock(state, history, 6);

  return (
    'halo mcc. pick ONE action word. no prose.\n' +
    'vocab: move_fwd move_back strafe_left strafe_right jump crouch sprint reload interact grenade melee fire ads look_left look_right look_up look_down noop\n' +
    'rules:\n' +
    '- activity=combat → fire or ads or strafe\n' +
    '- activity=idle → look_left or look_right\n' +
    '- activity=exploring → move_fwd\n' +
    '- never noop unless in a menu\n' +
    '- never repeat the same action 3 times in a row\n' +
    `state: ${shortState}\n` +
    `last 3: ${last3 || '(none)'}\n` +
    contextBlock +
    'action:'
  );
}

/* ── OBSERVE-mode prompt: the agent is WATCHING Ken play. It
   does NOT fire actions. Its job is to describe what it sees
   and what it would do, so every observation becomes training
   data for a future handoff to drive mode. ── */
function buildObservePrompt(state, history) {
  const notes = readKenNotes();
  const guide = readHaloGuide();
  const memo  = getMemory();
  const keys  = readRecentKeypresses(20);

  const historyBlock = history.slice(-3).map((h, i) =>
    `turn ${i + 1}: state=${JSON.stringify({ammo:h.stateBefore?.ammo,shield:h.stateBefore?.shield})} → you_would_have: ${h.action}`
  ).join('\n');

  // Condense ken's raw key events into a human-readable
  // trace the model can imitate. Only 'down' events are kept
  // because 'up' doubles the length without adding intent.
  const keysBlock = keys.length
    ? keys.map(k => {
        if (k.kind === 'key')   return `  ${k.at?.slice(11, 19)} key:${k.key}`;
        if (k.kind === 'mouse') return `  ${k.at?.slice(11, 19)} mouse:${k.button}`;
        return `  ${k.at?.slice(11, 19)} ${k.kind}`;
      }).join('\n')
    : '';

  return (
    (notes ? notes + '\n\n---\n\n' : '') +
    (guide ? '# HALO 2 REFERENCE\n\n' + guide + '\n\n---\n\n' : '') +
    (memo  ? memo  + '\n\n---\n\n' : '') +
    'OBSERVE MODE — ken is playing halo mcc right now, you are watching over his shoulder. you do NOT control the game. your job is to study his play so you can take over later.\n\n' +
    'given the HUD OCR state AND the recent list of actual keys ken pressed, respond with a SINGLE LINE in this format:\n' +
    '  ACTION|NOTE\n\n' +
    'where ACTION is the ONE action word from the vocabulary you would fire if YOU were driving right now, and NOTE is a 5-12 word observation describing what ken seems to be doing based on his keys + the screen.\n\n' +
    'examples:\n' +
    '  fire|ken burst-firing right mouse (ads) then left — enemy in frame\n' +
    '  move_fwd|ken holding w, walking through empty corridor\n' +
    '  grenade|ken hit f then strafed — probably threw at cover\n' +
    '  reload|ken pressed r, low ammo\n\n' +
    (keysBlock ? "ken's recent keypresses (oldest first):\n" + keysBlock + '\n\n' : '') +
    (historyBlock ? 'recent observations (last 3 turns):\n' + historyBlock + '\n\n' : '') +
    'current hud state:\n' + stateStr(state) + '\n\n' +
    jumpstartPromptBlock() +
    trainingPromptBlock() +
    'your ACTION|NOTE line:'
  );
}

/* ── Ask ken-ai (or whatever model is set) what to do. Parses
   to a known action or falls back to noop so the loop never
   crashes on bad output. Works for both drive and observe mode
   — observe replies look like "ACTION|note" which we split. ── */
async function askAgent(prompt) {
  const t0 = Date.now();
  const result = await new Promise(resolve => {
    const child = spawn('ollama', ['run', _model], {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    });

    let stdout = '';
    let stderr = '';
    let settled = false;
    const settle = (value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(value);
    };

    const timer = setTimeout(() => {
      try { child.kill(); } catch {}
      settle({ ok: false, error: 'ollama timeout' });
    }, 60000);

    child.stdout.on('data', chunk => { stdout += String(chunk || ''); });
    child.stderr.on('data', chunk => { stderr += String(chunk || ''); });
    child.on('error', err => settle({ ok: false, error: err.message || 'spawn failed' }));
    child.on('close', code => {
      if (code !== 0) {
        settle({
          ok: false,
          error: stripAnsi(stderr || '').trim() || ('ollama exit ' + code),
        });
        return;
      }
      settle({ ok: true, raw: stripAnsi(stdout || '').trim() });
    });

    try { child.stdin.end(prompt); }
    catch (err) { settle({ ok: false, error: err.message || 'stdin failed' }); }
  });

  const elapsed = Date.now() - t0;
  if (!result.ok) {
    return { action: 'noop', note: '', raw: '', elapsed, error: result.error };
  }

  const raw = result.raw || '';

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

/* ── Aim assist — spawn aimbot.py to scan for enemy-signature
   pixels in the center of the screen, snap mouse to the biggest
   blob, optionally fire. Supports three modes:

     scan-only   (default)   — just find a target, no mouse
     snap        (--snap)    — snap mouse onto target
     snap+fire   (--fire)    — snap then single click
     engage      (--engage)  — full burst with rescan between
                                shots and target tracking
                                ("better control" mode)

   Non-fatal on any error — callers just proceed without assist. ── */
function runAimbot(opts = {}) {
  const args = [AIM_PY, '--palette', opts.palette || _aimPalette,
                '--min-confidence', String(opts.minConfidence ?? _aimMinConfidence)];
  if (opts.engage) {
    args.push('--engage');
    if (opts.burstSize)  args.push('--burst-size', String(opts.burstSize));
    if (opts.shotDelay)  args.push('--shot-delay', String(opts.shotDelay));
    if (opts.maxShots)   args.push('--max-shots', String(opts.maxShots));
  } else {
    if (opts.snap !== false) args.push('--snap');
    if (opts.fire) args.push('--fire');
  }
  // Engagement can take up to ~1500ms (snap + 3-5 shots + rescans).
  // Bump timeout accordingly.
  const timeout = opts.engage ? 6000 : 4000;
  const res = spawnSync(_pythonBin, args, {
    encoding: 'utf8',
    timeout,
    maxBuffer: 2 * 1024 * 1024,
  });
  if (res.status !== 0) {
    return { found: false, error: 'aimbot exit ' + res.status, stderr: (res.stderr || '').slice(0, 200) };
  }
  try {
    const line = (res.stdout || '').split('\n').find(l => l.trim().startsWith('{'));
    return line ? JSON.parse(line) : { found: false, error: 'no json' };
  } catch (e) {
    return { found: false, error: 'parse: ' + e.message };
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
  const decision = await askAgent(prompt);

  let firing = { ok: true, detail: null };
  let followThroughsFired = 0;
  if (mode === 'drive') {
    // Lifelike timing: derive hold duration from the action and
    // fire optional follow-through presses for combat/look actions
    // so bursts feel responsive instead of metronomic.
    const holdMs = pickHoldMs(decision.action);
    firing = fireAction(decision.action, holdMs);
    const ftCount = pickFollowThroughs(decision.action);
    for (let i = 0; i < ftCount; i++) {
      // Short async pause between follow-throughs — bursts fire
      // at ~180ms intervals, looks at ~200ms. async so the event
      // loop (aimbot, metrics poll, etc) stays responsive.
      const gap = jitter(decision.action === 'fire' ? 180 : 200, 0.3);
      await new Promise(r => setTimeout(r, gap));
      fireAction(decision.action, pickHoldMs(decision.action));
      followThroughsFired++;
    }
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
    followThroughs: followThroughsFired,
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

  // Drive-mode side-effects: extract events from the state
  // delta, stamp counters, trigger post-mortem on death.
  if (mode === 'drive') {
    try {
      const evt = extractFromTick(entry);
      if (evt && evt.kind === 'died') {
        stampEvent('death');
        runPostMortem(_model, evt);
      } else if (evt && evt.kind === 'shield_regen') {
        stampEvent('win');
        appendLesson('wins_log', `survived low shield after ${entry.action}`);
      }
    } catch (e) { /* best-effort */ }
    stampEvent('dispatch');
  }

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
    let nextDelay = _tickMs;
    try {
      const entry = await tickOnce();
      // Lifelike tick scheduling — drive mode picks the next
      // delay from ACTION_TIMING[action] with jitter. Observe
      // mode stays on the base _tickMs to give OCR a stable
      // cadence for dream/learning reflection.
      nextDelay = pickNextDelay(entry && entry.action);
    }
    catch (e) { logTick({ at: new Date().toISOString(), error: 'loop: ' + e.message }); }
    if (_running) _loopTimer = setTimeout(fire, nextDelay);
  };
  fire();
  return { ok: true, tickMs: _tickMs, model: _model, mode: _mode, lifelike: _lifelike };
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

/* ── Continuous aimbot loop — independent of the game tick
   loop. Scans every _aimIntervalMs, snaps mouse on hit. Meant
   to run while Ken is playing so the mouse snaps to visible
   enemies on its own. Starts + stops via its own endpoints
   without touching the observe/drive loop. ── */
let _aimUseDaemon = false;

export function startAimLoop(opts = {}) {
  if (_aimRunning) return { ok: false, reason: 'aim loop already running' };
  _aimIntervalMs = Math.max(16, Math.min(2000, opts.intervalMs || 250));
  _aimPalette = opts.palette || _aimPalette;
  _aimMinConfidence = opts.minConfidence ?? _aimMinConfidence;
  _aimFire = !!opts.fire;
  _aimEngage = !!opts.engage;
  _aimBurstSize = opts.burstSize || 3;
  _aimShotDelay = opts.shotDelay || 140;
  _aimMaxShots = opts.maxShots || 5;
  _aimUseDaemon = opts.daemon !== false; // default ON — 30fps path
  _aimRunning = true;
  _aimStats = { scans: 0, hits: 0, shots: 0, lastConfidence: 0, startedAt: new Date().toISOString(), backend: 'spawnSync' };

  if (_aimUseDaemon) {
    startAimDaemon();
    _aimStats.backend = 'daemon';
  }

  const tickDaemon = async () => {
    if (!_aimRunning) return;
    try {
      if (!_aimDaemonReady) {
        // Daemon still booting — short retry
        _aimTimer = setTimeout(tickDaemon, 200);
        return;
      }
      const op = _aimEngage ? 'engage' : (_aimFire ? 'fire' : 'snap');
      const r = await daemonCommand({
        op,
        palette: _aimPalette,
        minConfidence: _aimMinConfidence,
        burstSize: _aimBurstSize,
        shotDelay: _aimShotDelay,
        maxShots: _aimMaxShots,
      }, 3500);
      _aimStats.scans += 1;
      if (r && r.found) {
        _aimStats.hits += 1;
        _aimStats.lastConfidence = r.confidence || 0;
        if (typeof r.shots_fired === 'number') _aimStats.shots += r.shots_fired;
      }
      _aimStats.lastCycleMs = r && r.cycleMs;
    } catch (e) {
      // Daemon crashed / timed out — restart it
      stopAimDaemon();
      if (_aimRunning) startAimDaemon();
    }
    if (_aimRunning) _aimTimer = setTimeout(tickDaemon, _aimIntervalMs);
  };

  const tickSpawn = () => {
    if (!_aimRunning) return;
    try {
      const r = runAimbot({
        snap: true,
        fire: _aimFire,
        engage: _aimEngage,
        burstSize: _aimBurstSize,
        shotDelay: _aimShotDelay,
        maxShots: _aimMaxShots,
        palette: _aimPalette,
        minConfidence: _aimMinConfidence,
      });
      _aimStats.scans += 1;
      if (r && r.found) {
        _aimStats.hits += 1;
        _aimStats.lastConfidence = r.confidence || 0;
        if (typeof r.shots_fired === 'number') _aimStats.shots += r.shots_fired;
      }
    } catch (e) { /* swallow so loop never dies */ }
    if (_aimRunning) _aimTimer = setTimeout(tickSpawn, _aimIntervalMs);
  };

  if (_aimUseDaemon) tickDaemon();
  else tickSpawn();

  return {
    ok: true,
    intervalMs: _aimIntervalMs,
    palette: _aimPalette,
    minConfidence: _aimMinConfidence,
    fire: _aimFire,
    engage: _aimEngage,
    burstSize: _aimBurstSize,
    shotDelay: _aimShotDelay,
    maxShots: _aimMaxShots,
    daemon: _aimUseDaemon,
  };
}

export function stopAimLoop() {
  if (!_aimRunning) return { ok: false, reason: 'aim loop not running' };
  _aimRunning = false;
  if (_aimTimer) { clearTimeout(_aimTimer); _aimTimer = null; }
  if (_aimUseDaemon) stopAimDaemon();
  return { ok: true, stats: _aimStats };
}

export function aimStatus() {
  return {
    running: _aimRunning,
    intervalMs: _aimIntervalMs,
    palette: _aimPalette,
    minConfidence: _aimMinConfidence,
    fire: _aimFire,
    engage: _aimEngage,
    burstSize: _aimBurstSize,
    shotDelay: _aimShotDelay,
    maxShots: _aimMaxShots,
    stats: _aimStats,
  };
}

/* ── One-shot aimbot scan without snapping — for debugging
   what the aimbot currently sees. ── */
export function aimScanOnce(opts = {}) {
  return runAimbot({
    snap: opts.snap === true,
    fire: opts.fire === true,
    palette: opts.palette || _aimPalette,
    minConfidence: opts.minConfidence ?? _aimMinConfidence,
  });
}

/* ── Vision cache loop — runs halo_vision.py on a slow cadence
   (default 20s) and caches the result for drive/observe prompts.
   Vision inference is ~15-40s per call on a 7.8GB model so this
   can NEVER run per-tick; it's a periodic "what does the screen
   look like" snapshot that's valid until the next cycle. ── */
function runVisionOnce() {
  const res = spawnSync(_pythonBin, [VISION_PY, '--model', _visionModel], {
    encoding: 'utf8',
    timeout: 60000,
    maxBuffer: 2 * 1024 * 1024,
  });
  if (res.status !== 0) {
    return { ok: false, error: 'vision exit ' + res.status, stderr: (res.stderr || '').slice(0, 200) };
  }
  try {
    const line = (res.stdout || '').split('\n').find(l => l.trim().startsWith('{'));
    return line ? JSON.parse(line) : { ok: false, error: 'no json' };
  } catch (e) {
    return { ok: false, error: 'parse: ' + e.message };
  }
}

export function startVisionLoop(opts = {}) {
  if (_visionRunning) return { ok: false, reason: 'vision loop already running' };
  _visionIntervalMs = Math.max(8000, Math.min(120000, opts.intervalMs || 20000));
  _visionModel = opts.model || 'llama3.2-vision';
  _visionRunning = true;
  const tick = () => {
    if (!_visionRunning) return;
    try {
      const r = runVisionOnce();
      if (r && r.ok) {
        _visionCache = {
          description:     r.description,
          situation:       r.situation,
          enemies_visible: r.enemies_visible,
          enemies:         r.enemies,
          weapon_hint:     r.weapon_hint,
          suggestion:      r.suggestion,
          at:              r.at,
          elapsedMs:       r.elapsedMs,
        };
        writeJsonSnapshot(HALO_VISION_CACHE, _visionCache);
      }
    } catch (e) { /* swallow */ }
    if (_visionRunning) _visionTimer = setTimeout(tick, _visionIntervalMs);
  };
  tick();
  return { ok: true, intervalMs: _visionIntervalMs, model: _visionModel };
}

export function stopVisionLoop() {
  if (!_visionRunning) return { ok: false, reason: 'not running' };
  _visionRunning = false;
  if (_visionTimer) { clearTimeout(_visionTimer); _visionTimer = null; }
  return { ok: true };
}

export function visionStatus() {
  return {
    running: _visionRunning,
    intervalMs: _visionIntervalMs,
    model: _visionModel,
    cache: _visionCache,
  };
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
