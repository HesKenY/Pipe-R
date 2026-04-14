# OfflineAgent v1.0

A fully offline AI coding agent running on your local machine via Ollama.
Windowed UI at `http://localhost:7777`. No cloud. No telemetry.

## Quick Start

```bat
# 1. Install Ollama from https://ollama.com
ollama serve
ollama pull qwen2.5-coder:14b

# 2. Setup
setup.bat

# 3. Run
python main.py

# 4. Open browser
# http://localhost:7777
```

## Permission Modes

| Mode | Name | Capability |
|------|------|------------|
| 0 | Read Only | Read files, search, plan. No writes. |
| 1 | Workspace | Edit files in workspace/, run tests/lint. |
| 2 | Elevated Dev | Install packages, Docker, browser. |
| 3 | Operator | Full desktop automation. Kill switch required. |

Start in **Mode 0**. Only escalate when the task needs it.

## Architecture

```
offline_agent/
├─ main.py               ← FastAPI server + WebSocket
├─ agent_core/
│  ├─ planner.py         ← Main agent loop
│  ├─ permissions.py     ← Mode enforcement
│  ├─ memory_retriever.py← Brain index search
│  ├─ session_manager.py ← Session logs + tasks
│  ├─ tool_router.py     ← Tool dispatch
│  ├─ patch_engine.py    ← Safe file patching
│  ├─ vision.py          ← Screenshot understanding
│  └─ desktop_controller.py ← Mouse/keyboard (Mode 3)
├─ models/
│  └─ ollama_client.py   ← Ollama API wrapper
├─ tools/
│  ├─ filesystem_tools.py
│  ├─ git_tools.py
│  ├─ shell_tools.py
│  ├─ search_tools.py
│  └─ ui_tools.py
├─ config/
│  ├─ permissions.yaml   ← Mode rules
│  ├─ models.yaml        ← Ollama settings
│  ├─ tools.yaml         ← Tool definitions
│  └─ projects.yaml      ← Your projects
├─ brain/
│  ├─ master_index/      ← Agent memory (markdown)
│  └─ sessions/          ← Session logs
├─ frontend/
│  └─ index.html         ← Full UI
└─ workspace/            ← Default project folder
```

## Safety

- Kill switch: `config/.kill_switch` file or UI button halts agent instantly
- All file writes create backups in `logs/backups/`
- All actions logged to `logs/actions.jsonl`
- Dry run mode on by default (config/permissions.yaml)

## Adding Your Project

Edit `config/projects.yaml`:
```yaml
projects:
  my_app:
    name: "My App"
    path: "C:/Users/Me/Projects/my_app"
    language: "python"
    test_command: "pytest tests/"
```

## Ollama Model Recommendations

| Model | Size | Use |
|-------|------|-----|
| qwen2.5-coder:14b | ~9GB | Best coding, default |
| qwen2.5-coder:7b  | ~4GB | Faster, smaller RAM |
| llava:13b         | ~8GB | Vision/screenshot mode |
| codellama:13b     | ~8GB | Alternative coder |
