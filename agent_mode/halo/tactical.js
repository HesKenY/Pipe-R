/* ══════════════════════════════════════════════════════
   Halo tactical layer — fast reactive action selection
   ──────────────────────────────────────────────────────
   This is the "hot loop" for the agent. It runs at 100-200ms
   cadence (10-20x faster than the LLM) and picks actions
   using pure state-machine rules. No ollama calls in the hot
   path — which is why it can actually feel responsive.

   The slow LLM driver sets a PLAN every 15-30 seconds. The
   tactical layer executes that plan continuously, reacting
   to local signals (motion/activity, shield state, shot
   history, idle frames) between LLM consults.

   Plans (set by the LLM driver):

     advance          — default exploration. move_fwd + scan
     hold_and_scan    — stay in place, rotate camera
     retreat          — back up + crouch
     engage           — aggressive combat, fire through aimbot
     reload_cover     — crouch + reload
     unknown / null   — fall back to advance

   Tactical rules override the plan on local signals:

     - activity=death_screen → noop (don't waste input)
     - last 3 actions all same → break repeat, pick orthogonal
     - motion=0 for 3+ ticks → idle nudge (look_left/right)
     - state.center matches "checkpoint" → noop (save screen)

   No LLM, no network, no disk reads — the function runs in
   sub-millisecond time. Caller loops this + halo_do.py to
   fire actions at real frame rate.

   ══════════════════════════════════════════════════════ */

// Internal state so rules can detect repeats + idle streaks.
let _recentActions = [];   // last 6 actions
let _idleStreak = 0;       // consecutive ticks with motion < 0.01
let _scanDir = 1;          // +1 = look_right, -1 = look_left (alternating)

const ORTHOGONAL = {
  move_fwd:     'strafe_right',
  move_back:    'strafe_left',
  strafe_left:  'move_fwd',
  strafe_right: 'move_fwd',
  look_left:    'look_right',
  look_right:   'look_left',
  fire:         'ads',
  ads:          'fire',
  reload:       'move_back',
  crouch:       'move_fwd',
};

const PLAN_DEFAULTS = {
  advance:       ['move_fwd', 'move_fwd', 'look_right', 'move_fwd', 'look_left'],
  hold_and_scan: ['look_right', 'look_right', 'look_left', 'look_left', 'crouch'],
  retreat:       ['move_back', 'move_back', 'strafe_left', 'crouch', 'move_back'],
  engage:        ['fire', 'strafe_right', 'fire', 'strafe_left', 'ads'],
  reload_cover:  ['crouch', 'reload', 'look_left', 'crouch', 'look_right'],
};

/* ── The hot-path function. Takes current state + current
   plan + step index, returns one action word + any updates
   to tactical state. Must not allocate large objects. ── */
export function pickTacticalAction(state, plan, stepIdx = 0) {
  const activity = state?.activity || 'unknown';
  const motion   = state?.motion || 0;

  // Hard override: death screen — let the post-mortem run,
  // don't waste input while faded.
  if (activity === 'death_screen') {
    return { action: 'noop', reason: 'death_screen' };
  }

  // Hard override: checkpoint text in center OCR.
  const center = String(state?.center || '').toLowerCase();
  if (center.includes('checkpoint') || center.includes('saving')) {
    return { action: 'noop', reason: 'checkpoint_save' };
  }

  // Break repeats: if last 3 actions were all the same,
  // pick the orthogonal action instead.
  if (_recentActions.length >= 3) {
    const last3 = _recentActions.slice(-3);
    if (last3[0] === last3[1] && last3[1] === last3[2]) {
      const orth = ORTHOGONAL[last3[0]] || 'move_fwd';
      _recentActions.push(orth);
      if (_recentActions.length > 6) _recentActions.shift();
      return { action: orth, reason: 'break_repeat' };
    }
  }

  // Idle nudge: if nothing is moving on screen for 3+ ticks,
  // fire a look_left/right to generate visual change so
  // motion detection has something to work with next tick.
  if (motion < 0.01) {
    _idleStreak += 1;
    if (_idleStreak >= 3) {
      _scanDir *= -1;
      const act = _scanDir > 0 ? 'look_right' : 'look_left';
      _recentActions.push(act);
      if (_recentActions.length > 6) _recentActions.shift();
      return { action: act, reason: 'idle_nudge' };
    }
  } else {
    _idleStreak = 0;
  }

  // Plan execution: cycle through the plan's default action
  // sequence. Step index wraps with modulo.
  const plannedSeq = PLAN_DEFAULTS[plan] || PLAN_DEFAULTS.advance;
  const idx = stepIdx % plannedSeq.length;
  const action = plannedSeq[idx];

  _recentActions.push(action);
  if (_recentActions.length > 6) _recentActions.shift();
  return { action, reason: 'plan_' + plan + '_step_' + idx };
}

/* ── LLM plan parser. Takes raw LLM output, extracts the
   first recognizable plan keyword. Falls back to 'advance'. ── */
const VALID_PLANS = new Set([
  'advance', 'hold_and_scan', 'retreat', 'engage', 'reload_cover'
]);

export function parsePlan(raw) {
  if (!raw) return 'advance';
  const lower = String(raw).toLowerCase();
  for (const plan of VALID_PLANS) {
    if (lower.includes(plan)) return plan;
  }
  // Fallback keyword matching
  if (lower.includes('attack') || lower.includes('fight')) return 'engage';
  if (lower.includes('back')   || lower.includes('cover')) return 'retreat';
  if (lower.includes('hold')   || lower.includes('wait'))  return 'hold_and_scan';
  if (lower.includes('reload'))                            return 'reload_cover';
  return 'advance';
}

export function resetTacticalState() {
  _recentActions = [];
  _idleStreak = 0;
  _scanDir = 1;
}

export function getTacticalState() {
  return {
    recentActions: _recentActions.slice(),
    idleStreak: _idleStreak,
    scanDir: _scanDir,
  };
}
