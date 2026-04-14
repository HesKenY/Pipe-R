# Tech Stack

## Agent Runtime
- Python 3.11+
- FastAPI (HTTP + WebSocket server)
- Uvicorn (ASGI server)
- Ollama (local model runtime, localhost:11434)

## Data Layer
- SQLite (session memory, brain index search)
- Markdown files (human-readable brain index)
- JSONL (action log)

## Tools / Shell
- ripgrep (rg) — fast code search
- git — version control
- black — Python formatter
- flake8 — Python linter
- pytest — Python test runner

## Desktop Automation (Mode 3 only)
- pyautogui — mouse, keyboard control
- Pillow — screenshot capture
- pytesseract — OCR (optional)

## Frontend
- Single HTML file served by FastAPI
- Vanilla JS with WebSocket client
- No build step required

## Config
- YAML (permissions, models, tools, projects)
- python-yaml (PyYAML)

## Platform
- Windows 10/11 (primary target)
- Linux compatible (paths adjust)

## Port Map — Ken's machine
- **Pipe-R server**: `127.0.0.1:7777` (Node.js, `server.js`)
- **Ken AI offline agent**: `127.0.0.1:7778` (this project,
  moved off 7777 to avoid clashing with Pipe-R — see `main.py`)
- **Ollama**: `127.0.0.1:11434`
- **Bird's Nest**: `127.0.0.1:8080`

## Local Ollama roster (Ken's machine as of 2026-04-14)
- `ken-ai:latest` — trainer (qwen2.5-coder:14b + Ken profile
  SYSTEM block)
- `qwen2.5-coder:14b` — implementation
- `cherp-piper:latest` — recon
- `forgeagent:latest` — integration
- `llama3.1:8b` — observability
- `jefferyjefferferson:latest` — quality
- `jefferferson:latest` — memory/archive (slow cold start)
- `m3w-learning:latest` — learning/tutor
- `llama3.2-vision` — for HUD reading, halo_vision_hunt

Prefer `ken-ai:latest` for anything voice-sensitive. Prefer
`qwen2.5-coder:14b` for code generation. Routing lives in
`config/models.yaml` under `profiles:`.

## Related Ken projects on this machine
See `config/projects.yaml` for paths. The key ones the agent
will touch most:
- `C:/Users/Ken/Desktop/Codex` — this clone (parallel Codex
  coordination with Claude)
- `C:/Users/Ken/Desktop/Claude` — the parallel Claude clone
- `C:/Users/Ken/Desktop/Codex/halo-trainer` — classroom drills
- `C:/Users/Ken/Desktop/Codex/offline_agent` — this project
- Workspace (via `workspace/` alias) — default sandbox for
  throwaway edits
