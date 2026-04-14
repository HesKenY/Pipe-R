/* ══════════════════════════════════════════════════════
   Halo game dumper — runs halo_game_dump.py and writes a
   structured markdown snapshot of MCC's loaded state.

   Outputs:
     agent_mode/memories/ken-ai-latest/halo-game-dump.md
         Human-readable bullets. Gets picked up by index.js
         the next time rebuildIndex() runs, so agents can
         retrieve "halo2.dll base 0x7ff61234..." from any
         prompt query about reverse engineering.

     agent_mode/memories/ken-ai-latest/halo-modules.jsonl
         One JSON line per loaded module. Lets agents scan
         for DLL names + base addrs without reparsing md.

   Runs on demand via POST /api/halo/dump/run, or on a
   loop via startGameDumpLoop (default 5 min cadence) so
   the index sees fresh data every few ticks while Ken
   plays.
   ══════════════════════════════════════════════════════ */

import { spawnSync } from 'node:child_process';
import { writeFileSync, appendFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DUMP_PY   = join(__dirname, 'halo_game_dump.py');
const MEM_DIR   = join(__dirname, '..', 'memories', 'ken-ai-latest');
const DUMP_MD   = join(MEM_DIR, 'halo-game-dump.md');
const MOD_JSONL = join(MEM_DIR, 'halo-modules.jsonl');

let _timer = null;
let _running = false;
let _intervalMs = 300000;
let _stats = { runs: 0, startedAt: null, lastRunAt: null, lastDump: null };

function fmtBytes(n) {
  if (!n) return '0';
  if (n < 1024) return n + 'B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(0) + 'K';
  if (n < 1024 * 1024 * 1024) return (n / 1048576).toFixed(1) + 'M';
  return (n / 1073741824).toFixed(2) + 'G';
}

function buildMarkdown(dump) {
  const lines = [];
  lines.push('# Halo MCC — game data dump');
  lines.push('');
  lines.push(`Generated: ${new Date(dump.at * 1000).toISOString()}`);
  lines.push(`MCC PID: ${dump.pid || 'not running'}`);
  lines.push(`Install: ${dump.install_path || 'not found'}`);
  lines.push('');

  if (dump.memory) {
    lines.push('## process memory (committed RW)');
    lines.push(`- rw_regions: ${dump.memory.rw_regions}`);
    lines.push(`- rw_total:   ${fmtBytes(dump.memory.rw_total_bytes)}`);
    lines.push(`- rw_largest: ${fmtBytes(dump.memory.rw_largest_bytes)}`);
    lines.push(`- exec_rw:    ${dump.memory.rw_exec_regions}`);
    lines.push('');
  }

  if (Array.isArray(dump.modules) && dump.modules.length) {
    lines.push('## loaded modules (top by size)');
    lines.push('');
    lines.push('reverse-engineering hints:');
    lines.push('- halo2.dll holds Halo 2 campaign code — AI, physics, damage');
    lines.push('- halo1.dll / halo3.dll / halo4.dll / haloreach.dll / halo3odst.dll are the other titles');
    lines.push('- mcc-win64-shipping.exe is the launcher/menu/engine shell');
    lines.push('- libcef.dll is the embedded browser, ignore');
    lines.push('');
    for (const m of dump.modules) {
      const baseHex = '0x' + BigInt(m.base || 0).toString(16).padStart(12, '0');
      lines.push(`- ${m.name} @ ${baseHex} size=${fmtBytes(m.size)} path=${m.path}`);
    }
    lines.push('');
  }

  if (dump.ext_summary && Object.keys(dump.ext_summary).length) {
    lines.push('## install tree — extensions by total bytes');
    const rows = Object.entries(dump.ext_summary)
      .map(([ext, v]) => ({ ext, ...v }))
      .sort((a, b) => b.bytes - a.bytes);
    for (const r of rows.slice(0, 20)) {
      lines.push(`- ${r.ext || '(none)'}: ${r.count} files, ${fmtBytes(r.bytes)}`);
    }
    lines.push('');
  }

  if (Array.isArray(dump.top_files) && dump.top_files.length) {
    lines.push('## install tree — top 40 files by size');
    lines.push('');
    lines.push('file-type decoder:');
    lines.push('- .map — mission data (AI scripts, geometry, scripts, tags)');
    lines.push('- .dll — native code (reverse-engineering target)');
    lines.push('- .bik — bink video cutscenes');
    lines.push('- .fmod / .bank — FMOD audio');
    lines.push('- .pak / .uasset — packaged assets');
    lines.push('');
    for (const f of dump.top_files.slice(0, 40)) {
      lines.push(`- ${f.rel} (${fmtBytes(f.size)}, ${f.ext || '(none)'})`);
    }
    lines.push('');
  }

  if (Array.isArray(dump.recent_saves) && dump.recent_saves.length) {
    lines.push('## save directory — recent files');
    lines.push(`save_dir: ${dump.save_dir}`);
    for (const s of dump.recent_saves) {
      const when = new Date(s.mtime * 1000).toISOString();
      lines.push(`- ${s.name} (${fmtBytes(s.size)}, mtime=${when})`);
    }
    lines.push('');
  }

  lines.push('## reverse-engineering plan — what to look for');
  lines.push('- health / shield floats: scan halo2.dll data section for 0.0–100.0 range floats that change under damage');
  lines.push('- AI state: look for per-enemy structs near player pointer; likely 200–800 bytes each with team_id byte + alert_state + target_ref');
  lines.push('- damage-apply function: AOB for MUL/FSUB on a float, CMP with zero, branch to death anim — patchable to NOP for invincibility');
  lines.push('- squad coord: elites share a combat_group_id, editable via a single byte flip to break their coordination');
  lines.push('- cheat floor: any address found via delta scan on shield value is a CANDIDATE; confirm with 2nd rescan after a different damage event');
  lines.push('');

  return lines.join('\n');
}

function writeModulesJsonl(dump) {
  if (!Array.isArray(dump.modules)) return;
  const lines = [];
  for (const m of dump.modules) {
    lines.push(JSON.stringify({
      at: dump.at,
      name: m.name,
      path: m.path,
      base_hex: '0x' + BigInt(m.base || 0).toString(16),
      size: m.size,
    }));
  }
  writeFileSync(MOD_JSONL, lines.join('\n') + '\n', 'utf8');
}

function pythonBin() {
  return process.env.HALO_PY || 'python';
}

export function runGameDump() {
  if (!existsSync(MEM_DIR)) mkdirSync(MEM_DIR, { recursive: true });
  const res = spawnSync(pythonBin(), [DUMP_PY], {
    encoding: 'utf8',
    timeout: 60000,
    maxBuffer: 8 * 1024 * 1024,
    windowsHide: true,
  });
  if (res.status !== 0) {
    return { ok: false, error: 'dumper exit ' + res.status, stderr: (res.stderr || '').slice(0, 400) };
  }
  let dump = null;
  try {
    dump = JSON.parse((res.stdout || '').trim());
  } catch (e) {
    return { ok: false, error: 'parse: ' + e.message, stdout: (res.stdout || '').slice(0, 400) };
  }
  try {
    const md = buildMarkdown(dump);
    writeFileSync(DUMP_MD, md, 'utf8');
    writeModulesJsonl(dump);
  } catch (e) {
    return { ok: false, error: 'write: ' + e.message };
  }
  const summary = {
    at: dump.at,
    pid: dump.pid,
    modules: (dump.modules || []).length,
    top_files: (dump.top_files || []).length,
    install_path: dump.install_path,
  };
  _stats.runs += 1;
  _stats.lastRunAt = new Date().toISOString();
  _stats.lastDump = summary;
  return { ok: true, summary };
}

export function startGameDumpLoop(opts = {}) {
  if (_running) return { ok: false, reason: 'already running' };
  _intervalMs = Math.max(60000, Math.min(1800000, opts.intervalMs || 300000));
  _running = true;
  _stats = { runs: 0, startedAt: new Date().toISOString(), lastRunAt: null, lastDump: null };
  const tick = () => {
    if (!_running) return;
    try { runGameDump(); } catch (e) { /* swallow */ }
    if (_running) _timer = setTimeout(tick, _intervalMs);
  };
  _timer = setTimeout(tick, 3000);
  return { ok: true, intervalMs: _intervalMs };
}

export function stopGameDumpLoop() {
  if (!_running) return { ok: false, reason: 'not running' };
  _running = false;
  if (_timer) { clearTimeout(_timer); _timer = null; }
  return { ok: true, stats: _stats };
}

export function gameDumpStatus() {
  return { running: _running, intervalMs: _intervalMs, stats: _stats };
}
