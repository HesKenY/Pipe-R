/* ══════════════════════════════════════════════════════
   Halo agent patcher — LLM-driven live tuning of the aimbot
   ──────────────────────────────────────────────────────
   Runs alongside auto_tuner.js. Where the tuner applies
   rule-based adjustments (hit_rate > 40% → raise conf),
   this module asks an LLM agent (fast 8B model) to look at
   recent aim performance + combat events and propose a
   JSON patch to the aimbot config.

   Cadence: every 3 minutes. Too slow for twitch reaction
   but fine for strategic "we've been missing shots, let's
   widen the palette" style adjustments.

   Agent gets:
     - last 50 engagement log entries (from aimbot.log.jsonl on desktop)
     - current aim config
     - running stats snapshot

   Agent returns a JSON object with any subset of tunable
   fields. Unknown keys are dropped. Values are bounded.

   Valid keys + ranges:
     intervalMs     40 - 400
     minConfidence  0.010 - 0.200
     burstSize      1 - 6
     shotDelay      60 - 300
     maxShots       1 - 8
     palette        "red" | "purple" | "all"

   Each applied patch is logged to halo-events.jsonl and
   halo-memory.md tactics_learned so the agent has a
   memory of its own tuning history.

   ══════════════════════════════════════════════════════ */

import { spawn } from 'node:child_process';
import { existsSync, readFileSync, appendFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { appendLesson } from './memory.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR   = join(__dirname, '..', 'memories', 'ken-ai-latest');
const EVENTS_PATH = join(MEM_DIR, 'halo-events.jsonl');
// Desktop aimbot log (ken_aimbot.py writes here)
const DESKTOP_AIMLOG = 'C:\\Users\\Ken\\Desktop\\aimbot.log.jsonl';

const VALID_PALETTES = new Set(['red', 'purple', 'all']);

let _timer = null;
let _running = false;
let _intervalMs = 180000;
let _model = 'llama3.1:8b';
let _stats = { passes: 0, startedAt: null, lastPatchAt: null, lastPatch: null };

function stripAnsi(s) {
  return String(s || '')
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '');
}

function readLastLines(path, n) {
  if (!existsSync(path)) return [];
  try {
    const raw = readFileSync(path, 'utf8');
    return raw.split('\n').filter(Boolean).slice(-n);
  } catch (e) { return []; }
}

function buildStatsSummary() {
  const lines = readLastLines(DESKTOP_AIMLOG, 200);
  let engages = 0, shotsFired = 0, scanOnly = 0, errors = 0;
  let confSum = 0, confCount = 0;
  for (const l of lines) {
    try {
      const r = JSON.parse(l);
      if (r.kind === 'engage') {
        engages++;
        shotsFired += r.fired || 0;
        if (r.initial_conf) { confSum += r.initial_conf; confCount++; }
      } else if (r.kind === 'scan') {
        scanOnly++;
      } else if (r.kind === 'error') {
        errors++;
      }
    } catch (e) { /* skip */ }
  }
  return {
    sampled: lines.length,
    engages,
    shotsFired,
    scanOnly,
    errors,
    avgConfidence: confCount ? (confSum / confCount).toFixed(3) : '0',
  };
}

function buildPrompt(currentConfig, summary) {
  return (
    'you are a halo mcc aimbot tuning agent. you are reviewing the aimbot\'s recent performance and proposing live config changes to improve hit rate + reduce false positives.\n\n' +
    'current config:\n' + JSON.stringify(currentConfig, null, 2) + '\n\n' +
    'recent performance (last 200 log rows):\n' + JSON.stringify(summary, null, 2) + '\n\n' +
    'tunable fields + ranges:\n' +
    '  intervalMs     40 - 400\n' +
    '  minConfidence  0.010 - 0.200\n' +
    '  burstSize      1 - 6\n' +
    '  shotDelay      60 - 300\n' +
    '  maxShots       1 - 8\n' +
    '  palette        "red" | "purple" | "all"\n\n' +
    'respond with ONE valid JSON object containing any subset of these fields. ' +
    'include only fields you want to CHANGE. do not include other keys. ' +
    'no prose, no markdown, no code fences — just the raw JSON object.\n\n' +
    'example valid responses:\n' +
    '  {"minConfidence": 0.04, "burstSize": 4}\n' +
    '  {"palette": "red", "intervalMs": 90}\n' +
    '  {}  (no changes)\n\n' +
    'your JSON patch:'
  );
}

function askAgent(prompt, timeoutMs = 45000) {
  return new Promise((resolve) => {
    let out = '';
    const child = spawn('ollama', ['run', _model], {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    });
    const timeout = setTimeout(() => {
      try { child.kill('SIGKILL'); } catch (e) {}
    }, timeoutMs);
    child.stdout.on('data', (d) => { out += d.toString('utf8'); });
    child.on('close', () => {
      clearTimeout(timeout);
      resolve(stripAnsi(out).trim());
    });
    try { child.stdin.write(prompt); child.stdin.end(); }
    catch (e) { resolve(''); }
  });
}

// Aggression floors — Ken's "DIAL IT IN" directive. The LLM
// patcher may ONLY walk values in the more-aggressive direction
// from these. Anything tamer gets clamped back.
const FLOORS = {
  burstSize:    4,      // never below
  maxShots:     5,      // never below
  minConfMax:   0.035,  // never tighten past this
  intervalMax:  90,     // never slow past this
};

function parsePatch(raw) {
  if (!raw) return null;
  // Find the first { ... } block in the response
  const m = raw.match(/\{[^}]*\}/);
  if (!m) return null;
  try {
    const obj = JSON.parse(m[0]);
    const clean = {};
    if (typeof obj.intervalMs === 'number')
      clean.intervalMs = Math.max(40, Math.min(FLOORS.intervalMax, obj.intervalMs));
    if (typeof obj.minConfidence === 'number')
      clean.minConfidence = Math.max(0.010, Math.min(FLOORS.minConfMax, obj.minConfidence));
    if (typeof obj.burstSize === 'number')
      clean.burstSize = Math.max(FLOORS.burstSize, Math.min(6, Math.round(obj.burstSize)));
    if (typeof obj.shotDelay === 'number')
      clean.shotDelay = Math.max(60, Math.min(300, obj.shotDelay));
    if (typeof obj.maxShots === 'number')
      clean.maxShots = Math.max(FLOORS.maxShots, Math.min(8, Math.round(obj.maxShots)));
    if (typeof obj.palette === 'string' && VALID_PALETTES.has(obj.palette))
      clean.palette = obj.palette;
    return Object.keys(clean).length ? clean : null;
  } catch (e) { return null; }
}

async function applyPatch(patch) {
  // Fetch current config + stop + restart with merged config
  try {
    const resStatus = await fetch('http://127.0.0.1:7777/api/halo/aim/status');
    if (!resStatus.ok) return false;
    const current = await resStatus.json();
    if (!current || !current.running) return false;

    await fetch('http://127.0.0.1:7777/api/halo/aim/stop', { method: 'POST' });
    const merged = {
      intervalMs:    patch.intervalMs    || current.intervalMs,
      palette:       patch.palette       || current.palette,
      minConfidence: patch.minConfidence != null ? patch.minConfidence : current.minConfidence,
      engage:        current.engage,
      burstSize:     patch.burstSize     || current.burstSize,
      shotDelay:     patch.shotDelay     || current.shotDelay,
      maxShots:      patch.maxShots      || current.maxShots,
      daemon:        false,
    };
    await fetch('http://127.0.0.1:7777/api/halo/aim/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(merged),
    });
    return true;
  } catch (e) { return false; }
}

async function runPass() {
  try {
    // Get current aim config
    const res = await fetch('http://127.0.0.1:7777/api/halo/aim/status');
    if (!res.ok) return;
    const current = await res.json();
    if (!current || !current.running) return;

    const summary = buildStatsSummary();
    if (summary.sampled < 10) return; // not enough data

    const prompt = buildPrompt({
      intervalMs:    current.intervalMs,
      palette:       current.palette,
      minConfidence: current.minConfidence,
      burstSize:     current.burstSize,
      shotDelay:     current.shotDelay,
      maxShots:      current.maxShots,
    }, summary);

    const raw = await askAgent(prompt);
    const patch = parsePatch(raw);
    if (!patch) return;

    const applied = await applyPatch(patch);
    if (!applied) return;

    _stats.passes += 1;
    _stats.lastPatchAt = new Date().toISOString();
    _stats.lastPatch = patch;

    // Log to halo-events.jsonl + memory
    try {
      appendFileSync(EVENTS_PATH, JSON.stringify({
        at: _stats.lastPatchAt,
        kind: 'agent_patch',
        model: _model,
        patch,
        stats: summary,
      }) + '\n', 'utf8');
    } catch (e) {}

    try {
      const parts = Object.entries(patch).map(([k, v]) => `${k}=${v}`).join(', ');
      appendLesson('tactics_learned',
        `agent_patch(${_model}): ${parts} — engages=${summary.engages}, shots=${summary.shotsFired}, avgConf=${summary.avgConfidence}`);
    } catch (e) {}
  } catch (e) { /* swallow */ }
}

export function startAgentPatcher(opts = {}) {
  if (_running) return { ok: false, reason: 'already running' };
  _intervalMs = Math.max(60000, Math.min(600000, opts.intervalMs || 180000));
  _model = opts.model || 'llama3.1:8b';
  _running = true;
  _stats = { passes: 0, startedAt: new Date().toISOString(), lastPatchAt: null, lastPatch: null };
  const tick = async () => {
    if (!_running) return;
    try { await runPass(); }
    catch (e) { /* swallow */ }
    if (_running) _timer = setTimeout(tick, _intervalMs);
  };
  _timer = setTimeout(tick, 20000); // first pass 20s after start
  return { ok: true, intervalMs: _intervalMs, model: _model };
}

export function stopAgentPatcher() {
  if (!_running) return { ok: false, reason: 'not running' };
  _running = false;
  if (_timer) { clearTimeout(_timer); _timer = null; }
  return { ok: true, stats: _stats };
}

export function agentPatcherStatus() {
  return {
    running: _running,
    intervalMs: _intervalMs,
    model: _model,
    stats: _stats,
  };
}
