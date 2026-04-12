#!/usr/bin/env node
// Goals 2 and 3: trainer dashboard, remote PIN gate, and agent control endpoints - see CHANGES.md
/**
 * PIPE-R Server v4.0
 * HTTP API on :7777 â€” serves the web UI, remote client, and all API endpoints
 * Unified backend for pipe-r.html, pipe-r-remote.html, and hub.js
 */

import { createServer } from 'http';
import { readFileSync, writeFileSync, existsSync, readdirSync, statSync, appendFileSync, mkdirSync } from 'fs';
import { execSync } from 'child_process';
import { join, basename, dirname } from 'path';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
const require = createRequire(import.meta.url);

const PORT = 7777;
const ROOT = dirname(fileURLToPath(import.meta.url));
const CLAUDE_DIR = join(ROOT, '.claude');
const LOG_DIR = join(CLAUDE_DIR, 'logs');
const HUB_LOG_FILE = join(LOG_DIR, 'hub.log');
const POKEDEX_ICON_DIR = 'C:\\Users\\Ken\\Desktop\\Pokemon icons';

const DIRS = {
  input:     join(ROOT, 'input'),
  output:    join(ROOT, 'output'),
  workspace: join(ROOT, 'workspace'),
  staging:   join(ROOT, 'staging'),
};

const PROJECTS = [
  { name: 'CHERP',         path: join(ROOT, 'output', 'cherp-modular'),                     codename: 'ALPHA', url: 'cherp.live',              repo: 'HesKenY/CHERP' },
  { name: "Bird's Nest",   path: join(ROOT, 'output', 'birds-nest'),                        codename: 'NEST',                                  repo: 'HesKenY/CHERP-Nest' },
  { name: 'Pipe-R',        path: ROOT,                                                      codename: 'PIPER',                                 repo: 'HesKenY/Pipe-R' },
  { name: 'CodeForge',     path: 'C:\\Users\\Ken\\Documents\\CodeForge\\CodeForge-main',    codename: 'FORGE', url: 'codesforge.netlify.app',   repo: 'HesKenY/CodeForge' },
  { name: 'ForgeAgent',    path: 'C:\\Users\\Ken\\Documents\\ForgeAgent\\FORGE-main',       codename: 'NEXUS',                                 repo: 'HesKenY/FORGE' },
  { name: 'CHERP Worker',  path: 'C:\\Users\\Ken\\Documents\\CHERP Projects\\CHERP-Worker', codename: 'GHOST' },
  { name: 'RDO Server',    path: 'C:\\Users\\Ken\\Desktop\\Claude\\input\\RDO Server',      codename: 'MERICA',                                repo: 'HesKenY/deibelmerica' },
];

const startTime = Date.now();
const LOG_FILE = join(LOG_DIR, 'server.log');

if (!existsSync(CLAUDE_DIR)) mkdirSync(CLAUDE_DIR, { recursive: true });
if (!existsSync(LOG_DIR)) mkdirSync(LOG_DIR, { recursive: true });

function log(msg) {
  try { appendFileSync(LOG_FILE, `[${new Date().toISOString()}] [SERVER] ${msg}\n`); } catch {}
}

function countFiles(dir) {
  try { return readdirSync(dir).filter(f => !f.startsWith('.')).length; }
  catch { return 0; }
}

function getUptime() {
  const s = Math.floor((Date.now() - startTime) / 1000);
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ${m % 60}m`;
  if (m > 0) return `${m}m ${s % 60}s`;
  return `${s}s`;
}

function getState() {
  // Ollama
  let ollamaStatus = 'offline';
  let models = [];
  try {
    const out = execSync('ollama list', { encoding: 'utf8', timeout: 3000 });
    ollamaStatus = 'online';
    models = out.trim().split('\n').slice(1).map(l => {
      const p = l.split(/\s+/);
      return { name: p[0], id: p[1] || '', size: p[2] || '' };
    }).filter(m => m.name);
  } catch {}

  // Claude
  let claudeStatus = 'not found';
  try { execSync('claude --version', { encoding: 'utf8', timeout: 2000 }); claudeStatus = 'available'; } catch {}

  // Node
  let nodeVersion = '';
  try { nodeVersion = execSync('node -v', { encoding: 'utf8' }).trim(); } catch {}

  // Storage
  const storage = {};
  let totalFiles = 0;
  Object.entries(DIRS).forEach(([name, dir]) => {
    const n = countFiles(dir);
    storage[name] = n;
    totalFiles += n;
  });

  // Projects
  const projects = PROJECTS.map(p => {
    const online = existsSync(p.path);
    let gitChanges = 0;
    let lastCommit = '';
    if (online) {
      try {
        const s = execSync('git status --short', { cwd: p.path, encoding: 'utf8', timeout: 3000 });
        gitChanges = s.trim().split('\n').filter(Boolean).length;
      } catch {}
      try {
        lastCommit = execSync('git log -1 --format="%ar"', { cwd: p.path, encoding: 'utf8', timeout: 3000 }).trim();
      } catch {}
    }
    return { ...p, online, gitChanges, lastCommit };
  });

  // Agents
  let agents = [];
  try {
    const stateFile = join(ROOT, 'agents', 'state.json');
    if (existsSync(stateFile)) {
      agents = JSON.parse(readFileSync(stateFile, 'utf8')).agents || [];
    }
  } catch {}

  // Agent Mode profiles
  let agentProfiles = [];
  try {
      const modelsFile = join(ROOT, 'agent_mode', 'config', 'agents.json');
    if (existsSync(modelsFile)) {
      agentProfiles = JSON.parse(readFileSync(modelsFile, 'utf8'));
    }
  } catch {}

  // Notes
  let notes = [];
  try { notes = JSON.parse(readFileSync(join(ROOT, 'agents', 'notes.json'), 'utf8')); } catch {}

  // Recent activity from the hub command deck log
  let recentActivity = [];
  try {
    const logLines = readFileSync(HUB_LOG_FILE, 'utf8').trim().split('\n').slice(-20);
    recentActivity = logLines.map(l => {
      const match = l.match(/\[(.*?)\]\s*\[(.*?)\]\s*(.*)/);
      if (!match) return null;
      const type = match[2].toLowerCase().includes('error') ? 'error' : match[3].includes('git') ? 'git' : match[3].includes('agent') || match[3].includes('Agent') ? 'agent' : 'system';
      return { time: new Date(match[1]).toLocaleTimeString(), level: match[2], msg: match[3], type };
    }).filter(Boolean).reverse();
  } catch {}

  // Mode
  let mode = 'hybrid';
  try {
    const rt = JSON.parse(readFileSync(join(ROOT, 'agent_mode', 'config', 'runtime.json'), 'utf8'));
    mode = rt.mode || 'hybrid';
  } catch {}

  return {
    ollamaStatus, models, claudeStatus, nodeVersion,
    storage, totalFiles, projects, agents, agentProfiles,
    notes, recentActivity, mode,
    uptime: getUptime(),
    timestamp: new Date().toISOString(),
  };
}

function handleCommand(cmd) {
  switch (cmd) {
    case 'status':
      return { result: `Uptime: ${getUptime()}, Files: ${Object.values(DIRS).reduce((s, d) => s + countFiles(d), 0)}` };
    case 'models':
      try { return { result: execSync('ollama list', { encoding: 'utf8', timeout: 5000 }).trim() }; }
      catch { return { result: 'Ollama offline', error: true }; }
    case 'git-status':
      try { const s = execSync('git status --short', { encoding: 'utf8' }); return { result: s.trim() || 'Clean' }; }
      catch { return { result: 'Not a git repo', error: true }; }
    case 'git-status-all': {
      let results = [];
      PROJECTS.forEach(p => {
        if (!existsSync(p.path)) { results.push(`${p.name}: MISSING`); return; }
        try {
          const s = execSync('git status --short', { cwd: p.path, encoding: 'utf8', timeout: 5000 });
          const n = s.trim().split('\n').filter(Boolean).length;
          results.push(`${p.name}: ${n > 0 ? n + ' changed' : 'clean'}`);
        } catch { results.push(`${p.name}: no git`); }
      });
      return { result: results.join('\n') };
    }
    case 'start-ollama':
      try { execSync('start "" cmd /k "ollama serve"', { shell: 'cmd.exe', stdio: 'ignore' }); return { result: 'Ollama starting...' }; }
      catch { return { result: 'Failed', error: true }; }
    case 'loc': {
      let results = [];
      PROJECTS.forEach(p => {
        if (!existsSync(p.path)) return;
        let loc = 0;
        const count = (dir, depth = 0) => {
          if (depth > 3) return;
          try {
            readdirSync(dir).forEach(f => {
              if (f.startsWith('.') || ['node_modules','__pycache__','dist','build','android','www','.git'].includes(f)) return;
              const fp = join(dir, f);
              try {
                const st = statSync(fp);
                if (st.isDirectory()) count(fp, depth + 1);
                else if (/\.(js|py|ts|jsx|tsx|html|css)$/.test(f) && st.size < 500000) loc += readFileSync(fp, 'utf8').split('\n').length;
              } catch {}
            });
          } catch {}
        };
        count(p.path);
        results.push(`${p.name}: ${loc.toLocaleString()} LOC`);
      });
      return { result: results.join('\n') };
    }
    case 'start-agent':
      return { result: 'Use Agent Mode in the web UI to manage agents' };
    case 'stop-agent':
      return { result: 'Use Agent Mode in the web UI to manage agents' };
    case 'pause-agents':
      agentsPaused = true;
      log('Agent Mode PAUSED');
      return { result: 'Agent Mode paused. Tasks will not auto-execute.' };
    case 'resume-agents':
      agentsPaused = false;
      log('Agent Mode RESUMED');
      return { result: 'Agent Mode resumed. Auto-execution active.' };
    case 'agent-status':
      return { result: 'Agents ' + (agentsPaused ? 'PAUSED' : 'RUNNING') + '. Auto-exec interval: 30s' };
    case 'refresh':
      return { result: 'State refreshed' };
    default:
      if (cmd.startsWith('ollama ')) {
        try { return { result: execSync(cmd, { encoding: 'utf8', timeout: 30000 }).trim() }; }
        catch (e) { return { result: e.message, error: true }; }
      }
      // Try as a shell command
      try { return { output: execSync(cmd, { encoding: 'utf8', timeout: 10000, cwd: ROOT }).trim() }; }
      catch (e) { return { result: e.message, error: true }; }
  }
}

function readRuntimeConfig() {
  try {
    return JSON.parse(readFileSync(join(ROOT, 'agent_mode', 'config', 'runtime.json'), 'utf8'));
  } catch {
    return {
      mode: 'hybrid',
      maxRetries: 5,
      trainerAgentId: 'ken-ai:latest',
      remotePin: '1996',
      theme: {
        name: 'gba-trainer-deck',
        trainerLabel: 'Ken AI',
        partyLabel: 'P0K3M0N-Style Dev Party',
        workbenchLabel: 'Game Boy Advance Field Kit',
      },
    };
  }
}

function getLoadedModels() {
  try {
    const out = execSync('ollama ps', { encoding: 'utf8', timeout: 3000 });
    return out.trim().split('\n').slice(1).map(line => {
      const parts = line.trim().split(/\s+/);
      return {
        name: parts[0],
        id: parts[1] || '',
        size: parts[2] || '',
        processor: parts[3] || '',
        until: parts.slice(4).join(' '),
      };
    }).filter(model => model.name);
  } catch {
    return [];
  }
}

async function getDashboardState() {
  const runtime = readRuntimeConfig();
  const state = getState();
  const { Orchestrator } = await import('./agent_mode/core/orchestrator.js');
  const orch = new Orchestrator();
  const dash = orch.dashboard();

  let sheets = { available: false, crews: 0, status: {} };
  try {
    const sync = require('./agent_mode/sheets/sync');
    const status = sync.getSyncStatus();
    sheets = {
      available: true,
      crews: Object.keys(status).length,
      status,
    };
  } catch (e) {
    sheets = {
      available: false,
      crews: 0,
      status: {},
      error: e.message,
    };
  }

  return {
    timestamp: new Date().toISOString(),
    uptime: state.uptime,
    system: {
      mode: dash.mode || state.mode,
      claudeStatus: state.claudeStatus,
      ollamaStatus: state.ollamaStatus,
      nodeVersion: state.nodeVersion,
      autoExecutePaused: agentsPaused,
    },
    theme: runtime.theme || {
      name: 'gba-trainer-deck',
      trainerLabel: 'Ken AI',
        partyLabel: 'P0K3M0N-Style Dev Party',
      workbenchLabel: 'Game Boy Advance Field Kit',
    },
    trainerAgentId: runtime.trainerAgentId || 'ken-ai:latest',
    queue: dash.queue,
    tasks: dash.tasks,
    trainer: dash.trainer,
    companion: dash.companion,
    party: dash.party,
    agents: dash.agents,
    projects: state.projects,
    storage: state.storage,
    recentActivity: state.recentActivity,
    models: state.models,
    loadedModels: getLoadedModels(),
    sheets,
  };
}

// â”€â”€ CORS â”€â”€
function isRemotePinValid(pin) {
  const runtime = readRuntimeConfig();
  const configuredPin = String(runtime.remotePin || '').trim();
  if (!/^\d{4}$/.test(configuredPin)) return false;
  return String(pin || '').trim() === configuredPin;
}

async function dispatchTaskFromPayload(payload = {}) {
  const { Orchestrator } = await import('./agent_mode/core/orchestrator.js');
  const orch = new Orchestrator();
  const { objective, type, scope, agent, priority, execute, maxRetries, coordinator } = payload;

  const task = orch.createTask({
    type: type || 'general',
    objective: objective || '',
    scope: scope
      ? (Array.isArray(scope)
          ? scope
          : String(scope).split(',').map(item => item.trim()).filter(Boolean))
      : [],
    assignedAgent: agent || null,
    coordinatorAgent: coordinator || orch.trainerAgentId,
    priority: parseInt(priority) || 3,
    maxRetries: Number.isFinite(Number(maxRetries)) ? parseInt(maxRetries) : undefined,
    requiresClaudeReview: true,
  });

  log(`Dispatch: ${task.objective.substring(0, 50)} -> ${task.assignedAgent || 'auto'}`);

  if (execute) {
    if (!task.assignedAgent) orch._tryAutoAssign(task);
    if (task.assignedAgent) {
      const result = await orch.executeTask(task.id);
      return { task: result.task, result };
    }
  }

  return { task };
}

function cors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

function jsonResp(res, data, status = 200) {
  cors(res);
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

function serveFile(res, filePath, contentType) {
  try {
    const content = readFileSync(filePath, 'utf8');
    cors(res);
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(content);
  } catch {
    res.writeHead(404);
    res.end('Not found');
  }
}

function serveBinaryFile(res, filePath, contentType) {
  try {
    const content = readFileSync(filePath);
    cors(res);
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(content);
  } catch {
    res.writeHead(404);
    res.end('Not found');
  }
}

function readBody(req) {
  return new Promise(resolve => {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => resolve(body));
  });
}

// â”€â”€ Server â”€â”€
const server = createServer(async (req, res) => {
  cors(res);
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  const url = req.url.split('?')[0];

  // â”€â”€ STATIC FILES â”€â”€

  // Main web UI
  if (url === '/' || url === '/index.html' || url === '/pipe-r.html') {
    return serveFile(res, join(ROOT, 'pipe-r.html'), 'text/html');
  }

  // Remote dashboard (legacy)
  if (url === '/remote' || url === '/remote.html') {
    return serveFile(res, join(ROOT, 'remote.html'), 'text/html');
  }

  if (url.startsWith('/assets/pokedex/')) {
    const requested = basename(decodeURIComponent(url.slice('/assets/pokedex/'.length)));
    if (!/^\d{4}(?:-icon|-icons)?\.png$/i.test(requested)) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }
    return serveBinaryFile(res, join(POKEDEX_ICON_DIR, requested), 'image/png');
  }

  // â”€â”€ API ROUTES â”€â”€

  // Full state
  if (url === '/api/state' && req.method === 'GET') {
    return jsonResp(res, getState());
  }

  // Dashboard state for the web UIs
  if (url === '/api/dashboard' && req.method === 'GET') {
    try {
      return jsonResp(res, await getDashboardState());
    } catch (e) {
      return jsonResp(res, { error: e.message }, 500);
    }
  }

  // Projects scan
  if (url === '/api/scan' && req.method === 'GET') {
    const results = PROJECTS.map(p => {
      if (!existsSync(p.path)) return { ...p, online: false, loc: 0 };
      let loc = 0;
      const count = (dir, depth = 0) => {
        if (depth > 3) return;
        try {
          readdirSync(dir).forEach(f => {
            if (f.startsWith('.') || ['node_modules','__pycache__','dist','build','android','www','.git'].includes(f)) return;
            const fp = join(dir, f);
            try {
              const st = statSync(fp);
              if (st.isDirectory()) count(fp, depth + 1);
              else if (/\.(js|py|ts|jsx|tsx|html|css)$/.test(f) && st.size < 500000) loc += readFileSync(fp, 'utf8').split('\n').length;
            } catch {}
          });
        } catch {}
      };
      count(p.path);
      let gitChanges = 0;
      try {
        const s = execSync('git status --short', { cwd: p.path, encoding: 'utf8', timeout: 3000 });
        gitChanges = s.trim().split('\n').filter(Boolean).length;
      } catch {}
      return { ...p, online: true, loc, gitChanges };
    });
    return jsonResp(res, results);
  }

  // Notes GET
  if (url === '/api/notes' && req.method === 'GET') {
    try { return jsonResp(res, JSON.parse(readFileSync(join(ROOT, 'agents', 'notes.json'), 'utf8'))); }
    catch { return jsonResp(res, []); }
  }

  // Notes POST
  if (url === '/api/notes' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { text, tag } = JSON.parse(body);
      const notesFile = join(ROOT, 'agents', 'notes.json');
      let notes = [];
      try { notes = JSON.parse(readFileSync(notesFile, 'utf8')); } catch {}
      notes.push({ text, tag: tag || '', ts: new Date().toISOString() });
      writeFileSync(notesFile, JSON.stringify(notes, null, 2));
      log(`Note added: ${text.substring(0, 50)}`);
      return jsonResp(res, { result: 'Note saved' });
    } catch (e) { return jsonResp(res, { result: e.message, error: true }, 400); }
  }

  // Remote entry PIN check
  if (url === '/api/remote/auth' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { pin } = JSON.parse(body || '{}');
      const runtime = readRuntimeConfig();
      const configured = /^\d{4}$/.test(String(runtime.remotePin || '').trim());
      const ok = configured && isRemotePinValid(pin);
      log(`Remote auth ${ok ? 'OK' : 'FAIL'}`);
      return jsonResp(res, {
        ok,
        unlocked: ok,
        configured,
        theme: runtime.theme || null,
      }, configured ? (ok ? 200 : 401) : 503);
    } catch (e) {
      return jsonResp(res, { ok: false, error: e.message }, 400);
    }
  }

  // Remote-only task dispatch behind the runtime PIN gate
  if (url === '/api/remote/dispatch' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const payload = JSON.parse(body || '{}');
      if (!isRemotePinValid(payload.pin)) return jsonResp(res, { error: 'Invalid PIN' }, 401);
      return jsonResp(res, await dispatchTaskFromPayload(payload));
    } catch (e) {
      return jsonResp(res, { error: e.message }, 400);
    }
  }

  // Remote-only task kill behind the runtime PIN gate
  if (url === '/api/remote/task/kill' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const payload = JSON.parse(body || '{}');
      if (!isRemotePinValid(payload.pin)) return jsonResp(res, { error: 'Invalid PIN' }, 401);
      const { Orchestrator } = await import('./agent_mode/core/orchestrator.js');
      const orch = new Orchestrator();
      if (!payload.taskId) return jsonResp(res, { error: 'taskId required' }, 400);
      const task = orch.killTask(payload.taskId, payload.reason || 'Killed from remote');
      if (!task) return jsonResp(res, { error: 'Task not found' }, 404);
      log(`Remote task killed: ${payload.taskId}`);
      return jsonResp(res, { result: 'Killed', task });
    } catch (e) {
      return jsonResp(res, { error: e.message }, 400);
    }
  }

  // Remote-only Sheets sync behind the runtime PIN gate
  if (url === '/api/remote/sheets/sync' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const payload = JSON.parse(body || '{}');
      if (!isRemotePinValid(payload.pin)) return jsonResp(res, { error: 'Invalid PIN' }, 401);
      const sync = require('./agent_mode/sheets/sync');
      let result;
      if (payload.teamCode) result = await sync.pushSync(payload.teamCode);
      else result = await sync.pushSyncAll();
      log(`Remote sheets sync: ${payload.teamCode || 'all'}`);
      return jsonResp(res, result);
    } catch (e) {
      return jsonResp(res, { error: e.message }, 500);
    }
  }

  // Command (legacy /api/command)
  if ((url === '/api/command' || url === '/api/cmd') && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { command, cmd } = JSON.parse(body);
      const result = handleCommand(command || cmd);
      log(`Command: ${command || cmd}`);
      return jsonResp(res, result);
    } catch (e) { return jsonResp(res, { result: e.message, error: true }, 400); }
  }

  // Deploy agent
  if (url === '/api/deploy' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { model } = JSON.parse(body);
      log(`Deploy: ${model}`);
      return jsonResp(res, { result: 'Deployed ' + model, id: 'agent-' + Date.now().toString(36) });
    } catch (e) { return jsonResp(res, { result: e.message, error: true }, 400); }
  }

  // Dispatch task (Claude Code â†’ Agent Mode)
  if (url === '/api/dispatch' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const payload = JSON.parse(body || '{}');
      return jsonResp(res, await dispatchTaskFromPayload(payload));
    } catch (e) { return jsonResp(res, { error: e.message }, 400); }
  }

  // Kill a queued or stuck task
  if (url === '/api/task/kill' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { Orchestrator } = await import('./agent_mode/core/orchestrator.js');
      const orch = new Orchestrator();
      const { taskId, reason } = JSON.parse(body || '{}');
      if (!taskId) return jsonResp(res, { error: 'taskId required' }, 400);
      const task = orch.killTask(taskId, reason || 'Killed from remote');
      if (!task) return jsonResp(res, { error: 'Task not found' }, 404);
      log(`Task killed: ${taskId}`);
      return jsonResp(res, { result: 'Killed', task });
    } catch (e) {
      return jsonResp(res, { error: e.message }, 400);
    }
  }

  // Heal an unhealthy agent
  if (url === '/api/agent/heal' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { Orchestrator } = await import('./agent_mode/core/orchestrator.js');
      const orch = new Orchestrator();
      const { agentId } = JSON.parse(body || '{}');
      if (!agentId) return jsonResp(res, { error: 'agentId required' }, 400);
      const healed = orch.healAgent(agentId);
      if (!healed) return jsonResp(res, { error: 'Agent not found' }, 404);
      log(`Agent healed: ${agentId}`);
      return jsonResp(res, { result: 'Healed', agentId });
    } catch (e) {
      return jsonResp(res, { error: e.message }, 400);
    }
  }

  // Get review queue (Claude Code pulls pending work)
  if (url === '/api/review' && req.method === 'GET') {
    try {
      const { Orchestrator } = await import('./agent_mode/core/orchestrator.js');
      const orch = new Orchestrator();
      return jsonResp(res, orch.buildClaudeReentryPacket());
    } catch (e) { return jsonResp(res, { error: e.message }, 400); }
  }

  // Approve/reject task (Claude Code reviews)
  if (url === '/api/review' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { Orchestrator } = await import('./agent_mode/core/orchestrator.js');
      const orch = new Orchestrator();
      const { taskId, approved, notes } = JSON.parse(body);
      orch.reviewTask(taskId, approved, notes || '');
      log(`Review: ${taskId} ${approved ? 'APPROVED' : 'REJECTED'}`);
      return jsonResp(res, { result: approved ? 'Approved' : 'Rejected', taskId });
    } catch (e) { return jsonResp(res, { error: e.message }, 400); }
  }

  // Project-specific git operations
  if (url === '/api/project-git' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { project, action } = JSON.parse(body);
      const proj = PROJECTS.find(p => p.name === project);
      if (!proj || !existsSync(proj.path)) return jsonResp(res, { result: 'Project not found: ' + project, error: true }, 404);
      let result = '';
      switch (action) {
        case 'status':
          result = execSync('git status --short', { cwd: proj.path, encoding: 'utf8', timeout: 5000 }).trim() || 'Clean â€” no changes';
          break;
        case 'pull':
          result = execSync('git pull', { cwd: proj.path, encoding: 'utf8', timeout: 30000 }).trim();
          break;
        case 'push':
          result = execSync('git push', { cwd: proj.path, encoding: 'utf8', timeout: 30000 }).trim();
          break;
        case 'log':
          result = execSync('git log --oneline -10', { cwd: proj.path, encoding: 'utf8', timeout: 5000 }).trim();
          break;
        case 'add-commit':
          const { message } = JSON.parse(body);
          execSync('git add -A', { cwd: proj.path, encoding: 'utf8', timeout: 5000 });
          result = execSync('git commit -m "' + (message || 'Update from Pipe-R').replace(/"/g, '\\"') + '"', { cwd: proj.path, encoding: 'utf8', timeout: 10000 }).trim();
          break;
        case 'remote':
          result = execSync('git remote -v', { cwd: proj.path, encoding: 'utf8', timeout: 3000 }).trim();
          break;
        default:
          result = 'Unknown action: ' + action;
      }
      log(`Project git: ${project} ${action}`);
      return jsonResp(res, { result });
    } catch (e) { return jsonResp(res, { result: e.message, error: true }, 400); }
  }

  // Download project as zip
  if (url.startsWith('/api/zip/') && req.method === 'GET') {
    const projName = decodeURIComponent(url.replace('/api/zip/', ''));
    const proj = PROJECTS.find(p => p.name === projName);
    if (!proj || !existsSync(proj.path)) { res.writeHead(404); res.end('Project not found'); return; }
    try {
      const zipName = projName.replace(/[^a-zA-Z0-9-]/g, '-') + '-' + new Date().toISOString().slice(0,10) + '.zip';
      const zipPath = join(ROOT, 'output', zipName);
      execSync('powershell -Command "Compress-Archive -Path \'' + proj.path + '\\*\' -DestinationPath \'' + zipPath + '\' -Force"', { timeout: 60000 });
      const zipData = readFileSync(zipPath);
      cors(res);
      res.writeHead(200, { 'Content-Type': 'application/zip', 'Content-Disposition': 'attachment; filename="' + zipName + '"', 'Content-Length': zipData.length });
      res.end(zipData);
      log(`Zip download: ${projName} â†’ ${zipName}`);
      return;
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }

  // â”€â”€ Google Sheets Sync â”€â”€

  // POST /api/sheets/sync â€” Push CHERP data to Sheets
  if (url === '/api/sheets/sync' && req.method === 'POST') {
    try {
      const sync = require('./agent_mode/sheets/sync');
      const body = await readBody(req);
      const { teamCode } = body ? JSON.parse(body) : {};
      let result;
      if (teamCode) {
        result = await sync.pushSync(teamCode);
      } else {
        result = await sync.pushSyncAll();
      }
      log(`Sheets push sync: ${teamCode || 'all'}`);
      return jsonResp(res, result);
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }

  // POST /api/sheets/pull â€” Import edits from Sheets to CHERP
  if (url === '/api/sheets/pull' && req.method === 'POST') {
    try {
      const sync = require('./agent_mode/sheets/sync');
      const body = await readBody(req);
      const { teamCode } = body ? JSON.parse(body) : {};
      if (!teamCode) return jsonResp(res, { error: 'teamCode required' }, 400);
      const result = await sync.pullSync(teamCode);
      log(`Sheets pull sync: ${teamCode} â€” ${result.changes} changes`);
      return jsonResp(res, result);
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }

  // GET /api/sheets/status â€” Sync status for all crews
  if (url === '/api/sheets/status' && req.method === 'GET') {
    try {
      const sync = require('./agent_mode/sheets/sync');
      return jsonResp(res, sync.getSyncStatus());
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }

  // POST /api/sheets/create â€” Create new crew spreadsheet
  if (url === '/api/sheets/create' && req.method === 'POST') {
    try {
      const sync = require('./agent_mode/sheets/sync');
      const body = await readBody(req);
      const { teamCode, crewName } = JSON.parse(body);
      if (!teamCode) return jsonResp(res, { error: 'teamCode required' }, 400);
      const spreadsheetId = await sync.createCrewSheet(teamCode, crewName);
      log(`Created crew sheet: ${teamCode} â†’ ${spreadsheetId}`);
      return jsonResp(res, { spreadsheetId, url: `https://docs.google.com/spreadsheets/d/${spreadsheetId}` });
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }

  // 404
  jsonResp(res, { error: 'Not found' }, 404);
});

// â”€â”€ AUTO-EXECUTOR: Pick up queued tasks and run them â”€â”€
let autoExecRunning = false;
let agentsPaused = false;
async function autoExecuteQueued() {
  if (autoExecRunning || agentsPaused) return;
  autoExecRunning = true;
  try {
    const { Orchestrator } = await import('./agent_mode/core/orchestrator.js');
    const orch = new Orchestrator();
    const queued = orch.queue.getOfflineSafe();
    if (queued.length > 0) {
      const task = queued.sort((a, b) => a.priority - b.priority)[0]; // highest priority first
      if (!task.assignedAgent) orch._tryAutoAssign(task);
      if (task.assignedAgent) {
        log(`Auto-exec: ${task.objective.substring(0, 50)} â†’ ${task.assignedAgent}`);
        const result = await orch.executeTask(task.id);
        log(`Auto-exec result: ${result.success ? 'OK' : 'FAIL'} â€” ${task.id}${result.error ? ' â€” ' + result.error : ''}`);
      }
    }
  } catch (e) {
    log(`Auto-exec error: ${e.message}`);
  }
  autoExecRunning = false;
}

// Check for queued tasks every 30 seconds
setInterval(autoExecuteQueued, 30000);

// â”€â”€ SHEETS AUTO-SYNC: Push CHERP data to Google Sheets â”€â”€
let sheetsSyncRunning = false;
async function autoSheetsSync() {
  if (sheetsSyncRunning) return;
  sheetsSyncRunning = true;
  try {
    const sync = require('./agent_mode/sheets/sync');
    const auth = require('./agent_mode/sheets/auth');
    if (!auth.hasToken()) { sheetsSyncRunning = false; return; }
    const crews = sync.getConfiguredCrews();
    if (crews.length === 0) { sheetsSyncRunning = false; return; }
    const results = await sync.pushSyncAll();
    const crewCount = Object.keys(results).length;
    const errorCount = Object.values(results).filter(r => r.error).length;
    if (errorCount > 0) {
      log(`Sheets auto-sync: ${crewCount} crews, ${errorCount} errors`);
    } else {
      log(`Sheets auto-sync: ${crewCount} crews synced`);
    }
  } catch (e) {
    log(`Sheets auto-sync error: ${e.message}`);
  }
  sheetsSyncRunning = false;
}

// Auto-sync every 15 minutes
setInterval(autoSheetsSync, 900000);

// â”€â”€ API endpoint for Claude Code to dispatch tasks directly â”€â”€
// POST /api/dispatch â€” create + optionally execute a task

server.listen(PORT, '0.0.0.0', () => {
  console.log();
  console.log(`  \x1b[38;5;80mâ•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—\x1b[0m`);
  console.log(`  \x1b[38;5;80mâ•‘\x1b[0m  \x1b[38;5;231m\x1b[1mPIPE-R Server v4.0\x1b[0m                  \x1b[38;5;80mâ•‘\x1b[0m`);
  console.log(`  \x1b[38;5;80mâ• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£\x1b[0m`);
  console.log(`  \x1b[38;5;80mâ•‘\x1b[0m  Web UI:  \x1b[38;5;80mhttp://localhost:${PORT}\x1b[0m       \x1b[38;5;80mâ•‘\x1b[0m`);
  try {
    const ipOut = execSync('powershell -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike \'*Loopback*\' -and $_.PrefixOrigin -eq \'Dhcp\' } | Select-Object -First 1).IPAddress"', { encoding: 'utf8', timeout: 5000 }).trim();
    if (ipOut) {
      const padded = `http://${ipOut}:${PORT}`;
      console.log(`  \x1b[38;5;80mâ•‘\x1b[0m  Phone:   \x1b[38;5;80m${padded}\x1b[0m${' '.repeat(Math.max(0, 21 - padded.length))}\x1b[38;5;80mâ•‘\x1b[0m`);
    }
  } catch {}
  console.log(`  \x1b[38;5;80mâ•‘\x1b[0m  Remote:  \x1b[38;5;80mhttp://localhost:${PORT}/remote\x1b[0m\x1b[38;5;80mâ•‘\x1b[0m`);
  console.log(`  \x1b[38;5;80mâ•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•\x1b[0m`);
  console.log();
  log('Server started on :' + PORT);
});
