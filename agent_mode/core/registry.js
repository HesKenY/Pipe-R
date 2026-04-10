/**
 * Agent Registry — tracks available Ollama models and their roles/personalities
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

const REGISTRY_FILE = join(process.cwd(), 'agent_mode', 'config', 'agents.json');

export class AgentRegistry {
  constructor() {
    this.agents = this._load();
  }

  _load() {
    try { return JSON.parse(readFileSync(REGISTRY_FILE, 'utf8')); }
    catch { return []; }
  }

  save() {
    const dir = join(process.cwd(), 'agent_mode', 'config');
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    writeFileSync(REGISTRY_FILE, JSON.stringify(this.agents, null, 2));
  }

  /** Register a new agent (Ollama model) */
  register(opts) {
    const existing = this.getById(opts.id);
    if (existing) return existing;

    const agent = {
      id: opts.id,
      base: opts.base,
      displayName: opts.displayName || opts.base.split(':')[0],
      role: opts.role || 'General Worker',
      personality: opts.personality || null,
      modeEligibility: opts.modeEligibility || 'both',
      status: 'idle',
      tasksCompleted: 0,
      tasksFailed: 0,
      lastUsed: null,
      registeredAt: new Date().toISOString(),
    };
    this.agents.push(agent);
    this.save();
    return agent;
  }

  getById(id) {
    return this.agents.find(a => a.id === id);
  }

  list() {
    // Check which models are actually available
    let liveModels = [];
    try {
      const out = execSync('ollama list', { encoding: 'utf8', timeout: 3000 });
      liveModels = out.trim().split('\n').slice(1).map(l => l.split(/\s+/)[0]).filter(Boolean);
    } catch {}

    return this.agents.map(a => ({
      ...a,
      available: liveModels.includes(a.base) || liveModels.includes(a.id),
    }));
  }

  rename(id, newName) {
    const a = this.getById(id);
    if (a) { a.displayName = newName; this.save(); }
  }

  setRole(id, role) {
    const a = this.getById(id);
    if (a) { a.role = role; this.save(); }
  }

  setPersonality(id, personality) {
    const a = this.getById(id);
    if (a) { a.personality = personality; this.save(); }
  }

  /** Record task completion for learning metrics */
  recordResult(id, success) {
    const a = this.getById(id);
    if (!a) return;
    if (success) a.tasksCompleted++;
    else a.tasksFailed++;
    a.lastUsed = new Date().toISOString();
    this.save();
  }
}
