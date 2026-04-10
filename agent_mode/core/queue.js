/**
 * Task Queue — persistent task storage with status tracking
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';

const QUEUE_FILE = join(process.cwd(), 'agent_mode', 'config', 'tasks.json');

export class TaskQueue {
  constructor() {
    this.tasks = this._load();
  }

  _load() {
    try { return JSON.parse(readFileSync(QUEUE_FILE, 'utf8')); }
    catch { return []; }
  }

  save() {
    const dir = join(process.cwd(), 'agent_mode', 'config');
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    writeFileSync(QUEUE_FILE, JSON.stringify(this.tasks, null, 2));
  }

  /** Add a new task */
  add(opts) {
    const task = {
      id: 'task-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6),
      type: opts.type || 'general',
      objective: opts.objective,
      scope: opts.scope || [],
      priority: opts.priority ?? 2,
      status: 'queued',
      assignedAgent: null,
      requiresClaudeReview: opts.requiresClaudeReview ?? true,
      output: null,
      reviewNotes: null,
      retries: 0,
      createdAt: new Date().toISOString(),
      startedAt: null,
      completedAt: null,
      reviewedAt: null,
    };
    this.tasks.push(task);
    this.save();
    return task;
  }

  get(id) {
    return this.tasks.find(t => t.id === id);
  }

  listByStatus(status) {
    return this.tasks.filter(t => t.status === status);
  }

  getForClaudeReview() {
    return this.tasks.filter(t => t.status === 'waiting_for_claude');
  }

  /** Safe subset for offline display */
  getOfflineSafe() {
    return this.tasks.filter(t => t.status === 'queued' || t.status === 'in_progress');
  }

  summary() {
    const counts = {};
    this.tasks.forEach(t => { counts[t.status] = (counts[t.status] || 0) + 1; });
    return {
      total: this.tasks.length,
      queued: counts.queued || 0,
      in_progress: counts.in_progress || 0,
      pendingReview: counts.waiting_for_claude || 0,
      approved: counts.approved_for_merge || 0,
      offlineReady: this.tasks.filter(t => t.status === 'queued' && !t.requiresClaudeReview).length,
    };
  }

  /** Archive completed/approved tasks older than N days */
  prune(days = 7) {
    const cutoff = Date.now() - days * 86400000;
    const archivable = this.tasks.filter(t =>
      (t.status === 'approved_for_merge' || t.status === 'archived') &&
      t.completedAt && new Date(t.completedAt).getTime() < cutoff
    );
    archivable.forEach(t => { t.status = 'archived'; });
    this.save();
    return archivable.length;
  }
}
