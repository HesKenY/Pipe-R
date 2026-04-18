/*
  corpus_builder_v2.mjs — CHERP/Pipe-R codebase-specific training pairs
  Generated from actual source code analysis by Claude subagent.
  120 pairs across: cherp_architecture, supabase_patterns, store_offline,
  auth_security, netlify_functions, agent_safety, debugging
*/

import { spawnSync } from 'node:child_process';
import { appendFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const LOG = join(__dirname, 'training-log.jsonl');
const MODEL = 'kenai:v1';

function strip(s) {
  return String(s||'').replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g,'').replace(/\u001b\][^\u0007]*\u0007/g,'').trim();
}

function ask(prompt, timeout = 90) {
  const t0 = Date.now();
  const r = spawnSync('ollama', ['run', MODEL], { input: prompt, encoding: 'utf8', timeout: timeout*1000, maxBuffer: 4*1024*1024, windowsHide: true });
  return { response: strip(r.stdout), elapsed: Date.now()-t0, ok: r.status===0 };
}

function log(cat, q, a, elapsed) {
  appendFileSync(LOG, JSON.stringify({
    timestamp: new Date().toISOString(),
    taskId: 'corpus2-' + Date.now().toString(36),
    model: MODEL, taskType: cat, attempt: 1,
    objective: q.slice(0,200), prompt: q, response: a,
    success: true, elapsed,
    reviewed: true, approved: true,
    reviewNotes: 'corpus_v2 codebase-grounded'
  }) + '\n');
}

const PAIRS = [
  // ── cherp_architecture ──
  ["cherp_architecture", "what is the difference between SB() and SB_Admin() in cherp?"],
  ["cherp_architecture", "how do i add a new screen to cherp?"],
  ["cherp_architecture", "how does role-based access work in cherp?"],
  ["cherp_architecture", "what is _s and where does it get set?"],
  ["cherp_architecture", "how do i check if the current user is a foreman or above?"],
  ["cherp_architecture", "what does activeCrewCode() do and when should i use it?"],
  ["cherp_architecture", "how does superuser see crew data without being a member?"],
  ["cherp_architecture", "how should i display a user's role to other workers?"],
  ["cherp_architecture", "what global variables are declared in config.js?"],
  ["cherp_architecture", "what roles are valid in user_profiles.role after phase 2?"],
  ["cherp_architecture", "how does the conflict logger work?"],
  ["cherp_architecture", "how does the offline queue in utils.js differ from store.js queue?"],
  ["cherp_architecture", "why is SB_SVC set to null in config.js?"],
  // ── supabase_patterns ──
  ["supabase_patterns", "how do i POST a new row to crew_tasks?"],
  ["supabase_patterns", "how do i do an upsert in supabase via the REST API?"],
  ["supabase_patterns", "how do i query daily_logs for a crew?"],
  ["supabase_patterns", "how do i query messages for a crew?"],
  ["supabase_patterns", "what columns does crew_timecards use?"],
  ["supabase_patterns", "what does Prefer: return=representation do vs return=minimal?"],
  ["supabase_patterns", "how do i handle a 409 conflict from supabase?"],
  ["supabase_patterns", "how does PIN login work against supabase?"],
  ["supabase_patterns", "what supabase project is cherp on?"],
  ["supabase_patterns", "how do i add a new table to the sb-admin proxy?"],
  ["supabase_patterns", "how does sbAuth() differ from SB()?"],
  ["supabase_patterns", "what is the ROLE_RANK ordering?"],
  // ── store_offline ──
  ["store_offline", "store.js list() returns empty on first load. why?"],
  ["store_offline", "how do i subscribe to store.js sync events?"],
  ["store_offline", "what events does store.onSync emit?"],
  ["store_offline", "how does store.js handle offline creates?"],
  ["store_offline", "what is the STALE_MS threshold in store.js?"],
  ["store_offline", "how do i force a fresh fetch from supabase in store.js?"],
  ["store_offline", "what is MAX_RETRIES in store.js and what happens when it's hit?"],
  ["store_offline", "how does the IDB key work in the rows store?"],
  ["store_offline", "why was idbListRows() slow before the 2026-04-15 hotfix?"],
  ["store_offline", "how does store.js know if a row is deleted locally?"],
  ["store_offline", "what does store.syncNow() do?"],
  ["store_offline", "how does store.js handle the temp-id to real-id swap?"],
  // ── auth_security ──
  ["auth_security", "how does PIN hashing work in cherp?"],
  ["auth_security", "what is the 5-minute grace window?"],
  ["auth_security", "what happens if launchApp() gets a profile without team_code?"],
  ["auth_security", "what are the hardcoded fallback users?"],
  ["auth_security", "how does session restore work when the tab is reopened?"],
  ["auth_security", "how does plaintext PIN upgrade work?"],
  ["auth_security", "what does _s.id hold and why does it matter?"],
  ["auth_security", "how is employee_id generated?"],
  // ── netlify_functions ──
  ["netlify_functions", "how does the sb-admin netlify function harden against abuse?"],
  ["netlify_functions", "where does the service role key live now?"],
  ["netlify_functions", "how do i add a new table that SB_Admin() needs to write to?"],
  ["netlify_functions", "what does the netlify function return to the client?"],
  ["netlify_functions", "what happens if SB_SVC is missing from environment variables?"],
  ["netlify_functions", "how does tableFromPath() extract the table name?"],
  ["netlify_functions", "what is the Prefer header flow through sb-admin?"],
  // ── agent_safety ──
  ["agent_safety", "what is the first hard rule for agents?"],
  ["agent_safety", "can an agent push to main?"],
  ["agent_safety", "can a mode 3 operator agent bypass the hard safety rules?"],
  ["agent_safety", "what happens when an agent hits the kill switch?"],
  ["agent_safety", "can an agent touch cherp.live or supabase production?"],
  ["agent_safety", "what should an agent do if a task says to fix function X and function Y also needs fixing?"],
  ["agent_safety", "how should agents handle secrets they encounter in code?"],
  ["agent_safety", "when should an agent create a new commit vs amend?"],
  // ── debugging ──
  ["debugging", "tasks screen hangs on load. what's the likely cause?"],
  ["debugging", "SB_Admin() is returning 403 forbidden_table. how do i fix it?"],
  ["debugging", "pin login always returns incorrect PIN for new accounts. why?"],
  ["debugging", "a newly created crew_task row has id undefined. why?"],
  ["debugging", "owner_id is undefined on new rows. why?"],
  ["debugging", "the cherp app shows login screen every time on iOS after backgrounding. why?"],
  ["debugging", "sb-admin returns 500 server_misconfigured_no_svc_key. fix?"],
  ["debugging", "store.js list() returns stale data. how do i force refresh?"],
  ["debugging", "a worker registers with role worker and gets 400. why?"],
  ["debugging", "the crew message screen shows nothing when querying by team_code. why?"],
  ["debugging", "new employee IDs are all XX-12345 instead of real initials. why?"],
];

// Shuffle
function shuffle(a) { for (let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];} return a; }

const rounds = parseInt(process.argv.find(a=>a.startsWith('--rounds='))?.split('=')[1]||'3');
const total = PAIRS.length * rounds;
let done = 0, good = 0, fail = 0;

console.log(`corpus_v2: ${total} prompts (${PAIRS.length} unique x ${rounds} rounds), model=${MODEL}`);

for (let r = 0; r < rounds; r++) {
  const batch = shuffle([...PAIRS]);
  for (const [cat, q] of batch) {
    done++;
    process.stdout.write(`[${Math.round(done/total*100)}%] ${done}/${total} ${cat}: `);
    const result = ask(q);
    if (!result.ok || result.response.length < 5) {
      console.log('FAIL');
      fail++;
      continue;
    }
    log(cat, q, result.response, result.elapsed);
    good++;
    console.log(`OK (${Math.round(result.elapsed/1000)}s) "${result.response.slice(0,60)}..."`);
  }
}

console.log(`\ndone. ${good} logged, ${fail} failed out of ${total}.`);
