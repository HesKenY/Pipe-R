# Ken AI

A personality-shell AI model built in Ken's voice, on top of `qwen2.5-coder:14b`, designed to plug into Pipe-R's Agent Mode orchestrator.

## What's in this folder

- **`profile.md`** — Ken's voice, coding rules, communication style, hard no's, and domain knowledge. This is the source of truth. Edit this to tune the personality.
- **`Modelfile`** — Ollama recipe that turns Qwen Coder into Ken AI by injecting the profile as a SYSTEM prompt.
- **`README.md`** — this file.

## How to build Ken AI (one-time, then again after each profile edit)

```bash
cd C:/Users/Ken/Desktop/Claude
ollama create ken-ai -f agent_mode/ken/Modelfile
```

That's it. After the command finishes, `ken-ai:latest` is available as an Ollama model and the Pipe-R orchestrator will auto-detect it on next boot.

## How to verify Ken AI is working

```bash
ollama run ken-ai:latest "What's your hard no list?"
```

If it responds with the hard no's from `profile.md`, the build worked.

## How it plugs into Pipe-R

Ken AI is already registered in `agent_mode/config/agents.json` with:

```json
{
  "id": "ken-ai:latest",
  "displayName": "Ken AI",
  "role": "Personality Lead",
  "personality": "ken-coder",
  "status": "pending_build"
}
```

Once the `ollama create` command succeeds, the registry's availability check will flip `ken-ai:latest` to live and the orchestrator will include it in auto-assignment. You can then:

- Route any task to Ken AI by assigning `ken-ai:latest` in hub.js
- Use Ken AI as the default for any task that fits its personality
- Let Ken AI co-pilot with Claude Code on Pipe-R and CHERP work

## How the `ken-coder` personality works without the Ollama build

Even before you run `ollama create`, any existing agent can run in Ken-mode by setting its `personality` field to `"ken-coder"` in `agents.json`. The executor will load `profile.md` at prompt-build time and inject it as the system prompt. This gives you a usable Ken voice immediately without waiting for a model rebuild.

## Training data flow

Every task Ken AI runs writes a prompt/response pair to `agent_mode/training/training-log.jsonl` (handled automatically by `executor.js`). Over time this becomes the training set for a real fine-tune — but not until there's enough curated data to justify it.

## When to rebuild

Rebuild Ken AI (`ollama create ken-ai -f Modelfile`) whenever you edit `profile.md` and want the changes baked into the Ollama model. If you only want the change to affect the `ken-coder` personality prefix used by existing agents, you don't need to rebuild — the executor reads `profile.md` fresh on every startup.
