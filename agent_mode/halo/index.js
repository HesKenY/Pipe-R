/* ══════════════════════════════════════════════════════
   Halo learning-data index — fast retrieval for prompts
   ──────────────────────────────────────────────────────
   The core problem: the full halo-memory.md + halo2-guide.md
   + notes.md dump into every prompt adds up to 20-30KB. At
   that size, llama3.1:8b inference is 10-30s per tick. Real
   cure: don't dump everything. Build an inverted keyword
   index and retrieve only the top-K relevant bullets for
   the current situation.

   Build: scan halo-memory.md (tactics_learned, deaths_log,
   wins_log, ken_patterns) + halo2-guide.md + the last 40
   halo-log ticks. Tokenize each bullet into words. Build
   a `Map<word, Set<bulletId>>`.

   Query: given a current state + recent actions, extract
   query terms (activity label, weapon hint, recent actions)
   and union-lookup the inverted index. Score bullets by
   match count, return top N.

   Rebuild: on-demand via rebuildIndex(). Called periodically
   by the drive loop (every 30s) so new dreams/patterns land
   in the index without a restart.

   No dependencies. Pure JS. ~30ms to build from scratch for
   ~500 bullets.
   ══════════════════════════════════════════════════════ */

import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR   = join(__dirname, '..', 'memories', 'ken-ai-latest');

const STOPWORDS = new Set([
  'the', 'and', 'or', 'a', 'an', 'to', 'for', 'in', 'on', 'at',
  'of', 'is', 'are', 'was', 'were', 'with', 'from', 'by', 'as',
  'it', 'that', 'this', 'you', 'your', 'be', 'not', 'but', 'so',
  'if', 'when', 'than', 'then', 'do', 'does', 'did', 'have',
  'has', 'had', 'will', 'would', 'can', 'could', 'should', 'may',
]);

const ACTION_WORDS = new Set([
  'move', 'fwd', 'back', 'strafe', 'left', 'right', 'jump',
  'crouch', 'sprint', 'reload', 'interact', 'grenade', 'melee',
  'fire', 'ads', 'look', 'up', 'down', 'noop', 'pause',
  'weapon', 'dual', 'wield', 'flashlight', 'scoreboard',
]);

let _index = {
  bullets: [],            // [{id, source, text, tokens}]
  inverted: new Map(),    // word → Set<bulletId>
  builtAt: null,
  tokenCount: 0,
};

function tokenize(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, ' ')
    .split(' ')
    .filter(t => t.length >= 3 && !STOPWORDS.has(t))
    .slice(0, 40);
}

function addBullet(source, text) {
  const cleaned = String(text || '').trim();
  if (!cleaned || cleaned.length < 6) return;
  const id = _index.bullets.length;
  const tokens = tokenize(cleaned);
  _index.bullets.push({ id, source, text: cleaned, tokens });
  for (const tok of tokens) {
    if (!_index.inverted.has(tok)) _index.inverted.set(tok, new Set());
    _index.inverted.get(tok).add(id);
    _index.tokenCount += 1;
  }
}

function loadMemoryBullets() {
  const path = join(MEM_DIR, 'halo-memory.md');
  if (!existsSync(path)) return;
  try {
    const raw = readFileSync(path, 'utf8');
    const lines = raw.split('\n');
    let currentSection = null;
    for (const line of lines) {
      const h = /^## (\w+)/.exec(line);
      if (h) { currentSection = h[1]; continue; }
      const b = /^-\s+(.+)/.exec(line);
      if (b && currentSection) {
        addBullet(`memory:${currentSection}`, b[1]);
      }
    }
  } catch (e) { /* skip */ }
}

function loadGuideBullets() {
  const path = join(__dirname, 'halo2-guide.md');
  if (!existsSync(path)) return;
  try {
    const raw = readFileSync(path, 'utf8');
    const lines = raw.split('\n');
    let currentSection = 'guide';
    for (const line of lines) {
      const h = /^#+\s*(.+)/.exec(line);
      if (h) { currentSection = h[1].toLowerCase().slice(0, 24); continue; }
      const b = /^-\s+(.+)/.exec(line);
      if (b) addBullet(`guide:${currentSection}`, b[1]);
      // Also index table rows (weapons table in the guide)
      const t = /^\|\s*([^|]+)\s*\|/.exec(line);
      if (t && t[1] && !t[1].includes('---')) addBullet(`guide:${currentSection}`, t[1]);
    }
  } catch (e) { /* skip */ }
}

function loadRecentTicks() {
  const path = join(MEM_DIR, 'halo-log.jsonl');
  if (!existsSync(path)) return;
  try {
    const raw = readFileSync(path, 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    // Last 40 ticks — enough for short-term context without bloat
    const recent = lines.slice(-40);
    for (const l of recent) {
      try {
        const r = JSON.parse(l);
        const sb = r.stateBefore || {};
        const snippet = `action=${r.action || '?'} activity=${sb.activity || '?'} motion=${sb.motion || 0}`;
        addBullet('ticks:recent', snippet);
      } catch (e) { /* skip */ }
    }
  } catch (e) { /* skip */ }
}

export function rebuildIndex() {
  _index = {
    bullets: [],
    inverted: new Map(),
    builtAt: new Date().toISOString(),
    tokenCount: 0,
  };
  loadMemoryBullets();
  loadGuideBullets();
  loadRecentTicks();
  return {
    bullets: _index.bullets.length,
    uniqueTokens: _index.inverted.size,
    totalTokens: _index.tokenCount,
    builtAt: _index.builtAt,
  };
}

/* ── Query the index: extract words from query, score each
   matching bullet by how many query words match, return the
   top K by score. ── */
export function query(queryText, limit = 6) {
  if (!_index.builtAt) rebuildIndex();
  const qTokens = tokenize(queryText);
  if (!qTokens.length) return [];

  const scores = new Map();
  for (const tok of qTokens) {
    const matches = _index.inverted.get(tok);
    if (!matches) continue;
    for (const id of matches) {
      scores.set(id, (scores.get(id) || 0) + 1);
    }
  }
  if (!scores.size) return [];

  // Sort by score desc, tiebreak by recency (higher id = newer)
  const ranked = Array.from(scores.entries())
    .sort((a, b) => b[1] - a[1] || b[0] - a[0])
    .slice(0, limit);
  return ranked.map(([id, score]) => {
    const b = _index.bullets[id];
    return { score, source: b.source, text: b.text };
  });
}

/* ── Build a compact prompt block from the top-K matches.
   Replaces the giant halo-memory.md + halo2-guide.md dump. ── */
export function buildContextBlock(state, history, limit = 6) {
  // Build query terms from the current state + last actions
  const parts = [];
  if (state?.activity) parts.push(state.activity);
  if (state?.ammo) parts.push(state.ammo);
  if (state?.shield) parts.push(state.shield);
  if (state?.center) parts.push(state.center);
  if (Array.isArray(history)) {
    for (const h of history.slice(-3)) {
      if (h.action) parts.push(h.action);
    }
  }
  const q = parts.join(' ');
  const hits = query(q, limit);
  if (!hits.length) return '';
  const lines = hits.map(h => `  - [${h.source}] ${h.text}`);
  return '\nrelevant context (top ' + hits.length + ' bullets):\n' + lines.join('\n') + '\n';
}

export function indexStats() {
  return {
    builtAt: _index.builtAt,
    bullets: _index.bullets.length,
    uniqueTokens: _index.inverted.size,
    totalTokens: _index.tokenCount,
  };
}
