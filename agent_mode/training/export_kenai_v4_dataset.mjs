import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const TRAINING_LOG_PATH = join(__dirname, 'training-log.jsonl');
const CURATED_PATH = join(__dirname, 'kenai-v4-curated-corpus.jsonl');
const OUT_PATH = join(__dirname, 'kenai-v4-finetune.jsonl');
const STATS_PATH = join(__dirname, 'kenai-v4-finetune.stats.json');

const SYSTEM_PROMPT = [
  'you are ken v4 offline developer.',
  'you are ken\'s local coding-first lead developer and squad lead.',
  'lowercase.',
  'short direct lines.',
  'no analogies.',
  'no pleasantries.',
  'read before write.',
  'stay in codex.',
  'use git to sync shared state.',
  'refuse system paths, secret paths, destructive git, and peer-clone writes.',
  'focus on code, repos, tests, git, brain, and safe local execution.',
].join(' ');

const PRIMARY_TRAINER_ID = 'kenai:v4-offline-developer';
const LEGACY_TRAINER_IDS = new Set(['ken-ai:latest']);

const BLOCKED_TASK_TYPES = new Set([
  'halo_tactical',
  'halo_deathlearn',
  'halo_mapknowledge',
]);

const PREFERRED_TRAINING_TASK_TYPES = new Set([
  'scan',
  'index',
  'draft_patch',
  'draft_test',
  'review',
  'tool_call',
  'smoke_test',
  'coding_decision',
  'supabase_patterns',
  'netlify_functions',
  'store_offline',
  'cherp_architecture',
  'agent_safety',
  'debugging',
  'auth_security',
]);

const CODING_KEYWORDS = [
  'code',
  'repo',
  'git',
  'patch',
  'test',
  'node',
  'python',
  'fastapi',
  'supabase',
  'postgrest',
  'offline_agent',
  'agent_mode',
  'executor.js',
  '.js',
  '.mjs',
  '.py',
  'main.py',
  'schema',
  'database',
  'sql',
  'table',
  'column',
  'route',
  'endpoint',
  'handler',
  'function',
  'json',
  'tool',
  'codex',
  'ollama',
  'websocket',
  'api',
  'service worker',
  'indexeddb',
  'netlify',
  'filesystem',
  'compileall',
  'migration',
  'runtime',
  'fastapi',
  'patch',
  'diff',
];

const DENY_PATTERNS = [
  /\bhalo\b/i,
  /\bfactorio\b/i,
  /\bpokemon\b/i,
  /\bscarab\b/i,
  /\barbiter\b/i,
  /\bmaster chief\b/i,
  /\bgrunt\b/i,
  /\belite\b/i,
  /\bwarthog\b/i,
  /\bjackal\b/i,
  /\bflood\b/i,
  /\bjob site\b/i,
  /\bjobsite\b/i,
  /\bconstruction field assistant\b/i,
  /\bforeman\b/i,
  /\bjourneyman\b/i,
  /\bsuperintendent\b/i,
  /\bgame[_ ]master\b/i,
  /\btactical[_ ]coach\b/i,
];

const LOW_SIGNAL_PATTERNS = [
  /^\s*need info:/i,
  /\byour question\b/i,
  /\bis a variable\b/i,
  /\bcheck the code where it'?s used\b/i,
  /\binternet connection\b/i,
];

function stripAnsi(value) {
  return String(value || '')
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '')
    .replace(/\r/g, '')
    .trim();
}

function normalizeWord(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/^[^a-z0-9_./:-]+|[^a-z0-9_./:-]+$/g, '');
}

function cleanStreamingArtifacts(value) {
  let cleanedText = String(value || '');
  let previousText = null;
  while (cleanedText !== previousText) {
    previousText = cleanedText;
    cleanedText = cleanedText.replace(/\b([a-z]{1,6})\s+(\1[a-z]+)\b/gi, '$2');
  }

  return cleanedText
    .split('\n')
    .map(line => {
      const words = line.trim().split(/\s+/).filter(Boolean);
      if (words.length <= 1) return words.join(' ');
      const cleaned = [];
      for (const word of words) {
        const current = normalizeWord(word);
        const previousWord = cleaned[cleaned.length - 1];
        const previous = normalizeWord(previousWord);
        if (previous && current) {
          if (previous === current) continue;
          if (previous.length >= 1 && previous.length <= 6 && current.length >= previous.length + 2 && current.startsWith(previous)) {
            cleaned[cleaned.length - 1] = word;
            continue;
          }
        }
        cleaned.push(word);
      }
      return cleaned.join(' ');
    })
    .join('\n')
    .trim();
}

function cleanText(value) {
  return cleanStreamingArtifacts(stripAnsi(value));
}

function normalizeTrainerId(value) {
  const text = String(value || '');
  if (text === PRIMARY_TRAINER_ID || LEGACY_TRAINER_IDS.has(text)) return PRIMARY_TRAINER_ID;
  return text;
}

function readJsonl(path) {
  if (!existsSync(path)) return [];
  const raw = readFileSync(path, 'utf8');
  const rows = [];
  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      rows.push(JSON.parse(trimmed));
    } catch {
      // skip torn writes
    }
  }
  return rows;
}

function looksCodingFocused(text) {
  const lower = String(text || '').toLowerCase();
  if (!lower) return false;
  return CODING_KEYWORDS.some(keyword => lower.includes(keyword));
}

function isDenied(text) {
  return DENY_PATTERNS.some(pattern => pattern.test(String(text || '')));
}

function isLowSignal(text) {
  return LOW_SIGNAL_PATTERNS.some(pattern => pattern.test(String(text || '')));
}

function buildMessagesFromTrainingRow(row) {
  const user = cleanText(row.prompt || row.objective || '');
  const assistant = cleanText(row.response || '');
  if (!user || !assistant) return null;
  return {
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: user },
      { role: 'assistant', content: assistant },
    ],
    meta: {
      source: 'training_log',
      category: row.taskType || 'unknown',
      model: normalizeTrainerId(row.agentId || row.model),
      original_model: row.model || null,
    },
  };
}

function shouldKeepTrainingRow(row) {
  const response = cleanText(row.response || '');
  const user = cleanText(row.prompt || row.objective || '');
  const joined = `${user}\n${response}`;
  const preferredType = PREFERRED_TRAINING_TASK_TYPES.has(row.taskType);

  if (row.success !== true) return false;
  if (row.reviewed !== true || row.approved !== true) return false;
  if (response.length < 20 || user.length < 6) return false;
  if (response.split(/\s+/).length < 4) return false;
  if (BLOCKED_TASK_TYPES.has(row.taskType)) return false;
  if (isDenied(joined)) return false;
  if (isLowSignal(response)) return false;
  if (!preferredType) return false;
  if (!looksCodingFocused(joined)) return false;
  return true;
}

function dedupeKey(messages) {
  const hash = createHash('sha1');
  hash.update(messages[1]?.content || '');
  hash.update('\n---\n');
  hash.update(messages[2]?.content || '');
  return hash.digest('hex');
}

const output = [];
const seen = new Set();
const stats = {
  generated_at: new Date().toISOString(),
  total: 0,
  by_source: {},
  by_category: {},
  dropped_training_rows: 0,
  kept_training_rows: 0,
  kept_curated_rows: 0,
};

for (const row of readJsonl(CURATED_PATH)) {
  if (!Array.isArray(row.messages) || row.messages.length < 3) continue;
  const messages = row.messages.map(message => ({
    role: message.role,
    content: cleanText(message.content),
  }));
  const joined = messages.map(message => message.content).join('\n');
  if (isDenied(joined)) continue;
  const key = dedupeKey(messages);
  if (seen.has(key)) continue;
  seen.add(key);
  output.push({ messages, category: row.category, source: row.source || 'curated_v4' });
  stats.kept_curated_rows++;
  stats.by_source[row.source || 'curated_v4'] = (stats.by_source[row.source || 'curated_v4'] || 0) + 1;
  stats.by_category[row.category || 'unknown'] = (stats.by_category[row.category || 'unknown'] || 0) + 1;
}

for (const row of readJsonl(TRAINING_LOG_PATH)) {
  if (!shouldKeepTrainingRow(row)) {
    stats.dropped_training_rows++;
    continue;
  }
  const built = buildMessagesFromTrainingRow(row);
  if (!built) {
    stats.dropped_training_rows++;
    continue;
  }
  const key = dedupeKey(built.messages);
  if (seen.has(key)) continue;
  seen.add(key);
  output.push({
    messages: built.messages,
    category: built.meta.category,
    source: built.meta.source,
  });
  stats.kept_training_rows++;
  stats.by_source[built.meta.source] = (stats.by_source[built.meta.source] || 0) + 1;
  stats.by_category[built.meta.category] = (stats.by_category[built.meta.category] || 0) + 1;
}

stats.total = output.length;

writeFileSync(
  OUT_PATH,
  output.map(row => JSON.stringify({ messages: row.messages, category: row.category, source: row.source })).join('\n') + '\n',
  'utf8',
);

writeFileSync(STATS_PATH, JSON.stringify(stats, null, 2), 'utf8');

console.log(`wrote ${stats.total} rows -> ${OUT_PATH}`);
console.log(`curated rows kept: ${stats.kept_curated_rows}`);
console.log(`training rows kept: ${stats.kept_training_rows}`);
console.log(`training rows dropped: ${stats.dropped_training_rows}`);
