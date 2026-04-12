// Per-agent memory system
//
// Each registered agent gets its own directory under agent_mode/memories/<slug>/
//   - notes.md        durable notes about the agent (edit freely, loaded into system prompt)
//   - chat-log.jsonl  append-only record of every chat turn (role, content, ts)
//   - charter.md      mirror of the agent's charter if one exists (read-only at runtime)
//
// Writes are append-only where possible so concurrent dispatches don't
// clobber each other. Reads are best-effort — missing files return empty
// strings / arrays rather than throwing.

import { readFileSync, writeFileSync, appendFileSync, existsSync, mkdirSync, readdirSync, copyFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const MEM_ROOT = join(ROOT, 'agent_mode', 'memories');

function slug(agentId) {
  return String(agentId || 'unknown').replace(/[:/\\?*"<>|]/g, '-');
}

export function memoryDir(agentId) {
  return join(MEM_ROOT, slug(agentId));
}

export function ensureMemoryDir(agent) {
  if (!agent?.id) return null;
  const dir = memoryDir(agent.id);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

  const notes = join(dir, 'notes.md');
  if (!existsSync(notes)) {
    const header = [
      `# ${agent.displayName || agent.id} — notes`,
      ``,
      `Durable memory for this agent. Anything below is prepended to the`,
      `system prompt on every chat turn, so use it for standing instructions,`,
      `project facts the agent should remember, and style corrections.`,
      ``,
      `Role: ${agent.role || agent.battleRole || 'General Worker'}`,
      `Track: ${agent.specialistTrack || 'generalist'}`,
      ``,
      `## Standing instructions`,
      ``,
      `- (empty)`,
      ``,
      `## Facts`,
      ``,
      `- (empty)`,
      ``,
    ].join('\n');
    writeFileSync(notes, header, 'utf8');
  }

  const chat = join(dir, 'chat-log.jsonl');
  if (!existsSync(chat)) writeFileSync(chat, '', 'utf8');

  const charterDest = join(dir, 'charter.md');
  if (agent.charterFile && !existsSync(charterDest)) {
    const src = join(ROOT, agent.charterFile);
    if (existsSync(src)) {
      try { copyFileSync(src, charterDest); } catch {}
    }
  }

  return dir;
}

export function ensureAllMemoryDirs(agents) {
  if (!existsSync(MEM_ROOT)) mkdirSync(MEM_ROOT, { recursive: true });
  const created = [];
  for (const agent of agents || []) {
    const dir = ensureMemoryDir(agent);
    if (dir) created.push({ id: agent.id, dir });
  }
  return created;
}

export function readNotes(agentId) {
  const file = join(memoryDir(agentId), 'notes.md');
  try { return readFileSync(file, 'utf8'); } catch { return ''; }
}

export function readCharter(agentId) {
  const file = join(memoryDir(agentId), 'charter.md');
  try { return readFileSync(file, 'utf8'); } catch { return ''; }
}

export function appendChat(agentId, role, content) {
  const file = join(memoryDir(agentId), 'chat-log.jsonl');
  const entry = JSON.stringify({ role, content: String(content || ''), ts: new Date().toISOString() });
  try {
    if (!existsSync(dirname(file))) mkdirSync(dirname(file), { recursive: true });
    appendFileSync(file, entry + '\n', 'utf8');
  } catch {}
}

export function readChatLog(agentId, limit = 200) {
  const file = join(memoryDir(agentId), 'chat-log.jsonl');
  if (!existsSync(file)) return [];
  let raw = '';
  try { raw = readFileSync(file, 'utf8'); } catch { return []; }
  const lines = raw.split('\n').filter(Boolean);
  const slice = lines.slice(-Math.max(1, limit));
  const out = [];
  for (const line of slice) {
    try { out.push(JSON.parse(line)); } catch {}
  }
  return out;
}

export function clearChatLog(agentId) {
  const file = join(memoryDir(agentId), 'chat-log.jsonl');
  try { writeFileSync(file, '', 'utf8'); } catch {}
}

// Build the combined system-prompt context for a chat turn.
// Keeps the turn window small so models with short contexts don't choke.
export function buildChatContext(agent, { historyTurns = 12 } = {}) {
  ensureMemoryDir(agent);
  const notes = readNotes(agent.id);
  const charter = readCharter(agent.id);
  const log = readChatLog(agent.id, historyTurns);
  return { notes, charter, history: log };
}
