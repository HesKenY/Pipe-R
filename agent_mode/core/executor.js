/**
 * Executor — runs tasks against Ollama models
 * Sends structured prompts, captures output, records learning data
 */

import { spawnSync } from 'child_process';
import { writeFileSync, existsSync, mkdirSync, readFileSync } from 'fs';
import { join } from 'path';

const LOG_DIR = join(process.cwd(), 'agent_mode', 'logs');
const TRAINING_DIR = join(process.cwd(), 'agent_mode', 'training');
const KEN_PROFILE = join(process.cwd(), 'agent_mode', 'ken', 'profile.md');

let _kenProfileCache = null;
function loadKenProfile() {
  if (_kenProfileCache !== null) return _kenProfileCache;
  try { _kenProfileCache = readFileSync(KEN_PROFILE, 'utf8'); }
  catch { _kenProfileCache = ''; }
  return _kenProfileCache;
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

    try {
      // Pipe prompt via stdin instead of shell argv — avoids Windows 8KB
      // command-line limit, shell escaping corruption, and lets us send
      // multi-line SYSTEM prompts (e.g. Ken's profile) cleanly.
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

      // Record for training
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
    const scope = task.scope.length ? `\nFocus on these files: ${task.scope.join(', ')}` : '';

    // Load file contents if scope references real files
    let fileContext = '';
    if (task.scope.length > 0) {
      const { readFileSync, existsSync } = await import('fs');
      const { join } = await import('path');
      for (const s of task.scope) {
        const fp = join(process.cwd(), s);
        if (existsSync(fp)) {
          try {
            const content = readFileSync(fp, 'utf8');
            // Truncate large files to keep prompt manageable
            const trimmed = content.length > 4000 ? content.substring(0, 4000) + '\n... (truncated)' : content;
            fileContext += `\n\n--- FILE: ${s} ---\n${trimmed}\n--- END ---`;
          } catch {}
        }
      }
    }

    const typePrompts = {
      scan: `You are a code analyst. Analyze this code and report: file purposes, key functions, dependencies, and potential issues.\n\nObjective: ${task.objective}${fileContext}`,
      index: `You are a code indexer. Create a structured summary listing all functions, exports, and their purposes.\n\nObjective: ${task.objective}${fileContext}`,
      draft_patch: `You are a developer. Write a code patch for the following task. Return ONLY the code changes needed, no explanation.\n\nTask: ${task.objective}${fileContext}`,
      draft_test: `You are a test engineer. Write test cases for the following. Return ONLY test code.\n\nWhat to test: ${task.objective}${fileContext}`,
      summarize: `You are a technical writer. Summarize the following concisely. Focus on what changed, what matters, and what needs attention.\n\nSubject: ${task.objective}${fileContext}`,
      memory_extract: `You are a knowledge curator. Extract key facts, decisions, and patterns that would be useful to remember for future work.\n\nSource: ${task.objective}${fileContext}`,
      general: `${task.objective}${fileContext}`,
    };

    const base = typePrompts[task.type] || typePrompts.general;
    return personality ? `${personality}\n\n${base}` : base;
  }

  _getPersonalityPrefix(personality) {
    if (personality === 'ken-coder') {
      const profile = loadKenProfile();
      return profile || 'You are Ken\'s AI — terse, Node-built-ins only, button-driven UIs, no external deps.';
    }
    const prefixes = {
      'primary-coder': 'You are a senior developer. Write clean, minimal code. No unnecessary abstractions.',
      'conservative-coder': 'You are a cautious developer. Prefer safe, well-tested patterns. Flag anything risky.',
      'fast-scanner': 'You are a fast code scanner. Be brief and direct. List findings as bullet points.',
      'test-writer': 'You are a test engineer. Write thorough but focused tests. Cover edge cases.',
      'summarizer': 'You are a technical writer. Be concise. Lead with the most important finding.',
      'curator': 'You are a knowledge curator. Extract only non-obvious, durable insights worth remembering.',
    };
    return prefixes[personality] || '';
  }

  _getTimeout(type) {
    const timeouts = {
      scan: 60000,
      index: 60000,
      draft_patch: 120000,
      draft_test: 120000,
      summarize: 30000,
      memory_extract: 30000,
      general: 60000,
    };
    return timeouts[type] || 60000;
  }

  /** Save prompt/response pairs as training data for future model improvement */
  _recordTraining(task, agent, prompt, output, success, elapsed) {
    if (!existsSync(TRAINING_DIR)) mkdirSync(TRAINING_DIR, { recursive: true });

    const entry = {
      timestamp: new Date().toISOString(),
      model: agent.base,
      taskType: task.type,
      prompt: prompt.substring(0, 2000),
      response: output.substring(0, 5000),
      success,
      elapsed,
      reviewed: false,
    };

    const file = join(TRAINING_DIR, 'training-log.jsonl');
    try {
      writeFileSync(file, JSON.stringify(entry) + '\n', { flag: 'a' });
    } catch {}
  }
}
