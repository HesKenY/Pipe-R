# ForgeAgent

Local AI coding agent hub. Train models, deploy as coding agents, control from phone.

## Quick Start

```
SETUP.bat     # First time (installs deps, pulls model)
START.bat     # Launch
```

## What It Does

- **Train** Ollama models on coding tasks (Auto Train, Improve, Shadow Learn)
- **Deploy** 1-6 models as coding agents on any project folder
- **COMPLETE TODO** — agents read .forgeagent/AGENT.md and build automatically
- **Remote control** from phone at http://YOUR_IP:7777
- **Learn** — agents harvest completed work as training data, get smarter each iteration

## Remote Dashboard

Auto-starts on port 7777. Open on phone. 5 tabs: Work, Train, Monitor, Chat.
Deploy to Netlify for access anywhere.

## Architecture

```
forgeagent/
  core/       QueryEngine, IterationEngine, ProjectWorker, SkillTracker
  tools/      12 tools: bash, read/write/edit file, search, glob, web fetch
  training/   DatasetManager, ModelBuilder, Evaluator, WebScraper
  deploy/     AgentDeployer, instructions, InstanceManager, templates
  ui/         TUI (Textual), AgentCLI (Rich), TeamCLI, wizards
  remote/     HTTP server + mobile dashboard
```
