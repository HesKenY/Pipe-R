/*
  Pokemon Crystal AI agent — drives gameplay via mGBA.

  GOAL: Beat the Elite Four.

  Architecture:
  - pokemon_tick.py captures screen state via mGBA window
  - kenai:v1 decides the next action based on state + memory
  - pokemon_do.py fires GBC inputs (A/B/Start/D-pad)
  - memory.md tracks team, gyms, deaths, tactics
  - Every battle loss → death-learning → store fix → apply next time

  Actions: a, b, start, select, up, down, left, right, noop

  Unlike Halo (FPS reflexes), Pokemon is turn-based. The AI can
  think longer per tick without penalty. 3-5s tick is fine.
*/

import { spawnSync, spawn } from 'node:child_process';
import { readFileSync, appendFileSync, existsSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR = join(__dirname, '..', 'memories', 'ken-ai-latest');
const MEMORY = join(__dirname, 'memory.md');
const LOG = join(MEM_DIR, 'pokemon-log.jsonl');
const TICK_PY = join(__dirname, 'pokemon_tick.py');
const DO_PY = join(__dirname, 'pokemon_do.py');

const VISION_PY = join(__dirname, 'pokemon_vision.py');
const POSTMORTEM_PY = join(__dirname, 'post_mortem.py');
const VALID = new Set(['a','b','start','select','up','down','left','right','noop']);

// Vision cache — updated every ~15s by background loop
let _visionCache = null;
let _visionTimer = null;
let _visionRunning = false;

function refreshVision() {
  // ASYNC — no spawnSync. Vision takes 20-40s; blocking the Node event
  // loop during that stalls the HTTP server and every other endpoint.
  if (_visionRunning) return;
  _visionRunning = true;
  const chunks = [];
  let settled = false;
  const finish = () => {
    if (settled) return;
    settled = true;
    _visionRunning = false;
  };
  try {
    const child = spawn('python', [VISION_PY], { windowsHide: true });
    child.stdout.on('data', d => chunks.push(d));
    child.on('close', () => {
      try {
        const out = Buffer.concat(chunks).toString('utf8');
        const line = out.split('\n').find(l => l.trim().startsWith('{'));
        if (line) _visionCache = JSON.parse(line);
      } catch(e) {}
      finish();
    });
    child.on('error', () => { finish(); });
    setTimeout(() => {
      try { child.kill('SIGKILL'); } catch(e) {}
      finish();
    }, 50000);
  } catch(e) {
    finish();
  }
}

function startVisionLoop() {
  if (_visionTimer) return;
  refreshVision();
  // Vision costs ~30s + evicts kenai from VRAM. Only pay that cost
  // when it matters: battle (needs HP bars, enemy sprites) or every
  // 60s as a sanity fallback. Overworld walking doesn't need vision.
  let visionTick = 0;
  _visionTimer = setInterval(() => {
    visionTick++;
    const inBattle = _stats.lastActivity === 'battle';
    if (inBattle || visionTick % 4 === 0) {
      refreshVision();
    }
  }, 15000);
}

function stopVisionLoop() {
  if (_visionTimer) clearInterval(_visionTimer);
  _visionTimer = null;
}

let _battleReviewCount = 0;

function runBattleReview() {
  _battleReviewCount++;
  // Pull the battle ticks from history
  const battleTicks = _history.filter(h => h.activity === 'battle');
  if (battleTicks.length < 2) return; // too short to learn from

  const battleActions = battleTicks.map(h => h.action).join(' → ');
  const visionDuringBattle = _visionCache && _visionCache.situation === 'battle' ? _visionCache.description : '';
  const lastBattleState = battleTicks[battleTicks.length - 1];

  const prompt = `pokemon crystal battle review #${_battleReviewCount}. a battle just ended.

battle actions taken: ${battleActions}
vision during battle: ${visionDuringBattle || 'none'}
last battle screen text: "${(lastBattleState.stateMid||'').slice(0,80)}"
battle ticks: ${battleTicks.length}

${readMemory().slice(0, 1000)}

analyze this battle in EXACTLY this format (one line each):
RESULT: win or loss
OPPONENT: what pokemon/trainer we fought (best guess from screen text)
MOVES_USED: what moves/actions we chose
LESSON: one specific tactical lesson from this battle
TEAM_UPDATE: any change needed to team or moveset (or "none")

be specific. if we won easily, note what worked. if it was close, note what to improve.`;

  try {
    const t0 = Date.now();
    const r = spawnSync('ollama', ['run', _model], {
      input: prompt, encoding: 'utf8', timeout: 45000,
      maxBuffer: 2*1024*1024, windowsHide: true
    });
    const elapsed = Date.now() - t0;
    const raw = strip(r.stdout || '');

    // Log the review
    logTick({
      at: new Date().toISOString(),
      type: 'battle_review',
      battleNumber: _battleReviewCount,
      battleTicks: battleTicks.length,
      actions: battleActions,
      review: raw.slice(0, 400),
      inferenceMs: elapsed,
    });

    // Extract LESSON and write to memory
    const lessonMatch = raw.match(/LESSON:\s*(.+)/i);
    const teamMatch = raw.match(/TEAM_UPDATE:\s*(.+)/i);
    if (lessonMatch || teamMatch) {
      try {
        let mem = readFileSync(MEMORY, 'utf8');
        const ts = new Date().toISOString().slice(0,19);
        if (lessonMatch) {
          mem = mem.replace('## tactics_learned',
            `## tactics_learned\n- ${ts} — battle #${_battleReviewCount}: ${lessonMatch[1].trim()}`);
        }
        if (teamMatch && teamMatch[1].trim().toLowerCase() !== 'none') {
          mem = mem.replace('## team',
            `## team\n- ${ts} — review: ${teamMatch[1].trim()}`);
        }
        writeFileSync(MEMORY, mem, 'utf8');
      } catch(e) {}
    }
  } catch(e) {}
}

function runPostMortem() {
  try {
    const r = spawnSync('python', [POSTMORTEM_PY], {
      encoding: 'utf8', timeout: 60000, windowsHide: true
    });
    if (r.status === 0) {
      const line = (r.stdout||'').split('\n').find(l => l.trim().startsWith('{'));
      if (line) {
        const pm = JSON.parse(line);
        logTick({ at: new Date().toISOString(), type: 'post_mortem', analysis: (pm.analysis||'').slice(0,300) });
      }
    }
  } catch(e) {}
}

let _running = false;
let _timer = null;
let _tickMs = 3000;
let _model = 'kenai:v3';
let _history = [];
let _stats = { ticks: 0, startedAt: null, lastAction: null, lastActivity: null };

function strip(s) {
  return String(s||'').replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g,'').replace(/\u001b\][^\u0007]*\u0007/g,'').trim();
}

function captureState() {
  const r = spawnSync('python', [TICK_PY], { encoding: 'utf8', timeout: 10000, windowsHide: true });
  if (r.status !== 0) return { error: 'tick failed: ' + (r.stderr||'').slice(0,200) };
  try {
    const line = (r.stdout||'').split('\n').find(l => l.trim().startsWith('{'));
    return line ? JSON.parse(line) : { error: 'no json' };
  } catch(e) { return { error: e.message }; }
}

function fireAction(action, durationMs = 200) {
  if (!VALID.has(action)) action = 'noop';
  const r = spawnSync('python', [DO_PY, action, String(durationMs)], {
    encoding: 'utf8', timeout: 4000, windowsHide: true
  });
  return r.status === 0;
}

function readMemory() {
  if (!existsSync(MEMORY)) return '';
  try { return readFileSync(MEMORY, 'utf8').slice(0, 3000); } catch(e) { return ''; }
}

function logTick(entry) {
  try { appendFileSync(LOG, JSON.stringify(entry) + '\n', 'utf8'); } catch(e) {}
}

function buildPrompt(state) {
  const mem = readMemory();
  const last5 = _history.slice(-5).map(h => h.action).join(' → ');
  const activity = state.activity || 'unknown';

  // Vision context from llama3.2-vision (updated every 15s)
  let visionBlock = '';
  if (_visionCache && _visionCache.ok) {
    visionBlock = `\nVISION (what the AI sees): ${_visionCache.description || ''}
- situation: ${_visionCache.situation || 'unknown'}
- pokemon: ${_visionCache.pokemon_visible || 'unknown'}
- hp: ${_visionCache.hp_status || 'unknown'}
- vision suggests: ${_visionCache.suggestion || 'noop'}`;
  }

  return `pokemon crystal via mgba. pick ONE action. no prose.
vocab: a b start select up down left right noop
GOAL: beat the elite four. complete the game.

current state:
- activity: ${activity}
- screen text top: "${(state.top||'').slice(0,60)}"
- screen text mid: "${(state.mid||'').slice(0,60)}"
- screen text bot: "${(state.bot||'').slice(0,60)}"
- motion: ${state.motion || 0}
- brightness: ${state.bright || 0}
- last 5 actions: ${last5 || '(none)'}${visionBlock}

rules:
- activity=menu → press a or start to open/confirm
- activity=dialogue → press b to advance text (a re-triggers NPCs on their tile)
- activity=battle → navigate with up/down, confirm with a (battle menus are deterministic)
- activity=exploring → use up/down/left/right to move; a only to interact with objects
- activity=idle → press a or start (might be waiting for input)
- activity=death → press a to continue, then go heal at pokemon center
- after dialogue ends, walk a tile before pressing a again (avoids re-trigger loop)

ADAPT RULE (important):
- if your last 3 actions are the same AND motion+brightness haven't changed meaningfully, the action is NOT working. STOP repeating it. Try something different:
  * if pressing a/b → try a direction or start
  * if pressing a direction → try a different direction, or a/b to interact
  * if pressing start → try a or b to navigate the menu, or select to cycle
- the point is to FIND A SOLUTION. if stuck, experiment. idle ≠ progress.
- never noop more than twice in a row
- if stuck (same screen 5+ ticks), try start or b to unstick

${mem ? '\ngame memory:\n' + mem.slice(0, 1500) : ''}

action:`;
}

async function tick() {
  const state = captureState();
  if (state.error) {
    logTick({ at: new Date().toISOString(), error: state.error });
    return;
  }

  // Vision-over-motion classifier: llama3.2-vision's situation is more
  // reliable than motion thresholds when OCR fails. Overrides activity
  // when vision cache is fresh + ok.
  if (_visionCache && _visionCache.ok && _visionCache.situation) {
    const visActivity = String(_visionCache.situation).toLowerCase().trim();
    const valid = ['battle', 'dialogue', 'menu', 'exploring', 'idle', 'death'];
    if (valid.includes(visActivity)) {
      state._motionActivity = state.activity;
      state.activity = visActivity;
    }
  }

  const prompt = buildPrompt(state);
  const t0 = Date.now();
  const r = spawnSync('ollama', ['run', _model], {
    input: prompt, encoding: 'utf8', timeout: 30000,
    maxBuffer: 2*1024*1024, windowsHide: true
  });
  const elapsed = Date.now() - t0;
  const raw = strip(r.stdout || '');

  // Parse action — find first valid word
  const rawLower = raw.toLowerCase();
  const tokens = rawLower.split(/[^a-z]+/).filter(Boolean);
  let action = tokens.find(t => VALID.has(t)) || 'noop';

  // Parser disambiguation: "a direction", "walk toward", etc. = model
  // wants a DIRECTION, not the A button. Without this, "try a direction"
  // parses as action='a' because 'a' is the first valid token.
  const wantsDirection = /\b(a direction|a valid direction|walk toward|move toward|head toward|walk to|head to|go toward)\b/.test(rawLower);
  if (wantsDirection && action === 'a') {
    // Prefer an explicit direction if the model named one
    const dir = tokens.find(t => ['up','down','left','right'].includes(t));
    action = dir || ['up','down','left','right'][_stats.ticks % 4];
  }

  // Anti-stuck: if motion is near-zero, alternate between A and walking
  // Pokemon Crystal requires walking to progress — A alone does nothing in overworld.
  // NOTE: runs FIRST so dialogue-force-B below can have the final word.
  // Only applies to NON-dialogue states (dialogue doesn't need directional
  // unsticking — just press B to advance text).
  if (state.activity !== 'dialogue') {
    const lowMotion = (state.motion || 0) < 0.01;
    const recentActions = _history.slice(-2).map(h => h.action);
    const wasA = recentActions.length >= 1 && recentActions.every(a => a === 'a' || a === 'noop' || a === 'b');
    if (lowMotion && (wasA || action === 'a' || action === 'noop')) {
      // Cycle: down, down, right, down, left, down — biased toward moving south (exits most rooms)
      const dirs = ['down', 'down', 'right', 'down', 'left', 'down', 'a', 'down'];
      action = dirs[_stats.ticks % dirs.length];
    }
  }

  // RULE ENFORCEMENT (FINAL WORD): dialogue → always B.
  // Runs AFTER anti-stuck so nothing can override it. B is the only
  // universally correct action in text/dialogue:
  //   - advances scrolling text
  //   - doesn't accidentally confirm yes/no prompts
  //   - doesn't re-trigger NPCs after dialog ends
  //   - arrow keys in dialog screens do nothing anyway
  if (state.activity === 'dialogue' && action !== 'b') {
    action = 'b';
  }

  // Fire it — send multiple rapid inputs per tick to compensate for slow inference
  const holdMs = ['up','down','left','right'].includes(action) ? 250 : 100;
  fireAction(action, holdMs);
  // Repeat directional inputs 3x for faster overworld movement
  if (['up','down','left','right'].includes(action)) {
    for (let i = 0; i < 2; i++) {
      fireAction(action, holdMs);
    }
  }
  // Repeat A presses for dialogue advancement
  if (action === 'a') {
    for (let i = 0; i < 3; i++) {
      fireAction('a', 80);
    }
  }

  _stats.ticks++;
  _stats.lastAction = action;
  _stats.lastActivity = state.activity;

  const entry = {
    at: new Date().toISOString(),
    action, activity: state.activity,
    stateTop: (state.top||'').slice(0,40),
    stateMid: (state.mid||'').slice(0,40),
    stateBot: (state.bot||'').slice(0,40),
    motion: state.motion, bright: state.bright,
    inferenceMs: elapsed, raw: raw.slice(0,80),
  };
  _history.push(entry);
  if (_history.length > 20) _history.shift();
  logTick(entry);

  // Battle-end learning: when transitioning OUT of battle, run analysis
  const prevActivity = _history.length > 1 ? _history[_history.length - 2]?.activity : null;
  const battleJustEnded = prevActivity === 'battle' && state.activity !== 'battle';
  if (battleJustEnded) {
    runBattleReview();
  }

  // Death-learning: if activity=death, log it + run post-mortem
  if (state.activity === 'death') {
    runPostMortem();
    const deathEntry = `- ${new Date().toISOString().slice(0,19)} — whiteout. screen: "${(state.mid||'').slice(0,60)}". last actions: ${_history.slice(-5).map(h=>h.action).join(',')}`;
    try {
      const mem = readFileSync(MEMORY, 'utf8');
      writeFileSync(MEMORY, mem.replace('## deaths_log', '## deaths_log\n' + deathEntry), 'utf8');
    } catch(e) {}
  }
}

export function startLoop(opts = {}) {
  if (_running) return { ok: false, reason: 'already running' };
  _tickMs = opts.tickMs || 3000;
  _model = opts.model || 'kenai:v1';
  _running = true;
  _stats.startedAt = new Date().toISOString();
  _stats.ticks = 0;

  startVisionLoop();
  const run = () => {
    if (!_running) return;
    tick().catch(() => {});
    if (_running) _timer = setTimeout(run, _tickMs);
  };
  run();
  return { ok: true, tickMs: _tickMs, model: _model };
}

export function stopLoop() {
  _running = false;
  if (_timer) clearTimeout(_timer);
  _timer = null;
  stopVisionLoop();
  return { ok: true, ticks: _stats.ticks };
}

export function status() {
  return { running: _running, stats: _stats, model: _model, tickMs: _tickMs, historyLength: _history.length };
}

export function readRecentLog(n = 20) {
  if (!existsSync(LOG)) return [];
  try {
    return readFileSync(LOG, 'utf8').trim().split('\n').slice(-n).map(l => {
      try { return JSON.parse(l); } catch(e) { return null; }
    }).filter(Boolean);
  } catch(e) { return []; }
}
