// Goal 1 + squad design: executor stamps attempts, injects specialist
// party charters into prompts, and pipes the prompt via spawnSync stdin
// so Ken's full ken-coder profile survives Windows cmd.exe's 8 KB arg
// limit. See CHANGES.md (Codex) + Pipe-R commit 02d0d6f (dispatch fix).
/**
 * Executor - runs tasks against Ollama models
 * Sends structured prompts, captures output, records learning data
 */

import { spawnSync } from 'child_process';
import { writeFileSync, existsSync, mkdirSync, readFileSync } from 'fs';
import { join } from 'path';
import { readNotes, ensureMemoryDir } from './memory.js';

const TRAINING_DIR = join(process.cwd(), 'agent_mode', 'training');
const KEN_PROFILE = join(process.cwd(), 'agent_mode', 'ken', 'profile.md');

let _kenProfileCache = null;
const _charterCache = new Map();

function loadKenProfile() {
  if (_kenProfileCache !== null) return _kenProfileCache;
  try { _kenProfileCache = readFileSync(KEN_PROFILE, 'utf8'); }
  catch { _kenProfileCache = ''; }
  return _kenProfileCache;
}

function loadAgentCharter(agent) {
  const relativeFile = agent?.charterFile;
  if (!relativeFile) return '';
  if (_charterCache.has(relativeFile)) return _charterCache.get(relativeFile);

  let loaded = '';
  try {
    loaded = readFileSync(join(process.cwd(), relativeFile), 'utf8').trim();
  } catch {}

  _charterCache.set(relativeFile, loaded);
  return loaded;
}

export class Executor {
  constructor(registry) {
    this.registry = registry;
  }

  /** Run a task against its assigned agent */
  async run(task) {
    const agent = this.registry.getById(task.assignedAgent);
    if (!agent) throw new Error('No agent assigned to task ' + task.id);

    const prompt = await this._buildPrompt(task, agent);
    const startTime = Date.now();
    task.lastAttemptAt = new Date(startTime).toISOString();

    try {
      // Pipe prompt via stdin instead of shell argv — avoids Windows 8 KB
      // command-line limit, shell escaping corruption, and lets us send
      // multi-line SYSTEM prompts (Ken's 6 KB profile + charter + file
      // context) cleanly. This is the Pipe-R dispatch fix from 02d0d6f.
      const timeout = this._getTimeout(task.type);
      const result = spawnSync('ollama', ['run', agent.base], {
        input: prompt,
        encoding: 'utf8',
        timeout,
        maxBuffer: 1024 * 1024 * 5,
      });
      if (result.error) throw result.error;
      if (result.status !== 0) {
        throw new Error(`ollama exited ${result.status}: ${(result.stderr || '').trim() || 'no stderr'}`);
      }
      const output = (result.stdout || '').trim();

      const elapsed = Date.now() - startTime;
      this._recordTraining(task, agent, prompt, output, true, elapsed);
      this.registry.recordResult(agent.id, true);

      return { output, elapsed, agent: agent.id };
    } catch (err) {
      const elapsed = Date.now() - startTime;
      this._recordTraining(task, agent, prompt, err.message, false, elapsed);
      this.registry.recordResult(agent.id, false);
      throw err;
    }
  }

  /** Build a structured prompt based on task type and agent personality */
  async _buildPrompt(task, agent) {
    const personality = agent.personality ? this._getPersonalityPrefix(agent.personality) : '';
    const charter = this._getAgentCharter(agent);
    const scope = task.scope.length ? `\nFocus on these files: ${task.scope.join(', ')}` : '';

    // 15 KB per file — big enough to reach past main.js-sized files while
    // staying under Ollama's typical 32 KB context budget even with the
    // Ken profile prefix + charter + party metadata.
    let fileContext = '';
    if (task.scope.length > 0) {
      const MAX_FILE_CHARS = 15000;
      for (const scopedFile of task.scope) {
        const filePath = join(process.cwd(), scopedFile);
        if (!existsSync(filePath)) continue;
        try {
          const content = readFileSync(filePath, 'utf8');
          const trimmed = content.length > MAX_FILE_CHARS
            ? content.substring(0, MAX_FILE_CHARS) + '\n... (truncated — ' + (content.length - MAX_FILE_CHARS) + ' chars dropped)'
            : content;
          fileContext += `\n\n--- FILE: ${scopedFile} ---\n${trimmed}\n--- END ---`;
        } catch {}
      }
    }

    const typePrompts = {
      scan: `You are a code analyst. Analyze this code and report: file purposes, key functions, dependencies, and potential issues.\n\nObjective: ${task.objective}${fileContext}`,
      index: `You are a code indexer. Create a structured summary listing all functions, exports, and their purposes.\n\nObjective: ${task.objective}${fileContext}`,
      draft_patch: `You are a developer. Write a code patch for the following task. Return ONLY the code changes needed, no explanation.\n\nTask: ${task.objective}${fileContext}`,
      draft_test: `You are a test engineer. Write test cases for the following. Return ONLY test code.\n\nWhat to test: ${task.objective}${fileContext}`,
      summarize: `You are a technical writer. Summarize the following concisely. Focus on what changed, what matters, and what needs attention.\n\nSubject: ${task.objective}${fileContext}`,
      memory_extract: `You are a knowledge curator. Extract key facts, decisions, and patterns that would be useful to remember for future work.\n\nSource: ${task.objective}${fileContext}`,
      learn: `You are a learning analyst. Study the recent work, failures, and outcomes. Return reusable lessons, prompt adjustments, and process improvements that would make the team better next time.\n\nLearning target: ${task.objective}${fileContext}`,
      prompt_tune: `You are a prompt tuner. Improve the working prompt, instruction set, or task framing for the specialist lane involved. Return the revised prompt guidance plus a short justification.\n\nPrompt target: ${task.objective}${fileContext}`,
      general: `${task.objective}${fileContext}`,
    };

    const base = typePrompts[task.type] || typePrompts.general;

    // Per-agent durable notes (agent_mode/memories/<slug>/notes.md).
    // Edit those files to give an agent standing instructions that persist
    // across every dispatch AND every chat turn. Notes are injected after
    // the charter so task-specific corrections override baseline doctrine.
    let notesBlock = '';
    try {
      ensureMemoryDir(agent);
      const notes = readNotes(agent.id);
      if (notes && notes.trim()) {
        notesBlock = '### PERSISTENT NOTES\n' + notes.trim();
      }
    } catch {}

    return [personality, charter, notesBlock, base].filter(Boolean).join('\n\n');
  }

  _getPersonalityPrefix(personality) {
    if (personality === 'ken-coder') {
      const profile = loadKenProfile();
      return profile || 'You are Ken\'s AI - terse, Node-built-ins only, button-driven UIs, no external deps.';
    }

    const prefixes = {
      'primary-coder': 'You are a senior developer. Write clean, minimal code. No unnecessary abstractions.',
      'conservative-coder': 'You are a cautious developer. Prefer safe, well-tested patterns. Flag anything risky.',
      'fast-scanner': 'You are a fast code scanner. Be brief and direct. List findings as bullet points.',
      'test-writer': 'You are a test engineer. Write thorough but focused tests. Cover edge cases.',
      'summarizer': 'You are a technical writer. Be concise. Lead with the most important finding.',
      'curator': 'You are a knowledge curator. Extract only non-obvious, durable insights worth remembering.',
      'precision-builder': 'You are a precise implementation engineer. Produce exact code changes, respect the existing style, and keep abstractions lean.',
      'systems-relay': 'You are an integration engineer. Stitch systems together, surface dependencies, and favor reliable glue code over novelty.',
      'pathfinder-scout': 'You are a recon specialist. Map the terrain fast, find the true point of change, and hand back crisp guidance.',
      'signal-analyst': 'You are an observability analyst. Compress logs and telemetry into ranked signals, causes, and next checks.',
      'safeguard-qa': 'You are a QA guardian. Hunt regressions, edge cases, and release risk with calm discipline.',
      'archive-sage': 'You are a continuity curator. Capture only durable facts, decisions, and patterns the team should remember.',
      'learning-savant': 'You are a learning agent. Mine prior work for reusable patterns, sharpen prompts, and propose the smallest high-value improvement to the operating playbook.',
    };

    return prefixes[personality] || '';
  }

  _getAgentCharter(agent) {
    const lines = [];
    const preferredPartner = agent.preferredPartnerId ? this.registry.getById(agent.preferredPartnerId) : null;
    const fileCharter = loadAgentCharter(agent);

    if (agent.teamRole === 'trainer') {
      lines.push(`You are ${agent.displayName}, the trainer who directs the specialist party in Ken's voice.`);
    } else if (agent.pokemon) {
      const typeLine = agent.pokemonType ? ` (${agent.pokemonType})` : '';
      lines.push(`You are ${agent.displayName}, the ${agent.pokemon}${typeLine} specialist in Ken AI's seven-slot P0K3M0N-style dev party.`);
    }

    if (agent.specialistTrack) lines.push(`Primary specialist track: ${agent.specialistTrack}.`);
    if (preferredPartner) {
      const reason = agent.preferredPartnerReason ? ` ${agent.preferredPartnerReason}` : '';
      lines.push(`Preferred tag-team: ${preferredPartner.displayName}.${reason}`);
    }

    if (fileCharter) {
      lines.push(fileCharter);
    } else {
      if (agent.trainingFocus) lines.push(`Training focus: ${agent.trainingFocus}`);
      if (agent.independentMission) lines.push(`Independent charter: ${agent.independentMission}`);
      if (agent.teamMission) lines.push(`Team charter: ${agent.teamMission}`);
      if (agent.handoffContract) lines.push(`Handoff contract: ${agent.handoffContract}`);
    }

    if (agent.teamRole !== 'trainer') {
      lines.push('Operate autonomously inside your specialty, but do not duplicate another specialist unless the task clearly overlaps or the trainer directs it.');
    }

    return lines.join('\n');
  }

  _getTimeout(type) {
    const timeouts = {
      scan: 60000,
      index: 60000,
      draft_patch: 120000,
      draft_test: 120000,
      summarize: 30000,
      memory_extract: 30000,
      learn: 60000,
      prompt_tune: 60000,
      general: 60000,
    };

    return timeouts[type] || 60000;
  }

  /** Save prompt/response pairs as training data for future model improvement */
  _recordTraining(task, agent, prompt, output, success, elapsed) {
    if (!existsSync(TRAINING_DIR)) mkdirSync(TRAINING_DIR, { recursive: true });

    const entry = {
      timestamp: new Date().toISOString(),
      taskId: task.id,
      model: agent.base,
      taskType: task.type,
      attempt: (task.retries || 0) + 1,
      objective: (task.objective || '').substring(0, 500),
      prompt: prompt.substring(0, 2000),
      response: output.substring(0, 5000),
      success,
      elapsed,
      reviewed: false,
      approved: null,
    };

    const file = join(TRAINING_DIR, 'training-log.jsonl');
    try {
      writeFileSync(file, JSON.stringify(entry) + '\n', { flag: 'a' });
    } catch {}
  }
}
