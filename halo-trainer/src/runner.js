/* runner — reads drills, fires each one against the
   assigned model, grades the output, writes per-run JSONL
   + updates the scoreboard.

   invocation:
     node src/runner.js                    — runs every drill
     node src/runner.js drill1 drill2      — runs specific drills by id
     node src/runner.js --student <id>     — only drills assigned to that student
     node src/runner.js --curriculum <tag> — only drills with that curriculum tag

   each drill json shape:
     {
       "id": "reverse-101",
       "title": "Find halo2.dll base address",
       "student": "cherp-piper:latest",
       "curriculum": "reverse-engineering",
       "contextFiles": ["../agent_mode/memories/ken-ai-latest/halo-game-dump.md"],
       "prompt": "Read the game dump above. What is the base address of halo2.dll in the loaded MCC process?",
       "rubric": [
         { "type": "contains", "needle": "halo2.dll", "weight": 1 },
         { "type": "regex", "pattern": "0x[0-9a-f]{10,}", "flags": "i", "weight": 2 },
         { "type": "min_length", "value": 40, "weight": 1 }
       ],
       "passingPercent": 0.66,
       "timeoutMs": 60000
     } */

import { readdirSync, readFileSync, writeFileSync, appendFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { askModel } from '../tools/ollama.js';
import { grade } from './grader.js';

const __dirname  = dirname(fileURLToPath(import.meta.url));
const ROOT       = resolve(__dirname, '..');
const DRILLS_DIR = join(ROOT, 'drills');
const RUNS_DIR   = join(ROOT, 'runs');
const CORPUS_DIR = join(ROOT, 'corpus');
const LOGS_DIR   = join(ROOT, 'logs');

for (const d of [RUNS_DIR, CORPUS_DIR, LOGS_DIR]) {
  if (!existsSync(d)) mkdirSync(d, { recursive: true });
}

function loadDrills() {
  if (!existsSync(DRILLS_DIR)) return [];
  const files = readdirSync(DRILLS_DIR).filter(f => f.endsWith('.json'));
  const out = [];
  for (const f of files) {
    try {
      const raw = readFileSync(join(DRILLS_DIR, f), 'utf8');
      const drill = JSON.parse(raw);
      drill._file = f;
      out.push(drill);
    } catch (e) {
      console.error(`[runner] bad drill ${f}: ${e.message}`);
    }
  }
  return out;
}

function loadContext(drill) {
  const chunks = [];
  for (const rel of drill.contextFiles || []) {
    const path = resolve(ROOT, rel);
    if (!existsSync(path)) {
      chunks.push(`# ${rel}\n(not found)\n`);
      continue;
    }
    try {
      const raw = readFileSync(path, 'utf8');
      chunks.push(`# ${rel}\n${raw.slice(0, 14000)}\n`);
    } catch (e) {
      chunks.push(`# ${rel}\n(read error: ${e.message})\n`);
    }
  }
  return chunks.join('\n---\n');
}

function parseArgs(argv) {
  const args = { ids: [], student: null, curriculum: null };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--student') { args.student = argv[++i]; continue; }
    if (a === '--curriculum') { args.curriculum = argv[++i]; continue; }
    args.ids.push(a);
  }
  return args;
}

function filterDrills(drills, args) {
  let out = drills;
  if (args.ids.length) out = out.filter(d => args.ids.includes(d.id));
  if (args.student) out = out.filter(d => d.student === args.student);
  if (args.curriculum) out = out.filter(d => d.curriculum === args.curriculum);
  return out;
}

async function runOneDrill(drill) {
  const ctx = loadContext(drill);
  const prompt = (ctx ? ctx + '\n\n---\n\n' : '') + drill.prompt;
  const started = new Date().toISOString();
  const r = askModel(drill.student, prompt, { timeoutMs: drill.timeoutMs || 120000 });
  const result = grade(drill, r.text);
  const row = {
    at: started,
    drillId: drill.id,
    drillFile: drill._file,
    student: drill.student,
    curriculum: drill.curriculum || 'general',
    ok: r.ok,
    elapsedMs: r.elapsed,
    responseLen: (r.text || '').length,
    response: r.text || '',
    grade: result,
    error: r.error || null,
  };
  return row;
}

function writeRunRow(row) {
  const path = join(RUNS_DIR, `${row.drillId}.jsonl`);
  appendFileSync(path, JSON.stringify(row) + '\n', 'utf8');
}

function curateIfPassed(row) {
  if (!row.grade || !row.grade.passed) return;
  const path = join(CORPUS_DIR, `${row.curriculum}.jsonl`);
  const keep = {
    at: row.at,
    drillId: row.drillId,
    student: row.student,
    response: row.response,
    percent: row.grade.percent,
    taskType: 'halo_trainer',
  };
  appendFileSync(path, JSON.stringify(keep) + '\n', 'utf8');
}

export async function runAll(argv = process.argv) {
  const args = parseArgs(argv);
  const all = loadDrills();
  const drills = filterDrills(all, args);
  if (!drills.length) {
    console.error(`[runner] no drills matched — ${all.length} total, ${JSON.stringify(args)}`);
    return { ran: 0, passed: 0 };
  }
  const startedAt = Date.now();
  let passed = 0;
  for (const d of drills) {
    const t0 = Date.now();
    const row = await runOneDrill(d);
    writeRunRow(row);
    curateIfPassed(row);
    if (row.grade && row.grade.passed) passed += 1;
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    const verdict = row.grade && row.grade.passed ? 'PASS' : 'FAIL';
    const pct = row.grade ? Math.round(row.grade.percent * 100) : 0;
    console.log(`[runner] ${d.id.padEnd(28)} ${d.student.padEnd(28)} ${verdict} ${pct}% ${elapsed}s`);
  }
  const totalElapsed = ((Date.now() - startedAt) / 1000).toFixed(1);
  console.log(`[runner] ${passed}/${drills.length} passed in ${totalElapsed}s`);
  return { ran: drills.length, passed, elapsedSec: totalElapsed };
}

const _entry = process.argv[1] || '';
if (import.meta.url === `file://${_entry.replace(/\\/g, '/')}` ||
    import.meta.url.endsWith('/runner.js') && _entry.endsWith('runner.js')) {
  runAll().catch(e => { console.error(e); process.exit(1); });
}
