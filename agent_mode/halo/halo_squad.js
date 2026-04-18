/* ══════════════════════════════════════════════════════
   Halo Voltron — six-agent action voting fusion
   ──────────────────────────────────────────────────────
   The party agents form a voting collective. Each member has
   a specialized Halo role + a terse prompt that outputs EXACTLY
   one action word. All six votes run in parallel via Promise
   .allSettled, votes are tallied, winner executes. Ken AI is
   the trainer + tiebreaker — if two actions tie, the trainer
   gets the final call.

   Voltron member roles:

     Head:      Ken AI            (kenai:v1)       — commander / tiebreak
     Right Arm: 5c1z0r Patchsmith (qwen2.5-coder:14b)    — weapon / combat
     Left Arm:  D3c1du3y3 Pathfinder (cherp-piper:latest) — scout / recon
     Right Leg: P0ryg0n Logdex    (llama3.1:8b)          — movement / pacing
     Left Leg:  Umbr30n Safeguard (jefferyjefferferson)  — defense / shield
     Torso:     R0t0m Relay       (forgeagent:latest)    — objective / path
     Spine:     4l4k4z4m Archive  (jefferferson:latest)  — memory / pattern
     Companion: M3w Promptdex     (m3w-learning:latest)  — learning signal

   Each agent sees the same compact context (halo-log tail,
   vision cache, training mode state) + a ROLE-SPECIFIC system
   prompt. Response format is fixed to EXACTLY one action word
   so tallying is trivial.

   Voltron vote cadence: every 20-30 seconds. Between votes
   the tactical layer (tactical.js) executes the chosen action
   at 100ms cadence. The aimbot runs independently for aim +
   fire. So the hot loop is:

     aim     (100ms)    — snap + engage targets
     tactical (200ms)   — execute current voted action
     voltron  (25s)     — re-vote on next action word
     drive    (paused)  — LLM driver is superseded by voltron

   ══════════════════════════════════════════════════════ */

import { spawn } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync, mkdirSync, appendFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MEM_DIR = join(__dirname, '..', 'memories');

const VALID_ACTIONS = new Set([
  'move_fwd', 'move_back', 'strafe_left', 'strafe_right',
  'jump', 'crouch', 'sprint', 'reload', 'interact', 'grenade',
  'melee', 'weapon_slot_1', 'switch_grenade', 'flashlight',
  'dual_wield', 'scoreboard', 'fire', 'ads',
  'look_left', 'look_right', 'look_up', 'look_down',
  'noop', 'pause',
]);

const VOLTRON_MEMBERS = [
  {
    id: 'qwen2.5-coder:14b',
    slug: 'qwen2.5-coder-14b',
    displayName: '5c1z0r',
    limb: 'right_arm',
    role: 'weapon',
    systemLine: 'you are 5c1z0r, the right arm of halo voltron. your job is weapon + combat timing. vote for fire/ads/reload/grenade/melee when enemies are up, strafe_left/strafe_right when dodging incoming fire.',
  },
  {
    id: 'cherp-piper:latest',
    slug: 'cherp-piper-latest',
    displayName: 'D3c1du3y3',
    limb: 'left_arm',
    role: 'scout',
    systemLine: 'you are D3c1du3y3, the left arm of halo voltron. your job is scout + sightline management. vote for look_left/look_right/look_up/look_down when checking corners, ads when you see a target, crouch when spotted.',
  },
  {
    id: 'llama3.1:8b',
    slug: 'llama3.1-8b',
    displayName: 'P0ryg0n',
    limb: 'right_leg',
    role: 'movement',
    systemLine: 'you are P0ryg0n, the right leg of halo voltron. your job is movement + pacing. vote for move_fwd to advance, move_back to retreat, strafe_left/strafe_right to flank, jump to clear obstacles, sprint for distance.',
  },
  {
    id: 'jefferyjefferferson:latest',
    slug: 'jefferyjefferferson-latest',
    displayName: 'Umbr30n',
    limb: 'left_leg',
    role: 'defense',
    systemLine: 'you are Umbr30n, the left leg of halo voltron. your job is defense + shield management. vote for crouch + move_back when shields low, reload when safe, fire only when shields full.',
  },
  {
    id: 'forgeagent:latest',
    slug: 'forgeagent-latest',
    displayName: 'R0t0m',
    limb: 'torso',
    role: 'objective',
    systemLine: 'you are R0t0m, the torso of halo voltron. your job is objective awareness. vote for move_fwd toward objectives, interact on markers, noop during cutscenes.',
  },
  {
    id: 'jefferferson:latest',
    slug: 'jefferferson-latest',
    displayName: '4l4k4z4m',
    limb: 'spine',
    role: 'memory',
    systemLine: 'you are 4l4k4z4m, the spine of halo voltron. your job is long-term pattern memory. vote for whatever action the halo-memory tactics_learned section most recommends for this situation.',
  },
];

// Ken AI is the head / tiebreaker — not in the primary vote
// but gets pulled in if the majority tie needs breaking.
const VOLTRON_HEAD = {
  id: 'kenai:v1',
  slug: 'ken-ai-latest',
  displayName: 'Ken AI',
  limb: 'head',
  role: 'commander',
};


function stripAnsi(s) {
  return String(s || '')
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '');
}

function readLastLines(path, n) {
  if (!existsSync(path)) return [];
  try {
    const raw = readFileSync(path, 'utf8');
    const lines = raw.split('\n').filter(Boolean);
    return lines.slice(-n);
  } catch (e) { return []; }
}

function buildContext() {
  const logPath    = join(MEM_DIR, 'ken-ai-latest', 'halo-log.jsonl');
  const keylogPath = join(MEM_DIR, 'ken-ai-latest', 'halo-keylog.jsonl');

  const logLines = readLastLines(logPath, 6);
  const logSummary = logLines.map(l => {
    try {
      const r = JSON.parse(l);
      const sb = r.stateBefore || {};
      return `${r.action || '?'}(motion=${sb.motion || 0} shield="${(sb.shield||'').slice(0,6)}")`;
    } catch (e) { return '?'; }
  }).join(' → ') || '(no log)';

  // KEN'S LIVE KEYPRESSES — the primary imitation signal.
  // Grab the last 30 down-events. Voltron members condition
  // their vote on what Ken actually pressed, not just what
  // the driver did. "Follow my inputs, agents."
  const keyLines = readLastLines(keylogPath, 60);
  const downEvents = [];
  for (const line of keyLines) {
    try {
      const r = JSON.parse(line);
      if (r.dir !== 'down') continue;
      if (r.kind === 'system') continue;
      const id = r.kind === 'key' ? r.key : r.button;
      if (id) downEvents.push(id);
    } catch (e) { /* skip */ }
  }
  const kenKeys = downEvents.slice(-30).join(' ') || '(no presses)';

  return { logSummary, kenKeys };
}

function buildMemberPrompt(member, ctx) {
  return (
    member.systemLine + '\n\n' +
    'KEN IS CURRENTLY PILOTING halo voltron. your job is to learn from what he presses and eventually take the sticks yourself.\n' +
    "ken's last 30 keypresses (oldest first): " + ctx.kenKeys + '\n\n' +
    'halo voltron is voting on the NEXT action word. base your vote on ken\'s pattern — imitate what he is doing. respond with EXACTLY ONE action word from this list, nothing else — no prose, no punctuation, no explanation:\n' +
    '  move_fwd move_back strafe_left strafe_right jump crouch sprint\n' +
    '  reload interact grenade melee fire ads\n' +
    '  look_left look_right look_up look_down noop\n\n' +
    'key mapping for reference:\n' +
    '  w=move_fwd, s=move_back, a=strafe_left, d=strafe_right\n' +
    '  space=jump, ctrl=crouch, shift=sprint, r=reload, e=interact\n' +
    '  f=grenade, q=melee, left=fire, right=ads, 1=weapon_slot_1\n\n' +
    'recent driver actions (last 6 ticks): ' + ctx.logSummary + '\n\n' +
    'your one-word vote (imitate ken):'
  );
}

function parseVote(raw) {
  const text = stripAnsi(raw || '').toLowerCase();
  const tokens = text.split(/[^a-z_]+/).filter(Boolean);
  return tokens.find(t => VALID_ACTIONS.has(t)) || null;
}

/* ── Run one voter in parallel. Non-blocking; returns a
   promise that resolves with {member, vote, elapsed, raw}. ── */
function castVote(member, prompt, timeoutMs = 30000) {
  return new Promise((resolve) => {
    const t0 = Date.now();
    let out = '';
    let err = '';
    let child;
    try {
      child = spawn('ollama', ['run', member.id], {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
      });
    } catch (e) {
      return resolve({ member: member.displayName, vote: null, elapsed: 0, error: e.message });
    }
    const timeout = setTimeout(() => {
      try { child.kill('SIGKILL'); } catch (_) {}
    }, timeoutMs);
    child.stdout.on('data', (d) => { out += d.toString('utf8'); });
    child.stderr.on('data', (d) => { err += d.toString('utf8'); });
    child.on('close', () => {
      clearTimeout(timeout);
      const elapsed = Date.now() - t0;
      const vote = parseVote(out);
      resolve({
        member: member.displayName,
        limb: member.limb,
        role: member.role,
        vote,
        raw: stripAnsi(out).slice(0, 60),
        elapsed,
        error: !vote ? (err.slice(0, 120) || 'no valid vote') : null,
      });
    });
    try { child.stdin.write(prompt); child.stdin.end(); }
    catch (e) { /* ignore */ }
  });
}

/* ── The vote: dispatch all 6 members in parallel, tally,
   break ties with ken-ai head. Returns the winning action +
   the full vote record for logging. ── */
export async function voltronVote() {
  const ctx = buildContext();
  const promises = VOLTRON_MEMBERS.map(m =>
    castVote(m, buildMemberPrompt(m, ctx), 30000)
  );
  const results = await Promise.allSettled(promises);
  const votes = results.map(r => r.status === 'fulfilled' ? r.value : null).filter(Boolean);

  // Tally
  const tally = {};
  for (const v of votes) {
    if (v.vote) tally[v.vote] = (tally[v.vote] || 0) + 1;
  }

  // Find top vote
  let top = null;
  let topCount = 0;
  let tied = [];
  for (const [action, count] of Object.entries(tally)) {
    if (count > topCount) {
      top = action; topCount = count; tied = [action];
    } else if (count === topCount) {
      tied.push(action);
    }
  }

  // Tiebreaker: if multiple actions tied for top, ask ken-ai head
  let tiebreak = null;
  if (tied.length > 1 && topCount > 0) {
    const headPrompt =
      VOLTRON_HEAD.displayName + ' is the head of halo voltron. the squad tied on: ' + tied.join(', ') +
      '. pick ONE action word from those to break the tie. recent gameplay: ' + ctx.logSummary +
      '. your one word:';
    const headVote = await castVote(VOLTRON_HEAD, headPrompt, 20000);
    if (headVote.vote && tied.includes(headVote.vote)) {
      top = headVote.vote;
      tiebreak = headVote;
    }
  }

  // If no votes came back at all (all members errored), fall
  // back to a safe exploration action.
  if (!top) top = 'move_fwd';

  const result = {
    at: new Date().toISOString(),
    action: top,
    tally,
    tied: tied.length > 1 ? tied : null,
    tiebreak: tiebreak ? { vote: tiebreak.vote, elapsed: tiebreak.elapsed } : null,
    votes: votes.map(v => ({
      member: v.member,
      limb: v.limb,
      vote: v.vote,
      elapsed: v.elapsed,
      error: v.error,
    })),
  };

  // Persist the vote for introspection
  try {
    const dir = join(MEM_DIR, 'ken-ai-latest');
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    appendFileSync(join(dir, 'halo-voltron-log.jsonl'), JSON.stringify(result) + '\n', 'utf8');
  } catch (e) { /* best-effort */ }

  return result;
}

/* ── Voltron loop — votes every N seconds, stores latest
   winning action for the drive loop / tactical layer to
   read and execute. ── */
let _voltronTimer = null;
let _voltronRunning = false;
let _voltronIntervalMs = 25000;
let _voltronLast = null;
let _voltronStats = { passes: 0, startedAt: null };

export function startVoltron(opts = {}) {
  if (_voltronRunning) return { ok: false, reason: 'voltron already running' };
  _voltronIntervalMs = Math.max(10000, Math.min(120000, opts.intervalMs || 25000));
  _voltronRunning = true;
  _voltronStats = { passes: 0, startedAt: new Date().toISOString() };
  const tick = async () => {
    if (!_voltronRunning) return;
    try {
      _voltronLast = await voltronVote();
      _voltronStats.passes += 1;
    } catch (e) { /* swallow */ }
    if (_voltronRunning) _voltronTimer = setTimeout(tick, _voltronIntervalMs);
  };
  tick();
  return { ok: true, intervalMs: _voltronIntervalMs, members: VOLTRON_MEMBERS.length };
}

export function stopVoltron() {
  if (!_voltronRunning) return { ok: false, reason: 'not running' };
  _voltronRunning = false;
  if (_voltronTimer) { clearTimeout(_voltronTimer); _voltronTimer = null; }
  return { ok: true, stats: _voltronStats };
}

export function voltronStatus() {
  return {
    running: _voltronRunning,
    intervalMs: _voltronIntervalMs,
    members: VOLTRON_MEMBERS.map(m => ({
      displayName: m.displayName,
      limb: m.limb,
      role: m.role,
    })),
    head: VOLTRON_HEAD.displayName,
    stats: _voltronStats,
    last: _voltronLast,
  };
}
