/**
 * Training log curator.
 *
 * Reads agent_mode/training/training-log.jsonl, filters out noise, writes
 * agent_mode/training/training-log.curated.jsonl. Also prints a per-agent
 * breakdown so Ken can see who's actually contributing clean data.
 *
 * Filter rules (tunable at the top):
 *   - success must be true
 *   - response length must be >= MIN_RESPONSE_CHARS
 *   - model must not be in BROKEN_AGENTS
 *   - taskType must not be in DROPPED_TYPES
 *
 * Node built-ins only. Run with:
 *   node agent_mode/training/curate.js
 *
 * Or from hub.js Agent Mode menu once the button is wired in.
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const LOG_PATH       = join(__dirname, 'training-log.jsonl');
const CURATED_PATH   = join(__dirname, 'training-log.curated.jsonl');

// --- tunables ---
const MIN_RESPONSE_CHARS = 40;
const BROKEN_AGENTS = new Set([
  'jefferferson:latest',   // 82-retry loop, always times out
]);
const DROPPED_TYPES = new Set([
  // Add task types here if we find systematic junk from one
]);
// -----------------

function main() {
  if (!existsSync(LOG_PATH)) {
    console.error('No training log at ' + LOG_PATH);
    process.exit(1);
  }

  const raw = readFileSync(LOG_PATH, 'utf8');
  const lines = raw.split('\n').filter(Boolean);

  const kept = [];
  const stats = {
    total: 0,
    kept: 0,
    droppedParseError: 0,
    droppedNotSuccess: 0,
    droppedShort: 0,
    droppedBrokenAgent: 0,
    droppedDroppedType: 0,
    byAgent: {},  // { 'ken-ai:latest': { kept: N, dropped: M }, ... }
  };

  for (const line of lines) {
    stats.total++;
    let e;
    try { e = JSON.parse(line); }
    catch { stats.droppedParseError++; continue; }

    const model = e.model || 'unknown';
    if (!stats.byAgent[model]) stats.byAgent[model] = { kept: 0, dropped: 0 };

    if (!e.success) {
      stats.droppedNotSuccess++;
      stats.byAgent[model].dropped++;
      continue;
    }
    if (BROKEN_AGENTS.has(model)) {
      stats.droppedBrokenAgent++;
      stats.byAgent[model].dropped++;
      continue;
    }
    if (DROPPED_TYPES.has(e.taskType)) {
      stats.droppedDroppedType++;
      stats.byAgent[model].dropped++;
      continue;
    }
    const respLen = (e.response || '').length;
    if (respLen < MIN_RESPONSE_CHARS) {
      stats.droppedShort++;
      stats.byAgent[model].dropped++;
      continue;
    }

    kept.push(line);
    stats.kept++;
    stats.byAgent[model].kept++;
  }

  writeFileSync(CURATED_PATH, kept.join('\n') + (kept.length ? '\n' : ''));

  // report
  const pct = stats.total ? Math.round((stats.kept / stats.total) * 100) : 0;
  console.log('training log curate — ' + LOG_PATH);
  console.log('  total entries:     ' + stats.total);
  console.log('  kept:              ' + stats.kept + '  (' + pct + '%)');
  console.log('  dropped (fail):    ' + stats.droppedNotSuccess);
  console.log('  dropped (short):   ' + stats.droppedShort);
  console.log('  dropped (broken):  ' + stats.droppedBrokenAgent);
  console.log('  dropped (type):    ' + stats.droppedDroppedType);
  if (stats.droppedParseError) console.log('  parse errors:      ' + stats.droppedParseError);
  console.log('');
  console.log('per-agent breakdown:');
  const rows = Object.entries(stats.byAgent).sort((a, b) => b[1].kept - a[1].kept);
  for (const [model, s] of rows) {
    const tot = s.kept + s.dropped;
    const p = tot ? Math.round((s.kept / tot) * 100) : 0;
    console.log('  ' + model.padEnd(32) + '  kept ' + String(s.kept).padStart(3) + ' / ' + String(tot).padStart(3) + '  (' + p + '%)');
  }
  console.log('');
  console.log('wrote ' + stats.kept + ' clean entries → ' + CURATED_PATH);

  // Exit code reflects whether we have enough to fine-tune yet
  const FINE_TUNE_THRESHOLD = 200;
  if (stats.kept >= FINE_TUNE_THRESHOLD) {
    console.log('\n✓ ready for fine-tune (>= ' + FINE_TUNE_THRESHOLD + ' clean entries)');
  } else {
    console.log('\n… ' + (FINE_TUNE_THRESHOLD - stats.kept) + ' more clean entries needed before fine-tune');
  }
}

main();
