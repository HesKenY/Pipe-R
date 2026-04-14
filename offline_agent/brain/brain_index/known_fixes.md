# Known Patterns & Fixes

## Pattern: Tool Call Parse Failure
**Symptom**: Model outputs malformed JSON for tool call
**Fix**: Retry with stricter system prompt. Include JSON schema in prompt. Max 3 retries then escalate to operator.

## Pattern: Context Overflow
**Symptom**: Model truncates mid-response or forgets earlier context
**Fix**: Summarize session history. Pull only top-K brain chunks. Reduce repo scan scope.

## Pattern: Patch Apply Failure
**Symptom**: unified diff fails to apply (line mismatch)
**Fix**: Re-read file, regenerate patch from fresh content. Never apply stale diffs.

## Pattern: Test Runner Not Found
**Symptom**: pytest/npm not on PATH
**Fix**: Check config/projects.yaml for test_command. Use full path or activate venv first.

## Pattern: Ollama Not Running
**Symptom**: Connection refused on localhost:11434
**Fix**: Start Ollama service. Check ollama serve is running. Verify model is pulled.

## Pattern: Permission Denied on File Write
**Symptom**: OS rejects file write
**Fix**: Verify path is in restricted_paths for current mode. Do not escalate automatically — notify operator.

## Pattern: Git Uncommitted Changes Before Task
**Symptom**: Dirty working tree
**Fix**: Run git status, log state. Offer to stash before proceeding. Never auto-commit existing changes.

## Pattern: Ollama CMD Window Spam (Windows)
**Symptom**: Every ollama subprocess spawns a visible cmd window
**Fix**: Pass `creationflags=subprocess.CREATE_NO_WINDOW` or the
equivalent `windowsHide: true` in Node. Shell-tools must set this
by default on Windows.

## Pattern: Ollama Stdout ANSI Spinner Leak
**Symptom**: chat-log.jsonl contains `\u001b[?25l...` terminal
spinner codes from `ollama run`
**Fix**: Strip before writing to memory:
`text.replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '').replace(/\u001b\][^\u0007]*\u0007/g, '')`.
Any new ollama spawn path needs this strip.

## Pattern: Python Stdout Block-Buffered on Windows
**Symptom**: Node spawn never sees python subprocess output until
the process exits
**Fix**: Spawn python with `-u` flag (unbuffered) or set
`PYTHONUNBUFFERED=1` in env.

## Pattern: CHERP `crew_tasks.id` Client-Side
**Symptom**: POST to crew_tasks returns 428C9 "cannot insert into
generated always column"
**Fix**: Never include `id` in the POST body. Use
`Prefer: return=representation` header and read the assigned bigint
back from the response.

## Pattern: Drill Drifts Into Role Persona
**Symptom**: halo-trainer drill response is plumbing chit-chat
instead of the rubric-requested format
**Fix**: The orchestrator's SYSTEM role wrapper is polluting.
halo-trainer bypasses via direct `ollama run`. If a drill still
drifts: tighten the prompt, add `must_not_contain` rubric checks
for the drift words ("plumbing", "construction", "analogy").

## Pattern: Ctypes OverflowError on x64 HMODULE
**Symptom**: `argument 2: OverflowError: int too long to convert`
when calling psapi.GetModuleBaseNameW
**Fix**: Use `(wintypes.HMODULE * 1024)()` not `(ctypes.c_void_p * 1024)()`
and set explicit `argtypes` on every psapi function you call.

## Pattern: CHERP Service Worker Cache Stale
**Symptom**: Users see old app version after deploy
**Fix**: Bump the cache version string in `sw.js` OR use the
`?sw=off` escape hatch or `/clear-sw.html` admin button.

## Pattern: Pipe-R Server Port Clash
**Symptom**: Can't start offline_agent — port 7777 already in use
**Fix**: Pipe-R owns 7777. offline_agent should bind 7778.
See `main.py` host/port args.
