/*
  Halo MCC game file scanner — reads game files to extract
  knowledge KenAI can use for tactical decisions.

  Scans:
  - Map files list → level names + campaign order
  - Save file timestamps → detect current mission progress
  - Config → keybindings, video settings, sensitivity
  - Subtitles → mission dialogue/objectives
  - Terminals → lore (secondary)

  Writes extracted knowledge to halo-memory.md and a structured
  halo-game-knowledge.json for prompt injection.

  Run on boot + after every detected mission change (save mtime).
*/

import { readdirSync, readFileSync, statSync, existsSync, writeFileSync, appendFileSync } from 'node:fs';
import { join, basename, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR = join(__dirname, '..', 'memories', 'ken-ai-latest');

const HALO_ROOT = 'E:/SteamLibrary/steamapps/common/Halo The Master Chief Collection';
const H2_ROOT = join(HALO_ROOT, 'halo2');
const MAPS_DIR = join(H2_ROOT, 'h2_maps_win64_dx11');
const SAVES_DIR = 'C:/Users/Ken/AppData/LocalLow/MCC';
const SETTINGS_INI = join(SAVES_DIR, 'Saved/Config/WindowsNoEditor/GameUserSettings.ini');

const CAMPAIGN_ORDER = [
  { file: '00a_introduction.map', name: 'The Heretic', desc: 'Opening cutscene, Covenant civil war begins' },
  { file: '01a_tutorial.map', name: 'The Armory', desc: 'Tutorial, Master Chief gets new armor on Cairo Station' },
  { file: '01b_spacestation.map', name: 'Cairo Station', desc: 'Defend the station from Covenant boarding party' },
  { file: '03a_oldmombasa.map', name: 'Outskirts', desc: 'Streets of Old Mombasa, Covenant invasion, Jackal snipers' },
  { file: '03b_newmombasa.map', name: 'Metropolis', desc: 'New Mombasa highway, Scarab tank battle, bridge assault' },
  { file: '04a_gasgiant.map', name: 'The Arbiter', desc: 'Play as the Arbiter, gas mine facility, heretic leader' },
  { file: '04b_floodlab.map', name: 'The Oracle', desc: 'Flood outbreak in the gas mine, fight to the bottom' },
  { file: '05a_deltaapproach.map', name: 'Delta Halo', desc: 'Landing on Delta Halo, ruins + Covenant forces, lake crossing' },
  { file: '05b_deltatowers.map', name: 'Regret', desc: 'Underwater temple, kill Prophet of Regret, Covenant honor guard' },
  { file: '06a_sentinelwalls.map', name: 'Sacred Icon', desc: 'Arbiter level, Sentinel Wall, fight through Sentinels to the Library' },
  { file: '06b_floodzone.map', name: 'Quarantine Zone', desc: 'Flood-infested zone, Scorpion tank, race to the Index' },
  { file: '07a_highcharity.map', name: 'Gravemind', desc: 'Master Chief in High Charity, Covenant civil war, prison break' },
  { file: '07b_forerunnership.map', name: 'Uprising', desc: 'Arbiter fights Brutes, Covenant civil war in full swing' },
  { file: '08a_deltacliffs.map', name: 'High Charity', desc: 'Flood invades High Charity, Master Chief pursues Truth' },
  { file: '08b_deltacontrol.map', name: 'The Great Journey', desc: 'Final level, Arbiter + Johnson, stop Tartarus from activating Halo' },
];

function scanMaps() {
  if (!existsSync(MAPS_DIR)) return { error: 'maps dir not found' };
  const files = readdirSync(MAPS_DIR).filter(f => f.endsWith('.map'));
  const campaign = files.filter(f => /^\d{2}[ab]_/.test(f));
  const multiplayer = files.filter(f => !/^\d{2}[ab]_/.test(f));
  return {
    total: files.length,
    campaign: campaign.map(f => {
      const meta = CAMPAIGN_ORDER.find(c => c.file === f);
      return { file: f, name: meta?.name || f, desc: meta?.desc || '' };
    }),
    multiplayer: multiplayer.map(f => f.replace('.map', '')),
  };
}

function detectCurrentMission() {
  // Halo MCC updates save mtimes when a mission loads/checkpoints.
  // We look at the most recently modified .map file access or the
  // save directory timestamps to infer which mission is active.
  const checkpoints = join(SAVES_DIR, 'Saved');
  if (!existsSync(checkpoints)) return { mission: 'unknown', reason: 'no save dir' };

  // Check which campaign map was most recently accessed
  if (!existsSync(MAPS_DIR)) return { mission: 'unknown', reason: 'no maps dir' };
  let latest = null;
  let latestTime = 0;
  for (const c of CAMPAIGN_ORDER) {
    const p = join(MAPS_DIR, c.file);
    if (!existsSync(p)) continue;
    try {
      const s = statSync(p);
      const t = s.atimeMs || s.mtimeMs;
      if (t > latestTime) { latestTime = t; latest = c; }
    } catch (e) {}
  }
  if (latest) {
    return {
      mission: latest.name,
      file: latest.file,
      desc: latest.desc,
      lastAccessed: new Date(latestTime).toISOString(),
    };
  }
  return { mission: 'unknown', reason: 'no map access times' };
}

function scanConfig() {
  if (!existsSync(SETTINGS_INI)) return { error: 'settings not found' };
  const raw = readFileSync(SETTINGS_INI, 'utf8');
  const result = {};

  // Extract sensitivity
  const sensMatch = raw.match(/MouseSensitivity[^=]*=\s*([\d.]+)/);
  if (sensMatch) result.mouseSensitivity = parseFloat(sensMatch[1]);

  // Extract resolution
  const resMatch = raw.match(/ResolutionSizeX=(\d+)[\s\S]*?ResolutionSizeY=(\d+)/);
  if (resMatch) result.resolution = `${resMatch[1]}x${resMatch[2]}`;

  // Extract FOV
  const fovMatch = raw.match(/FieldOfView[^=]*=\s*([\d.]+)/);
  if (fovMatch) result.fov = parseFloat(fovMatch[1]);

  // Fullscreen
  const fullMatch = raw.match(/FullscreenMode=(\d)/);
  if (fullMatch) result.fullscreen = fullMatch[1] === '1';

  return result;
}

function scanSubtitles() {
  const subDir = join(H2_ROOT, 'prebuild', 'subtitles');
  if (!existsSync(subDir)) return [];
  try {
    return readdirSync(subDir).filter(f => f.endsWith('.txt') || f.endsWith('.xml'));
  } catch (e) { return []; }
}

export function fullScan() {
  const maps = scanMaps();
  const mission = detectCurrentMission();
  const config = scanConfig();
  const subtitles = scanSubtitles();

  const knowledge = {
    scannedAt: new Date().toISOString(),
    haloRoot: HALO_ROOT,
    maps,
    currentMission: mission,
    config,
    subtitleFiles: subtitles.length,
    campaignOrder: CAMPAIGN_ORDER.map(c => `${c.name}: ${c.desc}`),
  };

  // Write structured knowledge
  const outPath = join(MEM_DIR, 'halo-game-knowledge.json');
  writeFileSync(outPath, JSON.stringify(knowledge, null, 2), 'utf8');

  // Append mission awareness to halo-memory.md
  const memPath = join(MEM_DIR, 'halo-memory.md');
  if (existsSync(memPath)) {
    const mem = readFileSync(memPath, 'utf8');
    const missionBlock = `\n- ${new Date().toISOString().slice(0,19)} — scanner: current mission is "${mission.mission}" (${mission.desc || 'unknown'})`;
    if (!mem.includes('## current_mission')) {
      appendFileSync(memPath, '\n\n## current_mission\n' + missionBlock + '\n', 'utf8');
    } else {
      // Update the existing block
      const updated = mem.replace(
        /## current_mission[\s\S]*?(?=\n##|$)/,
        '## current_mission\n' + missionBlock + '\n'
      );
      writeFileSync(memPath, updated, 'utf8');
    }
  }

  return knowledge;
}

export function getMissionContext() {
  const mission = detectCurrentMission();
  if (!mission || mission.mission === 'unknown') return '';

  const idx = CAMPAIGN_ORDER.findIndex(c => c.name === mission.mission);
  const prev = idx > 0 ? CAMPAIGN_ORDER[idx - 1] : null;
  const next = idx < CAMPAIGN_ORDER.length - 1 ? CAMPAIGN_ORDER[idx + 1] : null;

  return [
    `CURRENT MISSION: ${mission.mission}`,
    `OBJECTIVE: ${mission.desc}`,
    prev ? `PREVIOUS: ${prev.name} (${prev.desc})` : '',
    next ? `NEXT: ${next.name} (${next.desc})` : '',
  ].filter(Boolean).join('\n');
}

// CLI: node game_scanner.js
if (process.argv[1] && process.argv[1].endsWith('game_scanner.js')) {
  const k = fullScan();
  console.log(JSON.stringify(k, null, 2));
}
