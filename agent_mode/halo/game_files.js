/* ══════════════════════════════════════════════════════
   Halo MCC game file discovery
   ──────────────────────────────────────────────────────
   Locates the Master Chief Collection install + save dir on
   Windows so ken-ai can:

     - know whether MCC is actually installed
     - know the install source (Steam vs Xbox MS Store)
     - observe save file mtimes to infer mission progress
       (mtime updates when a checkpoint saves)
     - eventually read config files for keybind + resolution
       (deferred — binary parsing is out of scope for v1)

   Strategy: probe the known default paths for each storefront.
   If Steam is installed via a custom library the registry
   LibraryFolders.vdf would be the correct path but reading
   that requires a parser we don't need yet. Default paths
   cover 90% of installs.

   Exposes a single `discoverMCC()` function returning:
     {
       installed: bool,
       source: 'steam' | 'xbox' | null,
       path: string | null,
       savesDir: string | null,
       recentSaves: [{ name, mtimeISO, sizeKB }]
     }
   ══════════════════════════════════════════════════════ */

import { existsSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const CANDIDATES = [
  // Steam default library
  {
    source: 'steam',
    path: 'C:\\Program Files (x86)\\Steam\\steamapps\\common\\Halo The Master Chief Collection',
  },
  {
    source: 'steam',
    path: 'D:\\SteamLibrary\\steamapps\\common\\Halo The Master Chief Collection',
  },
  {
    source: 'steam',
    path: 'E:\\SteamLibrary\\steamapps\\common\\Halo The Master Chief Collection',
  },
  // Xbox / MS Store (PC Game Pass)
  {
    source: 'xbox',
    path: 'C:\\XboxGames\\Halo- The Master Chief Collection',
  },
  {
    source: 'xbox',
    path: 'C:\\XboxGames\\Halo-The Master Chief Collection',
  },
];

// Common save-dir shapes for MCC. Not every install has a save
// folder at these paths — the game uses Steam Cloud + the
// user's LocalAppData for MCC saves on Steam, and the Xbox
// package has its own sandboxed path.
function probeSaveDirs(userHome) {
  const home = userHome || process.env.USERPROFILE || 'C:\\Users\\Ken';
  return [
    join(home, 'AppData', 'LocalLow', 'MCC', 'Temporary'),
    join(home, 'AppData', 'LocalLow', 'MCC'),
    join(home, 'AppData', 'Local', 'MCC'),
    join(home, 'AppData', 'Local', 'Packages', 'Microsoft.Chelan_8wekyb3d8bbwe', 'LocalState'),
  ];
}

function listRecent(dir, limit = 8) {
  try {
    const names = readdirSync(dir);
    const stamped = [];
    for (const name of names) {
      try {
        const s = statSync(join(dir, name));
        if (s.isFile()) {
          stamped.push({
            name,
            mtimeISO: s.mtime.toISOString(),
            sizeKB: Math.round(s.size / 1024),
          });
        }
      } catch (e) { /* skip */ }
    }
    stamped.sort((a, b) => b.mtimeISO.localeCompare(a.mtimeISO));
    return stamped.slice(0, limit);
  } catch (e) { return []; }
}

export function discoverMCC() {
  let found = null;
  for (const c of CANDIDATES) {
    if (existsSync(c.path)) { found = c; break; }
  }

  let savesDir = null;
  let recentSaves = [];
  for (const candidate of probeSaveDirs()) {
    if (existsSync(candidate)) {
      savesDir = candidate;
      recentSaves = listRecent(candidate, 8);
      break;
    }
  }

  return {
    installed: !!found,
    source: found ? found.source : null,
    path:   found ? found.path   : null,
    savesDir,
    recentSaves,
    probedAt: new Date().toISOString(),
  };
}
