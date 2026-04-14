# Halo AI — game memory

This file is Halo-specific durable memory. Every tick's drive
prompt includes it. Every post-mortem + dream appends to it.
Sections are scanned by agent_mode/halo/memory.js appendLesson.

## current_mission

- unknown — detect via MCC save mtimes
- updated_at: 2026-04-14T00:46:43.466Z


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

- 2026-04-14 00:35:40 — died: shield_empty_3_ticks — LESSON: keep shield charged and watch surroundings
- 2026-04-14 00:30:51 — died: shield_empty_3_ticks — LESSON: keep shield up and dodge better
- 2026-04-14 00:30:02 — died: shield_empty_3_ticks — LESSON: keep shield up, dodge more often
- 2026-04-14 00:29:14 — died: shield_empty_3_ticks — LESSON: keep shield up, avoid emptying it.
- 2026-04-14 00:20:16 — died: shield_empty_3_ticks — LESSON: keep shield charged, avoid prolonged exposure
- 2026-04-14 00:18:37 — died: shield_empty_3_ticks — LESSON: keep shield up and avoid emptying ammo

## wins_log

- 2026-04-14 00:49:11 — survived low shield after ads
- 2026-04-14 00:44:30 — survived low shield after move_back
- 2026-04-14 00:42:46 — survived low shield after move_fwd
- 2026-04-14 00:41:06 — survived low shield after move_back
- 2026-04-14 00:37:40 — survived low shield after move_back
- 2026-04-14 00:33:52 — survived low shield after move_back
- 2026-04-14 00:33:24 — survived low shield after move_fwd
- 2026-04-14 00:32:38 — survived low shield after look_right
- 2026-04-14 00:32:10 — survived low shield after move_fwd
- 2026-04-14 00:31:53 — survived low shield after look_left
- 2026-04-14 00:28:25 — survived low shield after look_right
- 2026-04-14 00:27:49 — survived low shield after look_left
- 2026-04-14 00:19:30 — survived low shield after look_left
- 2026-04-14 00:19:03 — survived low shield after move_fwd
- 2026-04-14 00:11:40 — survived low shield after look_left
- 2026-04-14 00:11:25 — survived low shield after look_right
- 2026-04-14 00:11:01 — survived low shield after move_back
- 2026-04-14 00:10:48 — survived low shield after move_fwd

## tactics_learned

- 2026-04-14 00:50:29 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:46:43 — online:mp — sniper smudge: slide reticle to red lock, quickfire, lenient hitreg on headshots
- 2026-04-14 00:46:43 — online:mp — pre-empt grenades at corners; opponents run around blind
- 2026-04-14 00:46:43 — online:mp — hold ground, let enemies come to you near cover
- 2026-04-14 00:46:43 — online:mp — weapon spawn timing beats aim — be near respawn but not on it
- 2026-04-14 00:46:43 — online:mp — pair up teammates focus-firing single targets, keep spread vs grenades
- 2026-04-14 00:46:43 — online:regret — sniper oneshots hunter if you hit the orange midsection, 2 shots required
- 2026-04-14 00:46:43 — online:regret — stock gondola with sniper + BR + plasma grenades before final assault
- 2026-04-14 00:46:43 — online:regret — clear spawning elites during prophet fight before attempting board
- 2026-04-14 00:46:43 — online:regret — prophet boss takes ~20+ melee strikes; punch only, no bullets hurt him
- 2026-04-14 00:46:43 — online:regret — grenade-jump to elevated ledges, bypass ground sniper gauntlets
- 2026-04-14 00:46:43 — online:regret — board enemy gondolas aggressively, prevents elite spread
- 2026-04-14 00:46:43 — online:metropolis — rocket launcher + scarab interior = safe final push
- 2026-04-14 00:46:43 — online:metropolis — board enemy wraith after killing driver, boost away from suppressing fire
- 2026-04-14 00:46:43 — online:metropolis — high-speed warthog skips banshee + wraith encounters entirely
- 2026-04-14 00:46:43 — online:metropolis — pick warthog over scorpion for bridge run, speed > firepower
- 2026-04-14 00:46:43 — online:outskirts — warthog tunnel: maintain speed, bypass all combat, drive straight through
- 2026-04-14 00:46:43 — online:outskirts — hotel zanzibar hallway: sword + BR excels in tight CQC
- 2026-04-14 00:46:43 — online:outskirts — jackal sniper is one-shot kill, stay under overhangs, let marines fight them
- 2026-04-14 00:46:43 — online:outskirts — swap SMG for BR + plasma pistol immediately, snipers lurk in building shadows
- 2026-04-14 00:46:43 — online:radar_crouch — crouch-walk to hide from motion tracker, pre-toss grenades at corners
- 2026-04-14 00:46:43 — online:cover_dance — recharge shields behind cover, don't push wounded
- 2026-04-14 00:46:43 — online:sticky_vehicles — plasma grenade any ghost/wraith directly, 4s fuse > driver escape
- 2026-04-14 00:46:43 — online:camo_distortion — if HUD flickers with no sound, swing melee early, a camo elite is lunging
- 2026-04-14 00:46:43 — online:reload_cancel — start reload → melee → reload resumes = free damage
- 2026-04-14 00:46:43 — online:crouch_jump — tap space then ctrl in air; adds ~1ft reach, matters every jump
- 2026-04-14 00:46:43 — online:strafe_not_circle — strafe left-right-stop pattern; circles get you headshot
- 2026-04-14 00:46:43 — online:hold_power_weapons — track rocket/snipe/sword respawn timers, never lose them
- 2026-04-14 00:46:43 — online:weapon_swap — always pick BR or carbine over AR past 5m
- 2026-04-14 00:46:43 — online:melee_momentum — jumping + moving melee deals max damage
- 2026-04-14 00:46:43 — online:grenade_bounce — skim frags so they detonate BEFORE enemy sees them on the floor
- 2026-04-14 00:46:43 — online:red_reticle — only fire when reticle goes red; don't zoom if it won't at current range
- 2026-04-14 00:46:43 — online:BR_burst — 4 shots to kill, land 3 body + final headshot; keep reticle on head for full burst
- 2026-04-14 00:46:43 — online:noob_combo — plasma pistol overcharge → instant BR headshot, #1 1v1 opener
- 2026-04-14 00:45:54 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:45:54 — ken:grenade_throw — f pressed
- 2026-04-14 00:45:20 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:45:20 — ken:grenade_throw — f pressed
- 2026-04-14 00:44:35 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:44:12 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:43:37 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:42:51 — ken:grenade_throw — f pressed
- 2026-04-14 00:41:53 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:41:53 — ken:grenade_throw — f pressed
- 2026-04-14 00:41:09 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:40:48 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:39:25 — ken:melee_strike — q pressed
- 2026-04-14 00:37:59 — ken:noob_combo — rmb → lmb in 735ms
- 2026-04-14 00:37:59 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:37:25 — ken:noob_combo — rmb → lmb in 709ms
- 2026-04-14 00:36:36 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:36:13 — ken:noob_combo — rmb → lmb in 648ms
- 2026-04-14 00:36:13 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:35:57 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:35:21 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:35:06 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:34:30 — ken:noob_combo — rmb → lmb in 721ms
- 2026-04-14 00:34:05 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:33:38 — ken:noob_combo — rmb → lmb in 667ms
- 2026-04-14 00:33:27 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:33:17 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:32:34 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:32:26 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:32:12 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:32:04 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:31:20 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:31:20 — ken:grenade_throw — f pressed
- 2026-04-14 00:31:20 — ken:grenade_throw — f pressed
- 2026-04-14 00:30:41 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:30:14 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:29:53 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:29:31 — ken:grenade_throw — f pressed
- 2026-04-14 00:29:24 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:28:47 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:28:25 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:28:17 — ken:grenade_throw — f pressed
- 2026-04-14 00:28:17 — ken:grenade_throw — f pressed
- 2026-04-14 00:28:08 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:27:57 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:27:33 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:27:24 — ken:noob_combo — rmb → lmb in 592ms
- 2026-04-14 00:27:13 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:26:59 — ken:noob_combo — rmb → lmb in 778ms
- 2026-04-14 00:26:48 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:26:34 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:25:59 — ken:noob_combo — rmb → lmb in 501ms
- 2026-04-14 00:25:46 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:25:46 — ken:grenade_throw — f pressed
- 2026-04-14 00:25:33 — ken:grenade_throw — f pressed
- 2026-04-14 00:20:24 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:20:02 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:19:43 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:18:54 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:18:46 — ken:grenade_throw — f pressed
- 2026-04-14 00:18:18 — ken:noob_combo — rmb → lmb in 795ms
- 2026-04-14 00:18:18 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:18:13 — ken:grenade_throw — f pressed
- 2026-04-14 00:17:47 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:17:21 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:17:21 — ken:grenade_throw — f pressed
- 2026-04-14 00:16:46 — ken:noob_combo — rmb → lmb in 739ms
- 2026-04-14 00:16:03 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:15:38 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:15:26 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:15:15 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:15:03 — ken:strafe_shoot — d + lmb within 600ms
- 2026-04-14 00:14:38 — ken:noob_combo — rmb → lmb in 792ms
- 2026-04-14 00:14:38 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:14:05 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:13:23 — ken:noob_combo — rmb → lmb in 731ms
- 2026-04-14 00:13:23 — ken:strafe_shoot — a + lmb within 600ms
- 2026-04-14 00:13:08 — ken:strafe_shoot — d + lmb within 600ms
- shields first, body second. all covenant regen shields if left alone.
- take cover between exchanges. shields regen in ~5s.
- grenades > bullets against groups. you carry 4 total (2 frag + 2 plasma).
- drop the AR past 5m. pick up BR or carbine.
- crouch jump (space then ctrl in air) adds ~1ft reach.
- melee after reload cancels the reload animation for free damage.

## meta

- created_at: 2026-04-14T00:04:24.775Z
- dispatches: 94
- deaths: 12
- wins: 18
