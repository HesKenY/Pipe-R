# ForgeAgent — Project Instructions

## What This Is
ForgeAgent is a local AI coding agent hub. It trains Ollama models, deploys them as terminal coding agents, and manages them through a button-driven TUI. A mobile companion dashboard (Netlify) provides remote monitoring and control.

## Architecture

```
forgeagent/
  __main__.py          Entry point (--agent, --cli, --project flags)
  config.py            AppConfig from .env
  core/
    interfaces.py      Tool, Command, ChatMessage contracts
    query_engine.py    Multi-round tool orchestration + AGENT.md injection
  providers/ollama/
    client.py          OllamaClient (chat, stream, ping)
    tool_protocol.py   Tool call parsing (```tool JSON blocks)
  tools/
    registry.py        12 built-in tools (bash, read/write/edit file, search, glob, etc.)
  commands/
    registry.py        22 slash commands (/help, /train, /deploy, /eval, etc.)
  training/
    dataset_manager.py Datasets: create, harvest, import, export (JSONL/JSON/Alpaca)
    model_builder.py   Modelfile generation + ollama create
    evaluator.py       12 eval cases, smoke tests
    web_scraper.py     Scrape docs for training data
  deploy/
    agent_deployer.py  Deploy 1-6 models, launch terminals, generate scripts
    agent_instructions.py  AGENT.md generation, task management, framework detection
    instance_manager.py    6-slot multi-model coordination
    project_profile.py     Project config + git ops
    templates.py           8 agent presets
  ui/
    tui.py             Main Textual TUI (~2000 lines) — sci-fi theme, all button handlers
    cli.py             Agent CLI mode — rich terminal coding agent
    wizards.py         Modal dialogs (AutoTrain, Improve, LaunchAgents, etc.)
    automation.py      Training/testing pipelines (auto_train, improve, competition, etc.)
  remote/
    server.py          HTTP server on :7777, mobile dashboard, command queue
  memory/
    session_store.py   Session persistence + memory/dreams
  buddy/
    buddy.py           Tamagotchi companion (XP, levels, moods)
  utils/
    helpers.py         make_id, write_json, base36
public/
  index.html           Netlify-deployed mobile companion (connects to local :7777)
datasets/
  import/              Drop .jsonl files here for auto-import
```

## Key Flows

### COMPLETE TODO
1. Reads `.forgeagent/AGENT.md` pending tasks
2. Sends each to the active model with tool-use instructions
3. Shows percentage progress in chat
4. Marks tasks done in AGENT.md
5. Zips project to `Outputs/build-TIMESTAMP.zip`
6. Git commit + push (triggers Netlify deploy)
7. Auto-restarts to apply changes

### Deploy / Launch Agents
1. LaunchAgentsWizard: pick 1-6 models + project folder
2. `deploy_multi()` creates `.forgeagent/` with per-model configs
3. `launch_multi()` opens terminal windows with `--agent` mode
4. Each terminal runs the agent CLI against the project

### Remote Control (Mobile)
- Server on `0.0.0.0:7777` serves API + dashboard
- `public/index.html` on Netlify connects to local server
- Commands: pause, resume, stop, restart, add_task, set_tasks, chat, complete_todo
- State polled every 2s: progress, agents, tasks, log

## Rules for Agents Working on This Project
- Test imports after changes: `python -c "from forgeagent.ui.tui import ForgeAgentApp"`
- Never break the TUI — it must always launch with `python -m forgeagent`
- The user is a non-coder — everything must work through buttons, no typing required in the hub
- Agent terminal CLI is where users type tasks — keep it polished
- Use Rich markup colors from the sci-fi palette: #00e5ff (cyan), #7c4dff (purple), #00e676 (green), #ff1744 (red), #ffd740 (amber), #5c6b7a (dim)
- All new features need a button in the TUI sidebar
- Remote dashboard must stay lightweight (single HTML, no dependencies)
