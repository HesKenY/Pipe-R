/**
 * PIPE-R Agent Mode — Orchestrator
 * Hybrid AI framework: Claude Code dispatches, Ollama agents execute
 *
 * Modes:
 *   hybrid  — Claude reviews, Ollama executes, results come back for approval
 *   offline — Ollama agents work independently, results queued for later review
 */

import { TaskQueue } from './queue.js';
import { AgentRegistry } from './registry.js';
import { Executor } from './executor.js';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

const ROOT = process.cwd();
const CONFIG_DIR = join(ROOT, 'agent_mode', 'config');
const LOG_DIR = join(ROOT, 'agent_mode', 'logs');

export class Orchestrator {
  constructor() {
    this.queue = new TaskQueue();
    this.registry = new AgentRegistry();
    this.executor = new Executor(this.registry);
    this.mode = this._loadMode();
  }

  /** Detect what's available and return system state */
  init() {
    const claude = this._detectClaude();
    const ollama = this._detectOllama();
    const models = ollama ? this._listModels() : [];

    // Auto-register any Ollama models as agents
    models.forEach(m => {
      if (!this.registry.getById(m)) {
        this.registry.register({
          id: m,
          base: m,
          displayName: m.split(':')[0],
          role: 'General Worker',
          personality: null,
          modeEligibility: 'both',
        });
      }
    });

    return { mode: this.mode, claude, ollama, models };
  }

  /** Get dashboard summary */
  dashboard() {
    return {
      queue: this.queue.summary(),
      agents: this.registry.list(),
    };
  }

  /** Create a task and optionally auto-assign */
  createTask(opts) {
    const task = this.queue.add({
      type: opts.type || 'general',
      objective: opts.objective,
      scope: opts.scope || [],
      priority: opts.priority || 2,
      requiresClaudeReview: this.mode === 'hybrid',
    });

    this._tryAutoAssign(task);
    this._log('task_created', { id: task.id, objective: task.objective, assigned: task.assignedAgent });
    return task;
  }

  /** Assign a task to a specific agent */
  assignTask(taskId, agentId) {
    const task = this.queue.get(taskId);
    if (task) {
      task.assignedAgent = agentId;
      this.queue.save();
      this._log('task_assigned', { taskId, agentId });
    }
  }

  /** Execute a single task */
  async executeTask(taskId) {
    const task = this.queue.get(taskId);
    if (!task) throw new Error('Task not found: ' + taskId);

    task.status = 'in_progress';
    task.startedAt = new Date().toISOString();
    this.queue.save();

    try {
      const result = await this.executor.run(task);
      task.output = result.output;
      task.status = task.requiresClaudeReview ? 'waiting_for_claude' : 'approved_for_merge';
      task.completedAt = new Date().toISOString();
      this._log('task_completed', { id: task.id, agent: task.assignedAgent, success: true });
    } catch (err) {
      task.output = 'ERROR: ' + err.message;
      task.status = 'queued'; // back to queue for retry
      task.retries = (task.retries || 0) + 1;
      this._log('task_failed', { id: task.id, error: err.message });
    }

    this.queue.save();
    return task;
  }

  /** Run all offline-safe queued tasks */
  async runOfflineBatch() {
    const liveAgents = this.registry.list(); // includes availability check
    const queued = this.queue.listByStatus('queued').filter(t => {
      if (!t.assignedAgent) return false;
      const agent = liveAgents.find(a => a.id === t.assignedAgent);
      return agent && agent.available;
    });

    const results = [];
    for (const task of queued) {
      try {
        await this.executeTask(task.id);
        results.push({ task, agent: task.assignedAgent, success: true });
      } catch (err) {
        results.push({ task, agent: task.assignedAgent, success: false, error: err.message });
      }
    }

    this._log('batch_complete', { total: results.length, success: results.filter(r => r.success).length });
    return results;
  }

  /** Review a completed task */
  reviewTask(taskId, approved, notes) {
    const task = this.queue.get(taskId);
    if (!task) return;

    if (approved) {
      task.status = 'approved_for_merge';
      task.reviewNotes = notes || 'Approved';
    } else {
      task.status = 'queued';
      task.reviewNotes = notes || 'Rejected — needs rework';
      task.output = null;
    }
    task.reviewedAt = new Date().toISOString();
    this.queue.save();
    this._log('task_reviewed', { id: task.id, approved, notes });
  }

  /** Build a packet for Claude Code re-entry */
  buildClaudeReentryPacket() {
    const pending = this.queue.getForClaudeReview();
    return {
      timestamp: new Date().toISOString(),
      mode: this.mode,
      tasksForReview: pending.map(t => ({
        id: t.id,
        type: t.type,
        objective: t.objective,
        agent: t.assignedAgent,
        output: t.output,
        scope: t.scope,
      })),
      agentStatus: this.registry.list().map(a => ({
        name: a.displayName,
        model: a.base,
        status: a.status,
      })),
    };
  }

  /** Auto-assign a task to the best available agent */
  _tryAutoAssign(task) {
    if (task.assignedAgent) return;
    const available = this.registry.list().filter(a => a.available);
    if (available.length === 0) return;

    // Role matching
    const roleMap = {
      scan: 'Repo Scanner',
      index: 'Repo Scanner',
      draft_patch: 'Patch Drafter',
      draft_test: 'Test Builder',
      summarize: 'Log Summarizer',
      memory_extract: 'Memory Curator',
    };

    const preferredRole = roleMap[task.type];
    const match = preferredRole
      ? available.find(a => a.role === preferredRole) || available[0]
      : available[0];

    task.assignedAgent = match.id;
    this.queue.save();
  }

  _loadMode() {
    try {
      const rt = JSON.parse(readFileSync(join(CONFIG_DIR, 'runtime.json'), 'utf8'));
      return rt.mode || 'hybrid';
    } catch { return 'hybrid'; }
  }

  _detectClaude() {
    try { execSync('claude --version', { encoding: 'utf8', timeout: 3000 }); return true; }
    catch { return false; }
  }

  _detectOllama() {
    try { execSync('ollama list', { encoding: 'utf8', timeout: 3000 }); return true; }
    catch { return false; }
  }

  _listModels() {
    try {
      const out = execSync('ollama list', { encoding: 'utf8', timeout: 5000 });
      return out.trim().split('\n').slice(1).map(l => l.split(/\s+/)[0]).filter(Boolean);
    } catch { return []; }
  }

  _log(event, data) {
    if (!existsSync(LOG_DIR)) mkdirSync(LOG_DIR, { recursive: true });
    const entry = JSON.stringify({ ts: new Date().toISOString(), event, ...data }) + '\n';
    try { writeFileSync(join(LOG_DIR, 'orchestrator.log'), entry, { flag: 'a' }); } catch {}
  }
}
