import { spawnSync } from 'node:child_process';
import { appendFileSync } from 'node:fs';
const LOG = 'agent_mode/training/training-log.jsonl';
const MODEL = 'kenai:v1';
function strip(s){return String(s||'').replace(/[??[0-9;]*[a-zA-Z]/g,'').replace(/][^]*/g,'').trim();}
function ask(p,t=90){const t0=Date.now();const r=spawnSync('ollama',['run',MODEL],{input:p,encoding:'utf8',timeout:t*1000,maxBuffer:4*1024*1024,windowsHide:true});return{response:strip(r.stdout),elapsed:Date.now()-t0,ok:r.status===0};}
function log(cat,q,a,elapsed){appendFileSync(LOG,JSON.stringify({timestamp:new Date().toISOString(),taskId:'corpus3-'+Date.now().toString(36),model:MODEL,taskType:cat,attempt:1,objective:q.slice(0,200),prompt:q,response:a,success:true,elapsed,reviewed:true,approved:true,reviewNotes:'corpus_v3 dev-patterns'})+"
");}
const PAIRS = [
  [
    "ASYNC_JS",
    "My fetch is returning undefined inside an async function. What's wrong?"
  ],
  [
    "ASYNC_JS",
    "Should I use .then() chains or async/await?"
  ],
  [
    "ASYNC_JS",
    "How do I run 3 fetches in parallel instead of sequentially?"
  ],
  [
    "ASYNC_JS",
    "My async function throws but the error disappears. How do I catch it?"
  ],
  [
    "ASYNC_JS",
    "What's the difference between Promise.all and Promise.allSettled?"
  ],
  [
    "ASYNC_JS",
    "I need to retry a fetch up to 3 times with backoff. Pattern?"
  ],
  [
    "ASYNC_JS",
    "My forEach with async callbacks isn't working right."
  ],
  [
    "ASYNC_JS",
    "How do I abort a long-running fetch?"
  ],
  [
    "ASYNC_JS",
    "When should I use a top-level await vs wrapping in an async function?"
  ],
  [
    "ASYNC_JS",
    "I have a race condition where two async calls write the same file. Fix?"
  ],
  [
    "ASYNC_JS",
    "Difference between await and .then() for error handling?"
  ],
  [
    "ASYNC_JS",
    "My promise chain loses the original error message. Why?"
  ],
  [
    "NODE_BUILTINS",
    "How do I read a file synchronously without crashing the whole process?"
  ],
  [
    "NODE_BUILTINS",
    "Should I use readFileSync or readFile (async) for config loading?"
  ],
  [
    "NODE_BUILTINS",
    "How do I watch a file for changes in Node without external deps?"
  ],
  [
    "NODE_BUILTINS",
    "How do I run a shell command and capture its output synchronously?"
  ],
  [
    "NODE_BUILTINS",
    "Why use spawnSync over execSync?"
  ],
  [
    "NODE_BUILTINS",
    "How do I pass a large prompt to an ollama model without hitting cmd.exe arg limits?"
  ],
  [
    "NODE_BUILTINS",
    "How do I make a plain HTTP request without axios?"
  ],
  [
    "NODE_BUILTINS",
    "How do I ensure a directory exists before writing a file?"
  ],
  [
    "NODE_BUILTINS",
    "How do I append to a JSONL log file safely?"
  ],
  [
    "NODE_BUILTINS",
    "How do I parse command line args without a library?"
  ],
  [
    "NODE_BUILTINS",
    "How do I start an HTTP server that handles JSON APIs?"
  ],
  [
    "NODE_BUILTINS",
    "How do I detect the OS in Node without a dep?"
  ],
  [
    "NODE_BUILTINS",
    "How do I create a child process that stays alive (not spawnSync)?"
  ],
  [
    "ERROR_HANDLING",
    "Should I wrap every function in try/catch?"
  ],
  [
    "ERROR_HANDLING",
    "My error message is just \"Error\" with no context. How do I fix it?"
  ],
  [
    "ERROR_HANDLING",
    "How do I tell the difference between a network error and a 4xx response?"
  ],
  [
    "ERROR_HANDLING",
    "My app crashes on unhandled promise rejections. How do I catch them globally?"
  ],
  [
    "ERROR_HANDLING",
    "When is it OK to silently swallow an error?"
  ],
  [
    "ERROR_HANDLING",
    "How do I log errors without exposing stack traces to the client?"
  ],
  [
    "ERROR_HANDLING",
    "My try/catch isn't catching errors from async code inside it."
  ],
  [
    "ERROR_HANDLING",
    "What's the right pattern for a function that might fail but shouldn't crash the caller?"
  ],
  [
    "ERROR_HANDLING",
    "How do I distinguish between a timeout and a connection refused?"
  ],
  [
    "SUPABASE",
    "My Supabase insert returns a 428C9 error on an id field. Why?"
  ],
  [
    "SUPABASE",
    "How do I get the created row's id back after insert?"
  ],
  [
    "SUPABASE",
    "My Supabase query silently returns empty array. What's the first thing to check?"
  ],
  [
    "SUPABASE",
    "How do I filter a PostgREST query by a column value?"
  ],
  [
    "SUPABASE",
    "How do I do an upsert in PostgREST that won't fail on duplicate?"
  ],
  [
    "SUPABASE",
    "How do I query multiple rows where a column matches a list?"
  ],
  [
    "SUPABASE",
    "My Supabase call returns 401. What's wrong?"
  ],
  [
    "SUPABASE",
    "How do I sort and limit results in PostgREST?"
  ],
  [
    "SUPABASE",
    "How do I do a soft delete (set deleted_at) instead of hard delete?"
  ],
  [
    "SUPABASE",
    "My Supabase PATCH isn't updating. Returns 200 but nothing changed."
  ],
  [
    "SUPABASE",
    "How do I join two tables in a PostgREST query?"
  ],
  [
    "SUPABASE",
    "What headers do I always need for a Supabase REST call?"
  ],
  [
    "SUPABASE",
    "How do I check if a PostgREST request succeeded vs failed?"
  ],
  [
    "SUPABASE",
    "My daily_logs insert fails with a column error on team_code."
  ],
  [
    "SUPABASE",
    "My messages insert fails. I'm setting `content` but get a column error."
  ],
  [
    "SUPABASE",
    "crew_timecards is rejecting my insert. What columns does it expect?"
  ],
  [
    "SUPABASE",
    "user_profiles.role is rejecting my value. Valid values?"
  ],
  [
    "SUPABASE",
    "How do I do a recursive CTE query in Supabase?"
  ],
  [
    "INDEXEDDB",
    "How do I open an IndexedDB database and handle version upgrades?"
  ],
  [
    "INDEXEDDB",
    "How do I write to IndexedDB and wait for it to finish?"
  ],
  [
    "INDEXEDDB",
    "My IndexedDB read returns undefined. What did I miss?"
  ],
  [
    "INDEXEDDB",
    "How do I delete a record from IndexedDB?"
  ],
  [
    "INDEXEDDB",
    "What's the right key structure for a cache that stores rows by table and id?"
  ],
  [
    "INDEXEDDB",
    "How do I implement a write-through queue for offline sync?"
  ],
  [
    "INDEXEDDB",
    "My offline create returns a temp id. How do I swap it for the server's real id?"
  ],
  [
    "INDEXEDDB",
    "How do I check if IndexedDB is available in the current browser?"
  ],
  [
    "INDEXEDDB",
    "How do I clear an entire object store without deleting the database?"
  ],
  [
    "INDEXEDDB",
    "My IndexedDB transaction is aborting silently. Why?"
  ],
  [
    "INDEXEDDB",
    "How do I make a stale-while-revalidate cache with IndexedDB?"
  ],
  [
    "INDEXEDDB",
    "How do I avoid clobbering a record when two offline edits merge?"
  ],
  [
    "SERVICE_WORKER",
    "My service worker is caching stale JS. Users can't get the update."
  ],
  [
    "SERVICE_WORKER",
    "How do I force a service worker to take control immediately after update?"
  ],
  [
    "SERVICE_WORKER",
    "How do I intercept fetch and serve from cache first?"
  ],
  [
    "SERVICE_WORKER",
    "How do I update a cached file without busting every other cached asset?"
  ],
  [
    "SERVICE_WORKER",
    "My PWA works offline but a form submit fails. What to do?"
  ],
  [
    "SERVICE_WORKER",
    "How do I give users an escape hatch when the service worker breaks?"
  ],
  [
    "SERVICE_WORKER",
    "How do I check if the app is online inside a service worker?"
  ],
  [
    "SERVICE_WORKER",
    "How do I background-sync a failed request?"
  ],
  [
    "SERVICE_WORKER",
    "How do I cache dynamic API responses, not just static assets?"
  ],
  [
    "SERVICE_WORKER",
    "My service worker install is failing. How do I debug it?"
  ],
  [
    "NETLIFY",
    "How do I write a Netlify serverless function?"
  ],
  [
    "NETLIFY",
    "My Netlify function is returning a CORS error on the client."
  ],
  [
    "NETLIFY",
    "How do I read environment variables in a Netlify function?"
  ],
  [
    "NETLIFY",
    "My Netlify function times out. Default limit?"
  ],
  [
    "NETLIFY",
    "How do I keep a Supabase service key secret in a Netlify function?"
  ],
  [
    "NETLIFY",
    "How do I parse a JSON body from a POST to my Netlify function?"
  ],
  [
    "NETLIFY",
    "How do I redirect all routes to index.html for a SPA in Netlify?"
  ],
  [
    "NETLIFY",
    "My CSP is blocking Supabase fetch calls. Fix?"
  ],
  [
    "NETLIFY",
    "How do I test a Netlify function locally?"
  ],
  [
    "NETLIFY",
    "How do I return a file download from a Netlify function?"
  ],
  [
    "GIT",
    "I need to commit just one file, not everything."
  ],
  [
    "GIT",
    "I pushed to main by mistake. Can I revert?"
  ],
  [
    "GIT",
    "How do I see what changed in the last commit?"
  ],
  [
    "GIT",
    "I have uncommitted changes but need to switch branches."
  ],
  [
    "GIT",
    "How do I pull the latest without overwriting local changes?"
  ],
  [
    "GIT",
    "I accidentally added a secret to a commit. How do I remove it?"
  ],
  [
    "GIT",
    "How do I push to a specific remote (not origin)?"
  ],
  [
    "GIT",
    "How do I check which remotes this repo has?"
  ],
  [
    "GIT",
    "My merge has conflicts. What's the fastest way to resolve?"
  ],
  [
    "GIT",
    "How do I create a new branch from the current state?"
  ],
  [
    "GIT",
    "How do I see the commit log as one line per commit?"
  ],
  [
    "GIT",
    "I need to undo the last commit but keep the file changes."
  ],
  [
    "GIT",
    "How do I tag a release?"
  ],
  [
    "GIT",
    "How do I see which branch I'm on?"
  ],
  [
    "SECURITY",
    "Is it safe to put a Supabase anon key in client-side JS?"
  ],
  [
    "SECURITY",
    "My app has the Supabase service key in client JS. Is that a problem?"
  ],
  [
    "SECURITY",
    "How do I hash a PIN for storage?"
  ],
  [
    "SECURITY",
    "How do I prevent XSS when rendering user content to the DOM?"
  ],
  [
    "SECURITY",
    "How do I validate a UUID from user input before using it in a query?"
  ],
  [
    "SECURITY",
    "How do I protect an API endpoint with a PIN?"
  ],
  [
    "SECURITY",
    "How do I store sensitive tokens on the client?"
  ],
  [
    "SECURITY",
    "My API is wide open. What's the minimum viable auth?"
  ],
  [
    "SECURITY",
    "How do I prevent a user from accessing another user's data in Supabase?"
  ],
  [
    "SECURITY",
    "What's the minimum CSP for a Netlify-deployed app?"
  ],
  [
    "SECURITY",
    "How do I rotate a leaked API key safely?"
  ],
  [
    "SECURITY",
    "Someone is hammering my /api endpoint. Quick mitigation?"
  ],
  [
    "DEBUGGING",
    "My fetch is failing but I can't see why. How do I inspect it?"
  ],
  [
    "DEBUGGING",
    "I added a console.log but nothing shows up in Node."
  ],
  [
    "DEBUGGING",
    "My IndexedDB transaction isn't working and there's no error."
  ],
  [
    "DEBUGGING",
    "My API returns 200 but the data is wrong. Where do I start?"
  ],
  [
    "DEBUGGING",
    "I can't reproduce a bug locally that happens in prod."
  ],
  [
    "DEBUGGING",
    "My service worker is intercepting requests it shouldn't."
  ],
  [
    "DEBUGGING",
    "My Node.js server is leaking memory. How do I find the source?"
  ],
  [
    "DEBUGGING",
    "A spawnSync call is timing out but I don't know why."
  ],
  [
    "DEBUGGING",
    "How do I trace which code path is actually executing?"
  ],
  [
    "DEBUGGING",
    "My ANSI escape codes are appearing in log files as literal characters."
  ],
  [
    "DEBUGGING",
    "My JSON.parse is throwing. How do I debug without crashing?"
  ],
  [
    "DEBUGGING",
    "My endpoint is called but the handler function never runs. Why?"
  ],
  [
    "DEBUGGING",
    "How do I see what a running Node process is doing?"
  ],
  [
    "PIPE_R",
    "How do I add a new menu to hub.js?"
  ],
  [
    "PIPE_R",
    "Can I add npm packages to Pipe-R?"
  ],
  [
    "PIPE_R",
    "I edited tasks.json while server.js is running. Why didn't it take effect?"
  ],
  [
    "PIPE_R",
    "How do I add a new HTTP endpoint to server.js?"
  ],
  [
    "PIPE_R",
    "How do I pass an agent id to a dispatch and make sure it sticks?"
  ],
  [
    "PIPE_R",
    "Which agent do I route a Supabase/PostgREST implementation task to?"
  ],
  [
    "PIPE_R",
    "Which agent do I route a CHERP domain scan or recon task to?"
  ],
  [
    "PIPE_R",
    "Alakazam Archive keeps timing out on summarize tasks. What do I do?"
  ],
  [
    "PIPE_R",
    "How do I strip ANSI escape codes from ollama stdout before logging?"
  ],
  [
    "PIPE_R",
    "How do I add a new agent to the squad?"
  ],
  [
    "PIPE_R",
    "What's a \"blocked\" agent? How does it affect dispatch?"
  ],
  [
    "PIPE_R",
    "How do I check if a task was actually approved vs just successful?"
  ],
  [
    "PIPE_R",
    "How do I trigger a dream pass for an agent?"
  ],
  [
    "PIPE_R",
    "How do I warm a cold model before dispatching to it?"
  ],
  [
    "CHERP",
    "How do I add a new table to the CHERP sync?"
  ],
  [
    "CHERP",
    "A CHERP deploy broke the app and I can't fix it fast. Quick escape?"
  ],
  [
    "CHERP",
    "How does CHERP auth work without Supabase reachable?"
  ],
  [
    "CHERP",
    "My CHERP change is deployed but users still see the old version."
  ],
  [
    "CHERP",
    "store.js returns stale data. How fresh is the cache?"
  ],
  [
    "CHERP",
    "How do I ensure a store.js create retries if the network is down?"
  ],
  [
    "CHERP",
    "Why was `_s.id` never being set on owner_id fields before phase 6a?"
  ],
  [
    "CHERP",
    "How do I give a user their employee ID if they don't have one?"
  ],
  [
    "CHERP",
    "What does `Prefer: resolution=merge-duplicates,return=representation` do?"
  ],
  [
    "CHERP",
    "How do I look up another user by employee ID in the scanner flow?"
  ],
  [
    "CHERP",
    "My crew_tasks insert fails with a BIGINT identity error."
  ],
  [
    "CHERP",
    "How do I trigger a manual Google Sheets sync from the server?"
  ],
  [
    "CHERP",
    "How does the CHERP offline conflict resolution work for notes?"
  ],
  [
    "CHERP",
    "When does a CHERP conflict escalate beyond last-write-wins?"
  ],
  [
    "JS_PATTERNS",
    "How do I deep clone an object without lodash?"
  ],
  [
    "JS_PATTERNS",
    "How do I check if a value is a real number (not NaN)?"
  ],
  [
    "JS_PATTERNS",
    "How do I merge two objects, with the second overriding the first?"
  ],
  [
    "JS_PATTERNS",
    "How do I debounce an input handler?"
  ],
  [
    "JS_PATTERNS",
    "How do I throttle a function that fires on scroll or resize?"
  ],
  [
    "JS_PATTERNS",
    "How do I sort an array of objects by a date string field?"
  ],
  [
    "JS_PATTERNS",
    "How do I find the most recently modified entry in an array?"
  ],
  [
    "JS_PATTERNS",
    "How do I group an array of objects by a key?"
  ],
  [
    "JS_PATTERNS",
    "How do I deduplicate an array of primitives?"
  ],
  [
    "JS_PATTERNS",
    "How do I make a function that can only run once?"
  ],
  [
    "JS_PATTERNS",
    "How do I implement exponential backoff?"
  ],
  [
    "JS_PATTERNS",
    "What's the cleanest way to parse a URL's query params?"
  ],
  [
    "JS_PATTERNS",
    "How do I write a single-flight guard to prevent duplicate in-flight requests?"
  ],
  [
    "JS_PATTERNS",
    "How do I pipe a large string to a child process's stdin?"
  ],
  [
    "ES_MODULES",
    "How do I get __dirname in an ES module (it's not defined)?"
  ],
  [
    "ES_MODULES",
    "How do I do a dynamic import in ES modules?"
  ],
  [
    "ES_MODULES",
    "My ES module can't import a CommonJS module. Fix?"
  ],
  [
    "ES_MODULES",
    "How do I export multiple things from an ES module?"
  ],
  [
    "ES_MODULES",
    "I have circular imports and things are undefined at startup. Fix?"
  ],
  [
    "ES_MODULES",
    "How do I use top-level await in a Node.js script?"
  ],
  [
    "OLLAMA",
    "How do I run an ollama model with a prompt from stdin in Node?"
  ],
  [
    "OLLAMA",
    "My ollama call is taking too long. How do I set a timeout?"
  ],
  [
    "OLLAMA",
    "How do I create a custom ollama model from a Modelfile?"
  ],
  [
    "OLLAMA",
    "My Modelfile SYSTEM prompt isn't taking effect."
  ],
  [
    "OLLAMA",
    "How do I list which models are currently loaded in VRAM?"
  ],
  [
    "OLLAMA",
    "Ollama stdout has ANSI spinner codes. How do I strip them before logging?"
  ],
  [
    "OLLAMA",
    "Which ollama model should I use for code generation tasks?"
  ],
  [
    "OLLAMA",
    "How do I warm a model before it gets a task dispatch?"
  ],
  [
    "WINDOWS",
    "How do I find and kill a Node.js process on Windows?"
  ],
  [
    "WINDOWS",
    "My shell command works in PowerShell but not Git Bash."
  ],
  [
    "WINDOWS",
    "How do I run a PowerShell script from Node.js?"
  ],
  [
    "WINDOWS",
    "How do I get the current wallpaper path in Windows programmatically?"
  ],
  [
    "WINDOWS",
    "My Windows path has spaces and my shell command breaks."
  ],
  [
    "WINDOWS",
    "How do I check if a process is running by name in Node on Windows?"
  ],
  [
    "CODE_REVIEW",
    "This PR adds 400 lines for a feature I can do in 60. What do I say?"
  ],
  [
    "CODE_REVIEW",
    "The code works but has no error handling at all. How bad is that?"
  ],
  [
    "CODE_REVIEW",
    "This function is 200 lines. Should I split it?"
  ],
  [
    "CODE_REVIEW",
    "The PR adds a try/catch around every single function call including pure functions."
  ],
  [
    "CODE_REVIEW",
    "There are console.log statements all over this code."
  ],
  [
    "CODE_REVIEW",
    "The PR uses a class where a closure would do."
  ],
  [
    "CODE_REVIEW",
    "This code imports an npm package for a 10-line utility function."
  ],
  [
    "CODE_REVIEW",
    "The PR has no comments at all. Is that a problem?"
  ],
  [
    "HALO",
    "How do I structure a game-state keylog for a training loop?"
  ],
  [
    "HALO",
    "How do I detect what's on screen without a game API?"
  ],
  [
    "HALO",
    "How do I build a drive loop for automated game training?"
  ],
  [
    "HALO",
    "How do I inject keystrokes into a game window programmatically on Windows?"
  ],
  [
    "HALO",
    "How do I record and replay a sequence of inputs for testing?"
  ],
  [
    "ARCHITECTURE",
    "Should I use a class or module-level functions for a utility?"
  ],
  [
    "ARCHITECTURE",
    "When do I split a 3000-line file into multiple files?"
  ],
  [
    "ARCHITECTURE",
    "I need to cache expensive data with a TTL. Pattern?"
  ],
  [
    "ARCHITECTURE",
    "Should I use JSON or a database for task queue storage?"
  ],
  [
    "ARCHITECTURE",
    "My config has grown to 50 fields spread across 8 files. Fix?"
  ],
  [
    "ARCHITECTURE",
    "When should I use spawnSync vs spawn in Node?"
  ],
  [
    "ARCHITECTURE",
    "Should the CHERP store.js cache TTL be shorter or longer?"
  ],
  [
    "ARCHITECTURE",
    "How do I add a new data store to an existing IndexedDB schema?"
  ]
];


function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
const rounds=parseInt(process.argv.find(a=>a.startsWith('--rounds='))?.split('=')[1]||'2');
const total=PAIRS.length*rounds;
let done=0,good=0,fail=0;
console.log('corpus_v3: '+total+' prompts ('+PAIRS.length+' unique x '+rounds+' rounds)');
for(let r=0;r<rounds;r++){
  const batch=shuffle([...PAIRS]);
  for(const [cat,q] of batch){
    done++;
    process.stdout.write('['+Math.round(done/total*100)+'%] '+done+'/'+total+' '+cat+': ');
    const result=ask(q);
    if(!result.ok||result.response.length<5){console.log('FAIL');fail++;continue;}
    log(cat,q,result.response,result.elapsed);
    good++;
    console.log('OK ('+Math.round(result.elapsed/1000)+'s) "'+result.response.slice(0,60)+'..."');
  }
}
console.log('done. '+good+' logged, '+fail+' failed.');
