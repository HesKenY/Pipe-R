/* retry — re-runs only the drills that last failed.

   reads runs/*.jsonl, finds the LATEST row per drill, and
   queues a fresh run for every drill whose latest row is
   either missing or `grade.passed === false`. useful after
   a prompt tweak or a model warm-up. */

import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runAll } from './runner.js';

const __dirname  = dirname(fileURLToPath(import.meta.url));
const ROOT       = resolve(__dirname, '..');
const DRILLS_DIR = join(ROOT, 'drills');
const RUNS_DIR   = join(ROOT, 'runs');

function loadLatestRuns() {
  if (!existsSync(RUNS_DIR)) return new Map();
  const files = readdirSync(RUNS_DIR).filter(f => f.endsWith('.jsonl'));
  const latest = new Map();
  for (const f of files) {
    const raw = readFileSync(join(RUNS_DIR, f), 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    const last = lines[lines.length - 1];
    if (!last) continue;
    try {
      const row = JSON.parse(last);
      latest.set(row.drillId, row);
    } catch (e) { /* skip */ }
  }
  return latest;
}

function listAllDrillIds() {
  if (!existsSync(DRILLS_DIR)) return [];
  return readdirSync(DRILLS_DIR)
    .filter(f => f.endsWith('.json'))
    .map(f => {
      try {
        return JSON.parse(readFileSync(join(DRILLS_DIR, f), 'utf8')).id;
      } catch (e) { return null; }
    })
    .filter(Boolean);
}

export async function retryFailures() {
  const latest = loadLatestRuns();
  const all = listAllDrillIds();
  const retry = [];
  for (const id of all) {
    const row = latest.get(id);
    if (!row) { retry.push(id); continue; }
    if (!row.grade || !row.grade.passed) { retry.push(id); continue; }
  }
  if (!retry.length) {
    console.log('[retry] all drills currently passing — nothing to retry');
    return { ran: 0, passed: 0 };
  }
  console.log(`[retry] retrying ${retry.length} failing drill(s): ${retry.join(', ')}`);
  return runAll(['node', 'retry.js', ...retry]);
}

const _entry = process.argv[1] || '';
if (import.meta.url.endsWith('/retry.js') && _entry.endsWith('retry.js')) {
  retryFailures().catch(e => { console.error(e); process.exit(1); });
}
