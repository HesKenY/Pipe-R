# ForgeAgent — Local AI Coding Agent Hub

Train, deploy, and manage offline AI coding models. All-in-one terminal app powered by Ollama.

## Quick Start

```
SETUP.bat          First-time setup (installs everything)
START.bat          Launch ForgeAgent
```

Or manually:
```bash
pip install -e .
ollama pull qwen2.5-coder:14b
ollama create forgeagent -f Modelfile
python -m forgeagent
```

## Launchers

| File | What it does |
|------|-------------|
| `SETUP.bat` | Install Python deps, Ollama, pull model — run once |
| `START.bat` | Launch interactive TUI (auto-installs on first run) |
| `START-CLI.bat` | Launch plain text REPL mode |
| `TRAIN.bat` | Open with training tab focused |
| `DEPLOY.bat` | Open with deploy tab focused |
| `build-exe.bat` | Build standalone `ForgeAgent.exe` via PyInstaller |

## Features

### Train Custom Models
- Create training datasets from conversations, codebase, or web scraping
- Generate synthetic tool-use examples automatically
- Scrape GitHub repos and docs (TypeScript, Python, Rust, Node, React, DevOps)
- Build custom Ollama models with one click ("Easy Train" wizard)
- Evaluate models with 12 built-in benchmarks
- Export datasets in JSONL, ChatML, Alpaca, or OpenAI format

### Deploy Agents to Projects
- Deploy AI agents into any project folder (creates `.forgeagent/` config)
- 8 templates: fullstack, python, rust, go, devops, minimal, reviewer, docs
- Launch agents in new terminal windows
- Each agent gets its own memory, sessions, and launch scripts

### 6-Slot Multi-Model
- Load up to 6 different models simultaneously
- Send tasks to individual slots or broadcast to all
- AI-coordinated work splitting across slots
- Cross-reference detection for file conflicts between slots
- `@1 message` shorthand to talk to slot 1 directly

### 12 Built-In Tools
| Tool | What it does |
|------|-------------|
| `bash` | Run shell commands |
| `read_file` | Read files with line numbers |
| `write_file` | Create files (auto-mkdir) |
| `edit_file` | Find-and-replace edits |
| `list_dir` | Directory listings |
| `search_files` | Grep across files |
| `glob` | Find files by pattern |
| `web_fetch` | Fetch URL contents |
| `task` | Persistent todo list |
| `datetime` | Current date/time |
| `memory_save` | Save to long-term memory |
| `memory_search` | Search memory |

### Multi-Round Tool Orchestration
The query engine streams model responses, detects tool calls, executes them, feeds results back, and loops up to 8 rounds per query.

### Persistent Memory + Dream Consolidation
Conversations are periodically summarized and saved as "dreams" for cross-session continuity.

## Commands (29)

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/hub` | Dashboard overview |
| `/model <n>` | Switch model |
| **Training** | |
| `/dataset <sub>` | create, list, generate, harvest, harvest-code, export, delete, add |
| `/scrape <sub>` | topics, topic, url, github |
| `/train <sub>` | list, create, build, models, pull, bases, delete |
| `/eval <sub>` | run, smoke, reports |
| **Deploy** | |
| `/deploy <name> <path>` | Deploy agent to project |
| `/agents` | List deployed agents |
| `/launch <name>` | Open agent in new terminal |
| `/undeploy <name>` | Remove agent |
| `/templates` | List 8 agent presets |
| `/slots <sub>` | show, load, unload, send, broadcast, coordinate, crossref |
| **Session** | |
| `/tasks` | Task list |
| `/buddy` | Companion status |
| `/memory` | Memory stats |
| `/dream` | Force memory consolidation |
| `/compact` | Compress conversation context |
| `/status` | Runtime info |
| `/save` | Save session |
| `/clear` | Clear history |
| `/exit` | Quit |

## Architecture

```
forgeagent/
├── __main__.py              Entry point
├── config.py                .env configuration
├── core/
│   ├── interfaces.py        Tool, Command, Message types
│   └── query_engine.py      Multi-round orchestration + streaming
├── providers/ollama/
│   ├── client.py            Async HTTP client (httpx)
│   └── tool_protocol.py     Tool call parsing
├── tools/
│   └── registry.py          12 tool implementations
├── commands/
│   └── registry.py          29 slash commands
├── training/
│   ├── dataset_manager.py   Dataset CRUD + harvesting
│   ├── model_builder.py     Modelfile generation + Ollama build
│   ├── evaluator.py         Model benchmarking (12 cases)
│   └── web_scraper.py       Scrape docs/GitHub for training data
├── deploy/
│   ├── agent_deployer.py    Deploy to project folders
│   ├── instance_manager.py  6-slot multi-model manager
│   └── templates.py         8 agent presets
├── memory/
│   └── session_store.py     Sessions + dreams + MEMORY.md
├── buddy/
│   └── buddy.py             Companion (XP, levels, mood)
├── ui/
│   ├── tui.py               Interactive TUI (textual)
│   └── cli.py               Plain REPL (rich)
└── utils/
    └── helpers.py            ID gen, file I/O
```

## Requirements

- Python 3.10+
- Ollama (https://ollama.com)

## License

MIT
