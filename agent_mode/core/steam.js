// Steam library scanner
//
// Parses Steam's libraryfolders.vdf + each appmanifest_<appid>.acf to
// enumerate installed games. Returns an array of { appid, name, library }
// that the deck can render as launcher buttons. Launch URL scheme:
//   steam://rungameid/<appid>
// Header images (CDN):
//   https://cdn.akamai.steamstatic.com/steam/apps/<appid>/header.jpg

import { readFileSync, existsSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

const STEAM_ROOT = 'C:\\Program Files (x86)\\Steam';
const LIBRARY_VDF = join(STEAM_ROOT, 'steamapps', 'libraryfolders.vdf');
const USERDATA_ROOT = join(STEAM_ROOT, 'userdata');

// Tiny VDF reader: enough for our needs.
// Grabs all `"key" "value"` pairs at any depth, preserves duplicates.
function parseVdfFlat(text) {
  const pairs = [];
  const re = /"([^"]+)"\s+"([^"]*)"/g;
  let m;
  while ((m = re.exec(text)) != null) {
    pairs.push({ key: m[1], value: m[2] });
  }
  return pairs;
}

function findLibraryPaths() {
  const paths = [];
  if (!existsSync(LIBRARY_VDF)) return paths;
  let text = '';
  try { text = readFileSync(LIBRARY_VDF, 'utf8'); } catch { return paths; }
  const pairs = parseVdfFlat(text);
  for (const p of pairs) {
    if (p.key === 'path' && p.value) {
      // VDF uses escaped backslashes: "C:\\Program Files (x86)\\Steam"
      const clean = p.value.replace(/\\\\/g, '\\');
      paths.push(clean);
    }
  }
  if (!paths.length) paths.push(STEAM_ROOT);
  return paths;
}

function parseAppManifest(file) {
  try {
    const text = readFileSync(file, 'utf8');
    const pairs = parseVdfFlat(text);
    const row = {};
    for (const p of pairs) {
      if (p.key === 'appid' && !row.appid) row.appid = p.value;
      else if (p.key === 'name' && !row.name) row.name = p.value;
      else if (p.key === 'installdir' && !row.installdir) row.installdir = p.value;
      else if (p.key === 'LastPlayed' && !row.lastPlayed) row.lastPlayed = parseInt(p.value, 10) || 0;
      else if (p.key === 'SizeOnDisk' && !row.sizeBytes) row.sizeBytes = parseInt(p.value, 10) || 0;
    }
    return row;
  } catch { return null; }
}

// Proper VDF walker — tracks brace depth so nested keys stay scoped to
// their section. Returns a map { "<path>/<key>" : value } for all
// primitive key/value pairs, plus a map { "<path>" : [values...] } for
// repeated keys at the same depth.
function parseVdfScoped(text) {
  const pairs = [];
  const stack = [];
  let i = 0;
  const n = text.length;
  const readString = () => {
    // Advance past the opening quote
    i++;
    let start = i;
    let out = '';
    while (i < n) {
      const ch = text[i];
      if (ch === '\\' && text[i+1] === '"') { out += text.slice(start, i) + '"'; i += 2; start = i; continue; }
      if (ch === '"') break;
      i++;
    }
    out += text.slice(start, i);
    i++; // past closing quote
    return out;
  };
  let lastKey = null;
  while (i < n) {
    const ch = text[i];
    if (ch === '"') {
      const str = readString();
      if (lastKey == null) { lastKey = str; continue; }
      // key value pair
      pairs.push({ path: stack.join('/'), key: lastKey, value: str });
      lastKey = null;
    } else if (ch === '{') {
      if (lastKey != null) { stack.push(lastKey); lastKey = null; }
      i++;
    } else if (ch === '}') {
      stack.pop();
      i++;
    } else {
      i++;
    }
  }
  return pairs;
}

// Read total playtime per app (minutes) from localconfig.vdf. Scans each
// Steam user under userdata/ and picks the first one with data. Returns
// a map { appid (string): totalMinutes }.
export function getSteamPlaytimes() {
  const out = {};
  if (!existsSync(USERDATA_ROOT)) return out;
  let userDirs = [];
  try { userDirs = readdirSync(USERDATA_ROOT); } catch { return out; }
  for (const uid of userDirs) {
    const config = join(USERDATA_ROOT, uid, 'config', 'localconfig.vdf');
    if (!existsSync(config)) continue;
    let text = '';
    try { text = readFileSync(config, 'utf8'); } catch { continue; }
    const pairs = parseVdfScoped(text);
    // Look for keys matching path ending in "apps/<appid>" with key Playtime,
    // OR key "LastPlayed" / "Playtime" directly under an app section.
    for (const p of pairs) {
      if (p.key !== 'Playtime') continue;
      // p.path looks like: "UserLocalConfigStore/Software/Valve/Steam/apps/<appid>"
      const m = /\/apps\/(\d+)$/.exec(p.path);
      if (!m) continue;
      const appid = m[1];
      const minutes = parseInt(p.value, 10);
      if (Number.isFinite(minutes) && minutes > 0) out[appid] = minutes;
    }
    if (Object.keys(out).length) break;
  }
  return out;
}

export function listSteamGames({ limit = 200 } = {}) {
  const libs = findLibraryPaths();
  const playtimes = getSteamPlaytimes();
  const seen = new Set();
  const games = [];
  for (const lib of libs) {
    const apps = join(lib, 'steamapps');
    if (!existsSync(apps)) continue;
    let files = [];
    try { files = readdirSync(apps); } catch { continue; }
    for (const f of files) {
      if (!/^appmanifest_\d+\.acf$/i.test(f)) continue;
      const row = parseAppManifest(join(apps, f));
      if (!row || !row.appid || !row.name) continue;
      if (seen.has(row.appid)) continue;
      seen.add(row.appid);
      games.push({
        appid: row.appid,
        name: row.name,
        installdir: row.installdir || '',
        library: lib,
        lastPlayed: row.lastPlayed || 0,
        sizeBytes: row.sizeBytes || 0,
        playtimeMinutes: playtimes[row.appid] || 0,
        launchUrl: `steam://rungameid/${row.appid}`,
        storeUrl: `https://store.steampowered.com/app/${row.appid}/`,
        headerUrl: `https://cdn.akamai.steamstatic.com/steam/apps/${row.appid}/header.jpg`,
        libraryHeroUrl: `https://cdn.akamai.steamstatic.com/steam/apps/${row.appid}/library_hero.jpg`,
      });
    }
  }
  games.sort((a, b) => {
    // Recently played first, then alphabetical
    if (b.lastPlayed !== a.lastPlayed) return b.lastPlayed - a.lastPlayed;
    return a.name.localeCompare(b.name);
  });
  return games.slice(0, limit);
}
