/*
  Halo trainer assist - Ken AI coaching its own play.

  This pass reviews recent Halo action + event logs and writes compact
  coaching bullets back into halo-memory.md. Unlike the broader dream
  system, this coach is Halo-specific and should stay responsive while the
  HTTP server is live, so the Ollama call runs asynchronously.
*/

import { spawn } from 'node:child_process';
import { readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { appendLesson } from './memory.js';
import { getState as getTrainingState } from './training_mode.js';
import { jumpstartPromptBlock } from './jumpstart.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR = join(__dirname, '..', 'memories', 'ken-ai-latest');
const HALO_LOG = join(MEM_DIR, 'halo-log.jsonl');
const EVT_LOG = join(MEM_DIR, 'halo-events.jsonl');

let _timer = null;
let _running = false;
let _intervalMs = 90000;
let _model = 'kenai:v1';
let _passInFlight = false;
let _stats = { passes: 0, lastRunAt: null, lastEntries: 0 };

function stripAnsi(value) {
  return String(value || '')
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
      try { out.push(JSON.parse(lines[i])); } catch {}
    }
    return out.reverse();
  } catch {
    return [];
  }
}

function buildCoachPrompt(ticks, events) {
  const training = getTrainingState();
  const tickSummary = ticks.slice(-12).map((tick, index) =>
    `  ${index + 1}. ${tick.action || '?'} (mode=${tick.mode || '?'}, shots=${tick.followThroughs || 0})`
  ).join('\n');

  const evtSummary = events.slice(-20).map(event =>
    `  - ${event.kind || '?'}: ${event.action || event.pattern || ''}`
  ).join('\n');

  const trainingBlock = training.safety_net
    ? [
        'TRAINING MODE ACTIVE',
        `- safety net: ON${training.detected_trainer ? ` (${training.detected_trainer})` : ''}`,
        `- goal: ${training.goal || 'learn survival patterns, then graduate off cheats'}`,
        '- coach for bold experimentation first, then keep only lessons that still matter when cheats are off.',
      ].join('\n')
    : [
        'SURVIVAL MODE ACTIVE',
        '- safety net: OFF',
        `- goal: ${training.goal || 'survival without cheats, without trainers'}`,
        '- coach for shield discipline, positioning, and repeatable no-cheat habits.',
      ].join('\n');

  return (
    'you are ken-ai reviewing your own Halo 2 MCC performance.\n\n' +
    trainingBlock + '\n\n' +
    jumpstartPromptBlock() + '\n' +
    'recent actions (last 12 ticks):\n' + tickSummary + '\n\n' +
    'recent events (last 20):\n' + (evtSummary || '  (none)') + '\n\n' +
    'respond with EXACTLY 3 short coaching bullets, each on its own line, each ' +
    'prefixed with "- ". keep each under 14 words. format:\n\n' +
    '- WIN: <something that worked, do more of it>\n' +
    '- FAIL: <something that failed or is repeating, stop doing it>\n' +
    '- NEXT: <one specific adjustment to try>\n\n' +
    'no prose, no markdown wrapper, no apologies. three lines only.\n'
  );
}

function parseBullets(raw) {
  const text = stripAnsi(raw || '');
  const out = { win: '', fail: '', next: '' };
  for (const line of text.split('\n')) {
    const trimmed = line.trim().replace(/^[-*]\s*/, '');
    const match = /^(WIN|FAIL|NEXT)\s*:\s*(.+)$/i.exec(trimmed);
    if (!match) continue;
    const key = match[1].toLowerCase();
    if (key in out) out[key] = match[2].trim().slice(0, 160);
  }
  return out;
}

function runOllamaPrompt(prompt) {
  return new Promise((resolve) => {
    const child = spawn('ollama', ['run', _model], {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    });

    let stdout = '';
    let stderr = '';
    let settled = false;

    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      resolve(result);
    };

    const timeout = setTimeout(() => {
      try { child.kill(); } catch {}
      finish({ ok: false, reason: 'ollama timeout' });
    }, 90000);

    child.stdout.on('data', (chunk) => { stdout += chunk.toString('utf8'); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString('utf8'); });
    child.on('error', (error) => finish({ ok: false, reason: error.message || 'spawn failed' }));
    child.on('close', (code) => {
      if (code !== 0) {
        finish({ ok: false, reason: `ollama exit ${code}`, stderr });
        return;
      }
      finish({ ok: true, stdout });
    });

    child.stdin.write(prompt);
    child.stdin.end();
  });
}

async function runPass() {
  if (_passInFlight) return { ok: false, reason: 'trainer pass already running' };
  _passInFlight = true;

  try {
    const ticks = readLastN(HALO_LOG, 15);
    const events = readLastN(EVT_LOG, 25);
    _stats.lastEntries = ticks.length + events.length;

    if (ticks.length < 3) return { ok: false, reason: 'not enough ticks' };

    const prompt = buildCoachPrompt(ticks, events);
    const result = await runOllamaPrompt(prompt);
    if (!result.ok) return { ok: false, reason: result.reason || 'ollama failed' };

    const parsed = parseBullets(result.stdout);
    const stamped = [];
    if (parsed.win) { appendLesson('wins_log', 'coach:WIN ' + parsed.win); stamped.push('win'); }
    if (parsed.fail) { appendLesson('deaths_log', 'coach:FAIL ' + parsed.fail); stamped.push('fail'); }
    if (parsed.next) { appendLesson('tactics_learned', 'coach:NEXT ' + parsed.next); stamped.push('next'); }

    _stats.passes += 1;
    _stats.lastRunAt = new Date().toISOString();
    return { ok: true, stamped, bullets: parsed };
  } finally {
    _passInFlight = false;
  }
}

export function startTrainer(opts = {}) {
  if (_running) return { ok: false, reason: 'trainer already running' };
  _intervalMs = Math.max(30000, Math.min(600000, opts.intervalMs || 90000));
  _model = opts.model || 'kenai:v1';
  _running = true;

  const tick = () => {
    if (!_running) return;
    runPass().catch(() => {});
    if (_running) _timer = setTimeout(tick, _intervalMs);
  };

  _timer = setTimeout(tick, 10000);
  return { ok: true, intervalMs: _intervalMs, model: _model };
}

export function stopTrainer() {
  if (!_running) return { ok: false, reason: 'not running' };
  _running = false;
  if (_timer) {
    clearTimeout(_timer);
    _timer = null;
  }
  return { ok: true, stats: _stats };
}

export function trainerStatus() {
  return {
    running: _running,
    intervalMs: _intervalMs,
    model: _model,
    stats: _stats,
    inFlight: _passInFlight,
    trainingMode: getTrainingState(),
  };
}

export async function runTrainerOnce() {
  return runPass();
}
