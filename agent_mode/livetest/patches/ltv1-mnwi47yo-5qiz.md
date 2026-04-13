# Patch Plan — ltv1-mnwi47yo-5qiz

## Round summary
Reused standing Test crew `WS5A3Q` but every child-table insert (`crew_members`, `crew_tasks`, `crew_timecards`) failed with FK 23503 on `team_code_fkey`, meaning the reuse path never verified the parent row actually existed. Worse, cleanup then deleted `team_codes?code=eq.WS5A3Q` — the standing Test crew is now gone from production. 18/38 ops passed; Team B's Umbr30n agent also timed out (ollama ETIMEDOUT), so QA coverage is incomplete.

## Issues (ranked)
1. **Reuse mode runs destructive cleanup** — `cleanup_crew` deleted the standing Test crew even though livetest was told to reuse it — severity: **high**
   *Evidence*: op 34 `cleanup_crew — team_codes?code=eq.WS5A3Q` after op 5 said "reusing existing team_code"
2. **Reuse path skips parent-row existence check** — every `team_code`-scoped insert died with FK 23503, suggesting WS5A3Q was already missing (or column/case mismatch) before the round even started — severity: **high**
   *Evidence*: ops 7, 9, 11, 13, 14–20, 25–28 all `23503 ... _team_code_fkey`
3. **Cleanup order leaves messages dangling on user delete** — `cleanup_user` for the foreman hit `messages_sender_id_fkey` because the scenario's messages were deleted by id but the foreman had older residue — severity: **mid**
   *Evidence*: op 35 `23503 ... messages_sender_id_fkey`; CLAUDE.md already flags this as known FK order gotcha
4. **Umbr30n QA agent times out mid-round** — `spawnSync ollama ETIMEDOUT` means the observer debrief has no QA voice; round scoring is blind on the regression side — severity: **mid**
   *Evidence*: Team B section `Umbr30n QA · (error: spawnSync ollama ETIMEDOUT)`
5. **M3w companion hallucinated "task id 1234"** — no such id exists in this round's ops; learning proposal is citing fake evidence — severity: **low**
   *Evidence*: Companion proposal `task id 1234 (D3c1du3y3 Foreman's end-of-day site report)`

## Proposed fixes
1. **Guard cleanup when reusing a crew**
   - **target**: `agent_mode/core/livetest.js`
   - **change**: in the cleanup phase, skip the `cleanup_crew` step (and skip `cleanup_members` wholesale delete by team_code) whenever `reuseExistingCrew` / `teamCode` was passed. Only delete rows the round itself created, tracked by id.
   - **test**: re-run `POST /api/livetest/start` with `{ scenarioId: "kitchen-remodel-3day", teamCode: "WS5A3Q" }` against a restored WS5A3Q; confirm `team_codes?code=eq.WS5A3Q` still exists after the round ends.
   - **risk**: if the id-tracking list is incomplete, orphaned rows accumulate in the reused crew. Mitigate by logging any untracked inserts.
   - **confidence**: **high**
2. **Verify + restore WS5A3Q before any child inserts**
   - **target**: `agent_mode/core/livetest.js` (reuse branch of `create_crew` phase)
   - **change**: before proceeding past phase 2, `GET team_codes?code=eq.WS5A3Q&select=code`. If 0 rows, either re-create the row (preferred for standing Test crew) or abort the round with a clear error instead of cascading 23503s across 15 ops.
   - **test**: temporarily rename WS5A3Q in a dev copy, start a round with `teamCode: "WS5A3Q"`, confirm the round aborts at phase 2 with a readable message and does NOT attempt member/task/timecard inserts.
   - **risk**: auto-recreating the parent row could mask real schema drift. Safer to abort and surface the missing-row error to the deck.
   - **confidence**: **high**
3. **Restore WS5A3Q in production manually (one-shot, not a code fix)**
   - **target**: Supabase `team_codes` table (not a file — manual SQL via CHERP-Nest or dashboard)
   - **change**: `INSERT INTO team_codes (code, ...) VALUES ('WS5A3Q', ...)` using the previous row's column values (pull from the last successful round JSON in `agent_mode/livetest/rounds/`).
   - **test**: `GET /rest/v1/team_codes?code=eq.WS5A3Q` returns 1 row before any further livetest run.
   - **risk**: wrong column defaults could break real Test-crew usage. Cross-check against a known-good round file before inserting.
   - **confidence**: **mid**
4. **Delete messages before user_profiles in cleanup**
   - **target**: `agent_mode/core/livetest.js` cleanup phase ordering
   - **change**: ensure `DELETE messages?sender_id=eq.<uuid>` runs before `DELETE user_profiles?id=eq.<uuid>` for every sim user, not just the ones whose messages the scenario happens to track by id. Tolerate 0-row deletes.
   - **test**: run the scenario, check server log: no `messages_sender_id_fkey` errors in the cleanup block.
   - **risk**: very low — only deletes messages authored by sim users created this round.
   - **confidence**: **high**
5. **Raise Umbr30n executor timeout + add round-level "QA missing" flag**
   - **target**: `agent_mode/core/livetest.js` (observer dispatch) — reuse the same timeout bump pattern already used for `jefferferson:latest` cold starts
   - **change**: bump observer dispatch timeout to 120s for Umbr30n; if the call still ETIMEDOUTs, write `"qa": null, "qaError": "<msg>"` into the round JSON so the deck can render a red QA-MISSING badge instead of silently dropping the section.
   - **test**: start a fresh round, watch `agent_mode/livetest/rounds/<id>.json` — Umbr30n section should be populated; if not, the round should carry an explicit null.
   - **risk**: longer timeouts make rounds slower. Acceptable — QA blindness is worse.
   - **confidence**: **mid**

## Deploy gate
A re-run of `kitchen-remodel-3day` against WS5A3Q must reach ≥36/38 ops green with WS5A3Q still present in `team_codes` after cleanup, AND the round JSON must contain a non-null Umbr30n QA section — before anything touches `main`.