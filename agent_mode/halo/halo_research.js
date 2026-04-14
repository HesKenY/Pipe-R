/* ══════════════════════════════════════════════════════
   Halo squad research dispatcher
   ──────────────────────────────────────────────────────
   Ken tasked the party with finding an in-process way to
   make the character invincible in Halo MCC without a
   third-party trainer. This module dispatches each party
   member in parallel with a role-specific research prompt
   and collects their findings into halo-research.md.

   Each agent gets a specialized angle:

     5c1z0r (implementation) — write actual code path
     D3c1du3y3 (recon)       — map the MCC process layout
     P0ryg0n (observability) — what's observable from outside
     Umbr30n (safeguard)     — safety checks for the approach
     R0t0m (integration)     — tying tools together
     4l4k4z4m (memory)       — prior patterns / known offsets
     Ken AI (trainer)        — final decision on which to try

   Results land in memories/ken-ai-latest/halo-research.md
   under a timestamped section. Ken reviews + picks.
   ══════════════════════════════════════════════════════ */

import { spawn } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync, mkdirSync, appendFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR = join(__dirname, '..', 'memories', 'ken-ai-latest');
const RESEARCH_FILE = join(MEM_DIR, 'halo-research.md');

const AGENTS = [
  {
    id: 'qwen2.5-coder:14b',
    name: '5c1z0r Patchsmith',
    role: 'implementation',
    question: 'write the actual Python code that would make the Halo MCC player invincible without an external trainer. use ctypes OpenProcess / ReadProcessMemory / WriteProcessMemory on MCC-Win64-Shipping.exe. give me a concrete 15-line snippet.',
  },
  {
    id: 'cherp-piper:latest',
    name: 'D3c1du3y3 Pathfinder',
    role: 'recon',
    question: 'map out the attack surface for modifying Halo MCC player health in-process. what tools, what process, what addresses, what libraries? 4-6 bullets.',
  },
  {
    id: 'llama3.1:8b',
    name: 'P0ryg0n Logdex',
    role: 'observability',
    question: 'what can be observed from outside the Halo MCC process (without debugger / without injection) to detect player health? api scraping, screen OCR of the shield bar, log files. 4-6 bullets, ranked by feasibility.',
  },
  {
    id: 'jefferyjefferferson:latest',
    name: 'Umbr30n Safeguard',
    role: 'quality',
    question: 'if we memory-write health in MCC to achieve invincibility, what are the safety risks? anti-cheat, crashes, save corruption, ban risk? 4-5 bullets, terse.',
  },
  {
    id: 'forgeagent:latest',
    name: 'R0t0m Relay',
    role: 'integration',
    question: 'what existing Python libraries (pymem, frida-python, ReadWriteMemory, pywin32) can hook into Halo MCC\'s running process and modify player state? rank by ease. 4-6 bullets.',
  },
  {
    id: 'jefferferson:latest',
    name: '4l4k4z4m Archive',
    role: 'memory',
    question: 'recall any known Halo 2 MCC memory offsets, cheat table entries, or script hooks that have been published publicly. if you don\'t know, say so — don\'t make up addresses. 3-5 bullets.',
  },
];

const SYSTEM_PRIMER =
  'you are a halo mcc in-process modification researcher. ken is asking the squad how to make the player character invincible WITHOUT a third-party trainer like WeMod or Cheat Engine. the target is MCC-Win64-Shipping.exe on windows 11. all answers must be practical and in-process (no external software installs).\n\n' +
  'respond with bullets only — no prose, no apologies. be specific.\n\n';

function stripAnsi(s) {
  return String(s || '')
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '');
}

function runAgent(agent) {
  return new Promise((resolve) => {
    const prompt = SYSTEM_PRIMER +
      'your role: ' + agent.role + '\n\n' +
      'question: ' + agent.question + '\n\n' +
      'your answer:';
    let out = '';
    let err = '';
    const t0 = Date.now();
    let child;
    try {
      child = spawn('ollama', ['run', agent.id], {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
      });
    } catch (e) {
      return resolve({ name: agent.name, role: agent.role, ok: false, error: e.message });
    }
    const timeout = setTimeout(() => {
      try { child.kill('SIGKILL'); } catch (_) {}
    }, 120000);
    child.stdout.on('data', (d) => { out += d.toString('utf8'); });
    child.stderr.on('data', (d) => { err += d.toString('utf8'); });
    child.on('close', (code) => {
      clearTimeout(timeout);
      const elapsed = Date.now() - t0;
      if (code !== 0) {
        return resolve({ name: agent.name, role: agent.role, ok: false, elapsed, error: err.slice(0, 200) });
      }
      const raw = stripAnsi(out).trim();
      resolve({
        name: agent.name,
        role: agent.role,
        ok: true,
        elapsed,
        response: raw.slice(0, 1500),
      });
    });
    try { child.stdin.write(prompt); child.stdin.end(); }
    catch (e) { /* ignore */ }
  });
}

/* ── Fire all 6 agents in parallel, collect results, append
   timestamped research doc. Returns the full results array. ── */
export async function researchInvincibility() {
  const results = await Promise.allSettled(AGENTS.map(a => runAgent(a)));
  const findings = results.map(r => r.value || { error: String(r.reason) });

  // Persist to halo-research.md
  try {
    if (!existsSync(MEM_DIR)) mkdirSync(MEM_DIR, { recursive: true });
    const stamp = new Date().toISOString();
    let block = `\n# Invincibility research — ${stamp}\n\n`;
    for (const f of findings) {
      block += `## ${f.name || '?'} (${f.role || '?'})\n`;
      if (f.ok) {
        block += `elapsed: ${f.elapsed}ms\n\n`;
        block += f.response + '\n\n';
      } else {
        block += `error: ${f.error || 'unknown'}\n\n`;
      }
    }
    if (!existsSync(RESEARCH_FILE)) {
      writeFileSync(RESEARCH_FILE, '# Halo MCC — in-process invincibility research\n\n' +
        'Compiled by the squad on Ken\'s request. Sources are each party agent\'s ' +
        'specialized role. Ken picks the approach to implement.\n' + block, 'utf8');
    } else {
      appendFileSync(RESEARCH_FILE, block, 'utf8');
    }
  } catch (e) { /* best-effort */ }

  return {
    at: new Date().toISOString(),
    findings,
    path: RESEARCH_FILE,
  };
}
