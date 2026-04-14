/* ══════════════════════════════════════════════════════
   Halo learning agent — durable game memory (halo-memory.md)
   ──────────────────────────────────────────────────────
   Separate from the agent's general notes.md. This file is
   Halo-specific knowledge that grows over time as the agent
   plays + dies + reflects. Sections:

     - current_mission       ← last known mission / location
     - controls_verified     ← keys the agent has confirmed work
     - weapons_known         ← weapons encountered + what works
     - enemies_known         ← enemies fought + counter-tactics
     - deaths_log            ← cause → correction lessons
     - wins_log              ← tactics that produced good outcomes
     - tactics_learned       ← generic patterns the agent trusts
     - meta                  ← counters, play-time, last-updated

   Auto-seeded on first access with the core rules from the
   Halo 2 guide so the agent isn't starting blind. Every dream
   / post-mortem / event emitter can append bullets via the
   public API. Loaded once per process + invalidated on write.

   ══════════════════════════════════════════════════════ */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR   = join(__dirname, '..', 'memories', 'ken-ai-latest');
const MEM_FILE  = join(MEM_DIR, 'halo-memory.md');

const SECTIONS = [
  'current_mission',
  'controls_verified',
  'weapons_known',
  'enemies_known',
  'deaths_log',
  'wins_log',
  'tactics_learned',
  'meta',
];

const SEED = `# Halo AI — game memory

This file is Halo-specific durable memory. Every tick's drive
prompt includes it. Every post-mortem + dream appends to it.
Sections are scanned by agent_mode/halo/memory.js appendLesson.

## current_mission

- unknown — set by game_files.js when MCC save times update.

## controls_verified

- w/a/s/d hold via pdi:hold — confirmed moves character forward/back/strafe.
- ctypes mouse_event MOUSEEVENTF_MOVE — confirmed rotates camera in MCC.
- r reload, f grenade, q melee, 1 weapon_slot_1, c dual_wield — per halopedia.org Halo 2 default keybinds.

## weapons_known

- battle rifle — 4-shot headshot. primary. pair with plasma pistol for noob combo.
- magnum — short range sidearm. weaker than H1 pistol.
- plasma pistol — overcharge hold RMB → release to pop any shield. pair with BR headshot.
- energy sword — melee, ~4m lunge on RMB. hold power weapons, hold sword.
- sniper rifle — one-shot to head. hold for elites.
- needler — dual wield for supercombine vs elites.
- shotgun — close flood clearer. one-shot on infection forms.

## enemies_known

- grunt — cannon fodder. headshot. lowest priority.
- jackal — arm shield. shoot hand or flank. shield-side mag removes them.
- elite (red/gold) — shield then headshot. PP overcharge + BR is the 1v1 opener.
- elite (white camo) — listen for hum. melee early if you see HUD distortion.
- hunter — pair. shoot orange exposed back/stomach. sword oneshots from behind.
- brute (H2 delta halo on) — raw, no shield. berserk when partner dies — sidestep charge.
- flood infection — popcorn, sprint through them, they pop on contact.
- flood combat — reanimated corpse. shotgun or sword. soak body damage, hit knee/groin.

## deaths_log

- (none yet — post_mortem.js fills this)

## wins_log

- (none yet — events.js fills this on successful shield_regen after low health)

## tactics_learned

- shields first, body second. all covenant regen shields if left alone.
- take cover between exchanges. shields regen in ~5s.
- grenades > bullets against groups. you carry 4 total (2 frag + 2 plasma).
- drop the AR past 5m. pick up BR or carbine.
- crouch jump (space then ctrl in air) adds ~1ft reach.
- melee after reload cancels the reload animation for free damage.

## meta

- created_at: ${new Date().toISOString()}
- dispatches: 0
- deaths: 0
- wins: 0
`;

function ensureDir() {
  if (!existsSync(MEM_DIR)) mkdirSync(MEM_DIR, { recursive: true });
}

function ensureMemory() {
  ensureDir();
  if (!existsSync(MEM_FILE)) {
    writeFileSync(MEM_FILE, SEED, 'utf8');
  }
  return MEM_FILE;
}

let _cache = null;
export function getMemory() {
  if (_cache != null) return _cache;
  ensureMemory();
  try { _cache = readFileSync(MEM_FILE, 'utf8'); }
  catch (e) { _cache = ''; }
  return _cache;
}

function invalidate() { _cache = null; }

/* ── Append a single bullet to a named section. Creates the
   section if it doesn't exist. Prepends an ISO timestamp. ── */
export function appendLesson(section, text) {
  if (!section || !text) return false;
  if (!SECTIONS.includes(section)) section = 'tactics_learned';
  ensureMemory();
  const raw = readFileSync(MEM_FILE, 'utf8');
  const stamp = new Date().toISOString().slice(0, 19).replace('T', ' ');
  const bullet = `- ${stamp} — ${String(text).trim()}`;

  // Find "## <section>" header and insert after it.
  const header = new RegExp(`^## ${section}\\s*$`, 'm');
  if (!header.test(raw)) {
    // Section missing — append it at the end.
    const appended = raw + `\n\n## ${section}\n\n${bullet}\n`;
    writeFileSync(MEM_FILE, appended, 'utf8');
    invalidate();
    return true;
  }
  // Insert the bullet right after the section header (before the
  // next blank line / section). We find the first blank line after
  // the header and slot our bullet at that spot.
  const lines = raw.split('\n');
  let i = 0;
  for (; i < lines.length; i++) {
    if (new RegExp(`^## ${section}\\s*$`).test(lines[i])) break;
  }
  // Walk forward past blank line(s) to the first content line,
  // then insert before any "- (none yet ...)" placeholder.
  let insertAt = i + 2;
  if (insertAt > lines.length) insertAt = lines.length;
  // If the immediately-following line is a placeholder, replace it
  // so the file doesn't permanently show "none yet".
  if (lines[insertAt] && /^-\s*\(none yet/.test(lines[insertAt])) {
    lines.splice(insertAt, 1, bullet);
  } else {
    lines.splice(insertAt, 0, bullet);
  }
  writeFileSync(MEM_FILE, lines.join('\n'), 'utf8');
  invalidate();
  return true;
}

/* ── Stamp an event into the "meta" counter block. Keeps a
   running tally of deaths / wins / dispatches so halo-memory.md
   always shows current totals at a glance. ── */
export function stampEvent(kind) {
  ensureMemory();
  const raw = readFileSync(MEM_FILE, 'utf8');
  let next = raw;
  const bump = (label) => {
    const re = new RegExp(`- ${label}: (\\d+)`);
    const m = raw.match(re);
    const cur = m ? parseInt(m[1], 10) : 0;
    if (m) next = next.replace(re, `- ${label}: ${cur + 1}`);
    else next = next.replace(/## meta\s*\n/, `## meta\n\n- ${label}: 1\n`);
  };
  if (kind === 'death')     bump('deaths');
  if (kind === 'win')       bump('wins');
  if (kind === 'dispatch')  bump('dispatches');
  if (next !== raw) {
    writeFileSync(MEM_FILE, next, 'utf8');
    invalidate();
  }
}

export function setCurrentMission(missionName) {
  if (!missionName) return;
  ensureMemory();
  const raw = readFileSync(MEM_FILE, 'utf8');
  // Replace everything under ## current_mission up to the next ##
  const re = /## current_mission[\s\S]*?(?=\n## )/m;
  const block = `## current_mission\n\n- ${missionName}\n- updated_at: ${new Date().toISOString()}\n\n`;
  const next = re.test(raw) ? raw.replace(re, block) : raw + '\n' + block;
  writeFileSync(MEM_FILE, next, 'utf8');
  invalidate();
}
