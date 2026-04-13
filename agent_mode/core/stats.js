/* ══════════════════════════════════════════════════════
   CHERP / Pipe-R — Agent stats engine
   ──────────────────────────────────────────────────────
   Computes per-agent programming-ability stats from the
   raw training-log.jsonl rows. Every stat is grounded in
   actual task outcomes (success, approval, retry count,
   elapsed time) — no placeholder bars.

   Public API:
     computeAgentStats(agentId, opts?)  → stats object
     computeAllStats(opts?)             → { [agentId]: stats }
     xpToLevel(xp)                      → level number
     levelThreshold(level)              → xp required

   Stat definitions (0–100 scale where applicable):
     code   — approval rate on implementation-type tasks
              (draft_patch, draft_test, implement, refactor, fix)
     recon  — approval rate on scan / analyze / map tasks
     qa     — approval rate on review / audit / lint tasks
     docs   — approval rate on summarize / document / learn tasks
     speed  — inverse of median elapsed time (normalized 0–100)
     grit   — % of successful tasks that completed on first attempt
     volume — raw attempt count, log-scaled to 0–100
     xp     — weighted total across approved tasks
     level  — derived from xp via a soft curve
     class  — dominant specialty ("Implementor", "Auditor", etc.)

   A task is "approved" if reviewed===true && approved===true.
   A task is "successful" if success===true (executor exit code 0).
   These are DIFFERENT — a successful dispatch can still be
   rejected in review (hallucinated code, wrong approach).

   ══════════════════════════════════════════════════════ */

import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const TRAINING_LOG = join(__dirname, '..', 'training', 'training-log.jsonl');
const AGENTS_JSON  = join(__dirname, '..', 'config', 'agents.json');

/* ── Task type buckets ── */
const CODE_TYPES  = new Set(['draft_patch', 'draft_test', 'implement', 'refactor', 'fix', 'patch']);
const RECON_TYPES = new Set(['scan', 'analyze', 'map', 'investigate', 'trace']);
const QA_TYPES    = new Set(['review', 'audit', 'lint', 'test', 'critique']);
const DOCS_TYPES  = new Set(['summarize', 'document', 'learn', 'extract', 'memory_extract']);

/* ── Level curve: soft polynomial so early levels come
   fast (keeps morale), late levels slow down. ── */
const LEVEL_CURVE = [
  0, 100, 240, 430, 680, 1000, 1400, 1890, 2480, 3180, 4000,
  4960, 6080, 7380, 8880, 10600, 12560, 14780, 17280, 20080, 23200,
];

export function xpToLevel(xp) {
  if (xp == null || xp < 0) return 1;
  for (let i = LEVEL_CURVE.length - 1; i >= 0; i--) {
    if (xp >= LEVEL_CURVE[i]) return i + 1;
  }
  return 1;
}

export function levelThreshold(level) {
  if (level <= 0) return 0;
  if (level >= LEVEL_CURVE.length) return LEVEL_CURVE[LEVEL_CURVE.length - 1] + (level - LEVEL_CURVE.length) * 3500;
  return LEVEL_CURVE[level - 1];
}

/* ── Read the training log efficiently. We could stream but
   the file is small (<1MB for the life of the project so far);
   a full read is fine. Skip lines that don't parse. ── */
function readTrainingRows() {
  if (!existsSync(TRAINING_LOG)) return [];
  const raw = readFileSync(TRAINING_LOG, 'utf8');
  const out = [];
  const lines = raw.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    try { out.push(JSON.parse(line)); }
    catch (e) { /* torn write or non-json — skip */ }
  }
  return out;
}

/* ── Load agent roster so we can resolve agentId → base model. ── */
function readAgents() {
  if (!existsSync(AGENTS_JSON)) return [];
  try { return JSON.parse(readFileSync(AGENTS_JSON, 'utf8')); }
  catch (e) { return []; }
}

function getAgentByBase(agents, base) {
  return agents.find(a => (a.base || a.id) === base) || null;
}

/* ── XP weights per task type. Tuned so implementation work
   scores the most (it's the load-bearing skill for a standalone
   programmer) and chat scores the least (it's context, not output). ── */
const XP_BASE = {
  draft_patch:  40,
  draft_test:   35,
  implement:    40,
  refactor:     35,
  fix:          30,
  patch:        30,
  scan:         15,
  analyze:      18,
  map:          18,
  investigate:  20,
  trace:        18,
  review:       22,
  audit:        25,
  lint:         15,
  test:         25,
  critique:     20,
  summarize:    12,
  document:     15,
  learn:        12,
  extract:      12,
  memory_extract: 12,
  chat:          3,
};

function xpForTask(row) {
  const base = XP_BASE[row.taskType] || 10;
  // First-attempt bonus — getting it right on try 1 is a real skill
  const firstAttempt = (row.attempt == null || row.attempt === 1) ? 1.25 : 1.0;
  return Math.round(base * firstAttempt);
}

/* ── Compute a rate over a subset of rows. ── */
function bucketStats(rows) {
  let attempts = 0, approved = 0, rejected = 0, successful = 0;
  let totalElapsed = 0, elapsedCount = 0;
  let firstAttemptSuccesses = 0;
  for (const r of rows) {
    attempts++;
    if (r.success) successful++;
    if (r.success && (r.attempt == null || r.attempt === 1)) firstAttemptSuccesses++;
    if (r.reviewed && r.approved === true) approved++;
    if (r.reviewed && r.approved === false) rejected++;
    if (typeof r.elapsed === 'number' && r.elapsed > 0) {
      totalElapsed += r.elapsed;
      elapsedCount++;
    }
  }
  return { attempts, approved, rejected, successful, totalElapsed, elapsedCount, firstAttemptSuccesses };
}

/* ── Normalize a raw rate (0-1) to a display 0-100 scale.
   We apply a gentle floor so brand-new agents don't show 0s
   (which feels broken rather than "untested"). ── */
function rate(ok, total, fallback = 0) {
  if (total === 0) return fallback;
  return Math.round((ok / total) * 100);
}

/* ── Core per-agent computation ── */
export function computeAgentStats(agentId, opts = {}) {
  const rows = opts._rows || readTrainingRows();
  const agents = opts._agents || readAgents();
  const agent = agents.find(a => a.id === agentId);
  if (!agent) {
    return emptyStats(agentId);
  }
  // Match on base model name — training-log stores `model`,
  // which is the base, not the composed agent id.
  const base = agent.base || agent.id;
  const mine = rows.filter(r => r.model === base);

  const all   = bucketStats(mine);
  const code  = bucketStats(mine.filter(r => CODE_TYPES.has(r.taskType)));
  const recon = bucketStats(mine.filter(r => RECON_TYPES.has(r.taskType)));
  const qa    = bucketStats(mine.filter(r => QA_TYPES.has(r.taskType)));
  const docs  = bucketStats(mine.filter(r => DOCS_TYPES.has(r.taskType)));

  // XP from APPROVED tasks only. Rejected = no points.
  let xp = 0;
  for (const r of mine) {
    if (r.reviewed && r.approved === true) xp += xpForTask(r);
  }
  const level = xpToLevel(xp);
  const nextThreshold = levelThreshold(level + 1);
  const prevThreshold = levelThreshold(level);

  // Speed stat — invert median elapsed. Fast tasks get higher
  // scores. We use median not mean so one timeout doesn't tank it.
  const elapsedMs = mine.filter(r => typeof r.elapsed === 'number' && r.elapsed > 0).map(r => r.elapsed).sort((a,b) => a-b);
  let speed = 50; // default neutral
  if (elapsedMs.length) {
    const median = elapsedMs[Math.floor(elapsedMs.length / 2)];
    // 5s = 100, 60s = 50, 120s = 10
    speed = Math.max(0, Math.min(100, Math.round(100 - (median - 5000) / 1150)));
  }

  // Grit — success rate on first-attempt, out of tasks that
  // eventually succeeded. Measures "gets it right the first time".
  const grit = all.successful ? rate(all.firstAttemptSuccesses, all.successful, 0) : 0;

  // Volume — log-scaled attempt count. 1 attempt = 0, 100+ = 100.
  const volume = all.attempts === 0 ? 0
    : Math.min(100, Math.round(Math.log10(all.attempts + 1) * 50));

  // Per-bucket rate (approved / attempted within bucket, fallback 0)
  const codeStat  = code.attempts  ? rate(code.approved,  code.attempts,  0) : 0;
  const reconStat = recon.attempts ? rate(recon.approved, recon.attempts, 0) : 0;
  const qaStat    = qa.attempts    ? rate(qa.approved,    qa.attempts,    0) : 0;
  const docsStat  = docs.attempts  ? rate(docs.approved,  docs.attempts,  0) : 0;

  // Readiness — composite health index. A successful + high-
  // approval + fast + gritty agent is "ready". Weights tuned.
  const readiness = Math.round(
    (codeStat  * 0.30) +
    (reconStat * 0.15) +
    (qaStat    * 0.15) +
    (docsStat  * 0.10) +
    (speed     * 0.10) +
    (grit      * 0.10) +
    (Math.min(100, all.attempts * 2) * 0.10) // exposure baseline
  );

  // Dominant class — which stat is this agent strongest in?
  const classCandidates = [
    { name: 'Implementor', score: codeStat  + (code.attempts  * 1.5) },
    { name: 'Pathfinder',  score: reconStat + (recon.attempts * 1.5) },
    { name: 'Auditor',     score: qaStat    + (qa.attempts    * 1.5) },
    { name: 'Archivist',   score: docsStat  + (docs.attempts  * 1.5) },
  ];
  classCandidates.sort((a, b) => b.score - a.score);
  const dominantClass = all.attempts === 0 ? 'Untested' : classCandidates[0].name;

  return {
    agentId,
    base,
    level,
    xp,
    xpInLevel: xp - prevThreshold,
    xpForLevel: nextThreshold - prevThreshold,
    readiness,
    class: dominantClass,
    stats: {
      code:   codeStat,
      recon:  reconStat,
      qa:     qaStat,
      docs:   docsStat,
      speed:  Math.round(speed),
      grit:   Math.round(grit),
      volume: Math.round(volume),
    },
    counts: {
      attempts: all.attempts,
      approved: all.approved,
      rejected: all.rejected,
      successful: all.successful,
      codeAttempts:  code.attempts,
      reconAttempts: recon.attempts,
      qaAttempts:    qa.attempts,
      docsAttempts:  docs.attempts,
    },
    tuning: {
      lastSeenAt: mine.length ? mine[mine.length - 1].timestamp : null,
    },
  };
}

function emptyStats(agentId) {
  return {
    agentId,
    base: null,
    level: 1,
    xp: 0,
    xpInLevel: 0,
    xpForLevel: LEVEL_CURVE[1],
    readiness: 0,
    class: 'Untested',
    stats: { code: 0, recon: 0, qa: 0, docs: 0, speed: 50, grit: 0, volume: 0 },
    counts: { attempts: 0, approved: 0, rejected: 0, successful: 0, codeAttempts: 0, reconAttempts: 0, qaAttempts: 0, docsAttempts: 0 },
    tuning: { lastSeenAt: null },
  };
}

export function computeAllStats(opts = {}) {
  const rows   = opts._rows   || readTrainingRows();
  const agents = opts._agents || readAgents();
  const out = {};
  for (const agent of agents) {
    out[agent.id] = computeAgentStats(agent.id, { _rows: rows, _agents: agents });
  }
  return out;
}

/* Synchronous helpers used by the dashboard endpoint to avoid
   re-parsing the whole log on every /api/dashboard request. A
   tiny 2s cache matches the existing /api/metrics pattern. */
let _cache = { at: 0, stats: null };
export function getStatsCached(ttlMs = 2000) {
  const now = Date.now();
  if (_cache.stats && (now - _cache.at) < ttlMs) return _cache.stats;
  _cache = { at: now, stats: computeAllStats() };
  return _cache.stats;
}

export function invalidateStatsCache() {
  _cache = { at: 0, stats: null };
}
