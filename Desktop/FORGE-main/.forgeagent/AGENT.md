# Agent Instructions — FORGE-main

Generated: 2026-04-05 13:34
Agent: forge-dev
Model: forgeagent
Project: C:\Users\Ken\Desktop\FORGE-main

## Framework

### Python
- This is a Python project. Follow PEP 8 style.
- Use type hints. Run tests with `pytest`.
- Install dependencies: `pip install -r requirements.txt` or `pip install -e .`

### ForgeAgent (this project)
- This is ForgeAgent — a local AI coding agent hub built with Python/Textual.
- Main TUI: forgeagent/ui/tui.py. Wizards: forgeagent/ui/wizards.py.
- Training pipelines: forgeagent/ui/automation.py.
- Tools: forgeagent/tools/registry.py (12 built-in tools).
- Deploy system: forgeagent/deploy/agent_deployer.py.
- Entry point: forgeagent/__main__.py. Config: forgeagent/config.py.
- Test with: python -m forgeagent (TUI) or python -m forgeagent --agent (CLI).
- Dependencies: rich, textual, httpx, click, python-dotenv, pydantic.

## Project Structure
- Total files: 61
- Directories: datasets, forgeagent, forgeagent.egg-info, Outputs
- Config: .env.example, pyproject.toml, requirements.txt

## Rules
- Read files before modifying them.
- Run tests after making changes.
- Keep changes focused — one task at a time.
- Use existing patterns and conventions from the codebase.
- Do not delete or overwrite files without reading them first.
- Commit with clear messages describing what changed and why.

## Completion Protocol
When ALL tasks above are completed:
1. Run any tests to verify nothing is broken.
2. Create a timestamped zip of the entire project into the Outputs/ folder:
   - Command: `python -c "import shutil,datetime;shutil.make_archive('Outputs/build-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'),'zip','.')"` 
3. Report which tasks were completed and any issues found.
4. Wait for new instructions.

## Tasks

- [x] Read all files in forgeagent/ and understand the full architecture
- [ ] Add comprehensive error handling to forgeagent/providers/ollama/client.py — retry on timeout, graceful disconnect messages
- [ ] Add input validation to all tool run() methods in forgeagent/tools/registry.py — validate required params, check path safety
- [ ] Write unit tests in a new tests/ directory — test DatasetManager create/import/export, test ModelBuilder profile CRUD, test tool_protocol parse_tool_calls
- [ ] Add a /tasks command to commands/registry.py that reads and displays AGENT.md pending tasks
- [ ] Fix the edit_file tool in tools/registry.py — str.replace() does not accept encoding kwarg on line 86
- [ ] Add connection retry logic to OllamaClient — if first request fails, retry 3 times with 2s delay
- [ ] Create Outputs/ folder if missing when zip step runs
- [ ] After completing all tasks above, run pytest to verify, then zip the project to Outputs/build-TIMESTAMP.zip

- [ ] New task from hub: optimize startup time
<!-- Add new tasks above this line. Agents check this section on each prompt. -->
