/* ══════════════════════════════════════════════════════
   CHERP / Pipe-R — Per-agent dream (reflection) engine
   ──────────────────────────────────────────────────────
   Every agent can "dream" — an offline pass where the
   agent's own model reads a summary of its recent tasks
   and writes structured insights back to its memory dir.

   This is the REM-sleep layer for the squad. Facts that
   repeat across tasks get consolidated. Mistakes that keep
   happening become standing notes. Questions the agent
   couldn't answer alone get logged for the trainer.

   Dream entry shape (appended to dreams.jsonl):
   {
     at:          ISO timestamp,
     agentId:     string,
     windowSize:  int  (how many recent tasks considered),
     learned:     [string],  // facts the agent believes it picked up
     patterns:    [string],  // recurring approaches/failures
     questions:   [string],  // things it wants the trainer to clarify
     gaps:        [string],  // skills it feels underqualified for
     raw:         string     // full model output, clipped
   }

   Dreams are triggered manually via POST /api/agent/dream
   or on a schedule. They are NOT part of the main task
   queue — they're a meta-process the agent does to itself.

   Side effect: when a dream produces strong insights the
   agent wants to keep, those get appended to its notes.md
   under a "Dreamed" section. Notes.md is the source of
   truth; dreams.jsonl is the raw reflection log.

   ══════════════════════════════════════════════════════ */

import { existsSync, mkdirSync, appendFileSync, readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEMORIES_DIR = join(__dirname, '..', 'memories');
const TRAINING_LOG = join(__dirname, '..', 'training', 'training-log.jsonl');

function slugFor(agentId) {
  return String(agentId || '').replace(/:/g, '-');
}

function ensureDir(agentId) {
  const dir = join(MEMORIES_DIR, slugFor(agentId));
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  return dir;
}

/* ── Strip ANSI terminal spinner bytes from ollama stdout.
   Same regex that executor.js + the chat endpoint use. ── */
function stripAnsi(s) {
  if (!s) return '';
  return String(s)
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '');
}

/* ── Pull the last N training-log entries for a given base. ── */
function recentTasksFor(base, limit = 12) {
  if (!existsSync(TRAINING_LOG)) return [];
  const raw = readFileSync(TRAINING_LOG, 'utf8');
  const lines = raw.split('\n');
  const out = [];
  for (let i = lines.length - 1; i >= 0 && out.length < limit; i--) {
    const line = lines[i].trim();
    if (!line) continue;
    try {
      const row = JSON.parse(line);
      if (row.model === base) out.push(row);
    } catch (e) { /* skip */ }
  }
  return out.reverse();
}

/* ── Build the reflection prompt. This is what the model
   gets asked during a dream. The format is tight so we can
   parse structured fields out of the response. ── */
function buildDreamPrompt(agent, tasks) {
  const header =
    `You are ${agent.displayName || agent.id}. You are reviewing your most ` +
    `recent work to consolidate what you've learned. This is offline ` +
    `reflection — nobody is waiting on you.\n\n` +
    `Here are your last ${tasks.length} tasks, oldest first:\n\n`;

  const body = tasks.map((t, i) => {
    const outcome = t.reviewed
      ? (t.approved ? 'APPROVED' : 'REJECTED')
      : (t.success ? 'done, unreviewed' : 'failed');
    const obj = (t.objective || '').slice(0, 140);
    const resp = stripAnsi(t.response || '').slice(0, 240);
    return `[${i + 1}] ${t.taskType} / ${outcome} (${t.elapsed || 0}ms)\n` +
           `    obj: ${obj}\n` +
           `    out: ${resp}\n`;
  }).join('\n');

  const footer =
    `\n\nRespond in EXACTLY this format — four plain-text sections, ` +
    `each bullet on its own line starting with "- ". Keep bullets short ` +
    `(under 15 words each). No prose, no headers beyond the four labels.\n\n` +
    `LEARNED:\n- <what you now believe you know>\n\n` +
    `PATTERNS:\n- <recurring things across these tasks>\n\n` +
    `QUESTIONS:\n- <what you need the trainer to clarify>\n\n` +
    `GAPS:\n- <skills you feel underqualified for>\n`;

  return header + body + footer;
}

/* ── Parse the four labeled sections out of a dream response.
   Permissive — accepts any case, extra blank lines, missing
   sections (returns empty arrays for absent ones). ── */
function parseDream(raw) {
  const out = { learned: [], patterns: [], questions: [], gaps: [] };
  if (!raw) return out;
  const text = stripAnsi(raw);
  const sectionRe = /(LEARNED|PATTERNS|QUESTIONS|GAPS)\s*:([\s\S]*?)(?=(LEARNED|PATTERNS|QUESTIONS|GAPS)\s*:|$)/gi;
  let m;
  while ((m = sectionRe.exec(text)) !== null) {
    const key = m[1].toLowerCase();
    const body = m[2];
    const bullets = body
      .split('\n')
      .map(l => l.trim())
      .filter(l => l.startsWith('-'))
      .map(l => l.replace(/^-\s*/, '').trim())
      .filter(Boolean);
    if (key in out) out[key] = bullets;
  }
  return out;
}

/* ── Run the dream. Fires ollama with the agent's own base
   model, captures output, parses, appends to dreams.jsonl,
   optionally stamps notes.md with strong insights. ── */
export async function dreamAgent(agent, opts = {}) {
  const windowSize = opts.windowSize || 12;
  const timeoutMs = opts.timeoutMs || 90000;
  const base = agent.base || agent.id;
  const tasks = recentTasksFor(base, windowSize);

  if (tasks.length === 0) {
    return { ok: false, reason: 'no recent tasks to dream about' };
  }

  const prompt = buildDreamPrompt(agent, tasks);
  const t0 = Date.now();
  const result = spawnSync('ollama', ['run', base], {
    input: prompt,
    encoding: 'utf8',
    timeout: timeoutMs,
    maxBuffer: 4 * 1024 * 1024,
  });
  const elapsed = Date.now() - t0;

  if (result.error) return { ok: false, reason: result.error.message, elapsed };
  if (result.status !== 0) {
    return { ok: false, reason: 'ollama exit ' + result.status, elapsed, stderr: (result.stderr || '').slice(0, 300) };
  }

  const rawOut = stripAnsi(result.stdout || '').trim();
  const parsed = parseDream(rawOut);

  const entry = {
    at: new Date().toISOString(),
    agentId: agent.id,
    base,
    windowSize: tasks.length,
    elapsedMs: elapsed,
    learned: parsed.learned,
    patterns: parsed.patterns,
    questions: parsed.questions,
    gaps: parsed.gaps,
    raw: rawOut.slice(0, 2000),
  };

  const dir = ensureDir(agent.id);
  try {
    appendFileSync(join(dir, 'dreams.jsonl'), JSON.stringify(entry) + '\n', 'utf8');
  } catch (e) { /* best-effort */ }

  // Stamp strong insights into notes.md so they survive into
  // future task prompts. Only "learned" and "patterns" get
  // promoted — questions/gaps are for the trainer, not standing
  // memory. Capped at 6 bullets total to avoid runaway notes.
  if (entry.learned.length || entry.patterns.length) {
    try {
      const notesPath = join(dir, 'notes.md');
      const existing = existsSync(notesPath) ? readFileSync(notesPath, 'utf8') : '';
      const stamp = new Date().toISOString().slice(0, 10);
      const bullets = [
        ...entry.learned.slice(0, 3).map(b => '- ' + b),
        ...entry.patterns.slice(0, 3).map(b => '- ' + b),
      ].join('\n');
      if (bullets) {
        const block = `\n\n## Dreamed ${stamp}\n${bullets}\n`;
        writeFileSync(notesPath, existing + block, 'utf8');
      }
    } catch (e) { /* ignore */ }
  }

  return { ok: true, entry };
}

/* ── Read an agent's dream history (most recent first). ── */
export function readDreams(agentId, limit = 20) {
  const p = join(ensureDir(agentId), 'dreams.jsonl');
  if (!existsSync(p)) return [];
  try {
    const raw = readFileSync(p, 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    const out = [];
    for (let i = lines.length - 1; i >= 0 && out.length < limit; i--) {
      try { out.push(JSON.parse(lines[i])); }
      catch (e) { /* skip */ }
    }
    return out;
  } catch (e) { return []; }
}
