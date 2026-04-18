# Project Map

This is the high-level map of what matters for the offline developer
agent.

## Tier 1 - live product work

### CHERP
- what: construction crew management platform
- repo: private `HesKenY/CHERP`
- path: `C:/Users/Ken/Desktop/Codex/workspace/CHERP`
- stack: vanilla JS + HTML, Supabase, Netlify
- status: production-sensitive. offline-first rules matter.
- critical files: `js/store.js`, `demo.html`, `cherp-schema.sql`

### Pipe-R
- what: local command center and agent orchestration server
- repo: shared `HesKenY/CHERP-Backup` plus `Pipe-R`
- path: `C:/Users/Ken/Desktop/Codex`
- stack: Node.js built-ins, Ollama, local services
- status: daily-driver control surface
- critical files: `server.js`, `hub.js`, `pipe-r.html`, `agent_mode/*`

### Bird's Nest
- what: CHERP instance manager
- repo: `HesKenY/CHERP-Nest`
- status: active but secondary

## Tier 2 - local developer tooling

### offline_agent
- what: local Claude-Code-style coding workbench
- path: `C:/Users/Ken/Desktop/Codex/offline_agent`
- port: `127.0.0.1:7778`
- role: read the brain, patch code, run tests, track tasks, and lead the local coding squad

### agent_mode
- what: local squad runtime and training logs
- path: `C:/Users/Ken/Desktop/Codex/agent_mode`
- role: source of live roster state, safety rules, task queue, and recent dispatch history

### corpora and brain tooling
- what: dataset builders, manifests, exports
- path: `C:/Users/Ken/Desktop/Codex/brain` and `C:/Users/Ken/Desktop/Codex/corpora`
- role: training and alignment source for Ken V4 offline developer

## Tier 3 - parallel clone coordination

### Codex clone
- path: `C:/Users/Ken/Desktop/Codex`
- role: active working tree for this agent

### Claude clone
- path: `C:/Users/Ken/Desktop/Claude`
- role: peer clone for coordination
- rule: read if needed, do not write from offline_agent

## Never forget
- Codex is the write target
- Claude is the peer clone
- CHERP is production-sensitive
- offline_agent is coding-first by default
