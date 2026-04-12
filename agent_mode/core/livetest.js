// Live Test Mode v0
//
// Runs a scripted scenario against a real CHERP instance — creates a test
// crew, seeds members, fires a task workload through the live PostgREST
// endpoint, updates progress, and then asks an agent to write a round
// summary from the captured operation log. Everything that moves is
// persisted to disk under agent_mode/livetest/rounds/<timestamp>.json so
// the deck can browse history later.
//
// v0 deliberately uses ONE observer agent (P0ryg0n / llama3.1:8b) for the
// debrief instead of the full 6-agent dual-team split. The split is
// designed in .claude/WORKLIST.md and will land in v1 once the plumbing
// here is proven against the demo instance.

import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { spawnSync } from 'child_process';
import { createHash } from 'crypto';

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const LT_DIR = join(ROOT, 'agent_mode', 'livetest');
const SCENARIOS_DIR = join(LT_DIR, 'scenarios');
const ROUNDS_DIR = join(LT_DIR, 'rounds');

// CHERP Supabase credentials — same anon key the web app uses. Safe to
// embed here because the key is already public in cherp.live's js/config.js.
const SB_URL = 'https://nptmzihtujgkmqougkzd.supabase.co';
const SB_KEY = 'sb_publishable_G8KcjwIoJnBv7F6Pw02vqQ_WcQR39UX';

function sbHeaders(extra = {}) {
  return {
    'apikey': SB_KEY,
    'Authorization': 'Bearer ' + SB_KEY,
    'Content-Type': 'application/json',
    ...extra,
  };
}

async function sbFetch(path, opts = {}) {
  const url = SB_URL + '/rest/v1/' + path.replace(/^\/+/, '');
  const res = await fetch(url, {
    method: opts.method || 'GET',
    headers: sbHeaders(opts.headers || {}),
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  let json = null;
  let text = '';
  try { text = await res.text(); } catch {}
  if (text) { try { json = JSON.parse(text); } catch {} }
  return { ok: res.ok, status: res.status, body: json ?? text };
}

function listScenarios() {
  if (!existsSync(SCENARIOS_DIR)) return [];
  return readdirSync(SCENARIOS_DIR)
    .filter(f => f.endsWith('.json'))
    .map(f => {
      try {
        const obj = JSON.parse(readFileSync(join(SCENARIOS_DIR, f), 'utf8'));
        return { id: obj.id, name: obj.name, file: f };
      } catch { return null; }
    })
    .filter(Boolean);
}

function loadScenario(id) {
  const file = join(SCENARIOS_DIR, `${id}.json`);
  if (!existsSync(file)) throw new Error(`scenario not found: ${id}`);
  return JSON.parse(readFileSync(file, 'utf8'));
}

function listRounds() {
  if (!existsSync(ROUNDS_DIR)) return [];
  return readdirSync(ROUNDS_DIR)
    .filter(f => f.endsWith('.json'))
    .sort()
    .reverse()
    .slice(0, 40)
    .map(f => {
      try {
        const obj = JSON.parse(readFileSync(join(ROUNDS_DIR, f), 'utf8'));
        return {
          id: obj.id,
          scenarioId: obj.scenarioId,
          startedAt: obj.startedAt,
          durationMs: obj.durationMs,
          ok: obj.ok,
          teamCode: obj.teamCode,
          errorCount: (obj.operations || []).filter(o => !o.ok).length,
          opsCount: (obj.operations || []).length,
        };
      } catch { return null; }
    })
    .filter(Boolean);
}

function getRound(id) {
  const file = join(ROUNDS_DIR, `${id}.json`);
  if (!existsSync(file)) return null;
  try { return JSON.parse(readFileSync(file, 'utf8')); }
  catch { return null; }
}

// Call an ollama model with a single-shot prompt via stdin so no shell
// escaping ever corrupts the prompt. Strips ANSI spinner codes from
// stdout before returning.
function runOllama(model, prompt, timeoutMs = 90000) {
  const run = spawnSync('ollama', ['run', model], {
    input: prompt,
    encoding: 'utf8',
    timeout: timeoutMs,
    maxBuffer: 4 * 1024 * 1024,
  });
  if (run.error || (run.status !== 0 && !run.stdout)) {
    throw new Error(run.error?.message || run.stderr || 'ollama run failed');
  }
  const clean = String(run.stdout || '')
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '')
    .replace(/\r/g, '')
    .trim();
  return clean;
}

// Build the observer agent prompt from a captured operation log.
function buildDebriefPrompt(scenario, operations, teamCode) {
  const opsSummary = operations.map((op, i) => {
    const head = `${String(i + 1).padStart(2)}. [${op.ok ? 'OK ' : 'ERR'}] ${op.kind}`;
    const extra = op.ok
      ? (op.summary ? ` — ${op.summary}` : '')
      : ` — ${op.errorCode || op.status} · ${String(op.errorMsg || '').slice(0, 120)}`;
    return head + extra;
  }).join('\n');
  return [
    'You are P0ryg0n Logdex, the observability analyst for Ken AI\'s agent squad.',
    'A Live Test round just ran against a real CHERP instance. Read the',
    'operation log below and return a tight round debrief.',
    '',
    `Scenario: ${scenario.name} (${scenario.id})`,
    `Test crew code: ${teamCode}`,
    `Target: CHERP demo instance`,
    '',
    'Accept criteria:',
    ...scenario.acceptCriteria.map(c => `  - ${c}`),
    '',
    'Operation log:',
    opsSummary,
    '',
    'Return EXACTLY this shape in plain text, short and factual:',
    '',
    'VERDICT: <pass | partial | fail>',
    'SUMMARY: <one sentence>',
    'CRITERIA:',
    '  - <criterion>: <met | not met> — <why>',
    'ANOMALIES:',
    '  - <short bullet per real issue, or "none">',
    'NEXT:',
    '  - <one concrete follow-up>',
  ].join('\n');
}

function sha256(s) {
  return createHash('sha256').update(String(s), 'utf8').digest('hex');
}

// Main round runner — executes the scripted scenario against CHERP's
// REST API as if a real crew were signing up and using the app. Each
// operation is captured to the round log. The observer agent reads the
// log and writes the debrief. Cleanup reverses everything.
//
// Phase map:
//   1. create user_profiles (signup for each sim crew member, SHA-256 PINs)
//   2. create team_code (foreman creates the crew)
//   3. create crew_members (each worker joins, linked to user_profile)
//   4. create crew_tasks (foreman assigns the work)
//   5. PATCH tasks (workers update progress, add notes)
//   6. POST crew_timecards (workers clock in/out)
//   7. POST daily_logs (foreman writes a site log)
//   8. POST messages (crew chat)
//   9. cleanup (reverse order)
export async function runRound({ scenarioId, instanceUrl, observer = 'llama3.1:8b', cleanup = true, teamCode: forcedTeamCode } = {}) {
  if (!existsSync(ROUNDS_DIR)) mkdirSync(ROUNDS_DIR, { recursive: true });

  const scenario = loadScenario(scenarioId);
  const roundId = 'lt-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6);
  const started = Date.now();
  const suffix = Date.now().toString(36).slice(-4).toUpperCase();
  // Pre-existing crew wins. If the caller passes teamCode we reuse it
  // and skip the create/cleanup of the team_code row. Default target is
  // WS5A3Q — the standing Test crew on cherp.live (per Ken 2026-04-12).
  const reuseExistingCrew = !!(forcedTeamCode || scenario.seed.reuse_team_code);
  const teamCode = forcedTeamCode
    || scenario.seed.reuse_team_code
    || `${scenario.seed.team_code_prefix}-${suffix}`;
  const operations = [];
  const taskRowIds = [];
  const timecardIds = [];
  const dailyLogIds = [];
  const messageIds = [];
  const userProfileIds = [];
  const usernames = [];
  let overallOk = true;

  const record = (kind, res, summary, extra = {}) => {
    const op = {
      kind,
      ok: res.ok,
      status: res.status,
      summary: summary || '',
      ...extra,
    };
    if (!res.ok) {
      overallOk = false;
      if (res.body && typeof res.body === 'object') {
        op.errorCode = res.body.code || res.body.error || '';
        op.errorMsg = res.body.message || res.body.details || res.body.hint || '';
      } else {
        op.errorMsg = String(res.body || '').slice(0, 200);
      }
    }
    operations.push(op);
    return op;
  };

  // 1. SIGNUP: create user_profiles for each sim crew member.
  // PIN 1111 for everyone (SHA-256 hashed just like auth.js does).
  const pinHash = sha256('1111');
  for (const m of scenario.seed.members) {
    const username = `simlt_${suffix.toLowerCase()}_${m.name.replace(/\s+/g, '').toLowerCase()}`;
    const res = await sbFetch('user_profiles', {
      method: 'POST',
      headers: { 'Prefer': 'return=representation' },
      body: {
        username,
        display_name: m.name,
        pin_hash: pinHash,
        role: m.role,
        is_active: true,
        company_id: 'CHERP',
        crew: scenario.seed.crew_name,
        trade: m.trade || 'General',
        team_code: '',  // joined in phase 3
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    });
    record('signup_user', res, `${m.name} (${m.role}) · ${username}`);
    if (res.ok && Array.isArray(res.body) && res.body[0]?.id) {
      userProfileIds.push(res.body[0].id);
      usernames.push(username);
    } else {
      userProfileIds.push(null);
      usernames.push(username);
    }
  }

  // 2. CREW CREATE: foreman creates the team_code — UNLESS we're reusing
  //    a pre-existing crew (e.g. WS5A3Q), in which case we skip this phase
  //    entirely so we don't duplicate a real crew row.
  if (!reuseExistingCrew) {
    const res = await sbFetch('team_codes', {
      method: 'POST',
      headers: { 'Prefer': 'return=minimal' },
      body: {
        code: teamCode,
        crew_name: scenario.seed.crew_name,
        foreman_name: scenario.seed.foreman_name,
        company_name: 'CHERP',
        job_site: scenario.seed.job_site || 'Live Test Site',
        notes: 'Live Test v0 — safe to delete',
        active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    });
    record('create_crew', res, `team_code=${teamCode} · crew_name=${scenario.seed.crew_name}`);
  } else {
    operations.push({
      kind: 'create_crew',
      ok: true,
      status: 0,
      summary: `reusing existing team_code=${teamCode} (skipped creation)`,
    });
  }

  // 3. JOIN CREW: each user_profile updates its team_code, then the app
  // inserts a crew_members row. Two steps because CHERP's real flow does
  // both — we mirror it so the simulation exercises the actual path.
  for (let i = 0; i < scenario.seed.members.length; i++) {
    const m = scenario.seed.members[i];
    const uid = userProfileIds[i];
    if (uid) {
      const resUpdate = await sbFetch(`user_profiles?id=eq.${uid}`, {
        method: 'PATCH',
        headers: { 'Prefer': 'return=minimal' },
        body: { team_code: teamCode, updated_at: new Date().toISOString() },
      });
      record('user_join_crew', resUpdate, `${m.name} → ${teamCode}`);
    }
    const resMember = await sbFetch('crew_members', {
      method: 'POST',
      headers: { 'Prefer': 'return=minimal,resolution=merge-duplicates' },
      body: {
        team_code: teamCode,
        member_name: m.name,
        role: m.role.charAt(0).toUpperCase() + m.role.slice(1),
        is_foreman: m.role === 'foreman',
        device_id: `simlt-${teamCode}-${m.name.replace(/\s+/g, '-')}`,
        last_seen: new Date().toISOString(),
        created_at: new Date().toISOString(),
      },
    });
    record('add_member', resMember, `${m.name} (${m.role})`);
  }

  // 4. TASK CREATE: foreman assigns the workload.
  for (const t of scenario.tasks) {
    const res = await sbFetch('crew_tasks', {
      method: 'POST',
      headers: { 'Prefer': 'return=representation' },
      body: {
        team_code: teamCode,
        text: t.text,
        priority: t.priority,
        work_type: 'work',
        done: false,
        assigned_to: t.assigned_to,
        notes: '[]',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        created_by: scenario.seed.foreman_name,
      },
    });
    const summary = `${t.priority.toUpperCase()} → ${t.assigned_to}: ${t.text.slice(0, 48)}`;
    record('create_task', res, summary);
    if (res.ok && Array.isArray(res.body) && res.body[0]?.id) {
      taskRowIds.push(res.body[0].id);
    } else {
      taskRowIds.push(null);
    }
  }

  // 5. TASK PROGRESS: workers update tasks they own.
  for (const update of (scenario.progress_updates || [])) {
    const id = taskRowIds[update.task_index];
    if (id == null) {
      operations.push({
        kind: 'progress_update',
        ok: false,
        status: 0,
        summary: `task_index ${update.task_index}`,
        errorMsg: 'no server id captured (task create failed upstream)',
      });
      overallOk = false;
      continue;
    }
    const res = await sbFetch(`crew_tasks?id=eq.${id}`, {
      method: 'PATCH',
      headers: { 'Prefer': 'return=minimal' },
      body: {
        progress: update.progress,
        updated_at: new Date().toISOString(),
        notes: JSON.stringify([{ text: update.note, by: 'LiveTest', at: new Date().toISOString() }]),
      },
    });
    record('progress_update', res, `task#${update.task_index} → ${update.progress}% · ${update.note}`);
  }

  // 6. TIMECLOCK: workers clock in + out. crew_timecards uses a client-gen
  //    TEXT id and columns user_id/user_name/clock_in/clock_out/hours/date.
  for (let i = 0; i < scenario.seed.members.length; i++) {
    const m = scenario.seed.members[i];
    const uid = userProfileIds[i];
    const clockIn = new Date(Date.now() - 8 * 3600 * 1000).toISOString();
    const clockOut = new Date().toISOString();
    const tcId = `tc-${teamCode}-${i}-${Date.now().toString(36)}`;
    const res = await sbFetch('crew_timecards', {
      method: 'POST',
      headers: { 'Prefer': 'return=minimal' },
      body: {
        id: tcId,
        user_id: uid || usernames[i],
        user_name: m.name,
        team_code: teamCode,
        role: m.role,
        clock_in: clockIn,
        clock_out: clockOut,
        hours: 8,
        date: new Date().toISOString().slice(0, 10),
        status: 'complete',
        notes: 'live test timecard',
      },
    });
    record('timecard', res, `${m.name} 8h`);
    if (res.ok) timecardIds.push(tcId);
  }

  // 7. DAILY LOG: foreman writes a site note. daily_logs has no team_code
  //    column — uses company_id + created_by (UUID) + work_done/notes.
  {
    const foremanUid = userProfileIds[0];
    const res = await sbFetch('daily_logs', {
      method: 'POST',
      headers: { 'Prefer': 'return=representation' },
      body: {
        log_date: new Date().toISOString().slice(0, 10),
        weather: 'clear 62F',
        crew_present: scenario.seed.members.map(m => m.name),
        work_done: `Live test run ${roundId} against ${teamCode}. Kitchen remodel scenario executed.`,
        notes: 'Auto-generated by Pipe-R Live Test Mode v0',
        created_by: foremanUid || null,
        company_id: 'CHERP',
      },
    });
    record('daily_log', res, 'foreman end-of-day note');
    if (res.ok && Array.isArray(res.body) && res.body[0]?.id) {
      dailyLogIds.push(res.body[0].id);
    }
  }

  // 8. CREW MESSAGE: foreman pings the crew chat via messages table.
  //    Columns: sender_id (UUID), channel (team code), body, is_read, company_id.
  {
    const foremanUid = userProfileIds[0];
    if (!foremanUid) {
      operations.push({
        kind: 'crew_message',
        ok: false,
        status: 0,
        summary: 'no foreman user_profile id',
        errorMsg: 'upstream signup_user failed',
      });
      overallOk = false;
    } else {
      const res = await sbFetch('messages', {
        method: 'POST',
        headers: { 'Prefer': 'return=representation' },
        body: {
          sender_id: foremanUid,
          channel: teamCode,
          body: `Good hustle today, ${scenario.seed.crew_name}. Live test ${roundId} complete.`,
          is_read: false,
          company_id: 'CHERP',
        },
      });
      record('crew_message', res, 'foreman → channel');
      if (res.ok && Array.isArray(res.body) && res.body[0]?.id) {
        messageIds.push(res.body[0].id);
      }
    }
  }

  // 9. CLEANUP (reverse order to respect FKs)
  //    messages + daily_logs have no team_code column — delete by row id.
  //    crew_timecards has team_code (nullable FK), ok to delete by that.
  if (cleanup) {
    const del = async (kind, path) => {
      const res = await sbFetch(path, { method: 'DELETE', headers: { 'Prefer': 'return=minimal' } });
      record(kind, res, path);
    };
    for (const id of messageIds) {
      await del('cleanup_message', `messages?id=eq.${id}`);
    }
    for (const id of dailyLogIds) {
      await del('cleanup_daily_log', `daily_logs?id=eq.${id}`);
    }
    for (const id of timecardIds) {
      await del('cleanup_timecard', `crew_timecards?id=eq.${encodeURIComponent(id)}`);
    }
    for (const id of taskRowIds.filter(Boolean)) {
      await del('cleanup_task', `crew_tasks?id=eq.${id}`);
    }
    await del('cleanup_members', `crew_members?team_code=eq.${teamCode}`);
    await del('cleanup_crew', `team_codes?code=eq.${teamCode}`);
    for (const uid of userProfileIds.filter(Boolean)) {
      await del('cleanup_user', `user_profiles?id=eq.${uid}`);
    }
  }

  // 6. Debrief — observer agent reads the log and grades the round
  let debrief = '';
  let debriefErr = null;
  try {
    const prompt = buildDebriefPrompt(scenario, operations, teamCode);
    debrief = runOllama(observer, prompt, 120000);
  } catch (e) {
    debriefErr = e.message;
  }

  const round = {
    id: roundId,
    scenarioId,
    scenarioName: scenario.name,
    instanceUrl: instanceUrl || 'https://cherp.live/demo.html',
    teamCode,
    observer,
    startedAt: new Date(started).toISOString(),
    finishedAt: new Date().toISOString(),
    durationMs: Date.now() - started,
    ok: overallOk,
    operations,
    debrief,
    debriefError: debriefErr,
    acceptCriteria: scenario.acceptCriteria,
  };

  writeFileSync(join(ROUNDS_DIR, `${roundId}.json`), JSON.stringify(round, null, 2));
  return round;
}

// === Live Test Mode v1 — 6-agent dual-team split ====================
//
// v0: one observer reads the op log and writes a debrief.
// v1: six specialists split into Team A (Crew Roleplay) and Team B
//     (Ops + Maint). Ken AI refs + M3w proposes improvements.
//
// After the v0 engine finishes the real Supabase operations, we fan
// out the operation log to each agent in their specific role:
//
//   Team A (roleplays the crew from inside the workload)
//     - D3c1du3y3 (cherp-piper)  Foreman — end-of-day site report
//     - 5c1z0r    (qwen2.5)      Worker 1 — how-did-today-go note
//     - P0ryg0n   (llama3.1)     Apprentice — site anomaly report
//
//   Team B (watches the instance from outside)
//     - R0t0m     (forgeagent)   Integration ops — HTTP/schema audit
//     - Umbr30n   (jeffery…)     QA — top regression risks + fixes
//     - 4l4k4z4m  (jefferferson) Memory curator — durable round memory
//
//   Trainer + companion
//     - Ken AI    — pass/retry/fix decision
//     - M3w       — exactly one prompt/notes update proposal

const V1_ROSTER = {
  teamA: [
    {
      id: 'cherp-piper:latest',
      persona: 'D3c1du3y3 Foreman',
      title: 'Foreman end-of-day site report',
      promptBody: (ctx) => [
        'You are D3c1du3y3 Pathfinder, cherp-piper, playing the FOREMAN on',
        `the "${ctx.scenarioName}" live test round against CHERP.`,
        'In under 100 words, write your end-of-day site report in first',
        'person. Reference at least 2 real tasks from the operation log',
        'by their text. Mention which worker finished what. End with the',
        'next-day priorities.',
      ].join('\n'),
    },
    {
      id: 'qwen2.5-coder:14b',
      persona: '5c1z0r Worker 1',
      title: 'Worker how-did-today-go note',
      promptBody: (ctx) => [
        'You are 5c1z0r Patchsmith, playing Sim Worker 1 on this CHERP',
        'live test round. You handled the cabinets-demo / bracing tasks.',
        'In under 60 words, write a 3-line note for the foreman. First',
        'person. What got done, what blocked you, what you need tomorrow.',
        'No greeting, no signoff.',
      ].join('\n'),
    },
    {
      id: 'llama3.1:8b',
      persona: 'P0ryg0n Apprentice',
      title: 'Apprentice anomaly report',
      promptBody: (ctx) => [
        'You are P0ryg0n Logdex, playing the apprentice + incident reporter',
        'on this CHERP live test round. Read the operation log and list any',
        'anomalies you noticed from inside the app — slow saves, weird',
        'behavior, failed calls, stale data. Under 80 words, bullets.',
        'If the round was clean, say so in one line.',
      ].join('\n'),
    },
  ],
  teamB: [
    {
      id: 'forgeagent:latest',
      persona: 'R0t0m Integration',
      title: 'HTTP + schema audit',
      promptBody: (ctx) => [
        'You are R0t0m Relay, integration + ops engineer. Audit the live',
        'CHERP operation log from the outside. Call out any schema drift,',
        'non-2xx responses, PostgREST quirks, and latency hot spots you',
        'can see. Under 80 words. Lead with the worst finding.',
      ].join('\n'),
    },
    {
      id: 'jefferyjefferferson:latest',
      persona: 'Umbr30n QA',
      title: 'Top regression risks',
      promptBody: (ctx) => [
        'You are Umbr30n Safeguard, QA + release warden. Given Team A\'s',
        'reports and the operation log, list the top 3 regression risks',
        'for CHERP\'s next release. For each: ROOT_CAUSE (one line) +',
        'SMALLEST_SAFE_FIX (one line). Under 120 words total.',
      ].join('\n'),
    },
    {
      id: 'jefferferson:latest',
      persona: '4l4k4z4m Archive',
      title: 'Durable round memory',
      promptBody: (ctx) => [
        'You are 4l4k4z4m Archive, memory curator. Write a 3-bullet',
        'durable memory entry for this round: (1) what worked, (2) what',
        'broke, (3) what the team should remember next time. Under 100',
        'words. Bullet format. No preamble.',
      ].join('\n'),
    },
  ],
  trainer: {
    id: 'ken-ai:latest',
    persona: 'Ken AI',
    title: 'Trainer decision',
    promptBody: (ctx) => [
      'you are ken. read team a narration + team b audit + the operation',
      'log. make one decision: pass, retry, or fix-and-rerun. one line.',
      'then list the next concrete step. under 40 words total. lowercase.',
    ].join('\n'),
  },
  companion: {
    id: 'm3w-learning:latest',
    persona: 'M3w Promptdex',
    title: 'Prompt improvement proposal',
    promptBody: (ctx) => [
      'You are M3w Promptdex, learning companion. Propose EXACTLY ONE',
      'prompt / notes.md update that would make the next round better.',
      'Cite the specific task id or log line as evidence. Keep the',
      'proposed change shorter than what it replaces. Under 80 words.',
    ].join('\n'),
  },
};

function buildV1AgentPrompt(ctx, body, opsHeader) {
  return [
    body,
    '',
    '=== ROUND CONTEXT ===',
    `Scenario: ${ctx.scenarioName}`,
    `Team code: ${ctx.teamCode}`,
    `Target instance: ${ctx.instanceUrl}`,
    '',
    '=== OPERATION LOG ===',
    opsHeader,
    '',
    'Respond now in the format requested above.',
  ].join('\n');
}

async function dispatchV1Agent(slot, ctx, opsHeader, timeoutMs = 120000) {
  const prompt = buildV1AgentPrompt(ctx, slot.promptBody(ctx), opsHeader);
  const start = Date.now();
  try {
    const output = runOllama(slot.id, prompt, timeoutMs);
    return {
      id: slot.id,
      persona: slot.persona,
      title: slot.title,
      ok: true,
      elapsedMs: Date.now() - start,
      output,
    };
  } catch (e) {
    return {
      id: slot.id,
      persona: slot.persona,
      title: slot.title,
      ok: false,
      elapsedMs: Date.now() - start,
      error: e.message,
    };
  }
}

// Public v1 runner: runs the v0 operation engine first, then fans out to
// the 6-agent split, then lets Ken AI + M3w finalize.
export async function runRoundV1({ scenarioId, instanceUrl, cleanup = true, teamCode: forcedTeamCode } = {}) {
  // Re-use the v0 engine to do the real Supabase work. Pass a bogus
  // observer we'll ignore since v1 generates its own trainer decision.
  const base = await runRound({
    scenarioId,
    instanceUrl,
    cleanup,
    teamCode: forcedTeamCode,
    observer: 'llama3.1:8b',
  });

  const opsHeader = (base.operations || []).map((op, i) => {
    const head = `${String(i + 1).padStart(2)}. [${op.ok ? 'OK ' : 'ERR'}] ${op.kind}`;
    const extra = op.ok
      ? (op.summary ? ` — ${op.summary}` : '')
      : ` — ${op.errorCode || op.status} · ${String(op.errorMsg || '').slice(0, 120)}`;
    return head + extra;
  }).join('\n');

  const ctx = {
    scenarioName: base.scenarioName || scenarioId,
    teamCode: base.teamCode,
    instanceUrl: base.instanceUrl || 'https://cherp.live/demo.html',
  };

  // Team A + Team B fan-out. Sequential per-team (Ollama serializes on
  // GPU anyway) but concurrent across teams where the scheduler allows.
  const teamA = [];
  for (const slot of V1_ROSTER.teamA) {
    teamA.push(await dispatchV1Agent(slot, ctx, opsHeader));
  }
  const teamB = [];
  for (const slot of V1_ROSTER.teamB) {
    // Alakazam has a slow cold start — give it more room.
    const tout = slot.id === 'jefferferson:latest' ? 180000 : 120000;
    teamB.push(await dispatchV1Agent(slot, ctx, opsHeader, tout));
  }

  // Build a condensed handoff for trainer + companion: they see Team A +
  // Team B outputs but not the raw op log twice.
  const handoff = [
    '=== TEAM A (CREW ROLEPLAY) ===',
    ...teamA.map(r => `--- ${r.persona} · ${r.title} ---\n${r.output || '(error: ' + (r.error || 'no output') + ')'}`),
    '',
    '=== TEAM B (OPS + MAINT) ===',
    ...teamB.map(r => `--- ${r.persona} · ${r.title} ---\n${r.output || '(error: ' + (r.error || 'no output') + ')'}`),
  ].join('\n\n');

  const trainerCtx = { ...ctx };
  const trainerPrompt = [
    V1_ROSTER.trainer.promptBody(trainerCtx),
    '',
    '=== ROUND CONTEXT ===',
    `Scenario: ${ctx.scenarioName}`,
    `Team code: ${ctx.teamCode}`,
    `Ops summary: ${(base.operations || []).length} operations, ${(base.operations || []).filter(o => !o.ok).length} failures`,
    '',
    '=== TEAM REPORTS ===',
    handoff,
  ].join('\n');

  let trainerResult, companionResult;
  try {
    const out = runOllama(V1_ROSTER.trainer.id, trainerPrompt, 120000);
    trainerResult = { id: V1_ROSTER.trainer.id, persona: 'Ken AI', ok: true, output: out };
  } catch (e) {
    trainerResult = { id: V1_ROSTER.trainer.id, persona: 'Ken AI', ok: false, error: e.message };
  }

  const companionPrompt = [
    V1_ROSTER.companion.promptBody(trainerCtx),
    '',
    '=== TRAINER DECISION ===',
    trainerResult.output || '(unavailable)',
    '',
    '=== TEAM REPORTS ===',
    handoff,
  ].join('\n');
  try {
    const out = runOllama(V1_ROSTER.companion.id, companionPrompt, 120000);
    companionResult = { id: V1_ROSTER.companion.id, persona: 'M3w', ok: true, output: out };
  } catch (e) {
    companionResult = { id: V1_ROSTER.companion.id, persona: 'M3w', ok: false, error: e.message };
  }

  // Write a v1 round file that extends the v0 record.
  const v1Record = {
    ...base,
    id: 'ltv1-' + base.id.replace(/^lt-/, ''),
    mode: 'v1',
    teamA,
    teamB,
    trainer: trainerResult,
    companion: companionResult,
  };
  const outFile = join(ROUNDS_DIR, `${v1Record.id}.json`);
  writeFileSync(outFile, JSON.stringify(v1Record, null, 2));
  return v1Record;
}

export { listScenarios, loadScenario, listRounds, getRound };
