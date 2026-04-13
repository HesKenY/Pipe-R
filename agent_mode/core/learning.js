/* ══════════════════════════════════════════════════════
   CHERP / Pipe-R — Per-agent learning event log
   ──────────────────────────────────────────────────────
   Every time a task completes AND gets reviewed (approved
   or rejected), we stamp an entry to that agent's
   `learning.jsonl`. These are the ground-truth deltas
   that tell the stats engine "this agent got better at X"
   or "this agent keeps failing at Y".

   Each entry shape:
   {
     at:         ISO timestamp,
     taskId:     string,
     taskType:   string,
     outcome:    'approve' | 'reject' | 'fail',
     xpGain:     int (0 if rejected/failed),
     elapsed:    ms,
     attempt:    number (1 for first try),
     note:       string,       // reviewer note if any
     objective:  string        // what was asked
   }

   Writes are append-only. The file lives alongside notes.md
   and chat-log.jsonl in each agent's memory dir. Readers
   (dreams.js, stats.js, the deck) can stream it.

   ══════════════════════════════════════════════════════ */

import { existsSync, mkdirSync, appendFileSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEMORIES_DIR = join(__dirname, '..', 'memories');

function slugFor(agentId) {
  return String(agentId || '').replace(/:/g, '-');
}

function ensureDir(agentId) {
  const dir = join(MEMORIES_DIR, slugFor(agentId));
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  return dir;
}

function learningPath(agentId) {
  return join(ensureDir(agentId), 'learning.jsonl');
}

/* ── Write a learning event. Non-throwing. ── */
export function recordLearning(agentId, entry) {
  try {
    const row = {
      at: new Date().toISOString(),
      taskId: entry.taskId || null,
      taskType: entry.taskType || 'unknown',
      outcome: entry.outcome || 'unknown',
      xpGain: entry.xpGain || 0,
      elapsed: entry.elapsed || 0,
      attempt: entry.attempt || 1,
      note: entry.note || '',
      objective: entry.objective ? String(entry.objective).slice(0, 240) : '',
    };
    appendFileSync(learningPath(agentId), JSON.stringify(row) + '\n', 'utf8');
    return true;
  } catch (e) {
    return false;
  }
}

/* ── Read an agent's learning events (most recent first). ── */
export function readLearning(agentId, limit = 100) {
  const p = learningPath(agentId);
  if (!existsSync(p)) return [];
  try {
    const raw = readFileSync(p, 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    const out = [];
    for (let i = lines.length - 1; i >= 0 && out.length < limit; i--) {
      try { out.push(JSON.parse(lines[i])); }
      catch (e) { /* skip torn */ }
    }
    return out;
  } catch (e) { return []; }
}

/* ── Summary stats for a single agent's learning log.
   Called by the deck to show a quick "trajectory" chip. ── */
export function summarizeLearning(agentId, windowSize = 30) {
  const rows = readLearning(agentId, windowSize);
  if (!rows.length) return { count: 0, approveRate: 0, xpLast: 0, trajectory: 'idle' };

  const approved = rows.filter(r => r.outcome === 'approve').length;
  const xpLast = rows.reduce((s, r) => s + (r.xpGain || 0), 0);
  const approveRate = Math.round((approved / rows.length) * 100);

  // Trajectory — compare the most-recent half to the older half.
  // Rising = the agent is getting more approvals lately.
  let trajectory = 'steady';
  if (rows.length >= 10) {
    const half = Math.floor(rows.length / 2);
    const recent = rows.slice(0, half);
    const older  = rows.slice(half);
    const recentRate = recent.filter(r => r.outcome === 'approve').length / recent.length;
    const olderRate  = older.filter(r => r.outcome === 'approve').length / older.length;
    if (recentRate > olderRate + 0.12) trajectory = 'rising';
    else if (recentRate < olderRate - 0.12) trajectory = 'falling';
  }

  return {
    count: rows.length,
    approveRate,
    xpLast,
    trajectory,
    lastAt: rows[0]?.at || null,
  };
}

/* ── Bulk summary for the deck — one call, all agents. ── */
export function summarizeAllLearning(agentIds, windowSize = 30) {
  const out = {};
  for (const id of agentIds) {
    out[id] = summarizeLearning(id, windowSize);
  }
  return out;
}
