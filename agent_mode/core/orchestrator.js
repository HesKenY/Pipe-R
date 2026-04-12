// Goals 1 and 2 plus squad design: retry/backoff, unhealthy-agent routing, and track-based trainer-party orchestration - see CHANGES.md
/**
 * PIPE-R Agent Mode - Orchestrator
 * Hybrid AI framework: Claude Code dispatches, Ollama agents execute
 *
 * Modes:
 *   hybrid  - Claude reviews, Ollama executes, results come back for approval
 *   offline - Ollama agents work independently, results queued for later review
 */

import { TaskQueue } from './queue.js';
import { AgentRegistry } from './registry.js';
import { Executor } from './executor.js';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

const CONFIG_DIR = join(process.cwd(), 'agent_mode', 'config');
const LOG_DIR = join(process.cwd(), 'agent_mode', 'logs');
const DEFAULT_TRAINER_ID = 'ken-ai:latest';
const DEFAULT_THEME = {
  name: 'gba-trainer-deck',
  trainerLabel: 'Ken AI',
  partyLabel: 'P0K3M0N-Style Dev Party',
};

export class Orchestrator {
  constructor() {
    this.queue = new TaskQueue();
    this.registry = new AgentRegistry();
    this.executor = new Executor(this.registry);
    this.runtime = this._loadRuntime();
    this.mode = this.runtime.mode || 'hybrid';
    this.trainerAgentId = this.runtime.trainerAgentId || DEFAULT_TRAINER_ID;
  }

  /** Detect what's available and return system state */
  init() {
    const claude = this._detectClaude();
    const ollama = this._detectOllama();
    const models = ollama ? this._listModels() : [];

    models.forEach(modelId => {
      if (!this.registry.getById(modelId)) {
        this.registry.register({
          id: modelId,
          base: modelId,
          displayName: modelId.split(':')[0],
          role: 'General Worker',
          personality: null,
          modeEligibility: 'both',
        });
      }
    });

    return { mode: this.mode, claude, ollama, models, trainerAgentId: this.trainerAgentId };
  }

  getMode() {
    return this.mode;
  }

  setMode(mode) {
    this.mode = mode === 'offline' ? 'offline' : 'hybrid';
    this.runtime.mode = this.mode;
    this._saveRuntime();
    return this.mode;
  }

  /** Get dashboard summary */
  dashboard() {
    const agents = this.registry.list();
    const byId = new Map(agents.map(agent => [agent.id, agent]));
    const trainer = agents.find(agent => agent.id === this.trainerAgentId || agent.teamRole === 'trainer') || null;
    const companion = agents.find(agent => agent.teamRole === 'companion') || null;
    const party = agents.filter(agent => agent.id !== trainer?.id && agent.id !== companion?.id);
    const tasks = [...this.queue.tasks]
      .map(task => this.queue.get(task.id))
      .filter(Boolean)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, 12)
      .map(task => ({
        id: task.id,
        type: task.type,
        objective: task.objective,
        status: task.status,
        assignedAgent: task.assignedAgent,
        assignedAgentName: task.assignedAgent ? (byId.get(task.assignedAgent)?.displayName || null) : null,
        supportAgent: task.supportAgent,
        supportAgentName: task.supportAgent ? (byId.get(task.supportAgent)?.displayName || null) : null,
        coordinatorAgent: task.coordinatorAgent,
        coordinatorAgentName: task.coordinatorAgent ? (byId.get(task.coordinatorAgent)?.displayName || null) : null,
        routingLane: task.routingLane,
        routingReason: task.routingReason,
        retries: task.retries,
        maxRetries: task.maxRetries,
        nextRetryAt: task.nextRetryAt,
        failureReason: task.failureReason,
      }));

    return {
      mode: this.mode,
      queue: this.queue.summary(),
      agents,
      trainer,
      companion,
      party,
      tasks,
      theme: this.runtime.theme || DEFAULT_THEME,
      trainerAgentId: this.trainerAgentId,
    };
  }

  /** Create a task and optionally auto-assign */
  createTask(opts) {
    const task = this.queue.add({
      type: opts.type || 'general',
      objective: opts.objective,
      scope: opts.scope || [],
      priority: opts.priority || 2,
      assignedAgent: opts.assignedAgent || null,
      coordinatorAgent: opts.coordinatorAgent || this.trainerAgentId,
      maxRetries: Number.isFinite(opts.maxRetries) ? opts.maxRetries : (this.runtime.maxRetries || 5),
      requiresClaudeReview: opts.requiresClaudeReview ?? (this.mode === 'hybrid'),
    });

    if (task.assignedAgent) this._applyAssignedRouting(task);
    else this._tryAutoAssign(task);
    this._log('task_created', {
      id: task.id,
      type: task.type,
      objective: task.objective,
      assigned: task.assignedAgent,
      support: task.supportAgent,
      routingLane: task.routingLane,
      coordinator: task.coordinatorAgent,
      maxRetries: task.maxRetries,
    });
    return task;
  }

  /** Assign a task to a specific agent */
  assignTask(taskId, agentId) {
    const task = this.queue.get(taskId);
    if (!task) return null;
    task.assignedAgent = agentId;
    task.coordinatorAgent = task.coordinatorAgent || this.trainerAgentId;
    this._applyAssignedRouting(task);
    this._log('task_assigned', {
      taskId,
      agentId,
      support: task.supportAgent,
      routingLane: task.routingLane,
      coordinator: task.coordinatorAgent,
    });
    return task;
  }

  /** Execute a single task */
  async executeTask(taskId) {
    const task = this.queue.get(taskId);
    if (!task) throw new Error('Task not found: ' + taskId);

    if (task.status === 'failed') {
      return { success: false, task, error: task.failureReason || 'Task already marked failed' };
    }

    task.maxRetries = task.maxRetries || this.runtime.maxRetries || 5;
    task.status = 'in_progress';
    task.startedAt = new Date().toISOString();
    this.queue.save();

    try {
      const result = await this.executor.run(task);
      task.output = result.output;
      task.status = task.requiresClaudeReview ? 'waiting_for_claude' : 'approved_for_merge';
      task.completedAt = new Date().toISOString();
      task.failedAt = null;
      task.failureReason = null;
      task.nextRetryAt = null;
      this.queue.save();
      this._log('task_completed', {
        id: task.id,
        agent: task.assignedAgent,
        coordinator: task.coordinatorAgent,
        success: true,
        elapsed: result.elapsed,
      });
      return { success: true, task, output: task.output, elapsed: result.elapsed, agent: task.assignedAgent };
    } catch (err) {
      const retryCount = (task.retries || 0) + 1;
      const maxRetries = task.maxRetries || 5;
      task.retries = retryCount;
      task.failureReason = err.message;

      if (retryCount >= maxRetries) {
        task.status = 'failed';
        task.failedAt = new Date().toISOString();
        task.nextRetryAt = null;
        task.output = `ABORTED after ${retryCount} retries - ${err.message}`;
        this._log('task_dead_letter', {
          id: task.id,
          agent: task.assignedAgent,
          coordinator: task.coordinatorAgent,
          retries: retryCount,
          maxRetries,
          error: err.message,
        });
      } else {
        const backoffMs = this._getBackoffMs(retryCount);
        task.status = 'queued';
        task.nextRetryAt = new Date(Date.now() + backoffMs).toISOString();
        task.output = 'ERROR: ' + err.message;
        this._log('task_retry_scheduled', {
          id: task.id,
          agent: task.assignedAgent,
          coordinator: task.coordinatorAgent,
          retry: retryCount,
          maxRetries,
          backoffMs,
          nextRetryAt: task.nextRetryAt,
          error: err.message,
        });
      }

      this.queue.save();
      return {
        success: false,
        task,
        error: err.message,
        agent: task.assignedAgent,
        nextRetryAt: task.nextRetryAt,
      };
    }
  }

  /** Run all offline-safe queued tasks */
  async runOfflineBatch() {
    const liveAgents = this.registry.list();
    const queued = this.queue.listRunnable().filter(task => {
      if (!task.assignedAgent) return false;
      const agent = liveAgents.find(item => item.id === task.assignedAgent);
      return agent && agent.available && agent.status !== 'unhealthy';
    });

    const results = [];
    for (const task of queued) {
      try {
        const result = await this.executeTask(task.id);
        results.push({
          task: result.task,
          agent: task.assignedAgent,
          success: result.success,
          error: result.error || null,
        });
      } catch (err) {
        results.push({ task, agent: task.assignedAgent, success: false, error: err.message });
      }
    }

    this._log('batch_complete', {
      total: results.length,
      success: results.filter(result => result.success).length,
    });
    return results;
  }

  /** Review a completed task */
  reviewTask(taskId, approved, notes) {
    const task = this.queue.get(taskId);
    if (!task) return null;

    if (approved) {
      task.status = 'approved_for_merge';
      task.reviewNotes = notes || 'Approved';
    } else {
      task.status = 'queued';
      task.reviewNotes = notes || 'Rejected - needs rework';
      task.output = null;
      task.nextRetryAt = null;
      task.failureReason = task.reviewNotes;
    }

    task.reviewedAt = new Date().toISOString();
    this.queue.save();

    // Propagate the review back into training-log.jsonl so curate.js can
    // filter by approval status. Best-effort — never throw out of review.
    try { this._stampTrainingReview(taskId, approved, notes); } catch (e) {}

    this._log('task_reviewed', { id: task.id, approved, notes });
    return task;
  }

  /** Find the training-log entry for this task id and mark it reviewed. */
  _stampTrainingReview(taskId, approved, notes) {
    const logPath = join(process.cwd(), 'agent_mode', 'training', 'training-log.jsonl');
    if (!existsSync(logPath)) return;
    const raw = readFileSync(logPath, 'utf8');
    const lines = raw.split('\n');
    let touched = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line.trim()) continue;
      if (line.indexOf('"taskId":"' + taskId + '"') === -1) continue;
      try {
        const e = JSON.parse(line);
        e.reviewed = true;
        e.approved = !!approved;
        if (notes) e.reviewNotes = notes;
        lines[i] = JSON.stringify(e);
        touched = true;
      } catch (err) {}
    }
    if (touched) writeFileSync(logPath, lines.join('\n'));
  }

  killTask(taskId, reason = 'Killed by operator') {
    const task = this.queue.get(taskId);
    if (!task) return null;
    task.status = 'failed';
    task.failedAt = new Date().toISOString();
    task.nextRetryAt = null;
    task.failureReason = reason;
    task.output = `KILLED: ${reason}`;
    this.queue.save();
    this._log('task_killed', { id: task.id, reason, agent: task.assignedAgent });
    return task;
  }

  healAgent(agentId) {
    const healed = this.registry.heal(agentId);
    if (healed) this._log('agent_healed', { agentId });
    return healed;
  }

  /** Build a packet for Claude Code re-entry */
  buildClaudeReentryPacket() {
    const pending = this.queue.getForClaudeReview();
    const dashboard = this.dashboard();

    return {
      timestamp: new Date().toISOString(),
      mode: this.mode,
      pendingReviewCount: pending.length,
      trainer: dashboard.trainer ? {
        id: dashboard.trainer.id,
        name: dashboard.trainer.displayName,
        role: dashboard.trainer.role,
      } : null,
      companion: dashboard.companion ? {
        id: dashboard.companion.id,
        name: dashboard.companion.displayName,
        role: dashboard.companion.role,
        track: dashboard.companion.specialistTrack,
      } : null,
      tasksForReview: pending.map(task => ({
        id: task.id,
        type: task.type,
        objective: task.objective,
        agent: task.assignedAgent,
        supportAgent: task.supportAgent,
        routingLane: task.routingLane,
        routingReason: task.routingReason,
        coordinator: task.coordinatorAgent,
        output: task.output,
        scope: task.scope,
      })),
      agentStatus: dashboard.agents.map(agent => ({
        name: agent.displayName,
        model: agent.base,
        status: agent.status,
        available: agent.available,
        pokemon: agent.pokemon,
        specialistTrack: agent.specialistTrack,
        preferredPartnerName: agent.preferredPartnerName || null,
      })),
    };
  }

  /** Auto-assign a task to the best available agent */
  _tryAutoAssign(task) {
    if (task.assignedAgent) return;

    // Skip agents flagged `blocked: true` in agents.json so known-broken
    // models (e.g. jefferferson which times out on ollama run) never get
    // picked by auto-assign. Direct dispatch by id still works.
    const available = this.registry.list().filter(agent =>
      agent.available && agent.status !== 'unhealthy' && !agent.blocked
    );
    if (available.length === 0) return;

    const trainer = available.find(agent => agent.id === this.trainerAgentId || agent.teamRole === 'trainer') || null;
    const workers = available.filter(agent => agent.id !== trainer?.id);

    const trackMap = {
      scan: 'recon',
      index: 'recon',
      draft_patch: 'implementation',
      draft_test: 'quality',
      summarize: 'observability',
      memory_extract: 'memory',
      learn: 'learning',
      prompt_tune: 'learning',
      decision: 'trainer',
      orchestrate: 'trainer',
      review: 'trainer',
    };

    const preferredTrack = trackMap[task.type];
    let candidates;

    if (preferredTrack === 'trainer') {
      candidates = trainer ? [trainer] : available;
    } else if (preferredTrack) {
      candidates = workers.filter(agent => agent.specialistTrack === preferredTrack);
      if (candidates.length === 0 && preferredTrack === 'implementation') {
        candidates = workers.filter(agent => agent.specialistTrack === 'integration');
      }
      if (candidates.length === 0) candidates = workers.length > 0 ? workers : available;
    } else {
      candidates = workers.length > 0 ? workers : available;
    }

    candidates = [...candidates].sort((a, b) => {
      if ((a.lastUsed || '') < (b.lastUsed || '')) return -1;
      if ((a.lastUsed || '') > (b.lastUsed || '')) return 1;
      return (a.partySlot || 99) - (b.partySlot || 99);
    });

    const match = candidates[0];
    if (!match) return;

    task.assignedAgent = match.id;
    task.coordinatorAgent = task.coordinatorAgent || trainer?.id || this.trainerAgentId;
    this._applyRoutingPlan(task, match, workers);
    this.queue.save();
  }

  _applyAssignedRouting(task) {
    const roster = this.registry.list();
    const trainer = roster.find(agent => agent.id === this.trainerAgentId || agent.teamRole === 'trainer') || this.registry.getById(this.trainerAgentId);
    const primary = this.registry.getById(task.assignedAgent);
    const workers = roster.filter(agent => agent.status !== 'unhealthy' && agent.available && agent.teamRole !== 'trainer');

    if (!primary) {
      task.supportAgent = null;
      task.routingLane = null;
      task.routingReason = null;
      this.queue.save();
      return task;
    }

    task.coordinatorAgent = task.coordinatorAgent || trainer?.id || this.trainerAgentId;
    this._applyRoutingPlan(task, primary, workers);
    this.queue.save();
    return task;
  }

  _applyRoutingPlan(task, primary, workers) {
    const partner = this._pickSupportAgent(task, primary, workers);
    task.supportAgent = partner?.id || null;
    task.routingLane = partner
      ? `${primary.specialistTrack || primary.role || 'general'} + ${partner.specialistTrack || partner.role || 'general'}`
      : (primary.specialistTrack || primary.role || 'general');
    task.routingReason = this._buildRoutingReason(task, primary, partner);
  }

  _pickSupportAgent(task, primary, workers) {
    if (!primary || primary.teamRole === 'trainer') return null;
    if (!this._shouldPairTask(task, primary)) return null;

    const pool = (workers || []).filter(agent => agent.id !== primary.id);
    const preferred = primary.preferredPartnerId
      ? pool.find(agent => agent.id === primary.preferredPartnerId)
      : null;

    return preferred || null;
  }

  _shouldPairTask(task, primary) {
    const pairable = {
      implementation: new Set(['draft_patch', 'general']),
      integration: new Set(['scan', 'index', 'draft_patch', 'general']),
      recon: new Set(['scan', 'index', 'general']),
      observability: new Set(['summarize', 'general']),
      quality: new Set(['draft_test', 'review', 'general']),
      memory: new Set(['memory_extract', 'summarize', 'general']),
      learning: new Set(['learn', 'prompt_tune', 'memory_extract', 'general']),
    };

    const lane = pairable[primary.specialistTrack];
    if (!lane) return false;
    if (lane.has(task.type)) return true;
    return task.type === 'general' && (task.priority || 0) >= 3;
  }

  _buildRoutingReason(task, primary, partner) {
    if (primary.teamRole === 'trainer') {
      return 'Trainer lane: Ken AI owns this decision or orchestration call directly.';
    }

    if (partner) {
      return primary.preferredPartnerReason
        || `${primary.displayName} leads while ${partner.displayName} covers the adjacent specialty.`;
    }

    return `${primary.displayName} owns the ${primary.specialistTrack || 'general'} lane for this ${task.type || 'general'} task.`;
  }

  _loadRuntime() {
    try {
      return JSON.parse(readFileSync(join(CONFIG_DIR, 'runtime.json'), 'utf8'));
    } catch {
      return { mode: 'hybrid', maxRetries: 5, trainerAgentId: DEFAULT_TRAINER_ID, theme: DEFAULT_THEME };
    }
  }

  _saveRuntime() {
    if (!existsSync(CONFIG_DIR)) mkdirSync(CONFIG_DIR, { recursive: true });
    writeFileSync(join(CONFIG_DIR, 'runtime.json'), JSON.stringify(this.runtime, null, 2));
  }

  _getBackoffMs(retries) {
    const steps = [30000, 60000, 120000, 240000, 480000];
    return steps[Math.min(Math.max(retries - 1, 0), steps.length - 1)];
  }

  _detectClaude() {
    try {
      execSync('claude --version', { encoding: 'utf8', timeout: 3000 });
      return true;
    } catch {
      return false;
    }
  }

  _detectOllama() {
    try {
      execSync('ollama list', { encoding: 'utf8', timeout: 3000 });
      return true;
    } catch {
      return false;
    }
  }

  _listModels() {
    try {
      const out = execSync('ollama list', { encoding: 'utf8', timeout: 5000 });
      return out.trim().split('\n').slice(1).map(line => line.split(/\s+/)[0]).filter(Boolean);
    } catch {
      return [];
    }
  }

  _log(event, data) {
    if (!existsSync(LOG_DIR)) mkdirSync(LOG_DIR, { recursive: true });
    const entry = JSON.stringify({ ts: new Date().toISOString(), event, ...data }) + '\n';
    try { writeFileSync(join(LOG_DIR, 'orchestrator.log'), entry, { flag: 'a' }); } catch {}
  }
}
