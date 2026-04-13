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

// ── Now playing via Windows SMTC (cached 1.5s) ──────────────────
let _nowPlayingCache = { ts: 0, data: null };
function getNowPlaying() {
  const now = Date.now();
  if (_nowPlayingCache.data && (now - _nowPlayingCache.ts) < 1500) return _nowPlayingCache.data;
  const script = join(ROOT, '.claude', 'bin', 'smtc-nowplaying.ps1');
  if (!existsSync(script)) {
    const data = { available: false, error: 'smtc-nowplaying.ps1 missing' };
    _nowPlayingCache = { ts: now, data };
    return data;
  }
  try {
    const out = execSync(
      `powershell -NoProfile -ExecutionPolicy Bypass -File "${script}"`,
      { encoding: 'utf8', timeout: 6000 }
    ).trim();
    const parsed = JSON.parse(out);
    // Detect likely Spotify app via source app user model id
    if (parsed.source && typeof parsed.source === 'string') {
      parsed.isSpotify = /spotify/i.test(parsed.source);
    }
    _nowPlayingCache = { ts: now, data: parsed };
    return parsed;
  } catch (e) {
    const data = { available: false, error: e.message };
    _nowPlayingCache = { ts: now, data };
    return data;
  }
}

// ── System metrics (cached 2s) ──────────────────────────────────
// Pulls CPU / RAM / GPU / ollama model state via native commands.
// Anything that times out or fails returns null; the UI renders "—".
let _metricsCache = { ts: 0, data: null };
async function getSystemMetrics() {
  const now = Date.now();
  if (_metricsCache.data && (now - _metricsCache.ts) < 2000) return _metricsCache.data;

  const safeExec = (cmd, timeout = 4000) => {
    try { return execSync(cmd, { encoding: 'utf8', timeout }).trim(); }
    catch { return ''; }
  };

  // CPU: name, max clock, logical cores, current %
  const cpuName = safeExec(`powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).Name"`);
  const cpuMaxMhz = parseInt(safeExec(`powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).MaxClockSpeed"`), 10) || null;
  const cpuCores = parseInt(safeExec(`powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).NumberOfLogicalProcessors"`), 10) || null;
  const cpuLoadRaw = safeExec(`powershell -NoProfile -Command "(Get-Counter '\\Processor(_Total)\\% Processor Time' -ErrorAction SilentlyContinue).CounterSamples.CookedValue"`, 5000);
  const cpuLoad = cpuLoadRaw ? parseFloat(cpuLoadRaw) : null;

  // RAM: used + total in GB
  const ramRaw = safeExec(`powershell -NoProfile -Command "$os = Get-CimInstance Win32_OperatingSystem; Write-Host ([math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1024/1024, 2)); Write-Host ([math]::Round($os.TotalVisibleMemorySize/1024/1024, 2))"`);
  const ramLines = ramRaw.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  const ramUsedGb = ramLines[0] ? parseFloat(ramLines[0]) : null;
  const ramTotalGb = ramLines[1] ? parseFloat(ramLines[1]) : null;

  // CPU temp via WMI thermal zone (often empty on AMD). Converted from deci-Kelvin.
  let cpuTempC = null;
  const thermRaw = safeExec(`powershell -NoProfile -Command "(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object -First 1).CurrentTemperature"`);
  if (thermRaw) {
    const kTenths = parseInt(thermRaw, 10);
    if (Number.isFinite(kTenths) && kTenths > 2000) cpuTempC = Math.round((kTenths / 10) - 273.15);
  }

  // GPU via nvidia-smi (AMD Radeon fallback not implemented — Ken's on NVIDIA).
  let gpu = null;
  const gpuRaw = safeExec(`nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw --format=csv,noheader,nounits`, 4000);
  if (gpuRaw) {
    const parts = gpuRaw.split(',').map(s => s.trim());
    if (parts.length >= 5) {
      gpu = {
        name: parts[0],
        tempC: Number(parts[1]) || null,
        utilPct: Number(parts[2]) || null,
        memUsedMb: Number(parts[3]) || null,
        memTotalMb: Number(parts[4]) || null,
        powerW: parts[5] ? Number(parts[5]) || null : null,
      };
    }
  }

  // Loaded Ollama models (`ollama ps` — evicted models vanish)
  const ollamaPsRaw = safeExec('ollama ps', 3000);
  const loadedModels = [];
  if (ollamaPsRaw) {
    const lines = ollamaPsRaw.split(/\r?\n/).slice(1).filter(l => l.trim());
    for (const line of lines) {
      const cols = line.split(/\s{2,}/).map(s => s.trim()).filter(Boolean);
      if (cols.length >= 4) {
        loadedModels.push({
          name: cols[0],
          id: cols[1],
          size: cols[2],
          processor: cols[3] || '',
          context: cols[4] || '',
          until: cols.slice(5).join(' ') || '',
        });
      }
    }
  }

  // Disk free for the project drive
  let disk = null;
  const diskRaw = safeExec(`powershell -NoProfile -Command "$d = Get-PSDrive -Name C; Write-Host ([math]::Round($d.Used/1gb, 2)); Write-Host ([math]::Round(($d.Used + $d.Free)/1gb, 2))"`);
  const diskLines = diskRaw.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  if (diskLines.length >= 2) {
    disk = { usedGb: parseFloat(diskLines[0]) || null, totalGb: parseFloat(diskLines[1]) || null };
  }

  const data = {
    timestamp: new Date().toISOString(),
    cpu: {
      name: cpuName || null,
      maxMhz: cpuMaxMhz,
      cores: cpuCores,
      loadPct: cpuLoad != null ? Math.round(cpuLoad * 10) / 10 : null,
      tempC: cpuTempC,
    },
    ram: { usedGb: ramUsedGb, totalGb: ramTotalGb },
    disk,
    gpu,
    ollama: { loaded: loadedModels, count: loadedModels.length },
  };

  _metricsCache = { ts: now, data };
  return data;
}

function readRuntimeConfig() {
  try {
    return JSON.parse(readFileSync(join(ROOT, 'agent_mode', 'config', 'runtime.json'), 'utf8'));
  } catch {
    return {
      mode: 'hybrid',
      maxRetries: 5,
      trainerAgentId: 'ken-ai:latest',
      remotePin: '0615',
      theme: {
        name: 'vaporwave-ops',
        trainerLabel: 'Ken AI',
        partyLabel: 'Agent Squad',
        workbenchLabel: 'Vaporwave Ops Deck',
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

  // Surface per-agent memory state (hasNotes, turnCount) on each agent so
  // the deck can render a marker on party cards whose notes have been tuned.
  try {
    const mem = await import('./agent_mode/core/memory.js');
    const stamp = (agent) => {
      if (!agent) return agent;
      const notes = mem.readNotes(agent.id) || '';
      const log = mem.readChatLog(agent.id, 500);
      agent.hasNotes = /\S/.test(notes) && !/^#[^\n]*\n\s*(Durable memory|$)/i.test(notes.trim().slice(0, 80));
      agent.notesLength = notes.length;
      agent.chatTurns = log.length;
      return agent;
    };
    if (dash.trainer) stamp(dash.trainer);
    if (dash.companion) stamp(dash.companion);
    if (Array.isArray(dash.party)) dash.party.forEach(stamp);
    if (Array.isArray(dash.agents)) dash.agents.forEach(stamp);
  } catch (e) {
    log('Memory stamp failed: ' + e.message);
  }

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
      name: 'vaporwave-ops',
      trainerLabel: 'Ken AI',
      partyLabel: 'Agent Squad',
      workbenchLabel: 'Vaporwave Ops Deck',
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

  // Direct downloads — serves files dropped into the input/ folder so
  // they're reachable from any tailnet browser. Used as a fallback when
  // Taildrop doesn't show up on the receiving side. URL form:
  //   /dl/<filename>   (e.g. /dl/hp-remote-v3.zip)
  // Only allows files with safe names from the input directory.
  if (url.startsWith('/dl/') && req.method === 'GET') {
    const requested = basename(decodeURIComponent(url.slice('/dl/'.length)));
    if (!/^[A-Za-z0-9._-]+$/.test(requested)) {
      res.writeHead(400);
      res.end('bad filename');
      return;
    }
    const filePath = join(ROOT, 'input', requested);
    if (!existsSync(filePath)) {
      res.writeHead(404);
      res.end('not found: ' + requested);
      return;
    }
    const ext = requested.toLowerCase().split('.').pop();
    const mime = ext === 'zip' ? 'application/zip'
      : ext === 'html' ? 'text/html; charset=utf-8'
      : ext === 'js' ? 'application/javascript; charset=utf-8'
      : ext === 'txt' || ext === 'md' ? 'text/plain; charset=utf-8'
      : ext === 'png' ? 'image/png'
      : ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg'
      : 'application/octet-stream';
    res.setHeader('Content-Disposition', `attachment; filename="${requested}"`);
    return serveBinaryFile(res, filePath, mime);
  }

  if (url.startsWith('/assets/pokedex/')) {
    const requested = basename(decodeURIComponent(url.slice('/assets/pokedex/'.length)));
    const ok = /^\d{4}(?:-icon|-icons)?\.png$/i.test(requested)
      || /^trainer(?:-[a-z0-9_-]+)?\.(png|jpg|jpeg|webp)$/i.test(requested);
    if (!ok) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }
    const ext = requested.toLowerCase().split('.').pop();
    const mime = ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg'
      : ext === 'webp' ? 'image/webp'
      : 'image/png';
    return serveBinaryFile(res, join(POKEDEX_ICON_DIR, requested), mime);
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

  // Auto-generate tasks — asks Claude to propose N new dispatchable tasks
  // for the squad and creates them via orch.createTask(). Used by the
  // deck's Auto Mode loop to keep the pipeline fed.
  if (url === '/api/auto/generate-tasks' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const payload = JSON.parse(body || '{}');
      const count = Math.max(1, Math.min(8, Number(payload.count) || 3));
      const { Orchestrator } = await import('./agent_mode/core/orchestrator.js');
      const orch = new Orchestrator();
      const roster = orch.registry.list().filter(a => a.available && !a.blocked);
      const lanes = roster.map(a => `  - ${a.id} (${a.specialistTrack || 'generalist'}): ${a.role || a.battleRole || ''}`).join('\n');

      // Walk the last 8 tasks so Claude doesn't repeat recent work.
      const recent = (orch.queue.tasks || []).slice(-8).map(t =>
        `  - [${t.status}] ${t.type}: ${(t.objective || '').slice(0, 100)}`
      ).join('\n') || '  (none)';

      const prompt = [
        'You are generating the next batch of dispatchable tasks for Ken\'s Pipe-R',
        'agent squad running a Node.js command center. Tasks get routed to specialist',
        'lanes automatically. Return a valid JSON array of EXACTLY ' + count + ' task',
        'objects, nothing else. No prose, no markdown fences, no commentary.',
        '',
        'Task shape:',
        '  { "type": "<task type>",',
        '    "objective": "<one-line goal>",',
        '    "scope": ["relative/path/to/file.ext"]   // optional, file(s) the agent should read',
        '  }',
        '',
        'Valid types: scan, index, draft_patch, draft_test, summarize,',
        '             memory_extract, learn, prompt_tune, general',
        '',
        'Available specialist lanes (the orchestrator picks one):',
        lanes,
        '',
        'Recent tasks (do not repeat):',
        recent,
        '',
        'Rules:',
        '- Each objective must be specific, concrete, and actionable.',
        '- Favor scan / summarize / draft_test / learn — they complete fast.',
        '- draft_patch tasks must scope a real file under agent_mode/ or pipe-r.html.',
        '- Do NOT propose tasks that require Ken\'s manual approval, opinions, or deploys.',
        '- Output MUST start with [ and end with ] — no prose.',
      ].join('\n');

      const { spawnSync } = require('child_process');
      const run = spawnSync('claude', ['-p'], {
        input: prompt,
        encoding: 'utf8',
        timeout: 90000,
        maxBuffer: 2 * 1024 * 1024,
        shell: true,
      });
      if (run.error) throw run.error;
      if (run.status !== 0 && !run.stdout) {
        throw new Error(`claude exited ${run.status}: ${(run.stderr || '').trim().slice(0, 200)}`);
      }
      const raw = String(run.stdout || '')
        .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
        .replace(/\r/g, '')
        .trim();

      // Pull the first [ ... ] block out of the response (Claude sometimes
      // wraps JSON in ```json fences or prefixes it with commentary).
      const firstBracket = raw.indexOf('[');
      const lastBracket  = raw.lastIndexOf(']');
      if (firstBracket < 0 || lastBracket <= firstBracket) {
        return jsonResp(res, { ok: false, error: 'no JSON array in claude output', raw: raw.slice(0, 400) }, 500);
      }
      let proposed;
      try {
        proposed = JSON.parse(raw.slice(firstBracket, lastBracket + 1));
      } catch (e) {
        return jsonResp(res, { ok: false, error: 'JSON parse: ' + e.message, raw: raw.slice(0, 400) }, 500);
      }
      if (!Array.isArray(proposed)) {
        return jsonResp(res, { ok: false, error: 'expected array' }, 500);
      }

      const created = [];
      for (const p of proposed.slice(0, count)) {
        if (!p || typeof p !== 'object' || !p.objective) continue;
        const task = orch.createTask({
          type: p.type || 'general',
          objective: String(p.objective).slice(0, 500),
          scope: Array.isArray(p.scope) ? p.scope.slice(0, 5) : [],
          priority: 3,
          requiresClaudeReview: true,
        });
        created.push({ id: task.id, type: task.type, objective: task.objective.slice(0, 80), assignedAgent: task.assignedAgent });
      }
      log(`Auto-generate: ${created.length} new tasks from claude`);
      return jsonResp(res, { ok: true, count: created.length, created });
    } catch (e) {
      return jsonResp(res, { ok: false, error: e.message }, 500);
    }
  }

  // Auto-review — walks tasks sitting in waiting_for_claude status, asks
  // Claude Code to grade each one via `claude -p "..."`, and calls
  // orch.reviewTask(). Unsticks the squad when Ken is away and the 30s
  // auto-exec loop has nothing to pick up because everything is blocked
  // on human review. Cap per click so Ken keeps control.
  if (url === '/api/review/auto-run' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const payload = JSON.parse(body || '{}');
      const cap = Math.max(1, Math.min(20, Number(payload.max) || 6));
      const { Orchestrator } = await import('./agent_mode/core/orchestrator.js');
      const orch = new Orchestrator();
      const packet = orch.buildClaudeReentryPacket();
      const pending = (packet.tasks || packet.pending || packet.queue || []).filter(t => {
        const full = orch.queue.get(t.id);
        return full && full.status === 'waiting_for_claude';
      });
      // Fallback: walk the raw queue directly if the reentry packet shape surprises us.
      const targets = pending.length
        ? pending
        : orch.queue.tasks.filter(t => t.status === 'waiting_for_claude');
      const slice = targets.slice(0, cap);

      const results = [];
      for (const t of slice) {
        const full = orch.queue.get(t.id) || t;
        const output = String(full.output || full.result || '').slice(0, 2000);
        const prompt = [
          'You are reviewing a dispatched agent task for Ken\'s Pipe-R squad.',
          'Return EXACTLY one token on the first line: APPROVE or REJECT.',
          'Then one short line with the reason (under 80 chars).',
          '',
          'Rules:',
          '- APPROVE if the output actually addresses the objective and is not garbage.',
          '- APPROVE if the output is short but in-voice and on-task.',
          '- REJECT if the output is empty, a refusal, wall of unrelated text, or wrong domain.',
          '- Do NOT approve plumbing/pokemon analogies or "as an AI" disclaimers.',
          '',
          `Task type: ${full.type || 'general'}`,
          `Assigned agent: ${full.assignedAgent || '(auto)'}`,
          `Objective: ${(full.objective || '').slice(0, 400)}`,
          '',
          'Output:',
          output || '(no output captured)',
        ].join('\n');

        // Pipe the prompt via stdin to avoid command-line length limits
        // and PowerShell quoting corruption — same pattern executor.js
        // uses for ollama. `claude -p` reads the prompt from stdin when
        // no positional arg is passed.
        const { spawnSync } = require('child_process');
        let verdictLine = '';
        let reason = '';
        try {
          const run = spawnSync('claude', ['-p'], {
            input: prompt,
            encoding: 'utf8',
            timeout: 120000,
            maxBuffer: 2 * 1024 * 1024,
            shell: true,
          });
          if (run.error) throw run.error;
          if (run.status !== 0 && !run.stdout) {
            throw new Error(`claude exited ${run.status}: ${(run.stderr || '').trim().slice(0, 200)}`);
          }
          const clean = String(run.stdout || '')
            .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
            .replace(/\r/g, '')
            .trim();
          const lines = clean.split('\n').map(l => l.trim()).filter(Boolean);
          verdictLine = (lines[0] || '').toUpperCase();
          reason = (lines[1] || '').slice(0, 200);
          const approved = verdictLine.includes('APPROVE');
          orch.reviewTask(full.id, approved, reason || (approved ? 'claude auto-approve' : 'claude auto-reject'));
          results.push({ id: full.id, agent: full.assignedAgent, verdict: approved ? 'APPROVE' : 'REJECT', reason });
        } catch (e) {
          results.push({ id: full.id, agent: full.assignedAgent, error: e.message.slice(0, 200) });
        }
      }

      log(`Auto-review: ${results.filter(r => r.verdict === 'APPROVE').length} approved, ${results.filter(r => r.verdict === 'REJECT').length} rejected, ${results.filter(r => r.error).length} errored of ${results.length}`);
      return jsonResp(res, {
        count: results.length,
        remaining: Math.max(0, targets.length - slice.length),
        results,
      });
    } catch (e) {
      return jsonResp(res, { error: e.message }, 500);
    }
  }

  // Run everything sitting in the queue — processes queued tasks through
  // the executor one at a time and returns a compact summary. Wired to the
  // deck's "Run Queue" button so Ken can punch the work forward manually
  // instead of waiting for the 30s auto-exec loop.
  if (url === '/api/queue/run' && req.method === 'POST') {
    try {
      const { Orchestrator } = await import('./agent_mode/core/orchestrator.js');
      const orch = new Orchestrator();
      const dash = orch.dashboard();
      const queued = (dash.tasks || []).filter(t => t.status === 'queued');
      const ran = [];
      for (const t of queued.slice(0, 10)) { // cap 10 per click
        try {
          const result = await orch.executeTask(t.id);
          ran.push({ id: t.id, agent: t.assignedAgent, ok: true, elapsed: result?.elapsed });
        } catch (e) {
          ran.push({ id: t.id, agent: t.assignedAgent, ok: false, error: e.message });
        }
      }
      log(`Queue run: ${ran.length} task(s) processed, ${ran.filter(r => r.ok).length} ok`);
      return jsonResp(res, { count: ran.length, ran });
    } catch (e) {
      return jsonResp(res, { error: e.message }, 500);
    }
  }

  // === Live Test Mode ================================================
  // v0: runs a scripted scenario against a real CHERP instance, captures
  // the REST API responses, asks an observer agent for a debrief, and
  // persists the full round to agent_mode/livetest/rounds/<id>.json.
  if (url === '/api/livetest/scenarios' && req.method === 'GET') {
    try {
      const lt = await import('./agent_mode/core/livetest.js');
      return jsonResp(res, { scenarios: lt.listScenarios() });
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }
  if (url === '/api/livetest/rounds' && req.method === 'GET') {
    try {
      const lt = await import('./agent_mode/core/livetest.js');
      return jsonResp(res, { rounds: lt.listRounds() });
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }
  if (url === '/api/livetest/results' && req.method === 'GET') {
    try {
      const lt = await import('./agent_mode/core/livetest.js');
      return jsonResp(res, { results: lt.listResults({ limit: 100 }) });
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }
  if (url.startsWith('/api/livetest/rounds/') && req.method === 'GET') {
    try {
      const id = decodeURIComponent(url.slice('/api/livetest/rounds/'.length));
      const lt = await import('./agent_mode/core/livetest.js');
      const round = lt.getRound(id);
      if (!round) return jsonResp(res, { error: 'round not found: ' + id }, 404);
      return jsonResp(res, round);
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }
  if (url === '/api/livetest/start' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const payload = JSON.parse(body || '{}');
      const lt = await import('./agent_mode/core/livetest.js');
      const mode = payload.mode === 'v1' ? 'v1' : 'v0';
      log(`LiveTest start (${mode}): ${payload.scenarioId} → ${payload.instanceUrl || '(default)'}`);
      let round;
      if (mode === 'v1') {
        round = await lt.runRoundV1({
          scenarioId: payload.scenarioId,
          instanceUrl: payload.instanceUrl,
          cleanup: payload.cleanup !== false,
          teamCode: payload.teamCode,
        });
      } else {
        round = await lt.runRound({
          scenarioId: payload.scenarioId,
          instanceUrl: payload.instanceUrl,
          observer: payload.observer || 'llama3.1:8b',
          cleanup: payload.cleanup !== false,
          teamCode: payload.teamCode,
        });
      }
      log(`LiveTest done: ${round.id} ops=${round.operations.length} ok=${round.ok}`);
      return jsonResp(res, round);
    } catch (e) {
      log(`LiveTest error: ${e.message}`);
      return jsonResp(res, { error: e.message }, 500);
    }
  }

  // Now playing — Windows SMTC session bridge. Cached 1.5s.
  if (url === '/api/now-playing' && req.method === 'GET') {
    try {
      const np = getNowPlaying();
      return jsonResp(res, np);
    } catch (e) {
      return jsonResp(res, { available: false, error: e.message });
    }
  }

  // Volume — GET current system + Spotify app volumes, POST { target, value }
  // to set. target = 'system' | 'app'. Uses Core Audio API via volume.ps1.
  if (url === '/api/volume' && req.method === 'GET') {
    try {
      const script = join(ROOT, '.claude', 'bin', 'volume.ps1');
      if (!existsSync(script)) return jsonResp(res, { ok: false, error: 'volume.ps1 missing' }, 500);
      const out = execSync(
        `powershell -NoProfile -ExecutionPolicy Bypass -File "${script}" get`,
        { encoding: 'utf8', timeout: 8000 }
      ).trim();
      try { return jsonResp(res, JSON.parse(out)); }
      catch { return jsonResp(res, { ok: false, raw: out.slice(0, 200) }); }
    } catch (e) {
      return jsonResp(res, { ok: false, error: e.message }, 500);
    }
  }
  if (url === '/api/volume' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { target, value, app } = JSON.parse(body || '{}');
      if (!['system', 'app'].includes(target)) return jsonResp(res, { ok: false, error: 'target must be system|app' }, 400);
      const v = Math.max(0, Math.min(1, Number(value)));
      if (!Number.isFinite(v)) return jsonResp(res, { ok: false, error: 'value must be 0..1' }, 400);
      const script = join(ROOT, '.claude', 'bin', 'volume.ps1');
      const appName = app || 'Spotify';
      const cmd = target === 'system'
        ? `powershell -NoProfile -ExecutionPolicy Bypass -File "${script}" set system -Value ${v}`
        : `powershell -NoProfile -ExecutionPolicy Bypass -File "${script}" set-app -Target "${appName.replace(/"/g,'')}" -Value ${v}`;
      const out = execSync(cmd, { encoding: 'utf8', timeout: 8000 }).trim();
      try { return jsonResp(res, JSON.parse(out)); }
      catch { return jsonResp(res, { ok: false, raw: out.slice(0, 200) }); }
    } catch (e) {
      return jsonResp(res, { ok: false, error: e.message }, 500);
    }
  }

  // Now playing transport control — POST { action } with play/pause/toggle/next/prev
  if (url === '/api/now-playing/control' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { action } = JSON.parse(body || '{}');
      const valid = ['play', 'pause', 'toggle', 'next', 'prev'];
      if (!valid.includes(action)) return jsonResp(res, { error: 'action must be one of ' + valid.join(', ') }, 400);
      const script = join(ROOT, '.claude', 'bin', 'smtc-control.ps1');
      if (!existsSync(script)) return jsonResp(res, { error: 'smtc-control.ps1 missing' }, 500);
      const out = execSync(
        `powershell -NoProfile -ExecutionPolicy Bypass -File "${script}" ${action}`,
        { encoding: 'utf8', timeout: 5000 }
      ).trim();
      // Invalidate now-playing cache so the next GET picks up the new state.
      _nowPlayingCache = { ts: 0, data: null };
      try { return jsonResp(res, JSON.parse(out)); }
      catch { return jsonResp(res, { raw: out }); }
    } catch (e) {
      return jsonResp(res, { ok: false, error: e.message }, 500);
    }
  }

  // Macro — sends a real OS-level keystroke to the currently foreground
  // window via System.Windows.Forms.SendKeys. Used by the deck's AFK mode
  // to punch Enter on whatever window Ken has focused (Claude Code
  // terminal, a game, a chat app, whatever) every N seconds.
  if (url === '/api/macro/send' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { key } = JSON.parse(body || '{}');
      // Valid SendKeys tokens: "{ENTER}" "{TAB}" "{F5}" " " "a" etc.
      // Whitelist common AFK keys so random strings can't be injected.
      const map = {
        'enter': '{ENTER}',
        'space': ' ',
        'tab':   '{TAB}',
        'f15':   '{F15}',
        'esc':   '{ESC}',
      };
      const token = map[String(key || 'enter').toLowerCase()] || '{ENTER}';
      // PowerShell SendKeys. Single-quoted to avoid escaping, token is
      // from the whitelist so no injection risk.
      const cmd = `Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('${token}')`;
      execSync(
        `powershell -NoProfile -ExecutionPolicy Bypass -Command "${cmd}"`,
        { encoding: 'utf8', timeout: 3000 }
      );
      return jsonResp(res, { ok: true, key: token });
    } catch (e) {
      return jsonResp(res, { ok: false, error: e.message }, 500);
    }
  }

  // Shell runner — executes a PowerShell command and streams the result.
  // Local-only usage: server binds to 0.0.0.0 but assumption is LAN trust.
  if (url === '/api/shell/run' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { command } = JSON.parse(body || '{}');
      if (!command || typeof command !== 'string') {
        return jsonResp(res, { ok: false, error: 'command required' }, 400);
      }
      let trimmed = command.slice(0, 4000); // hard cap
      const cmdText = trimmed.trim();
      const firstToken = cmdText.split(/\s+/)[0] || '';

      // Auto-rewrite `claude <anything>` into `claude -p "<anything>"`.
      // Lets the shell feel like a Claude REPL: type a prompt, get a
      // response. Only rewrites when there's no -p/--print already and
      // there's actually something to ask. Bare `claude` still returns
      // the hint below.
      if (firstToken === 'claude' && cmdText !== 'claude') {
        const rest = cmdText.slice('claude'.length).trim();
        const alreadyPrint = /(^|\s)(-p|--print)(\s|$)/.test(rest);
        if (!alreadyPrint) {
          const safe = rest.replace(/`/g, '``').replace(/"/g, '`"');
          trimmed = `claude -p "${safe}"`;
        }
      }

      // Guard against interactive-only CLIs that bomb with no TTY: they'd
      // hang or return cryptic "Input must be provided" errors. Suggest
      // the one-shot form instead.
      const interactives = {
        'claude':  'Type `claude your prompt here` and pipe-r will wrap it as `claude -p "..."` automatically.',
        'node':    'Use `node -e "expression"` or `node script.js`.',
        'python':  'Use `python -c "expression"` or `python script.py`.',
        'python3': 'Use `python3 -c "expression"` or `python3 script.py`.',
        'irb':     'IRB is interactive-only — won\'t run here.',
        'pwsh':    'Already in PowerShell — drop the outer invocation.',
      };
      if (interactives[firstToken] && cmdText === firstToken) {
        return jsonResp(res, {
          ok: false,
          exitCode: 2,
          elapsed: 0,
          stdout: '',
          stderr: `[pipe-r shell] "${firstToken}" is interactive-only. ${interactives[firstToken]}`,
        });
      }
      const started = Date.now();
      let out = '';
      let err = '';
      let exitCode = 0;
      try {
        out = execSync(
          `powershell -NoProfile -ExecutionPolicy Bypass -Command ${JSON.stringify(trimmed)}`,
          { encoding: 'utf8', timeout: 30000, maxBuffer: 4 * 1024 * 1024, cwd: ROOT }
        );
      } catch (e) {
        err = (e.stderr || '') + (e.stdout || '');
        exitCode = e.status || 1;
        out = e.stdout || '';
      }
      const elapsed = Date.now() - started;
      log(`Shell: ${trimmed.slice(0, 60)} → ${exitCode === 0 ? 'ok' : 'err ' + exitCode} (${elapsed}ms)`);
      return jsonResp(res, {
        ok: exitCode === 0,
        exitCode,
        elapsed,
        stdout: String(out || '').slice(0, 200000),
        stderr: String(err || '').slice(0, 50000),
      });
    } catch (e) {
      return jsonResp(res, { ok: false, error: e.message }, 500);
    }
  }

  // Wallpaper color extraction — pulls dominant colors from the current
  // Windows desktop wallpaper so the deck can auto-theme off it. Cached 60s.
  if (url === '/api/wallpaper-colors' && req.method === 'GET') {
    try {
      const script = join(ROOT, '.claude', 'bin', 'wallpaper-colors.ps1');
      if (!existsSync(script)) return jsonResp(res, { ok: false, error: 'script missing' }, 500);
      const out = execSync(
        `powershell -NoProfile -ExecutionPolicy Bypass -File "${script}"`,
        { encoding: 'utf8', timeout: 20000 }
      ).trim();
      try { return jsonResp(res, JSON.parse(out)); }
      catch { return jsonResp(res, { ok: false, error: 'parse failed', raw: out.slice(0, 200) }, 500); }
    } catch (e) {
      return jsonResp(res, { ok: false, error: e.message }, 500);
    }
  }

  // Steam library — list installed games from libraryfolders.vdf + ACF manifests
  if (url === '/api/steam/library' && req.method === 'GET') {
    try {
      const steam = await import('./agent_mode/core/steam.js');
      const games = steam.listSteamGames({ limit: 300 });
      return jsonResp(res, { count: games.length, games });
    } catch (e) {
      return jsonResp(res, { error: e.message }, 500);
    }
  }

  // System metrics — CPU, RAM, GPU, loaded ollama models
  // Cached 2s so the deck's 3s poll doesn't thrash PowerShell.
  if (url === '/api/metrics' && req.method === 'GET') {
    try {
      const metrics = await getSystemMetrics();
      return jsonResp(res, metrics);
    } catch (e) {
      return jsonResp(res, { error: e.message }, 500);
    }
  }

  // Per-agent training log viewer — GET last N entries for this agent
  if (url.startsWith('/api/chat/') && url.includes('/training') && req.method === 'GET') {
    try {
      const rest = url.slice('/api/chat/'.length);
      const agentId = decodeURIComponent(rest.split('/training')[0]);
      const agents = JSON.parse(readFileSync(join(ROOT, 'agent_mode', 'config', 'agents.json'), 'utf8'));
      const agent = agents.find(a => a.id === agentId);
      if (!agent) return jsonResp(res, { error: 'agent not found: ' + agentId }, 404);
      const file = join(ROOT, 'agent_mode', 'training', 'training-log.jsonl');
      if (!existsSync(file)) return jsonResp(res, { agentId, entries: [] });
      const raw = readFileSync(file, 'utf8').split('\n').filter(Boolean);
      const needle = agent.base || agent.id;
      const entries = [];
      for (let i = raw.length - 1; i >= 0 && entries.length < 40; i--) {
        try {
          const obj = JSON.parse(raw[i]);
          if (obj.model === needle || obj.model === agent.id) entries.push({ lineNo: i, ...obj });
        } catch {}
      }
      return jsonResp(res, { agentId, count: entries.length, entries });
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }

  // Mark a training entry approved/rejected for curation
  if (url === '/api/training/review' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const { lineNo, approved, notes } = JSON.parse(body || '{}');
      if (!Number.isInteger(lineNo)) return jsonResp(res, { error: 'lineNo required' }, 400);
      const file = join(ROOT, 'agent_mode', 'training', 'training-log.jsonl');
      if (!existsSync(file)) return jsonResp(res, { error: 'training-log.jsonl missing' }, 404);
      const lines = readFileSync(file, 'utf8').split('\n');
      if (lineNo < 0 || lineNo >= lines.length || !lines[lineNo]) return jsonResp(res, { error: 'invalid lineNo' }, 400);
      let obj;
      try { obj = JSON.parse(lines[lineNo]); } catch { return jsonResp(res, { error: 'could not parse line' }, 500); }
      obj.reviewed = true;
      obj.approved = !!approved;
      if (notes) obj.reviewNotes = String(notes).slice(0, 500);
      obj.reviewedAt = new Date().toISOString();
      lines[lineNo] = JSON.stringify(obj);
      writeFileSync(file, lines.join('\n'));
      log(`Training review: line ${lineNo} ${obj.approved ? 'APPROVED' : 'REJECTED'}`);
      return jsonResp(res, { result: 'Reviewed', lineNo, approved: obj.approved });
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }

  // Per-agent chat log purge — DELETE wipes chat-log.jsonl for that agent
  if (url.startsWith('/api/chat/') && url.endsWith('/log') && req.method === 'DELETE') {
    try {
      const agentId = decodeURIComponent(url.slice('/api/chat/'.length, -'/log'.length));
      const agents = JSON.parse(readFileSync(join(ROOT, 'agent_mode', 'config', 'agents.json'), 'utf8'));
      const agent = agents.find(a => a.id === agentId);
      if (!agent) return jsonResp(res, { error: 'agent not found: ' + agentId }, 404);
      const mem = await import('./agent_mode/core/memory.js');
      mem.clearChatLog(agentId);
      log(`Chat log cleared: ${agentId}`);
      return jsonResp(res, { result: 'Chat log cleared', agentId });
    } catch (e) {
      return jsonResp(res, { error: e.message }, 500);
    }
  }

  // Per-agent notes editor — PUT { notes } overwrites notes.md
  if (url.startsWith('/api/chat/') && url.endsWith('/notes') && req.method === 'PUT') {
    const body = await readBody(req);
    try {
      const agentId = decodeURIComponent(url.slice('/api/chat/'.length, -'/notes'.length));
      const payload = JSON.parse(body || '{}');
      const notes = String(payload.notes ?? '');
      const agents = JSON.parse(readFileSync(join(ROOT, 'agent_mode', 'config', 'agents.json'), 'utf8'));
      const agent = agents.find(a => a.id === agentId);
      if (!agent) return jsonResp(res, { error: 'agent not found: ' + agentId }, 404);
      const mem = await import('./agent_mode/core/memory.js');
      mem.ensureMemoryDir(agent);
      const path = join(ROOT, 'agent_mode', 'memories', String(agentId).replace(/[:/\\?*"<>|]/g, '-'), 'notes.md');
      writeFileSync(path, notes, 'utf8');
      log(`Notes updated: ${agentId} (${notes.length} bytes)`);
      return jsonResp(res, { result: 'Notes saved', agentId, length: notes.length });
    } catch (e) {
      return jsonResp(res, { error: e.message }, 500);
    }
  }

  // Per-agent chat — GET history, POST sends a turn
  if (url.startsWith('/api/chat/') && req.method === 'GET') {
    try {
      const agentId = decodeURIComponent(url.slice('/api/chat/'.length).split('?')[0]);
      const mem = await import('./agent_mode/core/memory.js');
      const agents = JSON.parse(readFileSync(join(ROOT, 'agent_mode', 'config', 'agents.json'), 'utf8'));
      const agent = agents.find(a => a.id === agentId);
      if (!agent) return jsonResp(res, { error: 'agent not found: ' + agentId }, 404);
      mem.ensureMemoryDir(agent);
      return jsonResp(res, {
        agentId,
        history: mem.readChatLog(agentId, 200),
        notes: mem.readNotes(agentId),
      });
    } catch (e) { return jsonResp(res, { error: e.message }, 400); }
  }

  if (url === '/api/chat' && req.method === 'POST') {
    const body = await readBody(req);
    try {
      const payload = JSON.parse(body || '{}');
      const agentId = payload.agentId;
      const message = String(payload.message || '').trim();
      if (!agentId) return jsonResp(res, { error: 'agentId required' }, 400);
      if (!message) return jsonResp(res, { error: 'message required' }, 400);

      const agents = JSON.parse(readFileSync(join(ROOT, 'agent_mode', 'config', 'agents.json'), 'utf8'));
      const agent = agents.find(a => a.id === agentId);
      if (!agent) return jsonResp(res, { error: 'agent not found: ' + agentId }, 404);

      const mem = await import('./agent_mode/core/memory.js');
      mem.ensureMemoryDir(agent);
      const ctx = mem.buildChatContext(agent, { historyTurns: 12 });

      // Build a lightweight SYSTEM block. The agent's Modelfile already
      // carries its baked-in personality; these are the runtime additions.
      const systemBlocks = [];
      if (ctx.charter && ctx.charter.trim()) {
        systemBlocks.push('### CHARTER\n' + ctx.charter.trim());
      }
      if (ctx.notes && ctx.notes.trim()) {
        systemBlocks.push('### PERSISTENT NOTES\n' + ctx.notes.trim());
      }
      const systemBlock = systemBlocks.join('\n\n');

      const transcript = ctx.history
        .filter(m => m && m.role && m.content)
        .map(m => `${m.role === 'user' ? 'KEN' : 'AGENT'}: ${m.content}`)
        .join('\n');

      const finalPrompt = [
        systemBlock,
        transcript ? '### RECENT TURNS\n' + transcript : '',
        `### CURRENT TURN\nKEN: ${message}\nAGENT:`,
      ].filter(Boolean).join('\n\n');

      // Append user turn up-front so history persists even if the model errors.
      mem.appendChat(agentId, 'user', message);

      const { spawnSync } = require('child_process');
      const run = spawnSync('ollama', ['run', agent.base || agent.id], {
        input: finalPrompt,
        encoding: 'utf8',
        timeout: 120000,
        maxBuffer: 8 * 1024 * 1024,
      });

      if (run.error || (run.status !== 0 && !run.stdout)) {
        const errMsg = (run.error && run.error.message) || run.stderr || 'ollama run failed';
        mem.appendChat(agentId, 'system', 'ERROR: ' + errMsg);
        return jsonResp(res, { error: errMsg }, 500);
      }

      // ollama run emits spinner control codes (ANSI CSI + bracketed paste
       // mode) interleaved with model output. Strip them before storing so
       // chat history doesn't carry terminal noise into notes / training log.
      const stripAnsi = (s) => String(s || '')
        .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')  // CSI sequences
        .replace(/\u001b\][^\u0007]*\u0007/g, '')     // OSC sequences
        .replace(/\r/g, '');
      const reply = stripAnsi(run.stdout).trim();
      mem.appendChat(agentId, 'assistant', reply);

      // Feed the shared training log so chat turns become fine-tune corpus
      // for Ken AI v2. Mirrors executor._recordTraining's entry shape so
      // curate.js can process both dispatch + chat entries uniformly.
      try {
        const trainingDir = join(ROOT, 'agent_mode', 'training');
        if (!existsSync(trainingDir)) mkdirSync(trainingDir, { recursive: true });
        const entry = {
          timestamp: new Date().toISOString(),
          taskId: 'chat-' + Date.now().toString(36),
          model: agent.base || agent.id,
          taskType: 'chat',
          attempt: 1,
          objective: message.substring(0, 500),
          prompt: finalPrompt.substring(0, 2000),
          response: reply.substring(0, 5000),
          success: reply.length > 0,
          elapsed: 0,
          reviewed: false,
          approved: null,
        };
        appendFileSync(join(trainingDir, 'training-log.jsonl'), JSON.stringify(entry) + '\n');
      } catch {}

      log(`Chat ${agentId}: ${message.slice(0, 60)} -> ${reply.slice(0, 60)}`);
      return jsonResp(res, { agentId, reply });
    } catch (e) {
      return jsonResp(res, { error: e.message }, 500);
    }
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

  // ──────────────────────────────────────────────────────────
  // NEST BRIDGE — Piper can trigger Bird's Nest customer builds
  //              and read the customer registry. Every build
  //              pulls fresh from HesKenY/CHERP main via Nest's
  //              _fetchLatestCherp() step.
  // ──────────────────────────────────────────────────────────

  // GET /api/nest/customers — list registry with days-remaining
  if (url === '/api/nest/customers' && req.method === 'GET') {
    try {
      const custFile = join(ROOT, 'agent_mode', 'config', 'customers.json');
      const customers = existsSync(custFile) ? JSON.parse(readFileSync(custFile, 'utf8')) : [];
      const now = Date.now();
      const enriched = customers.map(c => {
        const expires = c.expiresAt ? new Date(c.expiresAt).getTime() : null;
        const daysRemaining = expires ? Math.max(0, Math.ceil((expires - now) / 86400000)) : null;
        const expired = expires ? now > expires : false;
        return { ...c, daysRemaining, expired };
      });
      return jsonResp(res, { customers: enriched });
    } catch (e) { return jsonResp(res, { error: e.message }, 500); }
  }

  // POST /api/nest/build — fire a Nest build for a customer
  // body: { slug, name, admin: { name }, branding: { companyName, primaryColor, secondaryColor },
  //          modules: { ... }, supabase: { url, anonKey, serviceKey } }
  if (url === '/api/nest/build' && req.method === 'POST') {
    try {
      const body = await readBody(req);
      const config = JSON.parse(body);
      if (!config.instance || !config.instance.slug) {
        return jsonResp(res, { error: 'instance.slug required' }, 400);
      }
      const nestPath = join(ROOT, 'nest', 'src', 'builder', 'instance-builder.js');
      if (!existsSync(nestPath)) {
        return jsonResp(res, { error: 'Nest not cloned at nest/. Run NEST.bat to clone.' }, 503);
      }
      // Pivot cwd so Nest's __dirname-relative paths resolve correctly.
      const originalCwd = process.cwd();
      const nestRoot = join(ROOT, 'nest');
      process.chdir(nestRoot);
      let result;
      try {
        const { InstanceBuilder } = await import('./nest/src/builder/instance-builder.js');
        const builder = new InstanceBuilder(config);
        result = await builder.build((step, i, n) => {
          log(`Nest build [${config.instance.slug}] ${i + 1}/${n}: ${step}`);
        });
      } finally {
        process.chdir(originalCwd);
      }

      // Record in customers.json
      const custFile = join(ROOT, 'agent_mode', 'config', 'customers.json');
      const customers = existsSync(custFile) ? JSON.parse(readFileSync(custFile, 'utf8')) : [];
      const buildAt = new Date().toISOString();
      const expiresAt = new Date(Date.now() + 90 * 86400000).toISOString();
      const existing = customers.findIndex(c => c.slug === config.instance.slug);
      const record = {
        id: config.instance.slug,
        slug: config.instance.slug,
        name: config.instance.name || config.instance.slug,
        status: 'active',
        buildAt,
        expiresAt,
        sourceCommit: builder?.sourceCommit || null,
        sourceCommitShort: builder?.sourceCommitShort || null,
        sourceCommitMessage: builder?.sourceCommitMessage || null,
        buildDir: result?.buildDir || null,
        zipPath: result?.zipPath || null,
        modules: config.modules || {},
        company: config.branding?.companyName || '',
        adminName: config.admin?.name || '',
        notes: 'Built via /api/nest/build',
      };
      if (existing >= 0) {
        record.notes = 'Rebuilt via /api/nest/build (replaced prior entry)';
        customers[existing] = record;
      } else {
        customers.push(record);
      }
      writeFileSync(custFile, JSON.stringify(customers, null, 2));
      log(`Nest build complete: ${config.instance.slug} → ${result?.zipPath || result?.buildDir}`);

      return jsonResp(res, {
        customer: record,
        buildLog: result?.log || [],
      });
    } catch (e) {
      log(`Nest build failed: ${e.message}`);
      return jsonResp(res, { error: e.message, stack: e.stack }, 500);
    }
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

// Scaffold per-agent memory directories at boot (no-op if they already exist)
try {
  const agentsFile = join(ROOT, 'agent_mode', 'config', 'agents.json');
  if (existsSync(agentsFile)) {
    const agents = JSON.parse(readFileSync(agentsFile, 'utf8'));
    const mem = await import('./agent_mode/core/memory.js');
    const created = mem.ensureAllMemoryDirs(agents);
    log('Memory dirs ready: ' + created.map(c => c.id).join(', '));
  }
} catch (e) {
  log('Memory scaffold failed: ' + e.message);
}

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
