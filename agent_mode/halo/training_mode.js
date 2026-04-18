/* ══════════════════════════════════════════════════════
   Halo training mode — safety-net flag for bold learning
   ──────────────────────────────────────────────────────
   Ken's directive: during training, hook into unlimited-
   health cheats (WeMod / Cheat Engine / mod tools) so Ken AI
   can take bold plays without dying every 30 seconds. Goal
   is to graduate OFF the safety net once the agent has
   enough reflexes to survive.

   This module doesn't apply cheats itself — that's Ken's
   responsibility via an external trainer (WeMod, Cheat
   Engine, etc). Instead, it manages a FLAG the drive
   prompt reads to tell the agent how aggressively to play:

     safety_net=true  → "you cannot die right now — test
                         risky maneuvers, fire at everything,
                         learn what works"
     safety_net=false → "survival mode — prioritize staying
                         alive, never push a wounded shield"

   The flag persists in agent_mode/config/halo_training.json
   so it survives server restarts.

   Also auto-detects known trainers (WeMod, Cheat Engine,
   Halo 2 trainers from gameradar / mrantifun) by scanning
   running process names. If detected, safety_net implicit.
   ══════════════════════════════════════════════════════ */

import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CFG_DIR  = join(__dirname, '..', 'config');
const CFG_FILE = join(CFG_DIR, 'halo_training.json');

// Process names (Windows) that indicate a trainer / cheat
// engine is running. Case-insensitive substring match.
const TRAINER_SIGNATURES = [
  'wemod',        // WeMod
  'cheatengine',  // Cheat Engine
  'plitch',       // Plitch trainer
  'mrantifun',    // Mr. Antifun (community Halo trainers)
  'trainer',      // generic
];

function defaultState() {
  return {
    safety_net: false,
    goal: 'survival without cheats, without trainers',
    graduated: false,
    target_practice: false,
    one_hit_kill: false,
    detected_trainer: null,
    enabled_at: null,
    last_check_at: null,
  };
}

function ensureDir() {
  if (!existsSync(CFG_DIR)) mkdirSync(CFG_DIR, { recursive: true });
}

export function getState() {
  ensureDir();
  if (!existsSync(CFG_FILE)) {
    const d = defaultState();
    writeFileSync(CFG_FILE, JSON.stringify(d, null, 2), 'utf8');
    return d;
  }
  try {
    return JSON.parse(readFileSync(CFG_FILE, 'utf8'));
  } catch (e) {
    return defaultState();
  }
}

function saveState(state) {
  ensureDir();
  writeFileSync(CFG_FILE, JSON.stringify(state, null, 2), 'utf8');
}

export function setSafetyNet(on, opts = {}) {
  const state = getState();
  state.safety_net = !!on;
  state.enabled_at = on ? new Date().toISOString() : null;
  if (opts.goal) state.goal = opts.goal;
  if (opts.graduated != null) state.graduated = !!opts.graduated;
  if (opts.targetPractice != null) state.target_practice = !!opts.targetPractice;
  if (opts.oneHitKill != null) state.one_hit_kill = !!opts.oneHitKill;
  saveState(state);
  return state;
}

/* ── Detect known trainer processes via tasklist ── */
export function detectTrainers() {
  const state = getState();
  state.last_check_at = new Date().toISOString();
  try {
    const res = spawnSync('tasklist', ['/FO', 'CSV', '/NH'], {
      encoding: 'utf8',
      timeout: 5000,
      maxBuffer: 4 * 1024 * 1024,
      windowsHide: true
    });
    if (res.status !== 0) {
      state.detected_trainer = null;
      saveState(state);
      return state;
    }
    const out = (res.stdout || '').toLowerCase();
    let found = null;
    for (const sig of TRAINER_SIGNATURES) {
      if (out.includes(sig)) { found = sig; break; }
    }
    state.detected_trainer = found;
    // Auto-arm safety_net if a trainer is detected and the user
    // hasn't graduated yet. Respects explicit graduated=true.
    if (found && !state.graduated && !state.safety_net) {
      state.safety_net = true;
      state.enabled_at = new Date().toISOString();
    }
    saveState(state);
    return state;
  } catch (e) {
    return state;
  }
}

/* ── Prompt block injected into drive + observe prompts.
   Flips language based on safety_net flag so the agent's
   risk calculus changes between training and survival. ── */
export function promptBlock() {
  const state = getState();
  if (state.safety_net) {
    const trainer = state.detected_trainer ? ` (detected: ${state.detected_trainer})` : '';
    const practice = state.target_practice ? '  - target practice active: prioritize visible enemies, snap fast, rep clean openings\n' : '';
    const oneHit = state.one_hit_kill ? '  - one-hit-kill drill active: treat first-shot accuracy and head-level snap as the whole rep\n' : '';
    return '\n\nTRAINING MODE — SAFETY NET ACTIVE' + trainer + '\n' +
      '  Ken enabled an external trainer (WeMod / Cheat Engine / mod) giving unlimited health.\n' +
      '  YOU CANNOT DIE RIGHT NOW. This is a learning window.\n' +
      practice +
      oneHit +
      '  - test risky plays (melee lunges, grenade cook-throws, charging elites)\n' +
      '  - fire at unknown blobs without hesitation — the aimbot handles targeting\n' +
      '  - try the noob combo, reload cancels, crouch jumps, sticky grenade boards\n' +
      '  - focus on VARIETY of actions so the dream pass has diverse data to consolidate\n' +
      '  - goal is to graduate: once you survive 5 minutes of this, Ken flips cheats off\n';
  }
  return '\n\nSURVIVAL MODE — NO SAFETY NET\n' +
    '  No cheats active. One wrong move is a death.\n' +
    '  - prioritize staying alive: take cover, recharge shields, never push a wounded engagement\n' +
    '  - follow the online:/coach: lessons in memory — especially deaths_log\n' +
    '  - use movement + positioning more than brute-force fire\n' +
    '  - the aimbot still handles aim; you handle strategy\n';
}
