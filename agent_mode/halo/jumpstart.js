import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR = join(__dirname, '..', 'memories', 'ken-ai-latest');
const KEYLOG_PATH = join(MEM_DIR, 'halo-keylog.jsonl');
const EVENTS_PATH = join(MEM_DIR, 'halo-events.jsonl');
const HALO_LOG_PATH = join(MEM_DIR, 'halo-log.jsonl');
const OUT_PATH = join(MEM_DIR, 'halo-jumpstart.json');

let _cache = null;
let _lastBuiltAt = 0;

function ensureDir() {
  if (!existsSync(MEM_DIR)) mkdirSync(MEM_DIR, { recursive: true });
}

function readLastNJson(path, limit = 200) {
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

function topEntries(map, limit = 4) {
  return Object.entries(map)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([name, count]) => ({ name, count }));
}

function countKeys(rows) {
  const counts = {};
  for (const row of rows) {
    if (row.kind === 'system' || row.dir === 'up') continue;
    const key = row.kind === 'key'
      ? String(row.key || '').toLowerCase()
      : `mouse:${String(row.button || '').toLowerCase()}`;
    if (!key) continue;
    counts[key] = (counts[key] || 0) + 1;
  }
  return counts;
}

function countPatterns(rows) {
  const counts = {};
  for (const row of rows) {
    if (row.kind !== 'ken_pattern' || !row.pattern) continue;
    const pattern = String(row.pattern);
    counts[pattern] = (counts[pattern] || 0) + 1;
  }
  return counts;
}

function countActions(rows) {
  const counts = {};
  for (const row of rows) {
    const action = String(row.action || '').toLowerCase();
    if (!action) continue;
    counts[action] = (counts[action] || 0) + 1;
  }
  return counts;
}

function buildStyleNotes(keys, patterns, actions) {
  const notes = [];
  const keyNames = new Set(topEntries(keys, 6).map(item => item.name));
  const patternNames = new Set(topEntries(patterns, 6).map(item => item.name));
  const actionNames = new Set(topEntries(actions, 6).map(item => item.name));

  if (keyNames.has('w')) notes.push('Ken pushes forward often. Default to pressure over freezing.');
  if (keyNames.has('a') || keyNames.has('d') || patternNames.has('strafe_shoot')) {
    notes.push('Ken fights while moving sideways. Keep lateral movement active in combat.');
  }
  if (patternNames.has('ads_fire') || keyNames.has('mouse:right')) {
    notes.push('Ken aims before bursting. Snap to head level, then commit.');
  }
  if (patternNames.has('reload_after_fire') || actionNames.has('reload')) {
    notes.push('Ken resets with reload after exchanges. Build that into downtime.');
  }
  if (patternNames.has('grenade_throw')) {
    notes.push('Ken uses grenades as openers. Check throw windows before pure gunplay.');
  }
  if (patternNames.has('noob_combo')) {
    notes.push('Ken reaches for the noob combo. Respect shield-pop into follow-up shots.');
  }
  if (actionNames.has('noop')) {
    notes.push('Recent noops are high. Replace idle ticks with scan, strafe, or advance.');
  }
  if (!notes.length) {
    notes.push('Use recent Ken key rhythms as the starting style, then tighten for survival.');
  }
  return notes.slice(0, 5);
}

function recentKeysLine(rows) {
  return rows
    .filter(row => row.kind !== 'system' && row.dir !== 'up')
    .slice(-8)
    .map(row => row.kind === 'key'
      ? String(row.key || '?').toLowerCase()
      : `mouse:${String(row.button || '?').toLowerCase()}`)
    .join(' ');
}

export function buildJumpstartSnapshot(opts = {}) {
  ensureDir();
  const keyRows = readLastNJson(KEYLOG_PATH, opts.keyLimit || 1200);
  const eventRows = readLastNJson(EVENTS_PATH, opts.eventLimit || 220);
  const haloRows = readLastNJson(HALO_LOG_PATH, opts.tickLimit || 120);

  const keys = countKeys(keyRows);
  const patterns = countPatterns(eventRows);
  const actions = countActions(haloRows);
  const snapshot = {
    builtAt: new Date().toISOString(),
    sourceCounts: {
      keyEvents: keyRows.length,
      patternEvents: eventRows.length,
      haloTicks: haloRows.length,
    },
    dominantKeys: topEntries(keys, 6),
    dominantPatterns: topEntries(patterns, 6),
    dominantActions: topEntries(actions, 6),
    styleNotes: buildStyleNotes(keys, patterns, actions),
    recentKeys: recentKeysLine(keyRows),
  };

  writeFileSync(OUT_PATH, JSON.stringify(snapshot, null, 2), 'utf8');
  _cache = snapshot;
  _lastBuiltAt = Date.now();
  return snapshot;
}

export function refreshJumpstartSnapshot(opts = {}) {
  const minimumIntervalMs = opts.minimumIntervalMs ?? 20000;
  if (_cache && (Date.now() - _lastBuiltAt) < minimumIntervalMs) return _cache;
  if (existsSync(OUT_PATH) && !_cache && (Date.now() - _lastBuiltAt) < minimumIntervalMs) {
    return getJumpstartSnapshot();
  }
  return buildJumpstartSnapshot(opts);
}

export function getJumpstartSnapshot() {
  if (_cache) return _cache;
  if (!existsSync(OUT_PATH)) return buildJumpstartSnapshot();
  try {
    _cache = JSON.parse(readFileSync(OUT_PATH, 'utf8'));
    return _cache;
  } catch {
    return buildJumpstartSnapshot();
  }
}

export function jumpstartPromptBlock() {
  const snapshot = getJumpstartSnapshot();
  if (!snapshot || !snapshot.sourceCounts?.keyEvents) return '';

  const styleLines = (snapshot.styleNotes || []).map(note => `  - ${note}`).join('\n');
  const keyLine = (snapshot.dominantKeys || []).map(item => `${item.name}:${item.count}`).join(', ');
  const patternLine = (snapshot.dominantPatterns || []).map(item => `${item.name}:${item.count}`).join(', ') || 'none yet';
  const actionLine = (snapshot.dominantActions || []).map(item => `${item.name}:${item.count}`).join(', ') || 'none yet';

  return (
    '\n\nKEN JUMPSTART FROM REAL KEYLOGS\n' +
    `  built: ${snapshot.builtAt}\n` +
    `  dominant_keys: ${keyLine || 'none yet'}\n` +
    `  dominant_patterns: ${patternLine}\n` +
    `  dominant_agent_actions: ${actionLine}\n` +
    (snapshot.recentKeys ? `  recent_keys: ${snapshot.recentKeys}\n` : '') +
    styleLines + '\n' +
    '  - Start from Ken-style movement and combat cadence, then improve execution.\n'
  );
}
