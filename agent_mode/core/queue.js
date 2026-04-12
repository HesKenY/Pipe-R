// Goal 1: added retry/backoff task fields and runnable-task filtering - see CHANGES.md
/**
 * Task Queue - persistent task storage with status tracking
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';

const QUEUE_FILE = join(process.cwd(), 'agent_mode', 'config', 'tasks.json');
const DEFAULT_MAX_RETRIES = 5;
const RETRY_BACKOFF_MS = [30000, 60000, 120000, 240000, 480000];

function getRetryDelayMs(retries) {
  if (!retries || retries < 1) return 0;
  return RETRY_BACKOFF_MS[Math.min(retries - 1, RETRY_BACKOFF_MS.length - 1)];
}

export class TaskQueue {
  constructor() {
    this.tasks = this._load();
  }

  _normalizeTask(task) {
    return {
      id: task.id,
      type: task.type || 'general',
      objective: task.objective || '',
      scope: Array.isArray(task.scope) ? task.scope : [],
      priority: Number.isFinite(task.priority) ? task.priority : 2,
      status: task.status || 'queued',
      assignedAgent: task.assignedAgent || null,
      supportAgent: task.supportAgent || null,
      coordinatorAgent: task.coordinatorAgent || null,
      routingLane: task.routingLane || null,
      routingReason: task.routingReason || null,
      requiresClaudeReview: task.requiresClaudeReview ?? true,
      output: task.output ?? null,
      reviewNotes: task.reviewNotes ?? null,
      retries: Number.isFinite(task.retries) ? task.retries : 0,
      maxRetries: Number.isFinite(task.maxRetries) ? task.maxRetries : DEFAULT_MAX_RETRIES,
      lastAttemptAt: task.lastAttemptAt || null,
      nextRetryAt: task.nextRetryAt || null,
      failureReason: task.failureReason || null,
      createdAt: task.createdAt || new Date().toISOString(),
      startedAt: task.startedAt || null,
      completedAt: task.completedAt || null,
      reviewedAt: task.reviewedAt || null,
      failedAt: task.failedAt || null,
    };
  }

  _touchTask(task) {
    Object.assign(task, this._normalizeTask(task));
    return task;
  }

  _load() {
    try {
      const parsed = JSON.parse(readFileSync(QUEUE_FILE, 'utf8'));
      if (!Array.isArray(parsed)) return [];
      return parsed.map(task => this._normalizeTask(task));
    } catch {
      return [];
    }
  }

  save() {
    const dir = join(process.cwd(), 'agent_mode', 'config');
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    writeFileSync(QUEUE_FILE, JSON.stringify(this.tasks, null, 2));
  }

  /** Add a new task */
  add(opts) {
    const task = this._normalizeTask({
      id: 'task-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6),
      type: opts.type || 'general',
      objective: opts.objective,
      scope: opts.scope || [],
      priority: opts.priority ?? 2,
      status: 'queued',
      assignedAgent: opts.assignedAgent || null,
      supportAgent: opts.supportAgent || null,
      coordinatorAgent: opts.coordinatorAgent || null,
      routingLane: opts.routingLane || null,
      routingReason: opts.routingReason || null,
      requiresClaudeReview: opts.requiresClaudeReview ?? true,
      output: null,
      reviewNotes: null,
      retries: 0,
      maxRetries: opts.maxRetries ?? DEFAULT_MAX_RETRIES,
      lastAttemptAt: null,
      nextRetryAt: null,
      failureReason: null,
      createdAt: new Date().toISOString(),
      startedAt: null,
      completedAt: null,
      reviewedAt: null,
      failedAt: null,
    });

    this.tasks.push(task);
    this.save();
    return task;
  }

  get(id) {
    const task = this.tasks.find(t => t.id === id);
    return task ? this._touchTask(task) : null;
  }

  listByStatus(status) {
    return this.tasks.filter(t => t.status === status).map(task => this._touchTask(task));
  }

  listRunnable(now = Date.now()) {
    return this.tasks.filter(task => {
      this._touchTask(task);
      if (task.status !== 'queued') return false;
      if (task.nextRetryAt) return new Date(task.nextRetryAt).getTime() <= now;
      if (!task.lastAttemptAt || !task.retries) return true;
      return new Date(task.lastAttemptAt).getTime() + getRetryDelayMs(task.retries) <= now;
    });
  }

  getForClaudeReview() {
    return this.tasks.filter(t => t.status === 'waiting_for_claude').map(task => this._touchTask(task));
  }

  /** Safe subset for offline execution */
  getOfflineSafe(now = Date.now()) {
    return this.listRunnable(now);
  }

  summary(now = Date.now()) {
    const counts = {};
    this.tasks.forEach(task => {
      this._touchTask(task);
      counts[task.status] = (counts[task.status] || 0) + 1;
    });

    return {
      total: this.tasks.length,
      queued: counts.queued || 0,
      in_progress: counts.in_progress || 0,
      pendingReview: counts.waiting_for_claude || 0,
      approved: counts.approved_for_merge || 0,
      failed: counts.failed || 0,
      archived: counts.archived || 0,
      offlineReady: this.listRunnable(now).length,
    };
  }

  /** Archive completed/approved tasks older than N days */
  prune(days = 7) {
    const cutoff = Date.now() - days * 86400000;
    const archivable = this.tasks.filter(task => {
      this._touchTask(task);
      return (
        (task.status === 'approved_for_merge' || task.status === 'archived') &&
        task.completedAt &&
        new Date(task.completedAt).getTime() < cutoff
      );
    });

    archivable.forEach(task => { task.status = 'archived'; });
    this.save();
    return archivable.length;
  }
}
