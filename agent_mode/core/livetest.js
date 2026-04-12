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
export async function runRound({ scenarioId, instanceUrl, observer = 'llama3.1:8b', cleanup = true } = {}) {
  if (!existsSync(ROUNDS_DIR)) mkdirSync(ROUNDS_DIR, { recursive: true });

  const scenario = loadScenario(scenarioId);
  const roundId = 'lt-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6);
  const started = Date.now();
  const suffix = Date.now().toString(36).slice(-4).toUpperCase();
  const teamCode = `${scenario.seed.team_code_prefix}-${suffix}`;
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

  // 2. CREW CREATE: foreman creates the team_code.
  {
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

export { listScenarios, loadScenario, listRounds, getRound };
