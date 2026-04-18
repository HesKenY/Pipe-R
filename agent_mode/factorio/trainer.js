/*
  Factorio trainer — coaching + strategic planning loop.

  Unlike Halo's tick-by-tick reflexes, Factorio needs STRATEGIC
  thinking. The trainer runs every 90s and:

  1. Reads the latest vision state (factorio_tick.py output)
  2. Reads the game knowledge (recipes, ratios, save state)
  3. Reads the memory (deaths, tactics, blueprints, bottlenecks)
  4. Asks kenai:v1 for a strategic assessment:
     - What should we build next?
     - Are there bottlenecks to fix?
     - Is the factory defended?
     - What research to prioritize?
  5. Writes the assessment to memory for the drive loop to act on

  The trainer thinks in GOALS, not actions. The drive loop
  translates goals into keypress sequences.
*/

import { spawnSync } from 'node:child_process';
import { readFileSync, appendFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR = join(__dirname, '..', 'memories', 'ken-ai-latest');
const MEMORY_FILE = join(__dirname, 'memory.md');
const KNOWLEDGE_FILE = join(MEM_DIR, 'factorio-game-knowledge.json');
const LOG_FILE = join(MEM_DIR, 'factorio-log.jsonl');

let _timer = null;
let _running = false;
let _intervalMs = 90000;
let _model = 'kenai:v1';
let _stats = { passes: 0, lastRunAt: null };

function stripAnsi(s) {
  return String(s || '')
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '')
    .trim();
}

function readMemory() {
  if (!existsSync(MEMORY_FILE)) return '';
  try { return readFileSync(MEMORY_FILE, 'utf8'); } catch (e) { return ''; }
}

function readKnowledge() {
  if (!existsSync(KNOWLEDGE_FILE)) return {};
  try { return JSON.parse(readFileSync(KNOWLEDGE_FILE, 'utf8')); } catch (e) { return {}; }
}

function appendLesson(section, line) {
  if (!existsSync(MEMORY_FILE)) return;
  try {
    const mem = readFileSync(MEMORY_FILE, 'utf8');
    const marker = `## ${section}`;
    if (mem.includes(marker)) {
      const updated = mem.replace(marker, marker + '\n- ' + new Date().toISOString().slice(0,19) + ' — ' + line);
      const fs = await import('node:fs');
      fs.writeFileSync(MEMORY_FILE, updated, 'utf8');
    }
  } catch (e) {}
}

function logEntry(entry) {
  try {
    appendFileSync(LOG_FILE, JSON.stringify(entry) + '\n', 'utf8');
  } catch (e) {}
}

async function runPass() {
  const memory = readMemory();
  const knowledge = readKnowledge();

  const prompt = `you are kenai, factorio strategic planner. review the factory state and decide what to do next.

## game knowledge
${knowledge.ratioGuide ? Object.entries(knowledge.ratioGuide).map(([k,v]) => `- ${k}: ${v}`).join('\n') : 'no ratios loaded'}

## current memory
${memory.slice(0, 3000)}

## task
analyze the factory state. respond with EXACTLY this format:
GOAL: (one sentence — what to build/fix/research next)
REASON: (one sentence — why this is the priority)
STEPS: (2-4 numbered steps to achieve the goal)
RISK: (one sentence — what could go wrong, how to mitigate)

be specific. name exact recipes, exact counts, exact belt types.`;

  const t0 = Date.now();
  const res = spawnSync('ollama', ['run', _model], {
    input: prompt,
    encoding: 'utf8',
    timeout: 120000,
    maxBuffer: 4 * 1024 * 1024,
    windowsHide: true,
  });

  const elapsed = Date.now() - t0;
  const raw = stripAnsi(res.stdout || '');
  _stats.passes++;
  _stats.lastRunAt = new Date().toISOString();

  const entry = {
    at: _stats.lastRunAt,
    type: 'trainer_pass',
    model: _model,
    elapsed,
    response: raw.slice(0, 1000),
    pass: _stats.passes,
  };
  logEntry(entry);

  // Extract GOAL line and append to memory
  const goalMatch = raw.match(/GOAL:\s*(.+)/i);
  if (goalMatch) {
    try {
      const mem = readFileSync(MEMORY_FILE, 'utf8');
      const updated = mem.replace(
        '## tactics_learned',
        '## tactics_learned\n- ' + new Date().toISOString().slice(0,19) + ' — trainer: ' + goalMatch[1].trim()
      );
      const { writeFileSync } = await import('node:fs');
      writeFileSync(MEMORY_FILE, updated, 'utf8');
    } catch (e) {}
  }

  return entry;
}

export function startTrainer(opts = {}) {
  if (_running) return { ok: false, reason: 'already running' };
  _intervalMs = opts.intervalMs || 90000;
  _model = opts.model || 'kenai:v1';
  _running = true;

  const tick = () => {
    if (!_running) return;
    runPass().catch(() => {});
    if (_running) _timer = setTimeout(tick, _intervalMs);
  };
  tick();
  return { ok: true, intervalMs: _intervalMs, model: _model };
}

export function stopTrainer() {
  _running = false;
  if (_timer) clearTimeout(_timer);
  _timer = null;
  return { ok: true, passes: _stats.passes };
}

export function trainerStatus() {
  return { running: _running, stats: _stats, model: _model, intervalMs: _intervalMs };
}
