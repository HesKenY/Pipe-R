/* One-shot seed script: dump a curated batch of online Halo 2
   tactical wisdom into halo-memory.md under tactics_learned so
   the driver prompt picks it up on next tick. Run once:
     node agent_mode/halo/_seed_online_wisdom.mjs
*/
import { appendLesson, setCurrentMission } from './memory.js';

const TIPS = [
  // Universal combat (from Halo 2 expert guides)
  'online:noob_combo — plasma pistol overcharge → instant BR headshot, #1 1v1 opener',
  'online:BR_burst — 4 shots to kill, land 3 body + final headshot; keep reticle on head for full burst',
  'online:red_reticle — only fire when reticle goes red; don\'t zoom if it won\'t at current range',
  'online:grenade_bounce — skim frags so they detonate BEFORE enemy sees them on the floor',
  'online:melee_momentum — jumping + moving melee deals max damage',
  'online:weapon_swap — always pick BR or carbine over AR past 5m',
  'online:hold_power_weapons — track rocket/snipe/sword respawn timers, never lose them',
  'online:strafe_not_circle — strafe left-right-stop pattern; circles get you headshot',
  'online:crouch_jump — tap space then ctrl in air; adds ~1ft reach, matters every jump',
  'online:reload_cancel — start reload → melee → reload resumes = free damage',
  'online:camo_distortion — if HUD flickers with no sound, swing melee early, a camo elite is lunging',
  'online:sticky_vehicles — plasma grenade any ghost/wraith directly, 4s fuse > driver escape',
  'online:cover_dance — recharge shields behind cover, don\'t push wounded',
  'online:radar_crouch — crouch-walk to hide from motion tracker, pre-toss grenades at corners',

  // Mission: Outskirts (from bungie.org legendary walkthrough)
  'online:outskirts — swap SMG for BR + plasma pistol immediately, snipers lurk in building shadows',
  'online:outskirts — jackal sniper is one-shot kill, stay under overhangs, let marines fight them',
  'online:outskirts — hotel zanzibar hallway: sword + BR excels in tight CQC',
  'online:outskirts — warthog tunnel: maintain speed, bypass all combat, drive straight through',

  // Mission: Metropolis
  'online:metropolis — pick warthog over scorpion for bridge run, speed > firepower',
  'online:metropolis — high-speed warthog skips banshee + wraith encounters entirely',
  'online:metropolis — board enemy wraith after killing driver, boost away from suppressing fire',
  'online:metropolis — rocket launcher + scarab interior = safe final push',

  // Mission: Regret
  'online:regret — board enemy gondolas aggressively, prevents elite spread',
  'online:regret — grenade-jump to elevated ledges, bypass ground sniper gauntlets',
  'online:regret — prophet boss takes ~20+ melee strikes; punch only, no bullets hurt him',
  'online:regret — clear spawning elites during prophet fight before attempting board',
  'online:regret — stock gondola with sniper + BR + plasma grenades before final assault',
  'online:regret — sniper oneshots hunter if you hit the orange midsection, 2 shots required',

  // Multiplayer mindset (applies in coop too)
  'online:mp — pair up teammates focus-firing single targets, keep spread vs grenades',
  'online:mp — weapon spawn timing beats aim — be near respawn but not on it',
  'online:mp — hold ground, let enemies come to you near cover',
  'online:mp — pre-empt grenades at corners; opponents run around blind',
  'online:mp — sniper smudge: slide reticle to red lock, quickfire, lenient hitreg on headshots',
];

let ok = 0;
for (const tip of TIPS) {
  try {
    if (appendLesson('tactics_learned', tip)) ok++;
  } catch (e) { /* skip */ }
}

// Also seed a placeholder current_mission so the section
// isn't empty. Ken plays different missions — this is just a
// hint that mission detection is available.
setCurrentMission('unknown — detect via MCC save mtimes');

console.log(`seeded ${ok}/${TIPS.length} online wisdom tips into halo-memory.md`);
