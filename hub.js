#!/usr/bin/env node
/**
 * PIPE-R v4.0 — Windows-Style Command Center
 * Professional terminal UI for project orchestration
 * Button-driven. No typing required.
 *
 * Folders:
 *   input/      — Drop files here for processing
 *   output/     — Finished deliverables
 *   workspace/  — Active in-progress work
 *   staging/    — Ready for review
 */

import { createInterface } from 'readline';
import { readdirSync, readFileSync, statSync, existsSync, mkdirSync, renameSync, unlinkSync, appendFileSync, writeFileSync } from 'fs';
import { join, basename, extname } from 'path';
import { execSync } from 'child_process';

const ROOT = process.cwd();
const DIRS = {
  input:     join(ROOT, 'input'),
  output:    join(ROOT, 'output'),
  workspace: join(ROOT, 'workspace'),
  staging:   join(ROOT, 'staging'),
};
const CLAUDE_DIR = join(ROOT, '.claude');
const LOG_DIR = join(CLAUDE_DIR, 'logs');
const LOG_FILE = join(LOG_DIR, 'hub.log');
const TASKS_FILE = join(ROOT, 'agents', 'tasks.json');
const BUSINESS_FILE = join(ROOT, 'agents', 'business.json');
const PATENT_FILE = join(ROOT, 'agents', 'patent.json');

Object.values(DIRS).forEach(d => { if (!existsSync(d)) mkdirSync(d, { recursive: true }); });
if (!existsSync(join(ROOT, 'agents'))) mkdirSync(join(ROOT, 'agents'), { recursive: true });
if (!existsSync(CLAUDE_DIR)) mkdirSync(CLAUDE_DIR, { recursive: true });
if (!existsSync(LOG_DIR)) mkdirSync(LOG_DIR, { recursive: true });

// ═══════════════════════════════════════════════════════
// COLORS — Modern 2026 Dark Theme
// ═══════════════════════════════════════════════════════
const c = {
  reset:   '\x1b[0m',
  bold:    '\x1b[1m',
  dim:     '\x1b[2m',
  under:   '\x1b[4m',
  italic:  '\x1b[3m',
  // UI chrome — gradient blues
  title:   '\x1b[38;5;15m\x1b[48;5;25m',   // white on rich blue
  titleHi: '\x1b[38;5;231m\x1b[48;5;32m',  // bright white on vibrant blue
  menu:    '\x1b[38;5;254m\x1b[48;5;237m',  // light on charcoal (modern flat)
  menuHi:  '\x1b[38;5;231m\x1b[48;5;32m',  // white on blue
  status:  '\x1b[38;5;250m\x1b[48;5;236m', // gray on dark charcoal
  panel:   '\x1b[38;5;60m',                 // muted slate blue (subtle borders)
  // Text
  white:   '\x1b[38;5;231m',
  text:    '\x1b[38;5;252m',
  dim2:    '\x1b[38;5;245m',
  gray:    '\x1b[38;5;240m',
  dark:    '\x1b[38;5;237m',
  // Modern accent palette
  blue:    '\x1b[38;5;69m',     // soft periwinkle blue
  cyan:    '\x1b[38;5;80m',     // teal cyan
  green:   '\x1b[38;5;114m',    // muted sage green
  amber:   '\x1b[38;5;215m',    // warm peach amber
  red:     '\x1b[38;5;167m',    // soft coral red
  mag:     '\x1b[38;5;177m',    // lavender
  yellow:  '\x1b[38;5;222m',    // warm gold
  orange:  '\x1b[38;5;209m',    // soft tangerine
  mint:    '\x1b[38;5;122m',    // fresh mint
  violet:  '\x1b[38;5;141m',    // cool violet
  pink:    '\x1b[38;5;211m',    // soft pink
  // Priority colors (distinct, accessible)
  p0:      '\x1b[38;5;167m',  // coral
  p1:      '\x1b[38;5;209m',  // tangerine
  p2:      '\x1b[38;5;222m',  // gold
  p3:      '\x1b[38;5;80m',   // teal
  p4:      '\x1b[38;5;245m',  // gray
  // Backgrounds
  bgDark:  '\x1b[48;5;234m',
  bgPanel: '\x1b[48;5;235m',
  bgInput: '\x1b[48;5;237m',
  bgBlue:  '\x1b[48;5;25m',
  bgGreen: '\x1b[48;5;22m',
  bgRed:   '\x1b[48;5;52m',
  bgAccent:'\x1b[48;5;236m',
};

// ═══════════════════════════════════════════════════════
// LOGGING
// ═══════════════════════════════════════════════════════
function hubLog(level, message) {
  const ts = new Date().toISOString();
  try { appendFileSync(LOG_FILE, `[${ts}] [${level.toUpperCase()}] ${message}\n`); } catch {}
}
hubLog('info', '═══ PIPE-R v4.0 session started ═══');

const rl = createInterface({ input: process.stdin, output: process.stdout });
const ask = (q) => new Promise(r => rl.question(q, r));
const cls = () => process.stdout.write('\x1Bc');
const pad = (s, w = 30) => String(s).padEnd(w);
const rpad = (s, w = 10) => String(s).padStart(w);

function launchTerminal(dir, cmd) {
  const script = cmd ? `cd /d "${dir}" && ${cmd}` : `cd /d "${dir}"`;
  try {
    execSync(`start "" cmd /k "${script}"`, { shell: 'cmd.exe', stdio: 'ignore' });
    hubLog('info', `Terminal launched: ${dir}${cmd ? ' → ' + cmd : ''}`);
  } catch (e) {
    hubLog('error', `Terminal launch failed: ${e.message}`);
  }
}

// ═══════════════════════════════════════════════════════
// WINDOWS-STYLE UI RENDERER
// ═══════════════════════════════════════════════════════
const W = 72; // inner width

function winTitle(title, active = true) {
  cls();
  const color = active ? c.titleHi : c.title;
  const icon = '◆';
  const titleText = ` ${icon} ${title} `;
  const closeBtn = ` ✕ `;
  const maxBtn = ` □ `;
  const minBtn = ` ─ `;
  const btns = `${minBtn}${maxBtn}${closeBtn}`;
  const padLen = W + 2 - titleText.length - btns.length;
  const padding = padLen > 0 ? ' '.repeat(padLen) : '';
  console.log(`${color}${titleText}${padding}${btns}${c.reset}`);
}

function winMenuBar(items) {
  let bar = ' ';
  items.forEach((item, i) => {
    bar += ` ${item} `;
    if (i < items.length - 1) bar += `${c.reset}${c.menu}·`;
  });
  const padLen = W + 2 - bar.replace(/\x1b\[[0-9;]*m/g, '').length;
  console.log(`${c.menu}${bar}${padLen > 0 ? ' '.repeat(padLen) : ''}${c.reset}`);
}

function winLine(text = '', indent = 1) {
  const clean = text.replace(/\x1b\[[0-9;]*m/g, '');
  const padding = W - clean.length - indent;
  const spaces = padding > 0 ? ' '.repeat(padding) : '';
  console.log(`${c.panel}│${c.reset}${' '.repeat(indent)}${text}${c.reset}${spaces} ${c.panel}│${c.reset}`);
}

function winEmpty() {
  console.log(`${c.panel}│${' '.repeat(W + 1)}│${c.reset}`);
}

function winSep(char = '─') {
  console.log(`${c.panel}├${c.dark}${char.repeat(W + 1)}${c.panel}┤${c.reset}`);
}

function winTop() {
  console.log(`${c.panel}┌${c.dark}${'─'.repeat(W + 1)}${c.panel}┐${c.reset}`);
}

function winBottom() {
  console.log(`${c.panel}└${c.dark}${'─'.repeat(W + 1)}${c.panel}┘${c.reset}`);
}

function winStatusBar(left, right = '') {
  const cleanL = left.replace(/\x1b\[[0-9;]*m/g, '');
  const cleanR = right.replace(/\x1b\[[0-9;]*m/g, '');
  const padLen = W + 2 - cleanL.length - cleanR.length;
  const padding = padLen > 0 ? ' '.repeat(padLen) : ' ';
  console.log(`${c.status}${left}${padding}${right}${c.reset}`);
}

function winSection(title) {
  const line = '━'.repeat(W - title.length - 5);
  winLine(`${c.cyan}${c.bold}▸ ${title}${c.reset} ${c.dark}${line}${c.reset}`, 1);
}

function winBtn(key, label, desc = '') {
  const k = key === '0' ? `${c.dark}⌊${c.gray}${key}${c.dark}⌋` : `${c.panel}⌊${c.cyan}${c.bold}${key}${c.reset}${c.panel}⌋`;
  const l = key === '0' ? `${c.gray}${label}` : `${c.white}${label}`;
  const d = desc ? `  ${c.dim2}· ${desc}` : '';
  winLine(`  ${k}${c.reset}  ${l}${c.reset}${d}${c.reset}`, 1);
}

function winBtnRow(opts) {
  opts.forEach(([key, label, desc]) => winBtn(key, label, desc));
}

function winPrompt() {
  return ask(`${c.bgInput} ${c.cyan}▸${c.reset}${c.bgInput} ${c.reset} `);
}

// ═══════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════
function countFiles(dir) {
  try { return readdirSync(dir).filter(f => !f.startsWith('.')).length; }
  catch { return 0; }
}

function listFiles(dir) {
  try {
    return readdirSync(dir)
      .filter(f => !f.startsWith('.'))
      .map(f => {
        const full = join(dir, f);
        const stat = statSync(full);
        const size = stat.isDirectory() ? 'DIR' : formatSize(stat.size);
        return { name: f, size, isDir: stat.isDirectory(), path: full };
      });
  } catch { return []; }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function getUptime() {
  const s = process.uptime();
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ${m % 60}m`;
  if (m > 0) return `${m}m ${Math.floor(s % 60)}s`;
  return `${Math.floor(s)}s`;
}

function getTimestamp() {
  return new Date().toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

// ═══════════════════════════════════════════════════════
// PROJECTS REGISTRY
// ═══════════════════════════════════════════════════════
const PROJECTS = [
  { key: '1', name: 'CHERP',         path: 'C:\\Users\\Ken\\Documents\\CHERP Projects\\CHERP-main',   url: 'cherp.live',              codename: 'ALPHA' },
  { key: '2', name: 'CodeForge',     path: 'C:\\Users\\Ken\\Documents\\CodeForge\\CodeForge-main',    url: 'codesforge.netlify.app',  codename: 'FORGE' },
  { key: '3', name: 'ForgeAgent',    path: 'C:\\Users\\Ken\\Documents\\ForgeAgent\\FORGE-main',       url: null,                      codename: 'NEXUS' },
  { key: '4', name: 'CHERP Worker',  path: 'C:\\Users\\Ken\\Documents\\CHERP Projects\\CHERP-Worker', url: null,                      codename: 'GHOST' },
  { key: '5', name: 'CHERP Modular', path: join(ROOT, 'output', 'cherp-modular'),                     url: null,                      codename: 'MODULAR' },
  { key: '6', name: "Bird's Nest",   path: join(ROOT, 'output', 'birds-nest'),                        url: null,                      codename: 'NEST' },
];

// ═══════════════════════════════════════════════════════
// BOOT SEQUENCE
// ═══════════════════════════════════════════════════════
async function bootSequence() {
  cls();
  const wait = (ms) => new Promise(r => setTimeout(r, ms));

  // Modern splash with gradient feel
  const bw = 62;
  const splash = c.bgBlue;
  console.log();
  console.log(`  ${c.dark}${'▄'.repeat(bw)}${c.reset}`);
  console.log(`  ${splash}${' '.repeat(bw)}${c.reset}`);
  console.log(`  ${splash}${c.white}${c.bold}      ██████╗  ██╗ ██████╗  ███████╗       ██████╗         ${c.reset}`);
  console.log(`  ${splash}${c.white}${c.bold}      ██╔══██╗ ██║ ██╔══██╗ ██╔════╝       ██╔══██╗        ${c.reset}`);
  console.log(`  ${splash}${c.cyan}${c.bold}      ██████╔╝ ██║ ██████╔╝ █████╗  ═════╗ ██████╔╝        ${c.reset}`);
  console.log(`  ${splash}${c.cyan}      ██╔═══╝  ██║ ██╔═══╝  ██╔══╝  ═════╝ ██╔══██╗        ${c.reset}`);
  console.log(`  ${splash}${c.dim2}      ██║      ██║ ██║      ███████╗       ██║  ██║        ${c.reset}`);
  console.log(`  ${splash}${c.dim2}      ╚═╝      ╚═╝ ╚═╝      ╚══════╝       ╚═╝  ╚═╝        ${c.reset}`);
  console.log(`  ${splash}${' '.repeat(bw)}${c.reset}`);
  console.log(`  ${splash}  ${c.white}  ◆ Command Center${c.reset}${splash}                         ${c.dim2}v4.0  ${c.reset}`);
  console.log(`  ${splash}${' '.repeat(bw)}${c.reset}`);
  console.log(`  ${c.dark}${'▀'.repeat(bw)}${c.reset}`);
  console.log();
  await wait(400);

  // System check
  const checks = [
    ['Node.js Engine', () => { try { return execSync('node -v', { encoding: 'utf8' }).trim(); } catch { return null; } }],
    ['Ollama AI Core', () => { try { execSync('ollama list', { encoding: 'utf8', timeout: 2000 }); return 'Online'; } catch { return null; } }],
    ['Claude Code', () => { try { execSync('claude --version', { encoding: 'utf8', timeout: 2000 }); return 'Linked'; } catch { return null; } }],
    ['Git Control', () => { try { return execSync('git --version', { encoding: 'utf8' }).trim().replace('git version ', ''); } catch { return null; } }],
    ['Projects', () => { const n = PROJECTS.filter(p => existsSync(p.path)).length; return `${n}/${PROJECTS.length} online`; }],
  ];

  console.log(`  ${c.dim2}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${c.reset}`);
  for (const [label, check] of checks) {
    process.stdout.write(`  ${c.panel}░${c.reset} ${c.dim2}${label}...${c.reset}`);
    await wait(80);
    const result = check();
    const icon = result ? `${c.green}●` : `${c.amber}○`;
    const val = result || 'standby';
    process.stdout.write(`\r  ${icon}${c.reset} ${c.text}${label.padEnd(18)}${c.reset} ${c.dim2}${val}${c.reset}\n`);
  }
  console.log(`  ${c.dim2}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${c.reset}`);

  console.log();

  // Modern gradient progress bar
  const barW = 40;
  const gradChars = ['░', '▒', '▓', '█'];
  for (let i = 0; i <= barW; i++) {
    let bar = '';
    for (let j = 0; j < barW; j++) {
      if (j < i - 2) bar += `${c.cyan}█`;
      else if (j < i - 1) bar += `${c.blue}▓`;
      else if (j < i) bar += `${c.panel}▒`;
      else bar += `${c.dark}░`;
    }
    const pct = Math.round((i / barW) * 100);
    process.stdout.write(`\r  ${c.panel}[${bar}${c.panel}]${c.reset} ${pct < 100 ? c.dim2 : c.green}${String(pct).padStart(3)}%${c.reset}`);
    await wait(12);
  }
  console.log();
  console.log();

  const greetings = [
    'All systems nominal. Ready when you are.',
    'Welcome back. The deck is yours.',
    'Standing by for deployment orders.',
    'Pipe-R online. What are we building?',
    'Systems green. Let\'s get to work.',
    'Good to see you, Commander.',
  ];
  console.log(`  ${c.green}◆${c.reset} ${c.text}${greetings[Math.floor(Math.random() * greetings.length)]}${c.reset}`);
  console.log();
  await wait(400);
}

// ═══════════════════════════════════════════════════════
// MAIN MENU
// ═══════════════════════════════════════════════════════
let _booted = false;

async function mainMenu() {
  if (!_booted) {
    await bootSequence();
    _booted = true;
  }

  winTitle(' Pipe-R v4.0 — Command Center ');
  winMenuBar(['File', 'Projects', 'Tools', 'AI', 'View', 'Help']);
  winTop();

  // Status overview row — modern dashboard strip
  const online = PROJECTS.filter(p => existsSync(p.path)).length;
  const totalFiles = Object.values(DIRS).reduce((s, d) => s + countFiles(d), 0);
  winEmpty();
  winLine(`${c.green}●${c.reset} ${c.dim2}Projects${c.reset} ${c.white}${c.bold}${online}${c.reset}${c.dim2}/${PROJECTS.length}${c.reset}    ${c.cyan}●${c.reset} ${c.dim2}Files${c.reset} ${c.white}${c.bold}${totalFiles}${c.reset}    ${c.amber}●${c.reset} ${c.dim2}Uptime${c.reset} ${c.white}${getUptime()}${c.reset}    ${c.violet}●${c.reset} ${c.dim2}${getTimestamp()}${c.reset}`, 1);
  winEmpty();

  // Folder status — compact indicator bar
  const folderStatus = Object.entries(DIRS).map(([name, dir]) => {
    const n = countFiles(dir);
    return `${n > 0 ? c.green + '▰' : c.dark + '▱'} ${c.dim2}${name}${c.panel}:${n > 0 ? c.white : c.dark}${n}${c.reset}`;
  }).join('  ');
  winLine(folderStatus, 2);
  winEmpty();
  winSep();

  // Main menu buttons
  winEmpty();
  winSection('Navigation');
  winEmpty();
  winBtnRow([
    ['1', 'File Manager',       'Files & folder operations'],
    ['2', 'Projects',           'All project dashboards'],
    ['3', 'AI Core',            'Ollama models & agents'],
    ['4', 'Training Lab',       'Build custom AI models'],
    ['5', 'Git Control',        'Version control ops'],
    ['6', 'Claude Code',        'Launch Claude sessions'],
    ['7', 'Quick Launch',       'Apps, browser, tools'],
    ['8', 'Remote Server',      'Mobile dashboard :7777'],
    ['9', 'Batch Operations',   'Run across all projects'],
  ]);
  winEmpty();
  winSep();
  winSection('Panels');
  winEmpty();
  winBtnRow([
    ['P', 'Project Dashboard',  'Status board overview'],
    ['T', 'Task Board',         'Kanban task tracker'],
    ['B', 'Blueprints',         'Document center'],
    ['C', 'Customer Console',   "Bird's Nest integration"],
    ['S', 'Search',             'Search across everything'],
    ['F', 'File Ops',           'Zip, rename, scan'],
    ['I', 'Business Intel',     'Revenue, patents, contacts'],
    ['A', 'Activity Feed',      'Recent actions log'],
  ]);
  winEmpty();
  winSep();
  winBtnRow([
    ['M', 'Agent Mode',         'Hybrid AI framework'],
    ['G', 'Sheets Sync',        'Google Sheets backup'],
    ['N', 'Notes',              "Commander's log"],
    ['D', 'Diagnostics',        'Full system scan'],
    ['L', 'Logs',               'Flight recorder'],
    ['0', 'Exit',               ''],
  ]);
  winEmpty();
  winBottom();
  winStatusBar(` Pipe-R v4.0`, `${online} projects online | ${getTimestamp()} `);

  const choice = await winPrompt();
  switch (choice.trim().toUpperCase()) {
    case '1': return filesMenu();
    case '2': return projectsMenu();
    case '3': return ollamaMenu();
    case '4': return trainingMenu();
    case '5': return gitMenu();
    case '6': return claudeMenu();
    case '7': return quickLaunch();
    case '8': return remoteMenu();
    case '9': return batchMenu();
    case 'P': return projectDashboard();
    case 'T': return taskBoard();
    case 'B': return blueprintCenter();
    case 'C': return customerConsole();
    case 'S': return searchPanel();
    case 'F': return fileOps();
    case 'I': return businessIntel();
    case 'A': return activityFeed();
    case 'M': return agentMode();
    case 'G': return sheetsMenu();
    case 'N': return notesMenu();
    case 'D': return systemDiag();
    case 'L': return viewLogs();
    case '0': case 'Q': case 'EXIT':
      hubLog('info', '═══ PIPE-R session ended ═══');
      cls();
      console.log();
      console.log(`  ${c.dark}${'▄'.repeat(46)}${c.reset}`);
      console.log(`  ${c.bgBlue}${c.white}${c.bold}  ◆ Pipe-R shutting down...                      ${c.reset}`);
      console.log(`  ${c.bgBlue}${c.dim2}  Session logged. See you, Commander.              ${c.reset}`);
      console.log(`  ${c.dark}${'▀'.repeat(46)}${c.reset}`);
      console.log();
      rl.close();
      process.exit(0);
    default: return mainMenu();
  }
}

// ═══════════════════════════════════════════════════════
// [P] PROJECT DASHBOARD — Status board overview
// ═══════════════════════════════════════════════════════
async function projectDashboard() {
  winTitle(' Project Dashboard ');
  winMenuBar(['Overview', 'Health', 'Refresh']);
  winTop();

  winEmpty();
  winSection('All Projects');
  winEmpty();

  // Header
  winLine(`  ${c.dim2}${pad('Project', 16)} ${pad('Status', 10)} ${pad('Git', 12)} ${pad('LOC', 8)} ${pad('Last Commit', 20)}${c.reset}`, 1);
  winLine(`  ${c.dark}${'─'.repeat(66)}${c.reset}`, 1);

  for (const p of PROJECTS) {
    const exists = existsSync(p.path);
    const statusIcon = exists ? `${c.green}● Online ` : `${c.red}○ Missing`;
    let gitInfo = `${c.dark}—`;
    let loc = `${c.dark}—`;
    let lastCommit = `${c.dark}—`;

    if (exists) {
      // Git status
      try {
        const s = execSync('git status --short', { cwd: p.path, encoding: 'utf8', timeout: 3000 });
        const changes = s.trim().split('\n').filter(Boolean).length;
        gitInfo = changes > 0 ? `${c.amber}${changes} changed` : `${c.green}Clean`;
      } catch { gitInfo = `${c.dark}No git`; }

      // LOC count
      try {
        let lines = 0;
        const countL = (dir, depth = 0) => {
          if (depth > 3) return;
          try {
            readdirSync(dir).forEach(f => {
              if (f.startsWith('.') || ['node_modules','__pycache__','dist','build','android','www','.git'].includes(f)) return;
              const fp = join(dir, f);
              try {
                const st = statSync(fp);
                if (st.isDirectory()) countL(fp, depth + 1);
                else if (/\.(js|py|ts|jsx|tsx|html|css)$/.test(f) && st.size < 500000) {
                  lines += readFileSync(fp, 'utf8').split('\n').length;
                }
              } catch {}
            });
          } catch {}
        };
        countL(p.path);
        loc = `${c.cyan}${lines.toLocaleString()}`;
      } catch {}

      // Last commit
      try {
        const log = execSync('git log -1 --format="%ar"', { cwd: p.path, encoding: 'utf8', timeout: 3000 }).trim();
        lastCommit = `${c.dim2}${log}`;
      } catch {}
    }

    const url = p.url ? `${c.dim2}${p.url}` : '';
    winLine(`  ${c.white}${c.bold}${pad(p.name, 16)}${c.reset}${pad('', 0)}${statusIcon}${c.reset} ${pad('', 2)}${gitInfo}${c.reset}  ${loc}${c.reset}  ${lastCommit}${c.reset}`, 1);
  }

  winEmpty();
  winSep();
  winSection('Quick Health');
  winEmpty();

  // Aggregate stats
  let totalLoc = 0;
  let dirtyCount = 0;
  let missingCount = 0;
  for (const p of PROJECTS) {
    if (!existsSync(p.path)) { missingCount++; continue; }
    try {
      const s = execSync('git status --short', { cwd: p.path, encoding: 'utf8', timeout: 3000 });
      if (s.trim()) dirtyCount++;
    } catch {}
  }

  const healthColor = missingCount > 0 ? c.red : dirtyCount > 0 ? c.amber : c.green;
  const healthText = missingCount > 0 ? 'Issues Detected' : dirtyCount > 0 ? 'Uncommitted Changes' : 'All Clear';
  winLine(`  System Health: ${healthColor}${c.bold}${healthText}${c.reset}`, 1);
  if (dirtyCount > 0) winLine(`  ${c.amber}${dirtyCount} project(s) have uncommitted changes${c.reset}`, 1);
  if (missingCount > 0) winLine(`  ${c.red}${missingCount} project(s) not found on disk${c.reset}`, 1);

  winEmpty();
  winSep();
  winBtnRow([['0', 'Back to Main', '']]);
  winEmpty();
  winBottom();
  winStatusBar(` Dashboard`, `${PROJECTS.length} projects tracked `);

  await winPrompt();
  return mainMenu();
}

// ═══════════════════════════════════════════════════════
// [T] TASK BOARD — Kanban tracker
// ═══════════════════════════════════════════════════════
function loadTasks() {
  try { return JSON.parse(readFileSync(TASKS_FILE, 'utf8')); }
  catch { return []; }
}
function saveTasks(tasks) {
  writeFileSync(TASKS_FILE, JSON.stringify(tasks, null, 2));
}

async function taskBoard() {
  const tasks = loadTasks();

  winTitle(' Task Board ');
  winMenuBar(['All', 'By Project', 'By Priority', 'Add New']);
  winTop();

  const columns = ['BACKLOG', 'IN PROGRESS', 'REVIEW', 'DONE', 'PARKED'];
  const colColors = { 'BACKLOG': c.dim2, 'IN PROGRESS': c.cyan, 'REVIEW': c.amber, 'DONE': c.green, 'PARKED': c.gray };
  const priorityColors = { 0: c.p0, 1: c.p1, 2: c.p2, 3: c.p3, 4: c.p4 };

  winEmpty();

  // Column counts
  const counts = {};
  columns.forEach(col => { counts[col] = tasks.filter(t => t.status === col).length; });
  const colSummary = columns.map(col => `${colColors[col]}${col}: ${counts[col]}${c.reset}`).join('  ');
  winLine(colSummary, 2);
  winEmpty();
  winSep();

  // Show tasks grouped by column
  for (const col of columns) {
    const colTasks = tasks.filter(t => t.status === col);
    if (colTasks.length === 0) continue;

    winEmpty();
    winLine(`${colColors[col]}${c.bold}━━ ${col} (${colTasks.length}) ━━${c.reset}`, 2);
    colTasks.forEach((t, i) => {
      const pColor = priorityColors[t.priority] || c.dim2;
      const pLabel = `P${t.priority}`;
      const proj = t.project ? `${c.dim2}[${t.project}]` : '';
      const typeIcon = t.type === 'bug' ? `${c.red}●` : t.type === 'feature' ? `${c.green}◆` : t.type === 'docs' ? `${c.blue}◇` : `${c.dim2}○`;
      winLine(`  ${typeIcon}${c.reset} ${pColor}${pLabel}${c.reset}  ${c.white}${t.title.substring(0, 42)}${c.reset} ${proj}${c.reset}`, 1);
    });
  }

  if (tasks.length === 0) {
    winEmpty();
    winLine(`${c.dim2}No tasks yet. Add your first task below.${c.reset}`, 3);
  }

  winEmpty();
  winSep();
  winEmpty();
  winBtnRow([
    ['1', 'Add Task',       'Create new task'],
    ['2', 'Move Task',      'Change column'],
    ['3', 'Delete Task',    'Remove task'],
    ['4', 'Filter',         'By project or priority'],
    ['0', 'Back',           ''],
  ]);
  winEmpty();
  winBottom();
  winStatusBar(` Tasks: ${tasks.length}`, `${counts['IN PROGRESS'] || 0} active `);

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1': {
      console.log();
      const title = await ask(`  ${c.text}Title: ${c.reset}`);
      if (!title.trim()) return taskBoard();

      console.log(`  ${c.dim2}Projects: ${PROJECTS.map((p, i) => `${i + 1}.${p.name}`).join(', ')}${c.reset}`);
      const projPick = await ask(`  ${c.text}Project # (or Enter for none): ${c.reset}`);
      const projName = PROJECTS[parseInt(projPick) - 1]?.name || '';

      console.log(`  ${c.dim2}Priority: 0=Critical 1=High 2=Medium 3=Low 4=Someday${c.reset}`);
      const pri = await ask(`  ${c.text}Priority (0-4, default 2): ${c.reset}`);

      console.log(`  ${c.dim2}Types: bug, feature, docs, business, infra${c.reset}`);
      const type = await ask(`  ${c.text}Type (default: feature): ${c.reset}`);

      const task = {
        id: Date.now().toString(36),
        title: title.trim(),
        project: projName,
        priority: parseInt(pri) || 2,
        type: type.trim() || 'feature',
        status: 'BACKLOG',
        created: new Date().toISOString(),
        blockedBy: [],
      };
      tasks.push(task);
      saveTasks(tasks);
      console.log(`  ${c.green}✓ Task added to BACKLOG${c.reset}`);
      hubLog('info', `Task added: ${task.title}`);
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return taskBoard();
    }
    case '2': {
      if (!tasks.length) { console.log(`  ${c.dim2}No tasks${c.reset}`); await ask(`  ${c.dim2}[Enter]${c.reset} `); return taskBoard(); }
      console.log();
      tasks.forEach((t, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${t.title.substring(0, 45)}${c.reset} ${c.dim2}[${t.status}]${c.reset}`));
      const tPick = await ask(`  ${c.text}Task #: ${c.reset}`);
      const tIdx = parseInt(tPick) - 1;
      if (tIdx < 0 || tIdx >= tasks.length) return taskBoard();

      console.log(`  ${c.dim2}Columns: 1=BACKLOG 2=IN PROGRESS 3=REVIEW 4=DONE 5=PARKED${c.reset}`);
      const cPick = await ask(`  ${c.text}Move to column #: ${c.reset}`);
      const newCol = columns[parseInt(cPick) - 1];
      if (newCol) {
        tasks[tIdx].status = newCol;
        saveTasks(tasks);
        console.log(`  ${c.green}✓ Moved to ${newCol}${c.reset}`);
        hubLog('info', `Task moved: ${tasks[tIdx].title} → ${newCol}`);
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return taskBoard();
    }
    case '3': {
      if (!tasks.length) return taskBoard();
      console.log();
      tasks.forEach((t, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${t.title}${c.reset}`));
      const dPick = await ask(`  ${c.text}Delete task #: ${c.reset}`);
      const dIdx = parseInt(dPick) - 1;
      if (dIdx >= 0 && dIdx < tasks.length) {
        const confirm = await ask(`  ${c.red}Delete "${tasks[dIdx].title}"? [y/N]: ${c.reset}`);
        if (confirm.trim().toLowerCase() === 'y') {
          tasks.splice(dIdx, 1);
          saveTasks(tasks);
          console.log(`  ${c.green}✓ Deleted${c.reset}`);
        }
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return taskBoard();
    }
    case '4': {
      console.log(`  ${c.dim2}Filter by: 1=Project 2=Priority${c.reset}`);
      const fPick = await ask(`  ${c.text}Filter: ${c.reset}`);
      if (fPick.trim() === '1') {
        PROJECTS.forEach((p, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${p.name}${c.reset}`));
        const pPick = await ask(`  ${c.text}Project #: ${c.reset}`);
        const pName = PROJECTS[parseInt(pPick) - 1]?.name;
        if (pName) {
          const filtered = tasks.filter(t => t.project === pName);
          console.log(`\n  ${c.blue}${filtered.length} tasks for ${pName}:${c.reset}`);
          filtered.forEach(t => console.log(`  ${c.dim2}[${t.status}]${c.reset} ${c.white}${t.title}${c.reset}`));
        }
      } else if (fPick.trim() === '2') {
        for (let p = 0; p <= 4; p++) {
          const filtered = tasks.filter(t => t.priority === p);
          if (filtered.length) {
            const pColor = priorityColors[p] || c.dim2;
            console.log(`  ${pColor}P${p} (${filtered.length}):${c.reset}`);
            filtered.forEach(t => console.log(`    ${c.white}${t.title}${c.reset} ${c.dim2}[${t.status}]${c.reset}`));
          }
        }
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return taskBoard();
    }
    case '0': return mainMenu();
    default: return taskBoard();
  }
}

// ═══════════════════════════════════════════════════════
// [B] BLUEPRINT CENTER — Document management
// ═══════════════════════════════════════════════════════
async function blueprintCenter() {
  winTitle(' Blueprint Center ');
  winMenuBar(['Browse', 'Search', 'Recent']);
  winTop();

  winEmpty();
  winSection('Project Documentation');
  winEmpty();

  // Scan for markdown files
  const docs = [];
  for (const p of PROJECTS) {
    if (!existsSync(p.path)) continue;
    try {
      const scanMd = (dir, depth = 0) => {
        if (depth > 2) return;
        try {
          readdirSync(dir).forEach(f => {
            if (f.startsWith('.') || ['node_modules','__pycache__','dist','build','android'].includes(f)) return;
            const fp = join(dir, f);
            try {
              const st = statSync(fp);
              if (st.isDirectory()) scanMd(fp, depth + 1);
              else if (f.endsWith('.md')) {
                docs.push({ name: f, path: fp, project: p.name, modified: st.mtime });
              }
            } catch {}
          });
        } catch {}
      };
      scanMd(p.path);
    } catch {}
  }

  // Also scan memory
  const memDir = 'C:\\Users\\Ken\\.claude\\projects\\C--Users-Ken\\memory';
  if (existsSync(memDir)) {
    const scanMem = (dir) => {
      try {
        readdirSync(dir).forEach(f => {
          const fp = join(dir, f);
          try {
            const st = statSync(fp);
            if (st.isDirectory()) scanMem(fp);
            else if (f.endsWith('.md')) docs.push({ name: f, path: fp, project: 'Memory', modified: st.mtime });
          } catch {}
        });
      } catch {}
    };
    scanMem(memDir);
  }

  // Sort by recent
  docs.sort((a, b) => b.modified - a.modified);

  // Group by project
  const grouped = {};
  docs.forEach(d => {
    if (!grouped[d.project]) grouped[d.project] = [];
    grouped[d.project].push(d);
  });

  let idx = 1;
  const docList = [];
  for (const [proj, files] of Object.entries(grouped)) {
    winLine(`${c.blue}${c.bold}${proj}${c.reset} ${c.dim2}(${files.length} docs)${c.reset}`, 2);
    files.slice(0, 5).forEach(f => {
      const ago = timeSince(f.modified);
      winLine(`  ${c.cyan}${String(idx).padStart(2)}.${c.reset} ${c.white}${pad(f.name, 35)}${c.reset} ${c.dim2}${ago}${c.reset}`, 2);
      docList.push(f);
      idx++;
    });
    winEmpty();
  }

  winSep();
  winBtnRow([
    ['V', 'View Document',  'Enter # to view'],
    ['S', 'Search Docs',    'Search across all docs'],
    ['0', 'Back',            ''],
  ]);
  winEmpty();
  winBottom();
  winStatusBar(` Blueprints`, `${docs.length} documents found `);

  const choice = await winPrompt();
  if (choice.trim().toUpperCase() === 'V' || !isNaN(parseInt(choice))) {
    let num = parseInt(choice);
    if (isNaN(num)) {
      const n = await ask(`  ${c.text}Document #: ${c.reset}`);
      num = parseInt(n);
    }
    const doc = docList[num - 1];
    if (doc) {
      console.log();
      console.log(`  ${c.blue}${c.bold}── ${doc.name} ──${c.reset}`);
      console.log();
      try {
        const content = readFileSync(doc.path, 'utf8');
        const lines = content.split('\n').slice(0, 40);
        lines.forEach(l => console.log(`  ${c.text}${l}${c.reset}`));
        if (content.split('\n').length > 40) {
          console.log(`  ${c.dim2}... (${content.split('\n').length - 40} more lines)${c.reset}`);
        }
      } catch (e) { console.log(`  ${c.red}Error reading: ${e.message}${c.reset}`); }
    }
    await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
    return blueprintCenter();
  }
  if (choice.trim().toUpperCase() === 'S') {
    const query = await ask(`  ${c.text}Search: ${c.reset}`);
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      const results = docs.filter(d => {
        if (d.name.toLowerCase().includes(q)) return true;
        try { return readFileSync(d.path, 'utf8').toLowerCase().includes(q); } catch { return false; }
      });
      console.log(`\n  ${c.blue}${results.length} result(s):${c.reset}`);
      results.slice(0, 15).forEach(r => {
        console.log(`  ${c.white}${r.name}${c.reset} ${c.dim2}(${r.project})${c.reset}`);
      });
    }
    await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
    return blueprintCenter();
  }
  if (choice.trim() === '0') return mainMenu();
  return blueprintCenter();
}

function timeSince(date) {
  const s = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

// ═══════════════════════════════════════════════════════
// [C] CUSTOMER CONSOLE — Bird's Nest Integration
// ═══════════════════════════════════════════════════════
async function customerConsole() {
  winTitle(" Customer Console — Bird's Nest ");
  winMenuBar(['Customers', 'Deploy', 'Health']);
  winTop();

  winEmpty();

  const nestPath = join(ROOT, 'output', 'cherp-mcp');
  const nestExists = existsSync(nestPath);
  const customersFile = join(nestPath, 'data', 'customers.json');

  if (!nestExists) {
    winLine(`${c.amber}Bird's Nest not installed.${c.reset}`, 3);
    winLine(`${c.dim2}Build it from the CHERP MCP prompt to unlock:${c.reset}`, 3);
    winLine(`${c.dim2}  - Customer instance builder${c.reset}`, 3);
    winLine(`${c.dim2}  - Deployment management${c.reset}`, 3);
    winLine(`${c.dim2}  - Remote connections${c.reset}`, 3);
    winLine(`${c.dim2}  - Health monitoring${c.reset}`, 3);
    winEmpty();
    winLine(`${c.text}Expected at: ${c.dim2}${nestPath}${c.reset}`, 3);
  } else {
    winSection('Bird\'s Nest Status');
    winEmpty();
    winLine(`${c.green}● Bird's Nest installed${c.reset}`, 3);
    winLine(`${c.dim2}Path: ${nestPath}${c.reset}`, 3);
    winEmpty();

    // Try to load customers
    let customers = [];
    try {
      if (existsSync(customersFile)) {
        customers = JSON.parse(readFileSync(customersFile, 'utf8'));
      }
    } catch {}

    if (customers.length > 0) {
      winSection('Customers');
      winEmpty();
      winLine(`  ${c.dim2}${pad('Company', 20)} ${pad('Version', 10)} ${pad('Modules', 10)} ${pad('Status', 12)}${c.reset}`, 1);
      winLine(`  ${c.dark}${'─'.repeat(56)}${c.reset}`, 1);
      customers.forEach((cust, i) => {
        const statusColor = cust.status === 'active' ? c.green : cust.status === 'error' ? c.red : c.amber;
        winLine(`  ${c.cyan}${String(i + 1).padStart(2)}.${c.reset} ${c.white}${pad(cust.company_name, 18)}${c.reset} ${c.dim2}${pad(cust.version || 'N/A', 10)}${c.reset} ${c.dim2}${pad(String((cust.modules_enabled || []).length), 10)}${c.reset} ${statusColor}${cust.status || 'unknown'}${c.reset}`, 1);
      });
    } else {
      winLine(`${c.dim2}No customers yet. Launch Bird's Nest to create one.${c.reset}`, 3);
    }
  }

  winEmpty();
  winSep();
  winBtnRow([
    ['1', 'Launch Bird\'s Nest',  nestExists ? 'Open in new terminal' : 'Not installed'],
    ['0', 'Back',                  ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  if (choice.trim() === '1' && nestExists) {
    launchTerminal(nestPath, 'node nest.js');
    console.log(`  ${c.green}✓ Bird's Nest launching...${c.reset}`);
    await ask(`  ${c.dim2}[Enter]${c.reset} `);
  }
  return mainMenu();
}

// ═══════════════════════════════════════════════════════
// [S] SEARCH — Unified search
// ═══════════════════════════════════════════════════════
async function searchPanel() {
  winTitle(' Search ');
  winMenuBar(['Files', 'Content', 'Tasks', 'Notes']);
  winTop();

  winEmpty();
  winSection('Search Across Everything');
  winEmpty();
  winLine(`${c.dim2}Enter a search term to find matches in:${c.reset}`, 3);
  winLine(`${c.dim2}  File names, file contents, tasks, notes, and docs${c.reset}`, 3);
  winEmpty();
  winSep();
  winBtnRow([
    ['1', 'Search File Names',    'Find files by name'],
    ['2', 'Search File Contents', 'Grep across projects'],
    ['3', 'Search Tasks',         'Find tasks'],
    ['4', 'Search Notes',         'Search commander\'s log'],
    ['0', 'Back',                  ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1': {
      const query = await ask(`  ${c.text}File name search: ${c.reset}`);
      if (query.trim()) {
        const q = query.trim().toLowerCase();
        console.log(`\n  ${c.blue}Searching...${c.reset}`);
        const results = [];
        for (const p of PROJECTS) {
          if (!existsSync(p.path)) continue;
          const scan = (dir, depth = 0) => {
            if (depth > 4) return;
            try {
              readdirSync(dir).forEach(f => {
                if (f.startsWith('.') || ['node_modules','__pycache__','dist','.git','android'].includes(f)) return;
                const fp = join(dir, f);
                try {
                  const st = statSync(fp);
                  if (st.isDirectory()) scan(fp, depth + 1);
                  else if (f.toLowerCase().includes(q)) {
                    results.push({ name: f, project: p.name, path: fp.replace(p.path + '\\', '') });
                  }
                } catch {}
              });
            } catch {}
          };
          scan(p.path);
        }
        console.log(`  ${c.green}${results.length} file(s) found:${c.reset}`);
        results.slice(0, 20).forEach(r => {
          console.log(`  ${c.dim2}[${r.project}]${c.reset} ${c.white}${r.path}${c.reset}`);
        });
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return searchPanel();
    }
    case '2': {
      const query = await ask(`  ${c.text}Content search: ${c.reset}`);
      if (query.trim()) {
        const q = query.trim().toLowerCase();
        console.log(`\n  ${c.blue}Searching file contents...${c.reset}`);
        const results = [];
        for (const p of PROJECTS) {
          if (!existsSync(p.path)) continue;
          const scan = (dir, depth = 0) => {
            if (depth > 3 || results.length >= 30) return;
            try {
              readdirSync(dir).forEach(f => {
                if (f.startsWith('.') || ['node_modules','__pycache__','dist','.git','android'].includes(f)) return;
                const fp = join(dir, f);
                try {
                  const st = statSync(fp);
                  if (st.isDirectory()) scan(fp, depth + 1);
                  else if (/\.(js|py|ts|html|css|md|json)$/.test(f) && st.size < 200000) {
                    const content = readFileSync(fp, 'utf8');
                    const lines = content.split('\n');
                    lines.forEach((line, lineNum) => {
                      if (line.toLowerCase().includes(q) && results.length < 30) {
                        results.push({ file: f, project: p.name, line: lineNum + 1, text: line.trim().substring(0, 60) });
                      }
                    });
                  }
                } catch {}
              });
            } catch {}
          };
          scan(p.path);
        }
        console.log(`  ${c.green}${results.length} match(es):${c.reset}`);
        results.forEach(r => {
          console.log(`  ${c.dim2}[${r.project}]${c.reset} ${c.cyan}${r.file}:${r.line}${c.reset} ${c.text}${r.text}${c.reset}`);
        });
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return searchPanel();
    }
    case '3': {
      const query = await ask(`  ${c.text}Task search: ${c.reset}`);
      if (query.trim()) {
        const q = query.trim().toLowerCase();
        const tasks = loadTasks();
        const results = tasks.filter(t => t.title.toLowerCase().includes(q) || (t.project || '').toLowerCase().includes(q));
        console.log(`\n  ${c.green}${results.length} task(s):${c.reset}`);
        results.forEach(t => console.log(`  ${c.dim2}[${t.status}]${c.reset} ${c.white}${t.title}${c.reset} ${c.dim2}${t.project || ''}${c.reset}`));
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return searchPanel();
    }
    case '4': {
      const query = await ask(`  ${c.text}Notes search: ${c.reset}`);
      if (query.trim()) {
        const q = query.trim().toLowerCase();
        const notes = loadNotes();
        const results = notes.filter(n => n.text.toLowerCase().includes(q) || (n.tag || '').toLowerCase().includes(q));
        console.log(`\n  ${c.green}${results.length} note(s):${c.reset}`);
        results.forEach(n => {
          const tag = n.tag ? `${c.amber}[${n.tag}]${c.reset} ` : '';
          console.log(`  ${tag}${c.white}${n.text}${c.reset}`);
        });
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return searchPanel();
    }
    case '0': return mainMenu();
    default: return searchPanel();
  }
}

// ═══════════════════════════════════════════════════════
// [F] FILE OPS — File operations center
// ═══════════════════════════════════════════════════════
async function fileOps() {
  winTitle(' File Operations ');
  winMenuBar(['Zip', 'Rename', 'Scan', 'Clean']);
  winTop();

  winEmpty();
  winSection('File Operations Center');
  winEmpty();
  winBtnRow([
    ['1', 'Zip Folder',         'Create archive from folder'],
    ['2', 'Unzip Archive',      'Extract zip to output/'],
    ['3', 'Batch Rename',       'Rename files in a folder'],
    ['4', 'Size Scanner',       'Find largest files'],
    ['5', 'Duplicate Finder',   'Find duplicate file names'],
    ['6', 'Count Lines',        'LOC count for a folder'],
    ['0', 'Back',                ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1': {
      console.log(`\n  ${c.dim2}Available folders:${c.reset}`);
      Object.entries(DIRS).forEach(([name, dir], i) => {
        console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${name}/${c.reset} ${c.dim2}(${countFiles(dir)} files)${c.reset}`);
      });
      PROJECTS.forEach((p, i) => {
        if (existsSync(p.path)) console.log(`  ${c.cyan}${i + 5}.${c.reset} ${c.white}${p.name}${c.reset}`);
      });
      const pick = await ask(`  ${c.text}Folder #: ${c.reset}`);
      const idx = parseInt(pick) - 1;
      let targetPath = null;
      let targetName = '';
      if (idx >= 0 && idx < 4) {
        const keys = Object.keys(DIRS);
        targetPath = DIRS[keys[idx]];
        targetName = keys[idx];
      } else if (idx >= 4 && idx < 4 + PROJECTS.length) {
        const p = PROJECTS[idx - 4];
        targetPath = p.path;
        targetName = p.name.toLowerCase().replace(/\s+/g, '-');
      }
      if (targetPath && existsSync(targetPath)) {
        const ts = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
        const zipName = `${targetName}-${ts}.zip`;
        const zipPath = join(DIRS.output, zipName);
        console.log(`  ${c.blue}Zipping ${targetName}...${c.reset}`);
        try {
          const psCmd = `powershell -Command "Compress-Archive -Path '${targetPath.replace(/'/g, "''")}\\*' -DestinationPath '${zipPath.replace(/'/g, "''")}' -Force"`;
          execSync(psCmd, { timeout: 120000, stdio: 'pipe' });
          const size = formatSize(statSync(zipPath).size);
          console.log(`  ${c.green}✓ Created: output/${zipName} (${size})${c.reset}`);
          hubLog('info', `Zipped ${targetName} → ${zipName}`);
        } catch (e) { console.log(`  ${c.red}Failed: ${e.message}${c.reset}`); }
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return fileOps();
    }
    case '4': {
      console.log(`\n  ${c.blue}Scanning for large files...${c.reset}`);
      const bigFiles = [];
      for (const p of PROJECTS) {
        if (!existsSync(p.path)) continue;
        const scan = (dir, depth = 0) => {
          if (depth > 3) return;
          try {
            readdirSync(dir).forEach(f => {
              if (f.startsWith('.') || ['node_modules','__pycache__','dist','.git','android'].includes(f)) return;
              const fp = join(dir, f);
              try {
                const st = statSync(fp);
                if (st.isDirectory()) scan(fp, depth + 1);
                else bigFiles.push({ name: f, size: st.size, project: p.name, path: fp.replace(p.path + '\\', '') });
              } catch {}
            });
          } catch {}
        };
        scan(p.path);
      }
      bigFiles.sort((a, b) => b.size - a.size);
      console.log(`\n  ${c.blue}Top 20 Largest Files:${c.reset}`);
      bigFiles.slice(0, 20).forEach((f, i) => {
        console.log(`  ${c.dim2}${String(i + 1).padStart(3)}.${c.reset} ${c.white}${pad(f.path.substring(0, 40), 42)}${c.reset} ${c.cyan}${formatSize(f.size).padStart(10)}${c.reset} ${c.dim2}[${f.project}]${c.reset}`);
      });
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return fileOps();
    }
    case '5': {
      console.log(`\n  ${c.blue}Scanning for duplicate file names...${c.reset}`);
      const nameMap = {};
      for (const p of PROJECTS) {
        if (!existsSync(p.path)) continue;
        const scan = (dir, depth = 0) => {
          if (depth > 3) return;
          try {
            readdirSync(dir).forEach(f => {
              if (f.startsWith('.') || ['node_modules','__pycache__','dist','.git','android'].includes(f)) return;
              const fp = join(dir, f);
              try {
                const st = statSync(fp);
                if (st.isDirectory()) scan(fp, depth + 1);
                else {
                  if (!nameMap[f]) nameMap[f] = [];
                  nameMap[f].push({ project: p.name, path: fp.replace(p.path + '\\', '') });
                }
              } catch {}
            });
          } catch {}
        };
        scan(p.path);
      }
      const dupes = Object.entries(nameMap).filter(([, v]) => v.length > 1);
      if (dupes.length) {
        console.log(`\n  ${c.amber}${dupes.length} duplicate name(s) found:${c.reset}`);
        dupes.slice(0, 15).forEach(([name, locs]) => {
          console.log(`  ${c.white}${name}${c.reset} ${c.dim2}(${locs.length} copies)${c.reset}`);
          locs.forEach(l => console.log(`    ${c.dim2}[${l.project}] ${l.path}${c.reset}`));
        });
      } else {
        console.log(`  ${c.green}No duplicates found.${c.reset}`);
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return fileOps();
    }
    case '6': {
      console.log(`\n  ${c.blue}LOC count across all projects:${c.reset}\n`);
      let grandTotal = 0;
      for (const p of PROJECTS) {
        if (!existsSync(p.path)) continue;
        let loc = 0;
        const countLoc = (dir, depth = 0) => {
          if (depth > 3) return;
          try {
            readdirSync(dir).forEach(f => {
              if (f.startsWith('.') || ['node_modules','__pycache__','dist','build','android','www','.git'].includes(f)) return;
              const fp = join(dir, f);
              try {
                const st = statSync(fp);
                if (st.isDirectory()) countLoc(fp, depth + 1);
                else if (/\.(js|py|ts|jsx|tsx|html|css)$/.test(f) && st.size < 500000) {
                  loc += readFileSync(fp, 'utf8').split('\n').length;
                }
              } catch {}
            });
          } catch {}
        };
        countLoc(p.path);
        grandTotal += loc;
        console.log(`  ${c.cyan}${loc.toLocaleString().padStart(8)}${c.reset}  ${c.white}${p.name}${c.reset}`);
      }
      console.log(`  ${c.dark}${'─'.repeat(30)}${c.reset}`);
      console.log(`  ${c.green}${c.bold}${grandTotal.toLocaleString().padStart(8)}${c.reset}  ${c.white}TOTAL${c.reset}`);
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return fileOps();
    }
    case '0': return mainMenu();
    default: return fileOps();
  }
}

// ═══════════════════════════════════════════════════════
// [I] BUSINESS INTEL — Revenue, patents, contacts
// ═══════════════════════════════════════════════════════
function loadBusiness() {
  try { return JSON.parse(readFileSync(BUSINESS_FILE, 'utf8')); }
  catch {
    return {
      customers: [],
      mrr: 0,
      notes: 'No data yet. Add customers and revenue info.'
    };
  }
}
function saveBusiness(data) { writeFileSync(BUSINESS_FILE, JSON.stringify(data, null, 2)); }

function loadPatent() {
  try { return JSON.parse(readFileSync(PATENT_FILE, 'utf8')); }
  catch {
    return {
      title: 'CHERP — Construction Hierarchy, Engagement & Resource Platform',
      type: 'Provisional Patent',
      filed: '2026-04-04',
      claims: 10,
      status: 'Filed',
      notes: 'Provisional patent filed. 12-month window for full application.'
    };
  }
}
function savePatent(data) { writeFileSync(PATENT_FILE, JSON.stringify(data, null, 2)); }

async function businessIntel() {
  const biz = loadBusiness();
  const patent = loadPatent();

  winTitle(' Business Intelligence ');
  winMenuBar(['Revenue', 'Patent', 'Contacts', 'Generate']);
  winTop();

  winEmpty();
  winSection('Patent Status');
  winEmpty();
  winLine(`  ${c.white}${patent.title}${c.reset}`, 1);
  winLine(`  ${c.dim2}Type: ${c.text}${patent.type}${c.reset}  ${c.dim2}Filed: ${c.text}${patent.filed}${c.reset}  ${c.dim2}Claims: ${c.text}${patent.claims}${c.reset}`, 1);
  winLine(`  ${c.dim2}Status: ${c.green}${patent.status}${c.reset}`, 1);
  winLine(`  ${c.dim2}${patent.notes}${c.reset}`, 1);

  winEmpty();
  winSep();
  winSection('Revenue');
  winEmpty();

  if (biz.customers.length > 0) {
    winLine(`  ${c.dim2}${pad('Customer', 25)} ${pad('Tier', 12)} ${pad('MRR', 10)}${c.reset}`, 1);
    winLine(`  ${c.dark}${'─'.repeat(50)}${c.reset}`, 1);
    let totalMRR = 0;
    biz.customers.forEach(cust => {
      totalMRR += cust.mrr || 0;
      winLine(`  ${c.white}${pad(cust.name, 25)}${c.reset} ${c.dim2}${pad(cust.tier, 12)}${c.reset} ${c.green}$${(cust.mrr || 0).toLocaleString()}${c.reset}`, 1);
    });
    winLine(`  ${c.dark}${'─'.repeat(50)}${c.reset}`, 1);
    winLine(`  ${c.white}${pad('Total MRR', 37)}${c.reset} ${c.green}${c.bold}$${totalMRR.toLocaleString()}${c.reset}`, 1);
  } else {
    winLine(`  ${c.dim2}No customers yet. Pre-revenue.${c.reset}`, 1);
  }

  winEmpty();
  winSep();
  winSection('Contacts');
  winEmpty();
  winLine(`  ${c.white}Ken Deibel${c.reset}        ${c.dim2}CTO / Inventor${c.reset}`, 1);
  winLine(`  ${c.white}Sean Bedard${c.reset}       ${c.dim2}COO / Business Development${c.reset}`, 1);

  winEmpty();
  winSep();
  winBtnRow([
    ['1', 'Add Customer',     'Revenue tracking'],
    ['2', 'Update Patent',    'Change patent status'],
    ['0', 'Back',              ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1': {
      const name = await ask(`  ${c.text}Customer name: ${c.reset}`);
      if (!name.trim()) return businessIntel();
      console.log(`  ${c.dim2}Tiers: Free, Crew ($29), Site ($199), Enterprise${c.reset}`);
      const tier = await ask(`  ${c.text}Tier: ${c.reset}`);
      const mrr = await ask(`  ${c.text}MRR ($): ${c.reset}`);
      biz.customers.push({ name: name.trim(), tier: tier.trim() || 'Free', mrr: parseInt(mrr) || 0 });
      saveBusiness(biz);
      console.log(`  ${c.green}✓ Customer added${c.reset}`);
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return businessIntel();
    }
    case '2': {
      const status = await ask(`  ${c.text}New patent status: ${c.reset}`);
      if (status.trim()) {
        patent.status = status.trim();
        const note = await ask(`  ${c.text}Note (or Enter to skip): ${c.reset}`);
        if (note.trim()) patent.notes = note.trim();
        savePatent(patent);
        console.log(`  ${c.green}✓ Patent updated${c.reset}`);
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return businessIntel();
    }
    case '0': return mainMenu();
    default: return businessIntel();
  }
}

// ═══════════════════════════════════════════════════════
// [A] ACTIVITY FEED — Recent actions log
// ═══════════════════════════════════════════════════════
async function activityFeed() {
  winTitle(' Activity Feed ');
  winMenuBar(['All', 'Git', 'Files', 'Builds']);
  winTop();

  winEmpty();
  winSection('Recent Activity');
  winEmpty();

  const activities = [];

  // Hub log entries
  try {
    const raw = readFileSync(LOG_FILE, 'utf8');
    raw.trim().split('\n').slice(-30).forEach(line => {
      const match = line.match(/\[(.*?)\]\s*\[(.*?)\]\s*(.*)/);
      if (match) {
        activities.push({ ts: match[1], type: 'hub', level: match[2], msg: match[3] });
      }
    });
  } catch {}

  // Git commits from projects
  for (const p of PROJECTS) {
    if (!existsSync(p.path)) continue;
    try {
      const log = execSync('git log --oneline -5 --format="%aI|%s"', { cwd: p.path, encoding: 'utf8', timeout: 3000 });
      log.trim().split('\n').filter(Boolean).forEach(line => {
        const [ts, ...msg] = line.split('|');
        activities.push({ ts, type: 'git', level: 'INFO', msg: `[${p.name}] ${msg.join('|')}`, project: p.name });
      });
    } catch {}
  }

  // Sort by timestamp
  activities.sort((a, b) => new Date(b.ts) - new Date(a.ts));

  // Display
  const typeColors = { hub: c.blue, git: c.green, file: c.cyan, build: c.amber, error: c.red };
  const typeIcons = { hub: '●', git: '◆', file: '◇', build: '▲', error: '✗' };

  activities.slice(0, 40).forEach(a => {
    const color = typeColors[a.type] || c.dim2;
    const icon = typeIcons[a.type] || '○';
    const ts = new Date(a.ts).toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    const levelColor = a.level === 'ERROR' ? c.red : a.level === 'WARN' ? c.amber : c.dim2;
    winLine(`${color}${icon}${c.reset} ${c.dim2}${ts}${c.reset}  ${c.text}${a.msg.substring(0, 50)}${c.reset}`, 2);
  });

  if (activities.length === 0) {
    winLine(`${c.dim2}No activity recorded yet.${c.reset}`, 3);
  }

  winEmpty();
  winSep();
  winBtnRow([['0', 'Back', '']]);
  winEmpty();
  winBottom();
  winStatusBar(` Activity`, `${activities.length} events `);

  await winPrompt();
  return mainMenu();
}

// ═══════════════════════════════════════════════════════
// FILE MANAGER (was Cargo Bay)
// ═══════════════════════════════════════════════════════
async function filesMenu() {
  winTitle(' File Manager ');
  winMenuBar(['Input', 'Output', 'Workspace', 'Staging']);
  winTop();

  winEmpty();
  winSection('Storage Status');
  winEmpty();

  Object.entries(DIRS).forEach(([name, dir]) => {
    const files = listFiles(dir);
    let totalSize = 0;
    files.forEach(f => { try { if (!f.isDir) totalSize += statSync(f.path).size; } catch {} });
    const icon = files.length > 0 ? `${c.green}■` : `${c.dark}□`;
    winLine(`  ${icon}${c.reset} ${c.white}${pad(name + '/', 14)}${c.reset} ${c.dim2}${String(files.length).padStart(3)} items  ${formatSize(totalSize).padStart(10)}${c.reset}`, 1);
  });

  winEmpty();
  winSep();
  winSection('Operations');
  winEmpty();
  winBtnRow([
    ['1', 'Browse input/',         `${countFiles(DIRS.input)} items`],
    ['2', 'Browse output/',        `${countFiles(DIRS.output)} items`],
    ['3', 'Browse workspace/',     `${countFiles(DIRS.workspace)} items`],
    ['4', 'Browse staging/',       `${countFiles(DIRS.staging)} items`],
  ]);
  winEmpty();
  winSep();
  winBtnRow([
    ['5', 'Transfer input → workspace',   ''],
    ['6', 'Transfer workspace → staging',  ''],
    ['7', 'Transfer staging → output',     ''],
    ['8', 'Purge output/',                 ''],
    ['0', 'Back',                           ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1': return showDir('input');
    case '2': return showDir('output');
    case '3': return showDir('workspace');
    case '4': return showDir('staging');
    case '5': return moveFiles('input', 'workspace');
    case '6': return moveFiles('workspace', 'staging');
    case '7': return moveFiles('staging', 'output');
    case '8': return cleanDir('output');
    case '0': return mainMenu();
    default: return filesMenu();
  }
}

async function showDir(name) {
  winTitle(` ${name.toUpperCase()}/ `);
  winTop();
  winEmpty();

  const files = listFiles(DIRS[name]);
  if (files.length === 0) {
    winLine(`${c.dim2}Empty — no files found${c.reset}`, 3);
  } else {
    winLine(`  ${c.dim2}${pad('#', 4)} ${pad('Name', 40)} ${pad('Size', 10)}${c.reset}`, 1);
    winLine(`  ${c.dark}${'─'.repeat(58)}${c.reset}`, 1);
    files.forEach((f, i) => {
      const icon = f.isDir ? `${c.amber}📁` : `${c.cyan}📄`;
      winLine(`  ${c.dim2}${String(i + 1).padStart(3)}.${c.reset} ${icon} ${c.white}${pad(f.name, 38)}${c.reset} ${c.dim2}${f.size}${c.reset}`, 1);
    });
  }
  winEmpty();
  winLine(`${c.dim2}${files.length} item(s)${c.reset}`, 2);
  winBottom();
  await ask(`  ${c.dim2}[Enter] to return${c.reset} `);
  return filesMenu();
}

async function moveFiles(from, to) {
  const files = listFiles(DIRS[from]);
  if (files.length === 0) {
    console.log(`\n  ${c.dim2}${from}/ is empty — nothing to transfer${c.reset}`);
    await ask(`  ${c.dim2}[Enter]${c.reset} `);
    return filesMenu();
  }
  let moved = 0;
  files.forEach(f => {
    try { renameSync(f.path, join(DIRS[to], f.name)); moved++; }
    catch (e) { console.log(`  ${c.red}✗ ${f.name}: ${e.message}${c.reset}`); }
  });
  hubLog('info', `Transferred ${moved} item(s): ${from}/ → ${to}/`);
  console.log(`\n  ${c.green}✓ ${moved} item(s) transferred: ${from}/ → ${to}/${c.reset}`);
  await ask(`  ${c.dim2}[Enter]${c.reset} `);
  return filesMenu();
}

async function cleanDir(name) {
  const files = listFiles(DIRS[name]);
  if (files.length === 0) {
    console.log(`\n  ${c.dim2}Already empty${c.reset}`);
    await ask(`  ${c.dim2}[Enter]${c.reset} `);
    return filesMenu();
  }
  console.log(`\n  ${c.amber}⚠ Purge ${files.length} item(s) from ${name}/?${c.reset}`);
  const confirm = await ask(`  ${c.red}[y/N]: ${c.reset}`);
  if (confirm.trim().toLowerCase() === 'y') {
    let deleted = 0;
    files.forEach(f => { try { unlinkSync(f.path); deleted++; } catch {} });
    console.log(`  ${c.green}✓ ${deleted} item(s) purged${c.reset}`);
    hubLog('info', `Purged ${deleted} from ${name}/`);
  }
  await ask(`  ${c.dim2}[Enter]${c.reset} `);
  return filesMenu();
}

// ═══════════════════════════════════════════════════════
// PROJECTS MENU
// ═══════════════════════════════════════════════════════
async function projectsMenu() {
  winTitle(' Projects ');
  winMenuBar(['All', 'Active', 'New']);
  winTop();

  winEmpty();
  winSection('All Projects');
  winEmpty();

  PROJECTS.forEach(p => {
    const exists = existsSync(p.path);
    const status = exists ? `${c.green}● Online` : `${c.red}○ Offline`;
    const url = p.url ? `${c.dim2}${p.url}` : '';
    winLine(`  ${c.cyan}[${p.key}]${c.reset}  ${c.amber}${pad(p.codename, 8)}${c.reset} ${c.white}${c.bold}${pad(p.name, 16)}${c.reset} ${status}${c.reset}  ${url}${c.reset}`, 1);
  });

  winEmpty();
  winSep();
  winBtnRow([
    ['7', 'Open Desktop',     'File Explorer'],
    ['8', 'New Project',      'Scaffold from template'],
    ['9', 'Backup All',       'Zip all to output/'],
    ['0', 'Back',              ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  const proj = PROJECTS.find(p => p.key === choice.trim());
  if (proj) return projectDetail(proj);
  switch (choice.trim()) {
    case '7': try { execSync('explorer "C:\\Users\\Ken\\Desktop"'); } catch {} await ask(`  ${c.dim2}[Enter]${c.reset} `); break;
    case '8': return newProjectMenu();
    case '9': return backupAll();
    case '0': return mainMenu();
  }
  return projectsMenu();
}

async function newProjectMenu() {
  winTitle(' New Project ');
  winTop();
  winEmpty();
  winSection('Select Template');
  winEmpty();
  winBtnRow([
    ['1', 'Vanilla Web App',      'HTML + JS + CSS (PWA ready)'],
    ['2', 'Capacitor Android',    'Web app → Android'],
    ['3', 'Node.js CLI',          'Terminal tool'],
    ['4', 'Python Project',       'Python + requirements'],
    ['5', 'Empty Project',        'Folder + git init'],
    ['0', 'Cancel',                ''],
  ]);
  winEmpty();
  winBottom();

  const pick = await winPrompt();
  if (pick.trim() === '0') return projectsMenu();

  const name = await ask(`  ${c.text}Project name: ${c.reset}`);
  if (!name.trim()) return projectsMenu();
  const projName = name.trim();
  const projPath = join('C:\\Users\\Ken\\Desktop', projName);

  if (existsSync(projPath)) {
    console.log(`  ${c.red}✗ Folder already exists: ${projPath}${c.reset}`);
    await ask(`  ${c.dim2}[Enter]${c.reset} `);
    return newProjectMenu();
  }

  mkdirSync(projPath, { recursive: true });

  switch (pick.trim()) {
    case '1':
      writeFileSync(join(projPath, 'index.html'), `<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n<title>${projName}</title>\n<link rel="stylesheet" href="css/app.css">\n</head>\n<body>\n<div id="app"></div>\n<script src="js/app.js"><\/script>\n</body>\n</html>`);
      mkdirSync(join(projPath, 'js'), { recursive: true });
      mkdirSync(join(projPath, 'css'), { recursive: true });
      writeFileSync(join(projPath, 'js', 'app.js'), `// ${projName}\nconsole.log('${projName} loaded');\n`);
      writeFileSync(join(projPath, 'css', 'app.css'), `* { box-sizing: border-box; margin: 0; padding: 0; }\nbody { font-family: -apple-system, sans-serif; background: #0a0d14; color: #c8d6e5; min-height: 100vh; }\n`);
      writeFileSync(join(projPath, 'manifest.json'), JSON.stringify({ name: projName, short_name: projName, start_url: '/', display: 'standalone', background_color: '#0a0d14', theme_color: '#2563eb' }, null, 2));
      break;
    case '2':
      writeFileSync(join(projPath, 'index.html'), `<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n<title>${projName}</title>\n<link rel="stylesheet" href="css/app.css">\n</head>\n<body>\n<div id="app"><h1>${projName}</h1></div>\n<script src="js/app.js"><\/script>\n</body>\n</html>`);
      mkdirSync(join(projPath, 'js'), { recursive: true });
      mkdirSync(join(projPath, 'css'), { recursive: true });
      writeFileSync(join(projPath, 'js', 'app.js'), `console.log('${projName} loaded');\n`);
      writeFileSync(join(projPath, 'css', 'app.css'), `* { box-sizing: border-box; margin: 0; padding: 0; }\nbody { font-family: -apple-system, sans-serif; background: #0a0d14; color: #fff; }\n`);
      writeFileSync(join(projPath, 'package.json'), JSON.stringify({ name: projName.toLowerCase().replace(/\s+/g, '-'), version: '1.0.0', dependencies: { '@capacitor/core': '^8.3.0', '@capacitor/cli': '^8.3.0', '@capacitor/android': '^8.3.0' } }, null, 2));
      writeFileSync(join(projPath, 'capacitor.config.json'), JSON.stringify({ appId: `com.cherp.${projName.toLowerCase().replace(/\s+/g, '')}`, appName: projName, webDir: 'www', server: { androidScheme: 'https' } }, null, 2));
      break;
    case '3':
      writeFileSync(join(projPath, 'package.json'), JSON.stringify({ name: projName.toLowerCase().replace(/\s+/g, '-'), version: '1.0.0', type: 'module', scripts: { start: 'node index.js' } }, null, 2));
      writeFileSync(join(projPath, 'index.js'), `#!/usr/bin/env node\nconsole.log('${projName} v1.0');\n`);
      break;
    case '4':
      writeFileSync(join(projPath, 'requirements.txt'), '# Add dependencies here\n');
      writeFileSync(join(projPath, 'main.py'), `"""${projName}"""\n\ndef main():\n    print("${projName} running")\n\nif __name__ == "__main__":\n    main()\n`);
      break;
  }

  try { execSync('git init', { cwd: projPath, stdio: 'pipe' }); } catch {}

  console.log(`\n  ${c.green}✓ Project created: ${projPath}${c.reset}`);
  hubLog('info', `New project: ${projName}`);

  const openIt = await ask(`  ${c.text}Open in Explorer? [Y/n]: ${c.reset}`);
  if (openIt.trim().toLowerCase() !== 'n') {
    try { execSync(`explorer "${projPath}"`); } catch {}
  }
  await ask(`  ${c.dim2}[Enter]${c.reset} `);
  return projectsMenu();
}

async function backupAll() {
  console.log(`\n  ${c.blue}Backing up all projects...${c.reset}\n`);
  let backed = 0;
  for (const p of PROJECTS) {
    if (!existsSync(p.path)) {
      console.log(`  ${c.dim2}○ ${p.name} — skipped (missing)${c.reset}`);
      continue;
    }
    process.stdout.write(`  ${c.text}Zipping ${p.name}...${c.reset} `);
    const ts = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
    const zipName = `${p.name.toLowerCase().replace(/\s+/g, '-')}-${ts}.zip`;
    const zipPath = join(DIRS.output, zipName);
    try {
      const psCmd = `powershell -Command "` +
        `$tmp = Join-Path $env:TEMP 'piper-bak-${backed}'; ` +
        `if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }; ` +
        `Copy-Item '${p.path.replace(/'/g, "''")}' $tmp -Recurse; ` +
        `@('node_modules','.git','__pycache__','android','dist','build') | ForEach-Object { Get-ChildItem $tmp -Directory -Recurse -Filter $_ -EA 0 | Remove-Item -Recurse -Force -EA 0 }; ` +
        `Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath '${zipPath.replace(/'/g, "''")}' -Force; ` +
        `Remove-Item $tmp -Recurse -Force; ` +
        `"`;
      execSync(psCmd, { timeout: 120000, stdio: 'pipe' });
      const zipSize = formatSize(statSync(zipPath).size);
      console.log(`${c.green}${zipSize}${c.reset}`);
      backed++;
    } catch {
      console.log(`${c.red}FAILED${c.reset}`);
    }
  }
  console.log(`\n  ${c.green}✓ ${backed} project(s) backed up to output/${c.reset}`);
  hubLog('info', `Backup all: ${backed} projects archived`);
  await ask(`  ${c.dim2}[Enter]${c.reset} `);
  return projectsMenu();
}

async function projectDetail(proj) {
  winTitle(` ${proj.name} — ${proj.codename} `);
  winTop();

  if (!existsSync(proj.path)) {
    winEmpty();
    winLine(`${c.red}✗ Project directory not found${c.reset}`, 3);
    winLine(`${c.dim2}${proj.path}${c.reset}`, 3);
    winBottom();
    await ask(`  ${c.dim2}[Enter]${c.reset} `);
    return projectsMenu();
  }

  winEmpty();
  winSection('Project Info');
  winEmpty();

  if (proj.url) winLine(`  ${c.dim2}URL:${c.reset}     ${c.cyan}${proj.url}${c.reset}`, 1);
  winLine(`  ${c.dim2}Path:${c.reset}    ${c.text}${proj.path}${c.reset}`, 1);

  // Git status
  try {
    const status = execSync('git status --short', { cwd: proj.path, encoding: 'utf8' });
    const lines = status.trim().split('\n').filter(Boolean);
    winLine(`  ${c.dim2}Git:${c.reset}     ${lines.length > 0 ? `${c.amber}${lines.length} modified files` : `${c.green}Clean — all synced`}${c.reset}`, 1);
    if (lines.length > 0 && lines.length <= 6) {
      lines.forEach(l => winLine(`           ${c.dim2}${l}${c.reset}`, 1));
    }
  } catch {
    winLine(`  ${c.dim2}Git:${c.reset}     ${c.dim2}Not initialized${c.reset}`, 1);
  }

  // LOC
  try {
    let loc = 0;
    const countLoc = (dir, depth = 0) => {
      if (depth > 3) return;
      readdirSync(dir).forEach(f => {
        if (f.startsWith('.') || ['node_modules','__pycache__','dist','build','android','www','.git'].includes(f)) return;
        const fp = join(dir, f);
        try {
          const st = statSync(fp);
          if (st.isDirectory()) countLoc(fp, depth + 1);
          else if (/\.(js|py|ts|jsx|tsx|html|css)$/.test(f) && st.size < 500000) {
            loc += readFileSync(fp, 'utf8').split('\n').length;
          }
        } catch {}
      });
    };
    countLoc(proj.path);
    winLine(`  ${c.dim2}Code:${c.reset}    ${c.cyan}${loc.toLocaleString()} LOC${c.reset}`, 1);
  } catch {}

  // Stack
  const hasPkg = existsSync(join(proj.path, 'package.json'));
  const hasReqs = existsSync(join(proj.path, 'requirements.txt'));
  if (hasPkg) winLine(`  ${c.dim2}Stack:${c.reset}   ${c.cyan}Node.js${c.reset}`, 1);
  if (hasReqs) winLine(`  ${c.dim2}Stack:${c.reset}   ${c.cyan}Python${c.reset}`, 1);

  winEmpty();
  winSep();
  winSection('Actions');
  winEmpty();
  winBtnRow([
    ['1', 'Open in Explorer',     ''],
    ['2', 'Launch Terminal',       ''],
    ['3', 'Deploy Claude Code',   ''],
    ['4', 'Full Git Status',      ''],
    ['5', 'Deploy AI Agent',      'Ollama coding agent'],
    ['6', 'Deep Scan',            'Full codebase analysis'],
    ['7', 'Backup to Zip',        'Archive to output/'],
    ['0', 'Back',                  ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1':
      try { execSync(`explorer "${proj.path}"`); } catch {}
      break;
    case '2':
      launchTerminal(proj.path);
      break;
    case '3':
      launchTerminal(proj.path, 'claude');
      console.log(`  ${c.green}✓ Claude Code deploying to ${proj.name}...${c.reset}`);
      break;
    case '4':
      try {
        const full = execSync('git status', { cwd: proj.path, encoding: 'utf8' });
        console.log(`\n${full}`);
      } catch (e) { console.log(`  ${c.red}${e.message}${c.reset}`); }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '5': {
      let models = [];
      try { models = execSync('ollama list', { encoding: 'utf8', timeout: 3000 }).trim().split('\n').slice(1).map(l => l.split(/\s+/)[0]).filter(Boolean); } catch {}
      if (!models.length) {
        console.log(`\n  ${c.red}No models available. Start Ollama and pull a model first.${c.reset}`);
      } else {
        console.log(`\n  ${c.text}Models:${c.reset}`);
        models.forEach((m, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${m}${c.reset}`));
        const mp = await ask(`  ${c.text}Model #: ${c.reset}`);
        const mi = parseInt(mp) - 1;
        if (mi >= 0 && mi < models.length) {
          const stateFile = join(ROOT, 'agents', 'state.json');
          let st = { agents: [] };
          try { if (existsSync(stateFile)) st = JSON.parse(readFileSync(stateFile, 'utf8')); } catch {}
          st.agents.push({
            id: 'agent-' + Date.now().toString(36),
            model: models[mi], project: proj.path,
            projectName: proj.name, codename: proj.codename,
            task: 'Coding on ' + proj.name,
            status: 'running', deployedAt: new Date().toISOString(), log: []
          });
          st.lastUpdate = new Date().toISOString();
          writeFileSync(stateFile, JSON.stringify(st, null, 2));
          launchTerminal(proj.path, `ollama run ${models[mi]}`);
          console.log(`  ${c.green}✓ ${models[mi]} deployed to ${proj.name}${c.reset}`);
          hubLog('info', `Quick deploy: ${models[mi]} → ${proj.name}`);
        }
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    }
    case '6': return deepScan(proj);
    case '7': return backupProject(proj);
    case '0': return projectsMenu();
  }
  return projectDetail(proj);
}

async function deepScan(proj) {
  winTitle(` Deep Scan — ${proj.name} `);
  winTop();
  winEmpty();
  winSection('Analyzing...');
  winEmpty();

  const SKIP = new Set(['node_modules','__pycache__','.git','dist','build','android','www','.next','coverage','venv','.cache']);
  const LANG = { '.js':'JavaScript', '.jsx':'JSX', '.ts':'TypeScript', '.tsx':'TSX', '.py':'Python', '.html':'HTML', '.css':'CSS', '.json':'JSON', '.md':'Markdown', '.sql':'SQL' };

  let totalFiles = 0, totalLOC = 0, totalSize = 0;
  const langs = {};
  const biggest = [];

  function scan(dir, depth = 0) {
    if (depth > 5) return;
    try {
      readdirSync(dir).forEach(f => {
        if (f.startsWith('.') || SKIP.has(f)) return;
        const fp = join(dir, f);
        try {
          const st = statSync(fp);
          if (st.isDirectory()) scan(fp, depth + 1);
          else {
            const ext = f.substring(f.lastIndexOf('.')).toLowerCase();
            const lang = LANG[ext];
            if (lang && st.size < 500000) {
              totalFiles++;
              totalSize += st.size;
              try {
                const lines = readFileSync(fp, 'utf8').split('\n').length;
                totalLOC += lines;
                if (!langs[lang]) langs[lang] = { files: 0, loc: 0 };
                langs[lang].files++;
                langs[lang].loc += lines;
                biggest.push({ file: fp.replace(proj.path + '\\', '').replace(proj.path + '/', ''), loc: lines });
              } catch {}
            }
          }
        } catch {}
      });
    } catch {}
  }

  scan(proj.path);
  biggest.sort((a, b) => b.loc - a.loc);

  winLine(`  ${c.white}${c.bold}${totalLOC.toLocaleString()}${c.reset} ${c.text}lines of code${c.reset}`, 1);
  winLine(`  ${c.white}${totalFiles}${c.reset} ${c.text}source files${c.reset}`, 1);
  winLine(`  ${c.white}${formatSize(totalSize)}${c.reset} ${c.text}total size${c.reset}`, 1);

  winEmpty();
  winSep();
  winSection('Language Breakdown');
  winEmpty();

  const sorted = Object.entries(langs).sort((a, b) => b[1].loc - a[1].loc);
  sorted.forEach(([lang, data]) => {
    const pct = Math.round((data.loc / totalLOC) * 100);
    const barLen = Math.round(pct / 5);
    const bar = `${c.cyan}${'█'.repeat(barLen)}${c.dark}${'░'.repeat(20 - barLen)}`;
    winLine(`  ${c.white}${pad(lang, 14)}${c.reset} ${bar}${c.reset} ${c.cyan}${String(pct).padStart(3)}%${c.reset} ${c.dim2}${data.loc.toLocaleString()} LOC${c.reset}`, 1);
  });

  winEmpty();
  winSep();
  winSection('Largest Files');
  winEmpty();

  biggest.slice(0, 8).forEach((f, i) => {
    winLine(`  ${c.dim2}${String(i + 1).padStart(2)}.${c.reset} ${c.white}${pad(f.file, 40)}${c.reset} ${c.cyan}${f.loc.toLocaleString()} lines${c.reset}`, 1);
  });

  // Stack detection
  winEmpty();
  winSep();
  winSection('Detected Stack');
  winEmpty();
  const stack = [];
  if (existsSync(join(proj.path, 'package.json'))) {
    stack.push('Node.js');
    try {
      const pkg = JSON.parse(readFileSync(join(proj.path, 'package.json'), 'utf8'));
      const deps = { ...pkg.dependencies, ...pkg.devDependencies };
      if (deps.react) stack.push('React');
      if (deps.next) stack.push('Next.js');
      if (deps.vue) stack.push('Vue');
      if (deps.express) stack.push('Express');
      if (deps['@capacitor/core']) stack.push('Capacitor');
      if (deps['@capacitor/android']) stack.push('Android');
    } catch {}
  }
  if (existsSync(join(proj.path, 'requirements.txt'))) stack.push('Python');
  if (existsSync(join(proj.path, 'netlify.toml'))) stack.push('Netlify');
  if (existsSync(join(proj.path, 'Modelfile'))) stack.push('Ollama');
  winLine(`  ${c.cyan}${stack.join(' → ') || 'Unknown'}${c.reset}`, 1);

  // Recent commits
  try {
    const logOut = execSync('git log --oneline -5', { cwd: proj.path, encoding: 'utf8', timeout: 5000 });
    winEmpty();
    winSep();
    winSection('Recent Commits');
    winEmpty();
    logOut.trim().split('\n').forEach(l => winLine(`  ${c.dim2}${l}${c.reset}`, 1));
  } catch {}

  winEmpty();
  winSep();
  winBtnRow([['0', 'Back', '']]);
  winEmpty();
  winBottom();

  hubLog('info', `Deep scan: ${proj.name} — ${totalLOC} LOC, ${totalFiles} files`);
  await winPrompt();
  return projectDetail(proj);
}

async function backupProject(proj) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
  const zipName = `${proj.name.toLowerCase().replace(/\s+/g, '-')}-${timestamp}.zip`;
  const zipPath = join(DIRS.output, zipName);

  console.log(`\n  ${c.blue}Creating backup of ${proj.name}...${c.reset}`);
  try {
    const psCmd = `powershell -Command "` +
      `$src = '${proj.path.replace(/'/g, "''")}'; ` +
      `$dst = '${zipPath.replace(/'/g, "''")}'; ` +
      `$tmp = Join-Path $env:TEMP 'piper-backup-temp'; ` +
      `if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }; ` +
      `$exclude = @('node_modules','.git','__pycache__','dist','build','android','.next'); ` +
      `Copy-Item $src $tmp -Recurse; ` +
      `foreach ($ex in $exclude) { Get-ChildItem $tmp -Directory -Recurse -Filter $ex -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue }; ` +
      `Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $dst -Force; ` +
      `Remove-Item $tmp -Recurse -Force; ` +
      `"`;
    execSync(psCmd, { timeout: 120000, stdio: 'pipe' });
    const zipSize = formatSize(statSync(zipPath).size);
    console.log(`  ${c.green}✓ Backup saved: output/${zipName} (${zipSize})${c.reset}`);
    hubLog('info', `Backup: ${proj.name} → ${zipName} (${zipSize})`);
  } catch (e) {
    console.log(`  ${c.red}✗ Backup failed: ${e.message}${c.reset}`);
  }
  await ask(`  ${c.dim2}[Enter]${c.reset} `);
  return projectDetail(proj);
}

// ═══════════════════════════════════════════════════════
// AI CORE (Ollama)
// ═══════════════════════════════════════════════════════
async function ollamaMenu() {
  winTitle(' AI Core — Ollama ');
  winMenuBar(['Models', 'Agents', 'Chat']);
  winTop();

  let models = [];
  let running = false;
  try {
    const out = execSync('ollama list', { encoding: 'utf8', timeout: 5000 });
    running = true;
    models = out.trim().split('\n').slice(1).map(l => l.split(/\s+/)[0]).filter(Boolean);
  } catch { running = false; }

  winEmpty();
  winSection('Status');
  winEmpty();
  winLine(`  ${c.dim2}Engine:${c.reset}  ${running ? `${c.green}● Online` : `${c.red}○ Offline`}${c.reset}`, 1);
  if (running) {
    winLine(`  ${c.dim2}Models:${c.reset}  ${c.white}${models.length} installed${c.reset}`, 1);
    models.forEach(m => winLine(`           ${c.cyan}▸${c.reset} ${c.text}${m}${c.reset}`, 1));
  }

  // Show deployed agents
  let agents = [];
  try {
    const sf = join(ROOT, 'agents', 'state.json');
    if (existsSync(sf)) agents = JSON.parse(readFileSync(sf, 'utf8')).agents || [];
  } catch {}
  if (agents.length) {
    winEmpty();
    winSection('Deployed Agents');
    winEmpty();
    agents.forEach(a => {
      const stColor = a.status === 'running' ? c.green : a.status === 'stopped' ? c.red : c.amber;
      winLine(`  ${stColor}${a.status === 'running' ? '●' : '○'}${c.reset} ${c.white}${pad(a.model, 22)}${c.reset} ${stColor}${a.status.toUpperCase()}${c.reset} ${c.dim2}→ ${a.projectName || ''}${c.reset}`, 1);
    });
  }

  winEmpty();
  winSep();
  winSection('Operations');
  winEmpty();
  winBtnRow([
    ['1', 'List Models',          'Installed models'],
    ['2', 'Start Ollama',         'Launch AI engine'],
    ['3', 'Test Model',           'Quick ping'],
    ['4', 'Pull Model',           'Download new model'],
    ['5', 'Deploy Agent',         'Launch model on project'],
    ['6', 'Agent Control',        'Manage running agents'],
    ['7', 'Chat',                 'Interactive session'],
    ['0', 'Back',                  ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1':
      if (running) {
        console.log();
        if (models.length) models.forEach((m, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${m}${c.reset}`));
        else console.log(`  ${c.dim2}No models. Use [4] to pull one.${c.reset}`);
      } else { console.log(`\n  ${c.red}AI Core offline — start first [2]${c.reset}`); }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '2':
      if (running) { console.log(`\n  ${c.green}✓ AI Core already online${c.reset}`); }
      else {
        try {
          execSync('start "Ollama Server" cmd /k "ollama serve"', { shell: 'cmd.exe', stdio: 'ignore' });
          hubLog('info', 'Ollama started');
          console.log(`\n  ${c.green}✓ AI Core starting...${c.reset}`);
        } catch (e) { console.log(`\n  ${c.red}✗ Failed: ${e.message}${c.reset}`); }
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '3':
      if (!running || !models.length) { console.log(`\n  ${c.red}Need AI Core online with models${c.reset}`); await ask(`  ${c.dim2}[Enter]${c.reset} `); break; }
      if (models.length > 1) {
        models.forEach((m, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${m}${c.reset}`));
        var testPick = await ask(`  ${c.text}Model # (or Enter for ${models[0]}): ${c.reset}`);
        var testModel = models[parseInt(testPick) - 1] || models[0];
      } else { var testModel = models[0]; }
      console.log(`\n  ${c.blue}Pinging ${testModel}...${c.reset}`);
      try {
        const resp = execSync(`ollama run ${testModel} "Say hello in one creative sentence."`, { encoding: 'utf8', timeout: 30000 });
        console.log(`\n  ${c.green}◆ ${testModel}:${c.reset} ${resp.trim()}`);
      } catch (e) { console.log(`  ${c.red}✗ ${e.message}${c.reset}`); }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '4':
      if (!running) { console.log(`\n  ${c.red}Start AI Core first [2]${c.reset}`); await ask(`  ${c.dim2}[Enter]${c.reset} `); break; }
      console.log(`\n  ${c.text}Popular models:${c.reset}`);
      ['llama3.1 (8B)', 'codellama (7B)', 'qwen2.5-coder (7B)', 'deepseek-coder (6.7B)', 'phi3 (3.8B)'].forEach(m => console.log(`  ${c.dim2}  ${m}${c.reset}`));
      const modelName = await ask(`\n  ${c.text}Model to pull: ${c.reset}`);
      if (modelName.trim()) {
        launchTerminal(ROOT, `ollama pull ${modelName.trim()}`);
        console.log(`  ${c.green}✓ Pull started in new terminal${c.reset}`);
        hubLog('info', `Pulling model: ${modelName.trim()}`);
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '5': return deployAgentMenu(models, running);
    case '6': return agentControlMenu();
    case '7':
      if (!running || !models.length) { console.log(`\n  ${c.red}Need AI Core online with models${c.reset}`); await ask(`  ${c.dim2}[Enter]${c.reset} `); break; }
      if (models.length > 1) {
        models.forEach((m, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${m}${c.reset}`));
        var chatPick = await ask(`  ${c.text}Model #: ${c.reset}`);
        var chatModel = models[parseInt(chatPick) - 1] || models[0];
      } else { var chatModel = models[0]; }
      launchTerminal(ROOT, `ollama run ${chatModel}`);
      console.log(`\n  ${c.green}✓ Chat session opened with ${chatModel}${c.reset}`);
      hubLog('info', `Chat: ${chatModel}`);
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '0': return mainMenu();
  }
  return ollamaMenu();
}

async function deployAgentMenu(models, running) {
  if (!running || !models.length) {
    console.log(`\n  ${c.red}Need AI Core online with models${c.reset}`);
    await ask(`  ${c.dim2}[Enter]${c.reset} `);
    return ollamaMenu();
  }

  winTitle(' Deploy Agent ');
  winTop();
  winEmpty();
  winSection('Select Model');
  winEmpty();
  models.forEach((m, i) => winLine(`  ${c.cyan}[${i + 1}]${c.reset} ${c.white}${m}${c.reset}`, 1));
  winEmpty();
  winSection('Select Project');
  winEmpty();
  PROJECTS.forEach(p => {
    const exists = existsSync(p.path);
    winLine(`  ${exists ? c.cyan : c.red}[${String.fromCharCode(64 + parseInt(p.key))}]${c.reset} ${c.white}${p.name}${c.reset} ${!exists ? `${c.red}(missing)${c.reset}` : ''}`, 1);
  });
  winEmpty();
  winSep();
  winBtnRow([['0', 'Cancel', '']]);
  winEmpty();
  winBottom();

  const modelPick = await ask(`  ${c.text}Model #: ${c.reset}`);
  if (modelPick.trim() === '0') return ollamaMenu();
  const selectedModel = models[parseInt(modelPick) - 1];
  if (!selectedModel) return ollamaMenu();

  const projPick = await ask(`  ${c.text}Project letter: ${c.reset}`);
  const projIdx = projPick.trim().toUpperCase().charCodeAt(0) - 65;
  const selectedProj = PROJECTS[projIdx];
  if (!selectedProj || !existsSync(selectedProj.path)) return ollamaMenu();

  const task = await ask(`  ${c.text}Task (or Enter for general): ${c.reset}`);

  const stateFile = join(ROOT, 'agents', 'state.json');
  let state = { agents: [] };
  try { if (existsSync(stateFile)) state = JSON.parse(readFileSync(stateFile, 'utf8')); } catch {}
  const agent = {
    id: 'agent-' + Date.now().toString(36), model: selectedModel, project: selectedProj.path,
    projectName: selectedProj.name, codename: selectedProj.codename,
    task: task.trim() || 'General coding assistance',
    status: 'deployed', deployedAt: new Date().toISOString(), log: []
  };
  state.agents.push(agent);
  state.lastUpdate = new Date().toISOString();
  writeFileSync(stateFile, JSON.stringify(state, null, 2));

  console.log(`\n  ${c.green}✓ Agent deployed: ${selectedModel} → ${selectedProj.name}${c.reset}`);
  hubLog('info', `Agent deployed: ${selectedModel} → ${selectedProj.name}`);

  const launch = await ask(`  ${c.text}Launch now? [Y/n]: ${c.reset}`);
  if (launch.trim().toLowerCase() !== 'n') {
    launchTerminal(selectedProj.path, `ollama run ${selectedModel}`);
    agent.status = 'running';
    writeFileSync(stateFile, JSON.stringify(state, null, 2));
  }
  await ask(`  ${c.dim2}[Enter]${c.reset} `);
  return ollamaMenu();
}

async function agentControlMenu() {
  const stateFile = join(ROOT, 'agents', 'state.json');
  let agents = [];
  try { if (existsSync(stateFile)) agents = JSON.parse(readFileSync(stateFile, 'utf8')).agents || []; } catch {}

  winTitle(' Agent Control ');
  winTop();
  winEmpty();

  if (!agents.length) {
    winLine(`${c.dim2}No agents deployed. Use AI Core > Deploy Agent.${c.reset}`, 3);
    winSep();
    winBtnRow([['0', 'Back', '']]);
    winEmpty();
    winBottom();
    await winPrompt();
    return ollamaMenu();
  }

  agents.forEach((a, i) => {
    const stColor = a.status === 'running' ? c.green : a.status === 'stopped' ? c.red : c.amber;
    winLine(`${c.cyan}[${i + 1}]${c.reset} ${stColor}${a.status === 'running' ? '●' : '○'}${c.reset} ${c.white}${c.bold}${pad(a.model, 20)}${c.reset} ${c.dim2}→${c.reset} ${c.amber}${a.projectName || ''}${c.reset}`, 2);
    winLine(`    ${c.dim2}${a.task.substring(0, 50)}${c.reset}`, 2);
    winLine(`    ${c.dim2}Status: ${stColor}${a.status}${c.reset} ${c.dim2}| ID: ${a.id}${c.reset}`, 2);
    winEmpty();
  });

  winSep();
  winBtnRow([
    ['L', 'Launch Agent',     'Start in terminal'],
    ['S', 'Stop Agent',       'Mark stopped'],
    ['T', 'Assign Task',      'New task'],
    ['X', 'Remove Agent',     'Delete from roster'],
    ['0', 'Back',              ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  if (choice.trim() === '0') return ollamaMenu();

  if (['L','S','T','X'].includes(choice.trim().toUpperCase())) {
    const agentNum = await ask(`  ${c.text}Agent # (1-${agents.length}): ${c.reset}`);
    const idx = parseInt(agentNum) - 1;
    if (idx < 0 || idx >= agents.length) { await ask(`  ${c.dim2}[Enter]${c.reset} `); return agentControlMenu(); }

    const agent = agents[idx];
    const state = JSON.parse(readFileSync(stateFile, 'utf8'));

    switch (choice.trim().toUpperCase()) {
      case 'L':
        launchTerminal(agent.project, `ollama run ${agent.model}`);
        state.agents[idx].status = 'running';
        writeFileSync(stateFile, JSON.stringify(state, null, 2));
        console.log(`  ${c.green}✓ ${agent.model} launched${c.reset}`);
        break;
      case 'S':
        state.agents[idx].status = 'stopped';
        writeFileSync(stateFile, JSON.stringify(state, null, 2));
        console.log(`  ${c.amber}● ${agent.model} stopped${c.reset}`);
        break;
      case 'T':
        const newTask = await ask(`  ${c.text}New task: ${c.reset}`);
        if (newTask.trim()) {
          state.agents[idx].task = newTask.trim();
          writeFileSync(stateFile, JSON.stringify(state, null, 2));
          console.log(`  ${c.green}✓ Task assigned${c.reset}`);
        }
        break;
      case 'X':
        const confirm = await ask(`  ${c.red}Remove ${agent.model}? [y/N]: ${c.reset}`);
        if (confirm.trim().toLowerCase() === 'y') {
          state.agents.splice(idx, 1);
          writeFileSync(stateFile, JSON.stringify(state, null, 2));
          console.log(`  ${c.green}✓ Agent removed${c.reset}`);
        }
        break;
    }
    await ask(`  ${c.dim2}[Enter]${c.reset} `);
  }
  return agentControlMenu();
}

// ═══════════════════════════════════════════════════════
// TRAINING LAB
// ═══════════════════════════════════════════════════════
async function trainingMenu() {
  winTitle(' Training Lab ');
  winMenuBar(['Create', 'Harvest', 'Build', 'Templates']);
  winTop();

  winEmpty();
  winSection('Resources');
  winEmpty();

  const dsDir = join(ROOT, 'datasets');
  if (!existsSync(dsDir)) mkdirSync(dsDir, { recursive: true });
  let datasets = [];
  try {
    datasets = readdirSync(dsDir).filter(f => f.endsWith('.jsonl') || f.endsWith('.json')).map(f => {
      let count = 0;
      try { count = readFileSync(join(dsDir, f), 'utf8').trim().split('\n').length; } catch {}
      return { name: f, count };
    });
  } catch {}

  const modelsDir = join(ROOT, 'agents', 'models');
  if (!existsSync(modelsDir)) mkdirSync(modelsDir, { recursive: true });
  let modelfiles = [];
  try { modelfiles = readdirSync(modelsDir).filter(f => f.startsWith('Modelfile.')); } catch {}

  winLine(`  ${c.dim2}Datasets:${c.reset}     ${datasets.length > 0 ? `${c.white}${datasets.length} available` : `${c.dim2}none`}${c.reset}`, 1);
  datasets.forEach(d => winLine(`              ${c.cyan}▸${c.reset} ${c.text}${pad(d.name, 30)}${c.reset} ${c.dim2}${d.count} examples${c.reset}`, 1));
  winLine(`  ${c.dim2}Modelfiles:${c.reset}   ${modelfiles.length > 0 ? `${c.white}${modelfiles.length} created` : `${c.dim2}none`}${c.reset}`, 1);
  modelfiles.forEach(m => winLine(`              ${c.cyan}▸${c.reset} ${c.text}${m}${c.reset}`, 1));

  winEmpty();
  winSep();
  winBtnRow([
    ['1', 'Create Model',      'From template + dataset'],
    ['2', 'Harvest Project',   'Extract training data'],
    ['3', 'Build Model',       'ollama create'],
    ['4', 'View Templates',    'Pre-built agent types'],
    ['5', 'View Datasets',     'Browse training data'],
    ['0', 'Back',               ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1': return createModelMenu();
    case '2': return harvestMenu();
    case '3': return buildModelMenu(modelfiles);
    case '4': return templatesMenu();
    case '5':
      if (!datasets.length) { console.log(`  ${c.dim2}No datasets. Use [2] to harvest.${c.reset}`); }
      else {
        datasets.forEach((d, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${pad(d.name, 30)}${c.reset} ${c.dim2}${d.count} examples${c.reset}`));
        const peek = await ask(`\n  ${c.text}View # (or Enter to skip): ${c.reset}`);
        const pi = parseInt(peek) - 1;
        if (pi >= 0 && pi < datasets.length) {
          try {
            const lines = readFileSync(join(dsDir, datasets[pi].name), 'utf8').trim().split('\n').slice(0, 5);
            console.log(`\n  ${c.blue}First 5 entries:${c.reset}`);
            lines.forEach(l => {
              try { const obj = JSON.parse(l); console.log(`  ${c.dim2}Q:${c.reset} ${(obj.instruction || obj.prompt || '').substring(0, 50)}`); console.log(`  ${c.text}A:${c.reset} ${(obj.output || obj.completion || '').substring(0, 50)}\n`); } catch {}
            });
          } catch {}
        }
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '0': return mainMenu();
  }
  return trainingMenu();
}

async function createModelMenu() {
  winTitle(' Create Model ');
  winTop();
  winEmpty();
  winSection('Select Template');
  winEmpty();

  const templates = {
    '1': { key: 'code-assistant', name: 'Code Assistant', base: 'llama3.1', temp: 0.3 },
    '2': { key: 'plumbing-expert', name: 'Plumbing Expert', base: 'llama3.1', temp: 0.4 },
    '3': { key: 'web-developer', name: 'Web Developer', base: 'codellama', temp: 0.3 },
    '4': { key: 'python-developer', name: 'Python Developer', base: 'codellama', temp: 0.3 },
    '5': { key: 'custom', name: 'Custom', base: 'llama3.1', temp: 0.7 },
  };

  Object.entries(templates).forEach(([k, t]) => {
    winLine(`  ${c.cyan}[${k}]${c.reset} ${c.white}${c.bold}${pad(t.name, 20)}${c.reset} ${c.dim2}${t.base} @ temp ${t.temp}${c.reset}`, 1);
  });
  winEmpty();
  winSep();
  winBtnRow([['0', 'Cancel', '']]);
  winEmpty();
  winBottom();

  const pick = await winPrompt();
  if (pick.trim() === '0') return trainingMenu();
  const tmpl = templates[pick.trim()];
  if (!tmpl) return trainingMenu();

  const modelName = await ask(`  ${c.text}Model name: ${c.reset}`);
  if (!modelName.trim()) return trainingMenu();

  let system = '';
  let base = tmpl.base;
  let temp = tmpl.temp;

  if (tmpl.key === 'custom') {
    base = (await ask(`  ${c.text}Base model (default llama3.1): ${c.reset}`)).trim() || 'llama3.1';
    system = (await ask(`  ${c.text}System prompt: ${c.reset}`)).trim();
    const t = (await ask(`  ${c.text}Temperature (0.0-1.0): ${c.reset}`)).trim();
    if (t) temp = parseFloat(t) || 0.7;
  } else {
    const sysPrompts = {
      'code-assistant': 'You are an expert coding assistant. Write clean, readable code. Always explain your changes.',
      'plumbing-expert': 'You are Pipe-R, an expert in commercial and residential plumbing. You know IPC codes, pipe materials, OSHA safety.',
      'web-developer': 'You are a web development expert specializing in JavaScript, HTML, CSS. Mobile-first, dark theme.',
      'python-developer': 'You are a Python expert following PEP 8. Use type hints, write docstrings.',
    };
    system = sysPrompts[tmpl.key] || '';
  }

  // Dataset selection
  const dsDir = join(ROOT, 'datasets');
  let datasets = [];
  try { datasets = readdirSync(dsDir).filter(f => f.endsWith('.jsonl') || f.endsWith('.json')); } catch {}

  let datasetPath = null;
  if (datasets.length) {
    console.log(`\n  ${c.text}Datasets:${c.reset}`);
    datasets.forEach((d, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${d}${c.reset}`));
    const dsPick = await ask(`  ${c.text}Dataset # (or Enter for none): ${c.reset}`);
    const dsIdx = parseInt(dsPick) - 1;
    if (dsIdx >= 0 && dsIdx < datasets.length) datasetPath = join(dsDir, datasets[dsIdx]);
  }

  // Generate Modelfile
  const modelsDir = join(ROOT, 'agents', 'models');
  if (!existsSync(modelsDir)) mkdirSync(modelsDir, { recursive: true });

  let content = `FROM ${base}\n\nPARAMETER temperature ${temp}\nPARAMETER num_ctx 4096\n\n`;
  if (system) content += `SYSTEM """\n${system}\n"""\n\n`;

  if (datasetPath) {
    try {
      const lines = readFileSync(datasetPath, 'utf8').trim().split('\n');
      lines.forEach(line => {
        try {
          const item = JSON.parse(line);
          const q = item.instruction || item.prompt || '';
          const a = item.output || item.completion || '';
          if (q && a) content += `MESSAGE user ${q}\nMESSAGE assistant ${a}\n\n`;
        } catch {}
      });
      console.log(`  ${c.green}✓ Loaded ${lines.length} training examples${c.reset}`);
    } catch {}
  }

  const mfPath = join(modelsDir, `Modelfile.${modelName.trim()}`);
  writeFileSync(mfPath, content);
  console.log(`\n  ${c.green}✓ Modelfile created${c.reset}`);
  hubLog('info', `Modelfile created: ${modelName.trim()}`);

  const build = await ask(`  ${c.text}Build now? [Y/n]: ${c.reset}`);
  if (build.trim().toLowerCase() !== 'n') {
    console.log(`\n  ${c.blue}Building ${modelName.trim()}...${c.reset}`);
    try {
      execSync(`ollama create ${modelName.trim()} -f "${mfPath}"`, { encoding: 'utf8', timeout: 300000, stdio: 'inherit' });
      console.log(`\n  ${c.green}✓ Model created!${c.reset}`);
      hubLog('info', `Model built: ${modelName.trim()}`);
    } catch (e) { console.log(`\n  ${c.red}Build failed: ${e.message}${c.reset}`); }
  }
  await ask(`  ${c.dim2}[Enter]${c.reset} `);
  return trainingMenu();
}

async function harvestMenu() {
  winTitle(' Harvest Project ');
  winTop();
  winEmpty();
  winSection('Select Project to Harvest');
  winEmpty();
  PROJECTS.forEach(p => {
    const exists = existsSync(p.path);
    winLine(`  ${c.cyan}[${p.key}]${c.reset} ${c.white}${pad(p.name, 15)}${c.reset} ${exists ? `${c.green}●` : `${c.red}○`}${c.reset}`, 1);
  });
  winEmpty();
  winSep();
  winBtnRow([['0', 'Cancel', '']]);
  winEmpty();
  winBottom();

  const pick = await winPrompt();
  if (pick.trim() === '0') return trainingMenu();

  const proj = PROJECTS.find(p => p.key === pick.trim());
  if (!proj || !existsSync(proj.path)) {
    console.log(`  ${c.red}Invalid or missing project${c.reset}`);
    await ask(`  ${c.dim2}[Enter]${c.reset} `);
    return trainingMenu();
  }

  const outName = await ask(`  ${c.text}Dataset name (default: ${proj.name.toLowerCase()}-harvest): ${c.reset}`);
  const dsName = outName.trim() || `${proj.name.toLowerCase().replace(/\s+/g, '-')}-harvest`;

  console.log(`\n  ${c.blue}Scanning ${proj.name}...${c.reset}`);
  const dsDir = join(ROOT, 'datasets');
  if (!existsSync(dsDir)) mkdirSync(dsDir, { recursive: true });
  const dataset = [];
  const exts = ['.js', '.py', '.ts', '.jsx', '.tsx', '.css', '.html'];

  function scanDir(dir, depth = 0) {
    if (depth > 3) return;
    try {
      readdirSync(dir).forEach(item => {
        if (item.startsWith('.') || ['node_modules','__pycache__','dist','build','android','www'].includes(item)) return;
        const full = join(dir, item);
        try {
          const stat = statSync(full);
          if (stat.isDirectory()) scanDir(full, depth + 1);
          else if (exts.some(e => item.endsWith(e)) && stat.size < 50000) {
            const code = readFileSync(full, 'utf8');
            const funcs = code.match(/(?:function|async function|const|var|def)\s+(\w+)/g) || [];
            funcs.forEach(match => {
              const name = match.match(/(\w+)$/)?.[1];
              if (name && name.length > 2 && !['var','const','function','async','def'].includes(name)) {
                dataset.push({
                  instruction: `Explain the ${name} function in ${item}`,
                  output: `The ${name} function in ${item} handles ${name.replace(/([A-Z])/g, ' $1').toLowerCase().trim()} logic for the ${proj.name} project.`
                });
              }
            });
          }
        } catch {}
      });
    } catch {}
  }

  scanDir(proj.path);
  const outPath = join(dsDir, dsName + '.jsonl');
  writeFileSync(outPath, dataset.map(d => JSON.stringify(d)).join('\n'));

  console.log(`  ${c.green}✓ Harvested ${dataset.length} training pairs${c.reset}`);
  console.log(`  ${c.dim2}Saved to: datasets/${dsName}.jsonl${c.reset}`);
  hubLog('info', `Harvested ${dataset.length} pairs from ${proj.name}`);

  await ask(`  ${c.dim2}[Enter]${c.reset} `);
  return trainingMenu();
}

async function buildModelMenu(modelfiles) {
  if (!modelfiles.length) {
    console.log(`  ${c.dim2}No Modelfiles found. Create one first.${c.reset}`);
    await ask(`  ${c.dim2}[Enter]${c.reset} `);
    return trainingMenu();
  }
  console.log(`\n  ${c.text}Modelfiles:${c.reset}`);
  modelfiles.forEach((m, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${m.replace('Modelfile.', '')}${c.reset}`));
  const pick = await ask(`\n  ${c.text}Build #: ${c.reset}`);
  const idx = parseInt(pick) - 1;
  if (idx < 0 || idx >= modelfiles.length) return trainingMenu();
  const mfName = modelfiles[idx];
  const modelName = mfName.replace('Modelfile.', '');
  const mfPath = join(ROOT, 'agents', 'models', mfName);
  console.log(`\n  ${c.blue}Building ${modelName}...${c.reset}`);
  try {
    execSync(`ollama create ${modelName} -f "${mfPath}"`, { encoding: 'utf8', timeout: 300000, stdio: 'inherit' });
    console.log(`\n  ${c.green}✓ Model ${modelName} created!${c.reset}`);
    hubLog('info', `Model built: ${modelName}`);
  } catch (e) { console.log(`\n  ${c.red}Build failed: ${e.message}${c.reset}`); }
  await ask(`  ${c.dim2}[Enter]${c.reset} `);
  return trainingMenu();
}

async function templatesMenu() {
  winTitle(' Agent Templates ');
  winTop();
  winEmpty();
  const tmpls = [
    { name: 'Code Assistant',    desc: 'General coding help, debugging', base: 'llama3.1', temp: '0.3' },
    { name: 'Plumbing Expert',   desc: 'IPC codes, pipe specs, OSHA',   base: 'llama3.1', temp: '0.4' },
    { name: 'Web Developer',     desc: 'JS, HTML, CSS, responsive',     base: 'codellama', temp: '0.3' },
    { name: 'Python Developer',  desc: 'PEP 8, type hints, clean code', base: 'codellama', temp: '0.3' },
  ];
  tmpls.forEach((t, i) => {
    winLine(`  ${c.cyan}[${i + 1}]${c.reset} ${c.white}${c.bold}${pad(t.name, 20)}${c.reset} ${c.dim2}${t.base} @ ${t.temp}${c.reset}`, 1);
    winLine(`      ${c.dim2}${t.desc}${c.reset}`, 1);
    winEmpty();
  });
  winSep();
  winBtnRow([['0', 'Back', '']]);
  winEmpty();
  winBottom();
  await winPrompt();
  return trainingMenu();
}

// ═══════════════════════════════════════════════════════
// GIT CONTROL
// ═══════════════════════════════════════════════════════
async function gitMenu() {
  winTitle(' Git Control ');
  winMenuBar(['Status', 'Log', 'Commit', 'Push']);
  winTop();
  winEmpty();
  winBtnRow([
    ['1', 'Status',        'Changed files'],
    ['2', 'Log',           'Recent commits'],
    ['3', 'Stage + Commit','Save checkpoint'],
    ['4', 'Push',          'Push to remote'],
    ['0', 'Back',           ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1':
      try { const s = execSync('git status --short', { encoding: 'utf8' }); console.log(`\n${s || `  ${c.green}✓ All clear${c.reset}`}`); }
      catch { console.log(`  ${c.red}Not a git repo${c.reset}`); }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '2':
      try { console.log(`\n${execSync('git log --oneline -10', { encoding: 'utf8' })}`); }
      catch (e) { console.log(`  ${c.red}${e.message}${c.reset}`); }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '3':
      const msg = await ask(`  ${c.text}Commit message: ${c.reset}`);
      if (msg.trim()) {
        try {
          execSync('git add -A', { encoding: 'utf8' });
          execSync(`git commit -m "${msg.trim().replace(/"/g, '\\"')}"`, { encoding: 'utf8' });
          console.log(`  ${c.green}✓ Committed${c.reset}`);
          hubLog('info', `Git commit: ${msg.trim()}`);
        } catch (e) { console.log(`  ${c.red}${e.message}${c.reset}`); }
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '4':
      try { execSync('git push', { encoding: 'utf8' }); console.log(`  ${c.green}✓ Pushed to remote${c.reset}`); hubLog('info', 'Git push'); }
      catch (e) { console.log(`  ${c.red}${e.message}${c.reset}`); }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '0': return mainMenu();
  }
  return gitMenu();
}

// ═══════════════════════════════════════════════════════
// CLAUDE CODE
// ═══════════════════════════════════════════════════════
async function claudeMenu() {
  winTitle(' Claude Code ');
  winMenuBar(['Deploy', 'Sessions']);
  winTop();
  winEmpty();
  winSection('Deploy Claude Code');
  winEmpty();
  winBtnRow([['1', 'Deploy Here (Desktop/Claude)', '']]);
  PROJECTS.forEach(p => {
    winBtnRow([[String(parseInt(p.key) + 1), `Deploy to ${p.name}`, existsSync(p.path) ? '' : 'offline']]);
  });
  winBtnRow([['0', 'Back', '']]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  if (choice.trim() === '1') {
    launchTerminal(ROOT, 'claude');
    hubLog('info', 'Claude deployed to hub root');
    console.log(`  ${c.green}✓ Claude Code launching...${c.reset}`);
    await ask(`  ${c.dim2}[Enter]${c.reset} `);
  } else {
    const proj = PROJECTS.find(p => String(parseInt(p.key) + 1) === choice.trim());
    if (proj && existsSync(proj.path)) {
      launchTerminal(proj.path, 'claude');
      hubLog('info', `Claude deployed to ${proj.name}`);
      console.log(`  ${c.green}✓ Claude Code deploying to ${proj.name}...${c.reset}`);
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
    }
  }
  if (choice.trim() === '0') return mainMenu();
  return claudeMenu();
}

// ═══════════════════════════════════════════════════════
// QUICK LAUNCH
// ═══════════════════════════════════════════════════════
async function quickLaunch() {
  winTitle(' Quick Launch ');
  winTop();
  winEmpty();
  winBtnRow([
    ['1', 'Open Desktop',          'File Explorer'],
    ['2', 'Open Android Studio',   ''],
    ['3', 'Open cherp.live',       'Browser'],
    ['4', 'Open GitHub',           'HesKenY repos'],
    ['5', 'Serve CHERP Worker',    'Local dev server'],
    ['6', 'Terminal at Desktop',   ''],
    ['0', 'Back',                   ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1': try { execSync('explorer "C:\\Users\\Ken\\Desktop"'); } catch {} console.log(`  ${c.green}✓ Explorer opened${c.reset}`); break;
    case '2': try { execSync('start "" "C:\\Program Files\\Android\\Android Studio\\bin\\studio64.exe"', { shell: 'cmd.exe', stdio: 'ignore' }); } catch {} console.log(`  ${c.green}✓ Android Studio launching${c.reset}`); break;
    case '3': try { execSync('start "" "https://cherp.live"', { shell: 'cmd.exe', stdio: 'ignore' }); } catch {} break;
    case '4': try { execSync('start "" "https://github.com/HesKenY"', { shell: 'cmd.exe', stdio: 'ignore' }); } catch {} break;
    case '5':
      if (existsSync('C:\\Users\\Ken\\Desktop\\CHERP-Worker')) {
        launchTerminal('C:\\Users\\Ken\\Desktop\\CHERP-Worker', 'npx serve www');
        console.log(`  ${c.green}✓ Serving CHERP Worker...${c.reset}`);
      } else { console.log(`  ${c.red}CHERP-Worker not found${c.reset}`); }
      break;
    case '6': launchTerminal('C:\\Users\\Ken\\Desktop'); break;
    case '0': return mainMenu();
  }
  if (choice.trim() !== '0') await ask(`  ${c.dim2}[Enter]${c.reset} `);
  return quickLaunch();
}

// ═══════════════════════════════════════════════════════
// REMOTE SERVER
// ═══════════════════════════════════════════════════════
async function remoteMenu() {
  winTitle(' Remote Server ');
  winTop();
  winEmpty();

  let serverOnline = false;
  try { execSync('curl -s http://localhost:7777/api/state', { timeout: 2000 }); serverOnline = true; } catch {}

  let localIP = 'unknown';
  try {
    const ipOut = execSync('powershell -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike \'*Loopback*\' -and $_.PrefixOrigin -eq \'Dhcp\' } | Select-Object -First 1).IPAddress"', { encoding: 'utf8', timeout: 5000 }).trim();
    if (ipOut) localIP = ipOut;
  } catch {}

  winLine(`  ${c.dim2}Status:${c.reset}    ${serverOnline ? `${c.green}● Online (port 7777)` : `${c.red}○ Offline`}${c.reset}`, 1);
  if (localIP !== 'unknown') winLine(`  ${c.dim2}Phone URL:${c.reset} ${c.cyan}http://${localIP}:7777${c.reset}`, 1);

  winEmpty();
  winSep();
  winBtnRow([
    ['1', 'Start Server',     serverOnline ? '(already running)' : ''],
    ['2', 'Open in Browser',  'localhost:7777'],
    ['3', 'Show Phone URL',   ''],
    ['0', 'Back',              ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1':
      if (serverOnline) { console.log(`  ${c.green}✓ Already running${c.reset}`); }
      else {
        launchTerminal(ROOT, 'node server.js');
        hubLog('info', 'Remote server started');
        console.log(`  ${c.green}✓ Server starting on :7777${c.reset}`);
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '2':
      try { execSync('start "" "http://localhost:7777"', { shell: 'cmd.exe', stdio: 'ignore' }); } catch {}
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '3':
      if (localIP !== 'unknown') { console.log(`\n  ${c.cyan}http://${localIP}:7777${c.reset}`); console.log(`  ${c.dim2}Open on your phone (same WiFi)${c.reset}`); }
      else { console.log(`  ${c.red}Could not detect local IP${c.reset}`); }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '0': return mainMenu();
  }
  return remoteMenu();
}

// ═══════════════════════════════════════════════════════
// BATCH OPERATIONS
// ═══════════════════════════════════════════════════════
async function batchMenu() {
  winTitle(' Batch Operations ');
  winTop();
  winEmpty();
  winBtnRow([
    ['1', 'Git Status All',    'Check all projects'],
    ['2', 'Git Pull All',      'Update all repos'],
    ['3', 'LOC Count All',     'Lines of code report'],
    ['4', 'Health Check',      'Dependencies + issues'],
    ['0', 'Back',               ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1':
      console.log();
      for (const p of PROJECTS) {
        if (!existsSync(p.path)) { console.log(`  ${c.red}○${c.reset} ${c.white}${pad(p.name, 15)}${c.reset} ${c.red}MISSING${c.reset}`); continue; }
        try {
          const s = execSync('git status --short', { cwd: p.path, encoding: 'utf8', timeout: 5000 });
          const lines = s.trim().split('\n').filter(Boolean);
          console.log(`  ${lines.length > 0 ? c.amber + '●' : c.green + '●'}${c.reset} ${c.white}${pad(p.name, 15)}${c.reset} ${lines.length > 0 ? `${c.amber}${lines.length} changed` : `${c.green}clean`}${c.reset}`);
        } catch { console.log(`  ${c.dim2}○${c.reset} ${c.white}${pad(p.name, 15)}${c.reset} ${c.dim2}no git${c.reset}`); }
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '2':
      console.log();
      for (const p of PROJECTS) {
        if (!existsSync(p.path)) continue;
        process.stdout.write(`  ${c.text}Pulling ${p.name}...${c.reset} `);
        try { execSync('git pull', { cwd: p.path, encoding: 'utf8', timeout: 30000 }); console.log(`${c.green}OK${c.reset}`); }
        catch { console.log(`${c.red}FAILED${c.reset}`); }
      }
      hubLog('info', 'Batch git pull');
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '3':
      console.log(`\n  ${c.blue}Scanning...${c.reset}\n`);
      let grandTotal = 0;
      for (const p of PROJECTS) {
        if (!existsSync(p.path)) continue;
        let loc = 0;
        const countLoc = (dir, depth = 0) => {
          if (depth > 3) return;
          try {
            readdirSync(dir).forEach(f => {
              if (f.startsWith('.') || ['node_modules','__pycache__','dist','build','android','www','.git'].includes(f)) return;
              const fp = join(dir, f);
              try {
                const st = statSync(fp);
                if (st.isDirectory()) countLoc(fp, depth + 1);
                else if (/\.(js|py|ts|jsx|tsx|html|css)$/.test(f) && st.size < 500000) {
                  loc += readFileSync(fp, 'utf8').split('\n').length;
                }
              } catch {}
            });
          } catch {}
        };
        countLoc(p.path);
        grandTotal += loc;
        console.log(`  ${c.cyan}${loc.toLocaleString().padStart(8)}${c.reset}  ${c.white}${p.name}${c.reset}`);
      }
      console.log(`  ${c.dark}${'─'.repeat(24)}${c.reset}`);
      console.log(`  ${c.green}${c.bold}${grandTotal.toLocaleString().padStart(8)}${c.reset}  ${c.white}TOTAL${c.reset}`);
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '4':
      console.log(`\n  ${c.blue}Health check...${c.reset}\n`);
      for (const p of PROJECTS) {
        if (!existsSync(p.path)) { console.log(`  ${c.red}✗${c.reset} ${c.white}${p.name}${c.reset} ${c.red}— missing${c.reset}`); continue; }
        let issues = [];
        try {
          const s = execSync('git status --short', { cwd: p.path, encoding: 'utf8', timeout: 5000 });
          if (s.trim()) issues.push(`${s.trim().split('\n').length} uncommitted`);
        } catch { issues.push('no git'); }
        if (existsSync(join(p.path, 'package.json')) && !existsSync(join(p.path, 'node_modules'))) issues.push('npm install needed');
        if (existsSync(join(p.path, '.env.example')) && !existsSync(join(p.path, '.env'))) issues.push('.env missing');
        console.log(`  ${issues.length ? c.amber + '!' : c.green + '✓'}${c.reset} ${c.white}${pad(p.name, 15)}${c.reset} ${issues.length ? `${c.amber}${issues.join(', ')}` : `${c.green}healthy`}${c.reset}`);
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      break;
    case '0': return mainMenu();
  }
  return batchMenu();
}

// ═══════════════════════════════════════════════════════
// DIAGNOSTICS
// ═══════════════════════════════════════════════════════
async function systemDiag() {
  winTitle(' System Diagnostics ');
  winTop();
  winEmpty();
  winSection('Environment');
  winEmpty();

  const checks = [
    ['Node.js', () => { try { return execSync('node -v', { encoding: 'utf8' }).trim(); } catch { return 'NOT FOUND'; } }],
    ['npm', () => { try { return 'v' + execSync('npm -v', { encoding: 'utf8' }).trim(); } catch { return 'NOT FOUND'; } }],
    ['Git', () => { try { return execSync('git --version', { encoding: 'utf8' }).trim().replace('git version ', ''); } catch { return 'NOT FOUND'; } }],
    ['Ollama', () => { try { execSync('ollama list', { encoding: 'utf8', timeout: 3000 }); return 'Online'; } catch { try { execSync('ollama --version', { encoding: 'utf8', timeout: 3000 }); return 'Installed (not running)'; } catch { return 'Not installed'; } } }],
    ['Claude Code', () => { try { execSync('claude --version', { encoding: 'utf8', timeout: 3000 }); return 'Installed'; } catch { return 'Not found'; } }],
    ['Android Studio', () => existsSync('C:\\Program Files\\Android\\Android Studio\\bin\\studio64.exe') ? 'Installed' : '—'],
  ];

  checks.forEach(([label, check]) => {
    const result = check();
    const color = result.includes('NOT') || result === '—' || result.includes('Not') ? c.amber : c.green;
    winLine(`  ${c.dim2}${pad(label + ':', 18)}${c.reset} ${color}${result}${c.reset}`, 1);
  });

  winEmpty();
  winSep();
  winSection('Storage');
  winEmpty();

  Object.entries(DIRS).forEach(([name, dir]) => {
    const files = listFiles(dir);
    let totalSize = 0;
    files.forEach(f => { try { totalSize += statSync(f.path).size; } catch {} });
    const icon = files.length > 0 ? `${c.green}■` : `${c.dark}□`;
    winLine(`  ${icon}${c.reset} ${c.white}${name.padEnd(12)}${c.reset} ${c.dim2}${String(files.length).padStart(3)} files  ${formatSize(totalSize).padStart(10)}${c.reset}`, 1);
  });

  winEmpty();
  winSep();
  winSection('Project Health');
  winEmpty();

  for (const p of PROJECTS) {
    if (!existsSync(p.path)) {
      winLine(`  ${c.red}○${c.reset} ${c.white}${p.name.padEnd(15)}${c.reset} ${c.red}MISSING${c.reset}`, 1);
      continue;
    }
    let gitInfo = '';
    try {
      const status = execSync('git status --short', { cwd: p.path, encoding: 'utf8', timeout: 3000 });
      const changes = status.trim().split('\n').filter(Boolean).length;
      gitInfo = changes > 0 ? `${c.amber}${changes} uncommitted` : `${c.green}clean`;
    } catch { gitInfo = `${c.dim2}no git`; }
    winLine(`  ${c.green}●${c.reset} ${c.white}${p.name.padEnd(15)}${c.reset} ${gitInfo}${c.reset}`, 1);
  }

  winEmpty();
  winSep();
  winBtnRow([['0', 'Back', '']]);
  winEmpty();
  winBottom();

  await winPrompt();
  return mainMenu();
}

// ═══════════════════════════════════════════════════════
// FLIGHT RECORDER (Logs)
// ═══════════════════════════════════════════════════════
async function viewLogs() {
  winTitle(' Flight Recorder ');
  winTop();
  winEmpty();

  try {
    const raw = readFileSync(LOG_FILE, 'utf8');
    const lines = raw.trim().split('\n');
    const recent = lines.slice(-30);
    winLine(`${c.dim2}Showing ${recent.length} of ${lines.length} records${c.reset}`, 2);
    winSep();
    winEmpty();
    recent.forEach(l => {
      let color = c.dim2;
      if (l.includes('[ERROR]')) color = c.red;
      else if (l.includes('[WARN]')) color = c.amber;
      else if (l.includes('[INFO]')) color = c.text;
      winLine(`${color}${l.substring(0, W - 2)}${c.reset}`, 2);
    });
  } catch {
    winLine(`${c.dim2}No log data recorded${c.reset}`, 3);
  }

  winEmpty();
  winSep();
  winBtnRow([
    ['1', 'Wipe Logs', ''],
    ['0', 'Back',        ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  if (choice.trim() === '1') {
    writeFileSync(LOG_FILE, '');
    hubLog('info', 'Logs wiped');
    console.log(`  ${c.green}✓ Logs cleared${c.reset}`);
    await ask(`  ${c.dim2}[Enter]${c.reset} `);
  }
  return mainMenu();
}

// ═══════════════════════════════════════════════════════
// COMMANDER'S LOG — Notes
// ═══════════════════════════════════════════════════════
const NOTES_FILE = join(ROOT, 'agents', 'notes.json');

function loadNotes() {
  try { return JSON.parse(readFileSync(NOTES_FILE, 'utf8')); }
  catch { return []; }
}
function saveNotes(notes) {
  writeFileSync(NOTES_FILE, JSON.stringify(notes, null, 2));
}

async function notesMenu() {
  winTitle(" Commander's Log ");
  winMenuBar(['All', 'Add', 'Search']);
  winTop();
  winEmpty();

  const notes = loadNotes();

  if (!notes.length) {
    winLine(`${c.dim2}No entries. Add your first note below.${c.reset}`, 3);
  } else {
    notes.slice(-20).forEach((n, i) => {
      const ts = new Date(n.ts).toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' });
      const tag = n.tag ? `${c.amber}[${n.tag}]${c.reset} ` : '';
      winLine(`${c.dim2}${String(i + 1).padStart(3)}.${c.reset} ${tag}${c.white}${n.text.substring(0, 42)}${c.reset} ${c.dim2}${ts}${c.reset}`, 2);
    });
  }

  winEmpty();
  winSep();
  winBtnRow([
    ['1', 'Add Note',         'Quick text entry'],
    ['2', 'Add Tagged Note',  'With category'],
    ['3', 'Search Notes',     ''],
    ['4', 'Clear All',        ''],
    ['0', 'Back',              ''],
  ]);
  winEmpty();
  winBottom();

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1': {
      const text = await ask(`  ${c.text}Note: ${c.reset}`);
      if (text.trim()) {
        const notes = loadNotes();
        notes.push({ text: text.trim(), ts: new Date().toISOString(), tag: '' });
        saveNotes(notes);
        console.log(`  ${c.green}✓ Saved${c.reset}`);
        hubLog('info', 'Note added');
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    }
    case '2': {
      const tag = await ask(`  ${c.text}Tag (TODO, BUG, IDEA): ${c.reset}`);
      const text = await ask(`  ${c.text}Note: ${c.reset}`);
      if (text.trim()) {
        const notes = loadNotes();
        notes.push({ text: text.trim(), ts: new Date().toISOString(), tag: (tag.trim() || '').toUpperCase() });
        saveNotes(notes);
        console.log(`  ${c.green}✓ Saved [${tag.trim().toUpperCase()}]${c.reset}`);
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    }
    case '3': {
      const query = await ask(`  ${c.text}Search: ${c.reset}`);
      if (query.trim()) {
        const q = query.trim().toLowerCase();
        const results = loadNotes().filter(n => n.text.toLowerCase().includes(q) || (n.tag || '').toLowerCase().includes(q));
        console.log(`\n  ${c.blue}${results.length} result(s):${c.reset}`);
        results.forEach(n => {
          const tag = n.tag ? `${c.amber}[${n.tag}]${c.reset} ` : '';
          console.log(`  ${tag}${c.white}${n.text}${c.reset}`);
        });
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      break;
    }
    case '4': {
      const confirm = await ask(`  ${c.red}Clear all notes? [y/N]: ${c.reset}`);
      if (confirm.trim().toLowerCase() === 'y') {
        saveNotes([]);
        console.log(`  ${c.green}✓ Notes cleared${c.reset}`);
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      break;
    }
    case '0': return mainMenu();
  }
  return notesMenu();
}

// ═══════════════════════════════════════════════════════
// [G] GOOGLE SHEETS SYNC — Backup & Reference System
// ═══════════════════════════════════════════════════════
async function sheetsMenu() {
  let sync, auth;
  try {
    sync = require('./agent_mode/sheets/sync');
    auth = require('./agent_mode/sheets/auth');
  } catch (e) {
    winTitle(' Google Sheets Sync ');
    winTop();
    winEmpty();
    winLine(`${c.red}Sheets module not loaded: ${e.message.substring(0, 50)}${c.reset}`, 3);
    winEmpty();
    winSep();
    winBtnRow([['0', 'Back', '']]);
    winEmpty();
    winBottom();
    await winPrompt();
    return mainMenu();
  }

  const hasAuth = auth.hasToken();
  const crews = sync.getConfiguredCrews();
  const status = sync.getSyncStatus();

  winTitle(' Google Sheets Sync — CHERP Backup ');
  winMenuBar(['Sync', 'Crews', 'Config']);
  winTop();
  winEmpty();

  // Auth status
  const authIcon = hasAuth ? `${c.green}●${c.reset}` : `${c.red}○${c.reset}`;
  const authLabel = hasAuth ? 'Connected' : 'Not authorized';
  winLine(`${authIcon} ${c.white}Google Auth:${c.reset} ${hasAuth ? c.green : c.red}${authLabel}${c.reset}    ${c.dim2}Crews linked: ${crews.length}${c.reset}`, 1);
  winEmpty();

  // Crew sheets status
  if (crews.length > 0) {
    winSep();
    winSection('Linked Crews');
    winEmpty();
    crews.forEach((code, i) => {
      const s = status[code];
      const lastPush = s.lastPush ? new Date(s.lastPush).toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : 'never';
      const lastPull = s.lastPull ? new Date(s.lastPull).toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : 'never';
      winLine(`  ${c.cyan}${String(i + 1).padStart(2)}.${c.reset} ${c.white}${pad(s.crewName, 20)}${c.reset} ${c.dim2}Push: ${lastPush}${c.reset}  ${c.dim2}Pull: ${lastPull}${c.reset}`, 1);
    });
    winEmpty();
  } else {
    winLine(`${c.dim2}No crew sheets configured yet. Create one below.${c.reset}`, 3);
    winEmpty();
  }

  winSep();
  winSection('Actions');
  winEmpty();
  winBtnRow([
    ['1', 'Sync Now',           'Push CHERP → Sheets (all crews)'],
    ['2', 'Pull Changes',       'Import Sheet edits → CHERP'],
    ['3', 'Create Crew Sheet',  'New spreadsheet for a crew'],
    ['4', 'Sync Status',        'Detailed last-sync report'],
    ['5', 'Open in Browser',    'View crew spreadsheet'],
    ['6', 'Authorize Google',   hasAuth ? 'Re-auth' : 'Required first'],
    ['0', 'Back',                ''],
  ]);
  winEmpty();
  winBottom();
  winStatusBar(` Sheets Sync`, `${crews.length} crew(s) | ${hasAuth ? 'Authorized' : 'Needs Auth'} `);

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1': {
      if (!hasAuth) {
        console.log(`  ${c.red}Not authorized. Run option [6] first.${c.reset}`);
        await ask(`  ${c.dim2}[Enter]${c.reset} `);
        return sheetsMenu();
      }
      if (crews.length === 0) {
        console.log(`  ${c.amber}No crews configured. Create a crew sheet first.${c.reset}`);
        await ask(`  ${c.dim2}[Enter]${c.reset} `);
        return sheetsMenu();
      }
      console.log(`\n  ${c.cyan}Pushing data to Sheets...${c.reset}`);
      try {
        const results = await sync.pushSyncAll();
        for (const [code, res] of Object.entries(results)) {
          if (res.error) {
            console.log(`  ${c.red}✗ ${code}: ${res.error}${c.reset}`);
          } else {
            const tabSummary = Object.entries(res.tabs).map(([name, t]) => `${name}:${t.rows}`).join(', ');
            console.log(`  ${c.green}✓ ${code}${c.reset} — ${c.dim2}${tabSummary}${c.reset}`);
          }
        }
        hubLog('info', `Sheets push sync: ${crews.length} crew(s)`);
      } catch (e) {
        console.log(`  ${c.red}Sync failed: ${e.message}${c.reset}`);
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return sheetsMenu();
    }
    case '2': {
      if (!hasAuth || crews.length === 0) {
        console.log(`  ${c.red}${!hasAuth ? 'Not authorized.' : 'No crews configured.'}${c.reset}`);
        await ask(`  ${c.dim2}[Enter]${c.reset} `);
        return sheetsMenu();
      }
      console.log(`\n  ${c.cyan}Pulling changes from Sheets...${c.reset}`);
      try {
        for (const code of crews) {
          const result = await sync.pullSync(code);
          const changed = result.changes;
          const icon = changed > 0 ? `${c.amber}↓` : `${c.green}✓`;
          console.log(`  ${icon}${c.reset} ${code}: ${changed} change(s) imported`);
          if (result.errors.length) {
            result.errors.forEach(e => console.log(`    ${c.red}${e}${c.reset}`));
          }
        }
        hubLog('info', `Sheets pull sync: ${crews.length} crew(s)`);
      } catch (e) {
        console.log(`  ${c.red}Pull failed: ${e.message}${c.reset}`);
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return sheetsMenu();
    }
    case '3': {
      if (!hasAuth) {
        console.log(`  ${c.red}Not authorized. Run option [6] first.${c.reset}`);
        await ask(`  ${c.dim2}[Enter]${c.reset} `);
        return sheetsMenu();
      }
      const teamCode = await ask(`  ${c.text}Team code: ${c.reset}`);
      const crewName = await ask(`  ${c.text}Crew name: ${c.reset}`);
      if (teamCode.trim()) {
        console.log(`\n  ${c.cyan}Creating spreadsheet...${c.reset}`);
        try {
          const id = await sync.createCrewSheet(teamCode.trim(), crewName.trim());
          const url = `https://docs.google.com/spreadsheets/d/${id}`;
          console.log(`  ${c.green}✓ Created!${c.reset}`);
          console.log(`  ${c.blue}${url}${c.reset}`);
          hubLog('info', `Created crew sheet: ${teamCode.trim()}`);
          // Auto-push data
          console.log(`  ${c.cyan}Pushing initial data...${c.reset}`);
          const pushResult = await sync.pushSync(teamCode.trim());
          const tabSummary = Object.entries(pushResult.tabs).map(([name, t]) => `${name}:${t.rows}`).join(', ');
          console.log(`  ${c.green}✓ ${tabSummary}${c.reset}`);
        } catch (e) {
          console.log(`  ${c.red}Failed: ${e.message}${c.reset}`);
        }
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return sheetsMenu();
    }
    case '4': {
      console.log();
      if (crews.length === 0) {
        console.log(`  ${c.dim2}No crews configured.${c.reset}`);
      } else {
        for (const [code, s] of Object.entries(status)) {
          console.log(`  ${c.white}${s.crewName}${c.reset} ${c.dim2}(${code})${c.reset}`);
          console.log(`    ${c.dim2}Sheet:${c.reset} ${c.blue}${s.url}${c.reset}`);
          console.log(`    ${c.dim2}Last push:${c.reset} ${s.lastPush || 'never'}`);
          console.log(`    ${c.dim2}Last pull:${c.reset} ${s.lastPull || 'never'}`);
          console.log();
        }
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return sheetsMenu();
    }
    case '5': {
      if (crews.length === 0) {
        console.log(`  ${c.dim2}No crew sheets to open.${c.reset}`);
      } else if (crews.length === 1) {
        const url = sync.getSheetUrl(crews[0]);
        try { require('child_process').execSync(`start "" "${url}"`, { shell: 'cmd.exe', stdio: 'ignore' }); }
        catch { console.log(`  ${c.blue}${url}${c.reset}`); }
      } else {
        console.log();
        crews.forEach((code, i) => {
          console.log(`  ${c.cyan}${i + 1}.${c.reset} ${status[code].crewName} ${c.dim2}(${code})${c.reset}`);
        });
        const pick = await ask(`\n  ${c.text}Open #: ${c.reset}`);
        const idx = parseInt(pick) - 1;
        if (idx >= 0 && idx < crews.length) {
          const url = sync.getSheetUrl(crews[idx]);
          try { require('child_process').execSync(`start "" "${url}"`, { shell: 'cmd.exe', stdio: 'ignore' }); }
          catch { console.log(`  ${c.blue}${url}${c.reset}`); }
        }
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return sheetsMenu();
    }
    case '6': {
      console.log(`\n  ${c.cyan}Opening Google authorization in browser...${c.reset}`);
      try {
        await auth.authorizeInteractive();
        console.log(`  ${c.green}✓ Authorized! Token saved.${c.reset}`);
        hubLog('info', 'Google Sheets authorized');
      } catch (e) {
        console.log(`  ${c.red}Auth failed: ${e.message}${c.reset}`);
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return sheetsMenu();
    }
    case '0': return mainMenu();
    default: return sheetsMenu();
  }
}

// ═══════════════════════════════════════════════════════
// [M] AGENT MODE — Hybrid AI Framework
// ═══════════════════════════════════════════════════════
async function agentMode() {
  // Dynamic import of agent_mode core
  let Orchestrator;
  try {
    const mod = await import('./agent_mode/core/orchestrator.js');
    Orchestrator = mod.Orchestrator;
  } catch (e) {
    winTitle(' Agent Mode ');
    winTop();
    winEmpty();
    winLine(`${c.red}Agent Mode not loaded: ${e.message.substring(0, 50)}${c.reset}`, 3);
    winLine(`${c.dim2}Ensure agent_mode/core/ files exist${c.reset}`, 3);
    winEmpty();
    winSep();
    winBtnRow([['0', 'Back', '']]);
    winEmpty();
    winBottom();
    await winPrompt();
    return mainMenu();
  }

  const orch = new Orchestrator();
  const detection = orch.init();
  const dash = orch.dashboard();

  winTitle(' Agent Mode — Hybrid AI Framework ');
  winMenuBar(['Agents', 'Tasks', 'Offline', 'Review', 'Logs']);
  winTop();

  // Mode status
  winEmpty();
  const modeColor = detection.mode === 'hybrid' ? c.green : c.amber;
  const modeLabel = detection.mode === 'hybrid' ? 'HYBRID' : 'OFFLINE';
  winLine(`${modeColor}●${c.reset} ${c.white}${c.bold}Mode: ${modeLabel}${c.reset}    ${detection.claude ? `${c.green}●${c.reset} Claude` : `${c.red}○${c.reset} Claude`}    ${detection.ollama ? `${c.green}●${c.reset} Ollama` : `${c.red}○${c.reset} Ollama`}`, 1);
  winEmpty();

  // Queue summary
  const q = dash.queue;
  winLine(`${c.dim2}Tasks:${c.reset} ${c.white}${q.total}${c.reset}  ${c.dim2}Queued:${c.reset} ${c.cyan}${q.queued || 0}${c.reset}  ${c.dim2}Running:${c.reset} ${c.green}${q.in_progress || 0}${c.reset}  ${c.dim2}Review:${c.reset} ${c.amber}${q.pendingReview}${c.reset}  ${c.dim2}Offline:${c.reset} ${c.blue}${q.offlineReady}${c.reset}`, 1);
  winSep();

  // Agent cards
  winEmpty();
  winSection('Registered Agents');
  winEmpty();

  const agents = dash.agents;
  agents.forEach((a, i) => {
    const stColor = a.status === 'running' ? c.green : a.status === 'failed' ? c.red : a.status === 'idle' ? c.dim2 : c.amber;
    const stIcon = a.status === 'running' ? '●' : a.status === 'failed' ? '✗' : '○';
    const avail = a.available ? `${c.green}▰` : `${c.red}▱`;
    winLine(`  ${c.cyan}${String(i + 1).padStart(2)}.${c.reset} ${stColor}${stIcon}${c.reset} ${c.white}${pad(a.displayName, 22)}${c.reset} ${c.dim2}${pad(a.role, 16)}${c.reset} ${avail}${c.reset} ${c.dim2}${a.base}${c.reset}`, 1);
  });

  winEmpty();
  winSep();
  winSection('Actions');
  winEmpty();
  winBtnRow([
    ['1', 'Create Task',         'Queue a new task for agents'],
    ['2', 'Run Offline Batch',   'Execute all offline-safe queued tasks'],
    ['3', 'View Queue',          'See all tasks by status'],
    ['4', 'Review Pending',      `${q.pendingReview} tasks waiting for Claude`],
    ['5', 'Agent Details',       'View/edit agent profiles'],
    ['6', 'Assign Task',         'Manually assign task to agent'],
    ['7', 'Build Review Packet', 'Package work for Claude re-entry'],
    ['8', 'Switch Mode',         `Currently: ${modeLabel}`],
    ['T', 'Training Stats',      'Curate training log + show keep rate'],
    ['N', 'Edit Agent Notes',    'Open an agent notes.md in notepad'],
    ['0', 'Back',                 ''],
  ]);
  winEmpty();
  winBottom();
  winStatusBar(` Agent Mode — ${modeLabel}`, `${agents.length} agents | ${q.total} tasks `);

  const choice = await winPrompt();
  switch (choice.trim()) {
    case '1': {
      console.log(`\n  ${c.text}Task types: scan, index, draft_patch, draft_test, summarize, memory_extract, general${c.reset}`);
      const type = await ask(`  ${c.text}Type: ${c.reset}`);
      const objective = await ask(`  ${c.text}Objective: ${c.reset}`);
      const scope = await ask(`  ${c.text}File scope (comma-sep, or Enter for any): ${c.reset}`);
      if (objective.trim()) {
        const task = orch.createTask({
          type: type.trim() || 'general',
          objective: objective.trim(),
          scope: scope.trim() ? scope.trim().split(',').map(s => s.trim()) : [],
        });
        console.log(`  ${c.green}✓ Task ${task.id} created${task.assignedAgent ? ` → assigned to ${task.assignedAgent}` : ''}${c.reset}`);
        hubLog('info', `Agent task: ${task.objective}`);
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return agentMode();
    }
    case '2': {
      console.log(`\n  ${c.blue}Running offline batch...${c.reset}`);
      const results = await orch.runOfflineBatch();
      console.log(`  ${c.green}✓ ${results.length} tasks executed${c.reset}`);
      results.forEach(r => {
        if (r.success) console.log(`    ${c.green}●${c.reset} ${r.agent}: ${r.task?.objective?.substring(0, 40) || ''}${c.reset}`);
        else console.log(`    ${c.red}✗${c.reset} ${r.agent || '?'}: ${r.error?.substring(0, 40) || ''}${c.reset}`);
      });
      hubLog('info', `Offline batch: ${results.filter(r => r.success).length}/${results.length} succeeded`);
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return agentMode();
    }
    case '3': {
      const all = orch.queue.tasks;
      const statuses = ['queued', 'in_progress', 'waiting_for_claude', 'approved_for_merge', 'archived'];
      console.log();
      for (const st of statuses) {
        const tasks = all.filter(t => t.status === st);
        if (tasks.length === 0) continue;
        const stColor = st === 'queued' ? c.dim2 : st === 'in_progress' ? c.cyan : st === 'waiting_for_claude' ? c.amber : st === 'approved_for_merge' ? c.green : c.dark;
        console.log(`  ${stColor}${c.bold}━━ ${st.toUpperCase()} (${tasks.length}) ━━${c.reset}`);
        tasks.forEach(t => {
          console.log(`    ${c.dim2}${t.id}${c.reset} ${c.white}${t.objective.substring(0, 45)}${c.reset} ${c.dim2}[${t.type}]${c.reset}`);
        });
      }
      if (all.length === 0) console.log(`  ${c.dim2}No tasks in queue${c.reset}`);
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return agentMode();
    }
    case '4': {
      const pending = orch.queue.getForClaudeReview();
      if (pending.length === 0) {
        console.log(`\n  ${c.dim2}No tasks waiting for review${c.reset}`);
      } else {
        console.log(`\n  ${c.amber}${pending.length} task(s) pending review:${c.reset}`);
        pending.forEach((t, i) => {
          console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${t.objective.substring(0, 45)}${c.reset}`);
          if (t.output) console.log(`     ${c.dim2}Output: ${t.output.substring(0, 60)}...${c.reset}`);
        });
        const pick = await ask(`\n  ${c.text}Review # (or Enter to skip): ${c.reset}`);
        const idx = parseInt(pick) - 1;
        if (idx >= 0 && idx < pending.length) {
          const t = pending[idx];
          console.log(`\n  ${c.blue}Task: ${t.objective}${c.reset}`);
          console.log(`  ${c.dim2}Type: ${t.type} | Agent: ${t.assignedAgent}${c.reset}`);
          if (t.output) {
            console.log(`\n  ${c.text}Output:${c.reset}`);
            console.log(`  ${c.dim2}${t.output.substring(0, 500)}${c.reset}`);
          }
          const verdict = await ask(`\n  ${c.text}Approve? [Y/n]: ${c.reset}`);
          if (verdict.trim().toUpperCase() === 'N') {
            const reason = await ask(`  ${c.text}Reason: ${c.reset}`);
            orch.reviewTask(t.id, false, reason.trim());
            console.log(`  ${c.red}✗ Rejected — back to queue${c.reset}`);
          } else {
            orch.reviewTask(t.id, true);
            console.log(`  ${c.green}✓ Approved${c.reset}`);
          }
        }
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return agentMode();
    }
    case '5': {
      console.log();
      agents.forEach((a, i) => {
        console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${c.bold}${a.displayName}${c.reset}`);
        console.log(`     ${c.dim2}Model: ${a.base} | Role: ${a.role} | Personality: ${a.personality || 'none'}${c.reset}`);
        console.log(`     ${c.dim2}Status: ${a.status} | Mode: ${a.modeEligibility} | Available: ${a.available ? 'yes' : 'no'}${c.reset}`);
        console.log();
      });
      const agentPick = await ask(`  ${c.text}Agent # to edit (or Enter to skip): ${c.reset}`);
      const ai = parseInt(agentPick) - 1;
      if (ai >= 0 && ai < agents.length) {
        console.log(`  ${c.dim2}1=Rename 2=Set Role 3=Set Personality${c.reset}`);
        const action = await ask(`  ${c.text}Action: ${c.reset}`);
        if (action.trim() === '1') {
          const name = await ask(`  ${c.text}New name: ${c.reset}`);
          if (name.trim()) { orch.registry.rename(agents[ai].id, name.trim()); console.log(`  ${c.green}✓ Renamed${c.reset}`); }
        } else if (action.trim() === '2') {
          console.log(`  ${c.dim2}Roles: Repo Scanner, Patch Drafter, Diff Reviewer, Test Builder, Log Summarizer, Memory Curator, General Worker, Offline Prep Worker${c.reset}`);
          const role = await ask(`  ${c.text}Role: ${c.reset}`);
          if (role.trim()) { orch.registry.setRole(agents[ai].id, role.trim()); console.log(`  ${c.green}✓ Role set${c.reset}`); }
        } else if (action.trim() === '3') {
          console.log(`  ${c.dim2}Personalities: primary-coder, conservative-coder, fast-scanner, test-writer, summarizer, curator${c.reset}`);
          const pers = await ask(`  ${c.text}Personality: ${c.reset}`);
          if (pers.trim()) { orch.registry.setPersonality(agents[ai].id, pers.trim()); console.log(`  ${c.green}✓ Personality set${c.reset}`); }
        }
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return agentMode();
    }
    case '6': {
      const pending = orch.queue.listByStatus('queued');
      if (pending.length === 0) { console.log(`  ${c.dim2}No queued tasks${c.reset}`); await ask(`  ${c.dim2}[Enter]${c.reset} `); return agentMode(); }
      console.log(`\n  ${c.text}Queued tasks:${c.reset}`);
      pending.forEach((t, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${t.objective.substring(0, 45)}${c.reset}`));
      const tPick = await ask(`  ${c.text}Task #: ${c.reset}`);
      const tIdx = parseInt(tPick) - 1;
      if (tIdx >= 0 && tIdx < pending.length) {
        console.log(`\n  ${c.text}Agents:${c.reset}`);
        agents.forEach((a, i) => console.log(`  ${c.cyan}${i + 1}.${c.reset} ${c.white}${a.displayName}${c.reset} ${c.dim2}(${a.status})${c.reset}`));
        const aPick = await ask(`  ${c.text}Agent #: ${c.reset}`);
        const aIdx = parseInt(aPick) - 1;
        if (aIdx >= 0 && aIdx < agents.length) {
          orch.assignTask(pending[tIdx].id, agents[aIdx].id);
          console.log(`  ${c.green}✓ Assigned${c.reset}`);

          const runNow = await ask(`  ${c.text}Execute now? [Y/n]: ${c.reset}`);
          if (runNow.trim().toUpperCase() !== 'N') {
            console.log(`  ${c.blue}Executing...${c.reset}`);
            const result = await orch.executeTask(pending[tIdx].id);
            if (result.success) {
              console.log(`  ${c.green}✓ Complete${c.reset}`);
              console.log(`  ${c.dim2}${result.output?.substring(0, 200) || ''}${c.reset}`);
            } else {
              console.log(`  ${c.red}✗ ${result.error}${c.reset}`);
            }
          }
        }
      }
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return agentMode();
    }
    case '7': {
      const packet = orch.buildClaudeReentryPacket();
      const packetPath = join(ROOT, 'agent_mode', 'offline', 'review_queue', `packet-${Date.now().toString(36)}.json`);
      writeFileSync(packetPath, JSON.stringify(packet, null, 2));
      console.log(`\n  ${c.green}✓ Review packet built${c.reset}`);
      console.log(`  ${c.dim2}${packet.pendingReviewCount} tasks packaged${c.reset}`);
      console.log(`  ${c.dim2}Saved: ${packetPath}${c.reset}`);
      hubLog('info', `Review packet: ${packet.pendingReviewCount} tasks`);
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return agentMode();
    }
    case '8': {
      // Merged orchestrator (post-Codex) exposes getMode/setMode directly
      // on the orch object instead of the old nested orch.mode.*.
      const current = orch.getMode();
      const newMode = current === 'hybrid' ? 'offline' : 'hybrid';
      orch.setMode(newMode);
      console.log(`  ${c.green}✓ Switched to ${newMode.toUpperCase()} mode${c.reset}`);
      hubLog('info', `Mode: ${newMode}`);
      await ask(`  ${c.dim2}[Enter]${c.reset} `);
      return agentMode();
    }
    case 'T': case 't': {
      // Run curate.js and stream its output directly into the hub terminal.
      // Also offer the approved-only pass so Ken can see both numbers in one shot.
      console.log();
      try {
        const { execSync } = await import('child_process');
        const all = execSync('node agent_mode/training/curate.js', { cwd: ROOT, encoding: 'utf8' });
        console.log(all.replace(/^/gm, '  '));
        const approvedOnly = execSync('node agent_mode/training/curate.js --approved-only', { cwd: ROOT, encoding: 'utf8' });
        console.log();
        console.log(`  ${c.dim2}── approved-only pass ──${c.reset}`);
        console.log(approvedOnly.replace(/^/gm, '  '));
        hubLog('info', 'Training curate run from hub');
      } catch (err) {
        console.log(`  ${c.red}curate failed: ${err.message}${c.reset}`);
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return agentMode();
    }
    case 'N': case 'n': {
      // Open per-agent notes.md in notepad. Scaffolds the memory dir if it
      // doesn't exist yet so you can tune brand-new agents without touching disk.
      console.log();
      agents.forEach((a, i) => {
        console.log(`  ${c.cyan}${String(i + 1).padStart(2)}.${c.reset} ${c.white}${pad(a.displayName, 22)}${c.reset} ${c.dim2}${a.base}${c.reset}`);
      });
      const pick = await ask(`\n  ${c.text}Open notes # (0 cancel): ${c.reset}`);
      const n = parseInt(pick.trim(), 10);
      if (!Number.isInteger(n) || n < 1 || n > agents.length) return agentMode();
      const agent = agents[n - 1];
      try {
        const mem = await import('./agent_mode/core/memory.js');
        mem.ensureMemoryDir(agent);
        const slug = String(agent.id).replace(/[:/\\?*"<>|]/g, '-');
        const notesPath = join(ROOT, 'agent_mode', 'memories', slug, 'notes.md');
        console.log(`  ${c.dim2}Opening ${notesPath}${c.reset}`);
        const { spawn } = await import('child_process');
        spawn('notepad.exe', [notesPath], { detached: true, stdio: 'ignore' }).unref();
        hubLog('info', `Opened notes editor for ${agent.id}`);
      } catch (err) {
        console.log(`  ${c.red}notes open failed: ${err.message}${c.reset}`);
      }
      await ask(`\n  ${c.dim2}[Enter]${c.reset} `);
      return agentMode();
    }
    case '0': return mainMenu();
    default: return agentMode();
  }
}

// ═══════════════════════════════════════════════════════
// LAUNCH
// ═══════════════════════════════════════════════════════
mainMenu();
