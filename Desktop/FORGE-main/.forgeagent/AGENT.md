# Agent Instructions — FORGE-main

Generated: 2026-04-05 13:58
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
- Total files: 64
- Directories: -p, commands, datasets, forgeagent, Outputs, public, tools
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

- [ ] Fix edit_file tool bug in forgeagent/tools/registry.py line 86 — str.replace() does not accept encoding kwarg. Remove encoding param from replace call.
- [ ] Add connection retry logic to forgeagent/providers/ollama/client.py — wrap chat() and chat_stream() in retry loop: 3 attempts, 2s delay between, log each retry.
- [ ] Add input validation to all 12 tool run() methods in forgeagent/tools/registry.py — check required params exist, validate file paths dont escape cwd, return clear error messages.
- [ ] Fix the query_engine.py compact() method — handle edge case where messages list has fewer than 4 entries without crashing.
- [ ] Add try/except around all file I/O in memory/session_store.py — handle corrupted JSON files gracefully instead of crashing.
- [ ] Create tests/ directory with __init__.py and conftest.py. Add pytest to requirements.txt.
- [ ] Write tests/test_dataset_manager.py — test create_dataset, add_example, import_from_file with JSONL and JSON array formats, export_dataset in all 4 formats. Use tmp_path fixture.
- [ ] Write tests/test_tool_protocol.py — test parse_tool_calls with: tool block format, raw JSON format, no tools, malformed JSON, single tool shorthand. Test build_tool_instructions output.
- [ ] Write tests/test_tools.py — test BashTool (echo command), ReadFileTool (read existing file, missing file), WriteFileTool (create file), ListDirTool (list test dir), SearchFilesTool (find pattern).
- [ ] Write tests/test_agent_instructions.py — test detect_frameworks (Python project, Node project, empty dir), generate_agent_instructions, add_task, complete_task, get_pending_tasks.
- [ ] Add /tasks slash command to forgeagent/commands/registry.py — reads .forgeagent/AGENT.md and displays pending/completed tasks with checkboxes. Register it in create_commands().
- [ ] Add a History button to the TUI sidebar Session section — shows list of previous sessions from session_store with date and preview. Clicking one restores that session.
- [ ] Add auto-save to the COMPLETE TODO pipeline — after each task completes, auto-save the session so nothing is lost if the process crashes.
- [ ] Add a model download progress indicator — when AUTO TRAIN pulls a base model, show download percentage in the progress bar instead of just text updates.
- [ ] Add an Export Build button to the TUI sidebar — zips the project to Outputs/ on demand without running tasks. Useful for manual checkpoints.
- [ ] Add session history to the remote dashboard /api/state — include last 5 sessions with date and message count. Show in mobile UI.
- [ ] Add model list to remote dashboard — show installed models with size. Allow switching active model from phone via /api/command model:NAME.
- [ ] Add a notification sound/vibration trigger to the mobile dashboard when TODO completes — use navigator.vibrate() and a brief audio beep.
- [ ] Add dark/light theme toggle to the mobile dashboard with localStorage persistence.
- [ ] Update the README.md with current features: training, deploy, COMPLETE TODO, remote control, dataset import, mobile companion. Include screenshot placeholder sections and quick start steps.
- [ ] After completing all tasks: run pytest to verify tests pass, then zip project to Outputs/build-TIMESTAMP.zip

<!-- Add new tasks above this line. Agents check this section on each prompt. -->
