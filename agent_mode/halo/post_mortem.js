/* ══════════════════════════════════════════════════════
   Halo learning agent — death post-mortem
   ──────────────────────────────────────────────────────
   Triggered when events.js detects a 'died' event in drive
   mode. Pulls the last N tick entries from halo-log.jsonl,
   builds a specialized prompt asking ken-ai to diagnose its
   own death, parses the response, and appends a LESSON bullet
   to halo-memory.md under the deaths_log section.

   Non-blocking: runs via setTimeout(0) inside the Node event
   loop so the main tick cadence isn't gated on the ~3-6s
   ollama round-trip.

   ══════════════════════════════════════════════════════ */

import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { appendLesson, stampEvent } from './memory.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const HALO_LOG  = join(__dirname, '..', 'memories', 'ken-ai-latest', 'halo-log.jsonl');

function stripAnsi(s) {
  return String(s || '')
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '');
}

function readLastTicks(limit = 8) {
  if (!existsSync(HALO_LOG)) return [];
  try {
    const raw = readFileSync(HALO_LOG, 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    const out = [];
    for (let i = lines.length - 1; i >= 0 && out.length < limit; i--) {
      try {
        const row = JSON.parse(lines[i]);
        // Skip handoff / error rows — we want actual ticks.
        if (row.action && row.stateBefore) out.push(row);
      } catch (e) { /* skip */ }
    }
    return out.reverse(); // oldest → newest
  } catch (e) { return []; }
}

function buildPrompt(deathEvent, ticks) {
  const bulleted = ticks.map((t, i) => {
    const sb = t.stateBefore || {};
    const sa = t.stateAfter || {};
    const shield = (sb.shield || '').slice(0, 16);
    const ammo   = (sb.ammo || '').slice(0, 16);
    return `  ${i + 1}. did ${t.action} → shield_before="${shield}" ammo_before="${ammo}"`;
  }).join('\n');

  return (
    'you are ken-ai. you were driving the character in halo mcc and you just died.\n\n' +
    'here are your last ' + ticks.length + ' actions leading to the death, oldest first:\n\n' +
    bulleted + '\n\n' +
    'cause detected: ' + (deathEvent.cause || 'unknown') + '\n\n' +
    'respond with EXACTLY ONE LINE in this format:\n' +
    '  CAUSE: <10 words max — what killed you>\n' +
    '  LESSON: <12 words max — what to do differently next time>\n\n' +
    'no prose, no apologies, no "as an AI". two lines, two labels.\n'
  );
}

function parse(raw) {
  const text = stripAnsi(raw || '');
  const causeMatch = text.match(/CAUSE:\s*(.+)/i);
  const lessonMatch = text.match(/LESSON:\s*(.+)/i);
  return {
    cause:  causeMatch  ? causeMatch[1].trim().slice(0, 120) : '',
    lesson: lessonMatch ? lessonMatch[1].trim().slice(0, 160) : '',
  };
}

/* ── Main entry point. Model name is passed in so whichever
   agent is driving at the moment gets to diagnose its own death. ── */
export function runPostMortem(model, deathEvent) {
  setTimeout(() => {
    try {
      const ticks = readLastTicks(8);
      if (!ticks.length) {
        appendLesson('deaths_log', 'died with no tick history to analyze');
        stampEvent('death');
        return;
      }
      const prompt = buildPrompt(deathEvent, ticks);
      const res = spawnSync('ollama', ['run', model || 'kenai:v1'], {
        input: prompt,
        encoding: 'utf8',
        timeout: 60000,
        maxBuffer: 4 * 1024 * 1024,
        windowsHide: true,
      });
      if (res.status !== 0) {
        appendLesson('deaths_log',
          'died (' + (deathEvent.cause || 'unknown') + ') — post-mortem ollama failed');
        stampEvent('death');
        return;
      }
      const parsed = parse(res.stdout);
      const entry = parsed.cause && parsed.lesson
        ? `died: ${parsed.cause} — LESSON: ${parsed.lesson}`
        : `died (${deathEvent.cause}) — raw: ${stripAnsi(res.stdout).slice(0, 140)}`;
      appendLesson('deaths_log', entry);
      stampEvent('death');
    } catch (e) {
      try { appendLesson('deaths_log', 'post-mortem error: ' + e.message); }
      catch (_) {}
    }
  }, 0);
}
