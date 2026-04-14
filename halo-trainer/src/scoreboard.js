/* scoreboard — reads runs/*.jsonl and prints per-student
   progress. groups by student + curriculum. shows attempts,
   passes, latest percent, trend. */

import { readdirSync, readFileSync, existsSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname  = dirname(fileURLToPath(import.meta.url));
const ROOT       = resolve(__dirname, '..');
const RUNS_DIR   = join(ROOT, 'runs');
const REPORTS    = join(ROOT, 'reports');

function loadAllRuns() {
  if (!existsSync(RUNS_DIR)) return [];
  const files = readdirSync(RUNS_DIR).filter(f => f.endsWith('.jsonl'));
  const rows = [];
  for (const f of files) {
    const raw = readFileSync(join(RUNS_DIR, f), 'utf8');
    for (const line of raw.split('\n')) {
      if (!line.trim()) continue;
      try { rows.push(JSON.parse(line)); } catch (e) { /* skip */ }
    }
  }
  rows.sort((a, b) => (a.at || '').localeCompare(b.at || ''));
  return rows;
}

function groupBy(rows, keyFn) {
  const m = new Map();
  for (const r of rows) {
    const k = keyFn(r);
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(r);
  }
  return m;
}

function computeTrend(pcts) {
  if (pcts.length < 2) return 'flat';
  const first = pcts.slice(0, Math.ceil(pcts.length / 2));
  const second = pcts.slice(Math.ceil(pcts.length / 2));
  const avgA = first.reduce((a, b) => a + b, 0) / first.length;
  const avgB = second.reduce((a, b) => a + b, 0) / second.length;
  if (avgB - avgA > 0.05) return 'rising';
  if (avgA - avgB > 0.05) return 'falling';
  return 'flat';
}

export function buildScoreboard() {
  const rows = loadAllRuns();
  if (!rows.length) {
    return { empty: true, message: 'no runs yet — try `node src/runner.js`' };
  }

  const byStudent = groupBy(rows, r => r.student);
  const summary = [];
  for (const [student, studentRows] of byStudent) {
    const byCurr = groupBy(studentRows, r => r.curriculum || 'general');
    const currStats = [];
    for (const [curr, currRows] of byCurr) {
      const pcts = currRows.map(r => (r.grade && r.grade.percent) || 0);
      const passes = currRows.filter(r => r.grade && r.grade.passed).length;
      currStats.push({
        curriculum: curr,
        attempts: currRows.length,
        passes,
        passRate: Math.round((passes / currRows.length) * 100),
        latestPercent: Math.round(pcts[pcts.length - 1] * 100),
        avgPercent: Math.round((pcts.reduce((a, b) => a + b, 0) / pcts.length) * 100),
        trend: computeTrend(pcts),
      });
    }
    const allPcts = studentRows.map(r => (r.grade && r.grade.percent) || 0);
    const allPasses = studentRows.filter(r => r.grade && r.grade.passed).length;
    summary.push({
      student,
      totalAttempts: studentRows.length,
      totalPasses: allPasses,
      overallPassRate: Math.round((allPasses / studentRows.length) * 100),
      avgPercent: Math.round((allPcts.reduce((a, b) => a + b, 0) / allPcts.length) * 100),
      curricula: currStats,
    });
  }
  summary.sort((a, b) => b.avgPercent - a.avgPercent);
  return { empty: false, at: new Date().toISOString(), summary };
}

function printScoreboard(board) {
  if (board.empty) {
    console.log(board.message);
    return;
  }
  console.log(`\nhalo-trainer scoreboard — ${board.at}\n`);
  console.log('rank  student'.padEnd(42) + 'attempts  passes  pass%  avg%');
  console.log(''.padEnd(80, '─'));
  let rank = 1;
  for (const s of board.summary) {
    const line =
      String(rank).padEnd(6) +
      s.student.padEnd(32) +
      String(s.totalAttempts).padEnd(10) +
      String(s.totalPasses).padEnd(8) +
      (String(s.overallPassRate) + '%').padEnd(7) +
      (String(s.avgPercent) + '%');
    console.log(line);
    rank += 1;
  }
  console.log('');
  for (const s of board.summary) {
    console.log(`  ${s.student}`);
    for (const c of s.curricula) {
      console.log(`    ${c.curriculum.padEnd(24)} ${c.attempts}x  ${c.passes}✓  ${c.passRate}%  avg=${c.avgPercent}%  latest=${c.latestPercent}%  ${c.trend}`);
    }
  }
}

function saveReport(board) {
  if (!existsSync(REPORTS)) {
    try { require('fs').mkdirSync(REPORTS, { recursive: true }); } catch (e) {}
  }
  const path = join(REPORTS, 'scoreboard.json');
  writeFileSync(path, JSON.stringify(board, null, 2), 'utf8');
}

const _entry = process.argv[1] || '';
if (import.meta.url === `file://${_entry.replace(/\\/g, '/')}` ||
    (import.meta.url.endsWith('/scoreboard.js') && _entry.endsWith('scoreboard.js'))) {
  const board = buildScoreboard();
  printScoreboard(board);
  saveReport(board);
}
