/*
  Factorio game file scanner — reads install, saves, config, mods
  to extract knowledge KenAI can use for strategic decisions.

  Scans:
  - Save files (zipped Lua) → names, sizes, timestamps, detect active save
  - Config → keybindings, graphics settings
  - Mods → installed mod list
  - Player data → campaign progress, playtime
  - Game log → version, errors, last session

  Writes to factorio-game-knowledge.json in KenAI's memory dir.
*/

import { readdirSync, readFileSync, statSync, existsSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR = join(__dirname, '..', 'memories', 'ken-ai-latest');

const FACTORIO_EXE = 'C:/Program Files (x86)/Steam/steamapps/common/Factorio/bin/x64/Factorio.exe';
const FACTORIO_ROOT = 'C:/Program Files (x86)/Steam/steamapps/common/Factorio';
const FACTORIO_DATA = 'C:/Users/Ken/AppData/Roaming/Factorio';
const SAVES_DIR = join(FACTORIO_DATA, 'saves');
const CONFIG_INI = join(FACTORIO_DATA, 'config', 'config.ini');
const PLAYER_DATA = join(FACTORIO_DATA, 'player-data.json');
const GAME_LOG = join(FACTORIO_DATA, 'factorio-current.log');
const MODS_DIR = join(FACTORIO_DATA, 'mods');

function scanSaves() {
  if (!existsSync(SAVES_DIR)) return [];
  return readdirSync(SAVES_DIR)
    .filter(f => f.endsWith('.zip'))
    .map(f => {
      try {
        const s = statSync(join(SAVES_DIR, f));
        return {
          name: f.replace('.zip', ''),
          size: Math.round(s.size / 1024) + 'KB',
          modified: s.mtime.toISOString(),
          isAutosave: f.startsWith('_autosave'),
        };
      } catch (e) { return null; }
    })
    .filter(Boolean)
    .sort((a, b) => new Date(b.modified) - new Date(a.modified));
}

function scanConfig() {
  if (!existsSync(CONFIG_INI)) return { error: 'config.ini not found' };
  try {
    const raw = readFileSync(CONFIG_INI, 'utf8');
    const result = {};
    const res = raw.match(/; ?resolution[^=]*=\s*(\d+x\d+)/i);
    if (res) result.resolution = res[1];
    const full = raw.match(/; ?fullscreen[^=]*=\s*(true|false)/i);
    if (full) result.fullscreen = full[1] === 'true';
    return result;
  } catch (e) { return { error: e.message }; }
}

function scanMods() {
  const modList = join(MODS_DIR, 'mod-list.json');
  if (!existsSync(modList)) return [];
  try {
    const d = JSON.parse(readFileSync(modList, 'utf8'));
    return (d.mods || []).filter(m => m.enabled).map(m => m.name);
  } catch (e) { return []; }
}

function scanPlayerData() {
  if (!existsSync(PLAYER_DATA)) return {};
  try {
    const d = JSON.parse(readFileSync(PLAYER_DATA, 'utf8'));
    return {
      campaignProgress: d['available-campaign-levels'] || {},
      serviceUsername: d['service-username'] || null,
    };
  } catch (e) { return {}; }
}

function scanGameLog() {
  if (!existsSync(GAME_LOG)) return {};
  try {
    const raw = readFileSync(GAME_LOG, 'utf8');
    const lines = raw.split('\n').slice(0, 20);
    const version = lines.find(l => l.includes('Factorio'));
    const os = lines.find(l => l.includes('Operating system'));
    return {
      version: version ? version.replace(/^\s*[\d.]+\s*/, '').trim() : 'unknown',
      os: os ? os.replace(/^\s*[\d.]+\s*/, '').trim() : 'unknown',
      logLines: lines.length,
    };
  } catch (e) { return {}; }
}

function detectActiveSave() {
  const saves = scanSaves();
  if (!saves.length) return null;
  // Most recently modified non-autosave, or latest autosave
  const manual = saves.find(s => !s.isAutosave);
  const auto = saves.find(s => s.isAutosave);
  return manual || auto || saves[0];
}

export function fullScan() {
  const knowledge = {
    scannedAt: new Date().toISOString(),
    factorioRoot: FACTORIO_ROOT,
    exe: FACTORIO_EXE,
    installed: existsSync(FACTORIO_EXE),
    gameLog: scanGameLog(),
    config: scanConfig(),
    mods: scanMods(),
    playerData: scanPlayerData(),
    saves: scanSaves(),
    activeSave: detectActiveSave(),
    recipeKnowledge: CORE_RECIPES,
    ratioGuide: RATIO_GUIDE,
  };

  const outPath = join(MEM_DIR, 'factorio-game-knowledge.json');
  writeFileSync(outPath, JSON.stringify(knowledge, null, 2), 'utf8');
  return knowledge;
}

export function getFactorioContext() {
  const active = detectActiveSave();
  const mods = scanMods();
  return [
    'GAME: Factorio 2.0',
    active ? `ACTIVE SAVE: ${active.name} (${active.size}, modified ${active.modified.slice(0,10)})` : 'NO ACTIVE SAVE',
    mods.length ? `MODS: ${mods.join(', ')}` : 'MODS: vanilla',
  ].join('\n');
}

// ── Core game knowledge baked in ─────────────────────────

const CORE_RECIPES = {
  'iron plate': { input: '1 iron ore', time: 3.2, building: 'stone furnace' },
  'copper plate': { input: '1 copper ore', time: 3.2, building: 'stone furnace' },
  'steel plate': { input: '5 iron plates', time: 16, building: 'stone furnace' },
  'iron gear': { input: '2 iron plates', time: 0.5, building: 'assembler' },
  'copper cable': { input: '1 copper plate', output: 2, time: 0.5, building: 'assembler' },
  'green circuit': { input: '1 iron plate + 3 copper cable', time: 0.5, building: 'assembler' },
  'red circuit': { input: '2 green circuits + 2 plastic + 4 copper cable', time: 6, building: 'assembler 2' },
  'blue circuit': { input: '2 red circuits + 20 green circuits + 5 sulfuric acid', time: 10, building: 'assembler 2' },
  'red science': { input: '1 copper plate + 1 iron gear', time: 5, building: 'assembler' },
  'green science': { input: '1 transport belt + 1 inserter', time: 6, building: 'assembler' },
  'transport belt': { input: '1 iron plate + 1 iron gear', output: 2, time: 0.5, building: 'assembler' },
  'inserter': { input: '1 iron gear + 1 iron plate + 1 green circuit', time: 0.5, building: 'assembler' },
};

const RATIO_GUIDE = {
  'copper cable to green circuit': '3 cable assemblers : 2 green circuit assemblers (perfect ratio)',
  'iron smelters per yellow belt': '48 stone furnaces fill 1 yellow belt (15/s)',
  'red science': '1 assembler every 5 seconds = 12/min',
  'green science': '1 assembler every 6 seconds = 10/min. match with 1.2 belt + 1.2 inserter assemblers',
  'steel': '1 steel furnace per 5 iron furnaces (5:1 ratio)',
  'power': '1 steam engine needs 1 boiler. 1 boiler needs ~0.6 offshore pumps',
};

// CLI
if (process.argv[1]?.endsWith('game_scanner.js')) {
  console.log(JSON.stringify(fullScan(), null, 2));
}
