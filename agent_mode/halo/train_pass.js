/* ══════════════════════════════════════════════════════
   Halo training pass — direct ollama spawn, bypasses the
   orchestrator so we don't drag role SYSTEM prompts into
   the reverse-engineering context.

   For each task: (1) read any input files, (2) build a
   minimal task-only prompt, (3) spawn ollama, (4) strip
   ANSI, (5) write response straight to the target file.

   Invoked from /api/halo/train/run. Each task row has:
     { title, model, outputPath, contextFiles, prompt }
   ══════════════════════════════════════════════════════ */

import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync, existsSync, appendFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR   = join(__dirname, '..', 'memories', 'ken-ai-latest');
const TRAIN_LOG = join(__dirname, '..', 'training', 'training-log.jsonl');

function stripAnsi(s) {
  return String(s || '')
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '');
}

function readContext(files) {
  const chunks = [];
  for (const rel of files || []) {
    const path = join(MEM_DIR, rel);
    if (!existsSync(path)) {
      chunks.push(`# ${rel}\n(file not found)\n`);
      continue;
    }
    try {
      const raw = readFileSync(path, 'utf8');
      chunks.push(`# ${rel}\n${raw.slice(0, 12000)}\n`);
    } catch (e) {
      chunks.push(`# ${rel}\n(read error: ${e.message})\n`);
    }
  }
  return chunks.join('\n---\n');
}

function runOllama(model, prompt, timeoutMs = 90000) {
  const started = Date.now();
  const res = spawnSync('ollama', ['run', model], {
    input: prompt,
    encoding: 'utf8',
    timeout: timeoutMs,
    maxBuffer: 8 * 1024 * 1024,
    windowsHide: true,
  });
  const elapsed = Date.now() - started;
  if (res.status !== 0) {
    return { ok: false, elapsed, error: 'exit ' + res.status, stderr: (res.stderr || '').slice(0, 300) };
  }
  return { ok: true, elapsed, text: stripAnsi(res.stdout || '').trim() };
}

function logTraining(row) {
  try { appendFileSync(TRAIN_LOG, JSON.stringify(row) + '\n', 'utf8'); }
  catch (e) { /* best-effort */ }
}

export async function runTrainingPass(tasks) {
  const results = [];
  for (const t of tasks) {
    const ctx = readContext(t.contextFiles || []);
    const prompt = (ctx ? ctx + '\n\n---\n\n' : '') + t.prompt;
    const r = runOllama(t.model, prompt, t.timeoutMs || 90000);
    const outPath = join(MEM_DIR, t.outputPath);
    if (r.ok && r.text && r.text.length > 40) {
      try {
        writeFileSync(outPath, r.text, 'utf8');
        results.push({ title: t.title, model: t.model, outputPath: t.outputPath, bytes: r.text.length, elapsed: r.elapsed, ok: true });
      } catch (e) {
        results.push({ title: t.title, model: t.model, outputPath: t.outputPath, ok: false, error: 'write: ' + e.message });
      }
    } else {
      results.push({ title: t.title, model: t.model, outputPath: t.outputPath, ok: false, error: r.error || 'empty response', elapsed: r.elapsed });
    }
    logTraining({
      at: new Date().toISOString(),
      model: t.model,
      taskId: `halo-train-${Date.now().toString(36)}`,
      taskType: 'halo_train',
      prompt: prompt.slice(0, 2000),
      response: (r.text || '').slice(0, 8000),
      success: r.ok,
      elapsed: r.elapsed,
    });
  }
  return results;
}

/* Default task set — 6 training passes across the squad, each
   reading halo-game-dump.md + writing a new indexed artifact. */
export const DEFAULT_TASKS = [
  {
    title: 'halo2.dll entry points',
    model: 'cherp-piper:latest',
    outputPath: 'halo2-dll-entry-points.md',
    contextFiles: ['halo-game-dump.md'],
    prompt: `You have a MCC game dump above listing loaded modules with base addresses. Target: halo2.dll. Write a structured markdown document covering:

1. Which PE sections of halo2.dll probably hold (a) AI state structs (b) damage-apply code (c) enemy spawn tables. Use the section conventions (.text = code, .rdata = read-only constants, .data = mutable globals).
2. 6 candidate AOB (array of bytes) patterns for x64 opcodes a damage function would use: mulss xmm / subss xmm / movss [rcx+offset] / cmp / je.
3. A rough offset range from halo2.dll base where delta-scanning for 0.0-100.0 health floats should start.
4. Propose a halo2_reverse.py script outline using ctypes that: attaches to MCC, finds halo2.dll base, dumps first 2MB of .data section, finds floats in [0,200].

Respond with ONLY the markdown document — no prose intro, no code fences around the entire thing, just markdown starting with "# halo2.dll entry points". Use real bullets, no placeholders.`,
    timeoutMs: 120000,
  },
  {
    title: 'MCC module queries',
    model: 'qwen2.5-coder:14b',
    outputPath: 'halo-module-queries.md',
    contextFiles: ['halo-game-dump.md'],
    prompt: `You have a MCC game dump above listing loaded modules with base addresses + install file tree. Write a structured markdown document:

1. 10 natural-language queries a reverse-engineer would type to probe this data.
2. For each query, quote the exact bullet from the dump that answers it.
3. 5 cross-references combining module data with the install file tree.
4. 3 fields that should be added to future dumps (PE section headers, exported symbols, DLL imports).

Start with "# MCC module queries". No prose intro. No fenced code blocks around the whole thing.`,
    timeoutMs: 120000,
  },
  {
    title: 'Halo 2 .map format',
    model: 'kenai:v1',
    outputPath: 'halo-map-format.md',
    contextFiles: ['halo-game-dump.md'],
    prompt: `The install tree above has .map files — those are Halo 2 mission containers. Write a markdown doc:

1. The .map header layout: magic, version, tag index offset, scenario tag index.
2. Which mission names map to which campaign level based on the files you see in the dump.
3. How the hsc (halo script) tag type works.
4. Tag types relevant for cheating: ai_squad, weapon, projectile, damage_effect, biped.
5. A halo_map_parse.py outline using struct.unpack for the header + tag index walk.

Start with "# Halo 2 .map format". No prose intro.`,
    timeoutMs: 120000,
  },
  {
    title: 'Enemy AI disable — hostility flip',
    model: 'forgeagent:latest',
    outputPath: 'halo-enemy-disarm.md',
    contextFiles: ['halo-game-dump.md'],
    prompt: `You have a MCC dump above. Target: Halo 2 enemy NPCs (Covenant grunts, elites, jackals). Goal: make them stop shooting without killing them — disarm, not massacre.

Write a markdown doc covering:

1. The enemy biped struct layout in Halo 2 (inferred from community modding notes): team_id (byte), alert_state (byte), target_unit_index (word), weapon_ref (dword).
2. Three distinct strategies to neutralize them: (a) team_id swap to player's team, (b) freeze alert_state at 0 (unaware), (c) zero out weapon_ref so they hold nothing.
3. ctypes Python snippet for each: OpenProcess, find halo2.dll base, scan data section for biped struct signatures, write the neutralizing value.
4. A halo_pacify.py outline that runs a 100ms write loop pinning team_id=0 across all detected biped structs.
5. Why this doesn't trigger MCC anticheat (legacy campaign has no kernel AC).

Start with "# Enemy AI disarm". No prose intro.`,
    timeoutMs: 120000,
  },
  {
    title: 'Health pinning strategy',
    model: 'llama3.1:8b',
    outputPath: 'halo-health-pinning.md',
    contextFiles: ['halo-game-dump.md'],
    prompt: `Given the MCC dump above, write a markdown doc on health pinning strategies for Halo 2 MCC:

1. Where the player health/shield floats live: unit struct inside halo2.dll data section, offsets likely in 0x100-0x400 range from struct base.
2. Three ways to FIND them: (a) vision-read HUD + delta scan, (b) pointer chase from player biped, (c) AOB scan for known movss instructions near the damage path.
3. Why writing 9999 works (Halo 2 doesn't clamp health on read) vs why it might get overwritten by next frame (game clamps on damage apply — so pin at 80ms loop).
4. halo_health_pin.py outline: open process, find addrs, threading.Thread writing max float every 80ms.
5. Interaction with the aimbot: health pin means Ken can face-tank while the aimbot dials in the headshot engine.

Start with "# Halo 2 health pinning". No prose intro.`,
    timeoutMs: 120000,
  },
  {
    title: 'Index query patterns for the drive loop',
    model: 'llama3.1:8b',
    outputPath: 'halo-index-queries.md',
    contextFiles: ['halo-game-dump.md', 'halo-memory.md'],
    prompt: `You have the game dump + tactical memory above. Write a markdown doc with 15 index queries the drive-loop prompt builder should issue to the halo index:

1. Query form: 3-8 tokens, tactical situation + desired info.
2. For each query, what bullet from the indexed corpus it should retrieve.
3. Label each: [combat] / [recon] / [reverse] / [memory] / [meta].

Example row: "- [combat] shield low retreat → retreat cover plasma pistol"

Start with "# Halo index query patterns". No prose intro.`,
    timeoutMs: 120000,
  },
];
