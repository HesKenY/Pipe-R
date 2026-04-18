# Tech Stack

## Runtime
- Python 3.11+
- FastAPI
- Uvicorn
- Ollama on `127.0.0.1:11434`

## Storage
- SQLite for memory index
- Markdown for human-readable brain files
- JSONL for action and training logs
- JSON config files for live squad state under `agent_mode/config`

## Core tools
- git
- ripgrep
- pytest
- black / flake8 / ruff when available
- node for local repo checks

## Frontend
- single static HTML file
- vanilla JS
- WebSocket chat loop

## Port map
- Pipe-R: `127.0.0.1:7777`
- offline_agent: `127.0.0.1:7778`
- Ollama: `127.0.0.1:11434`
- Bird's Nest: `127.0.0.1:8080`

## Preferred local models
- `kenai:v4-offline-developer` - target planner tag
- `kenai:v3` - immediate fallback
- `ken-ai:latest` - voice-aware fallback
- `qwen2.5-coder:14b` - coding backbone
- `llama3.1:8b` - fast lightweight tasks
- `llama3.2-vision` - screenshots and UI reads

## Working paths
- `C:/Users/Ken/Desktop/Codex`
- `C:/Users/Ken/Desktop/Codex/offline_agent`
- `C:/Users/Ken/Desktop/Codex/agent_mode`
- `C:/Users/Ken/Desktop/Codex/workspace/CHERP`
- `C:/Users/Ken/Desktop/Claude` read-only from this runtime
