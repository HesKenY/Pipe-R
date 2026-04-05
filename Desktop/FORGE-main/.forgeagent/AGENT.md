# Agent Instructions — FORGE-main

Generated: 2026-04-05 14:31
Agent: forge-team
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
- Total files: 136
- Directories: -p, commands, datasets, forgeagent, forgeagent.egg-info, Outputs, public, tests, tools
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

- [x] Rewrite the WORK ON PROJECT flow in forgeagent/ui/tui.py — when user clicks the button and picks a folder, it should: 1) scan all files recursively 2) detect language/framework 3) read key files (README, config, entry points) 4) generate a full analysis report saved to .claude/analysis.md 5) auto-generate 10-15 development tasks based on what it found 6) write tasks to .forgeagent/AGENT.md 7) launch team terminal. Use read_file tool to actually read the project files.
- [x] Create forgeagent/core/project_worker.py — a ProjectWorker class that manages the full work cycle on any project folder. Methods: analyze(path) -> reads files and returns analysis dict, plan(analysis) -> generates task list, execute(tasks) -> runs COMPLETE TODO, iterate() -> harvest learning then generate next batch. This is the main engine agents use.
- [x] Add auto-iteration to ProjectWorker — after completing one batch of tasks, automatically: harvest training data, update agent memory, generate next task batch, start working again. Config: max_iterations (default 3), stop_on_error (default False). Each iteration gets smarter because agent memory carries forward.
- [x] Build the file analysis system in project_worker.py — analyze() should: count files by type (.py, .js, .ts, etc), read the first 100 lines of each entry point, extract function/class names from Python files, find TODO/FIXME/HACK comments, check for missing tests, check for missing docs. Return structured dict.
- [ ] Upgrade forgeagent/ui/team_cli.py — add automatic task distribution. When team receives a task list, the first agent (coordinator) reads the tasks and assigns each to the best-suited model. Use /assign command or auto-assign on startup. Track which agent owns which task.
- [ ] Add inter-agent communication to team_cli.py — after each agent completes a task, broadcast a summary to all other agents: "A1 completed: added error handling to client.py, modified 3 functions". Other agents incorporate this into their context automatically.
- [ ] Add a /iterate command to team_cli.py — triggers: run all remaining tasks, harvest results, generate next batch, continue working. Agents keep going through iterations until all work is done or user types /stop.
- [ ] Upgrade agent memory in forgeagent/core/iteration.py — after each task completion, save: what file was changed, what tool was used, whether it succeeded, how long it took. Build a skills profile per model: "qwen2.5-coder is good at Python refactoring, jefferyjefferferson is good at writing tests". Use this to assign tasks to the right model.
- [x] Add a learning database to forgeagent/deploy/agent_instructions.py — track every task ever completed across all projects. Store in .memory/task_history.json: task description, model used, success/fail, project path, timestamp. Use this history to generate better tasks in future iterations.
- [x] Create forgeagent/core/skills.py — a SkillTracker that builds model skill profiles from task_history.json. Methods: rate_model(model, category) -> score 0-100, best_model_for(task) -> model name, get_profile(model) -> dict of scores by category. Categories: code-gen, debugging, testing, refactoring, docs, devops.
- [ ] Upgrade the zip output in tui.py COMPLETE TODO — after zipping, also generate a CHANGELOG.md in the zip listing what changed this iteration. Read git diff or agent memory to build the changelog automatically.
- [ ] Add a BUILD & DEPLOY button to the TUI — runs COMPLETE TODO then: 1) zips to Outputs/ 2) git add + commit + push 3) logs the deployment to .claude/deploy_log.md 4) restarts the program. One click does everything.
- [ ] Create a project dashboard in the remote mobile UI (public/index.html) — show: current project being worked on, files changed this session, iteration count, model skill ratings, and a WORK ON FOLDER button with a path input field.
- [ ] Add /status command to team_cli.py that shows: each agent name+model, tasks assigned, tasks completed, tools used count, current activity. Formatted as a clean table.
- [x] Update README.md with complete documentation: what ForgeAgent is, how to install (pip install -e .), how to run (python -m forgeagent), all buttons explained, mobile remote setup, team mode, WORK ON PROJECT flow, the iteration learning loop.
- [ ] After completing all tasks: run python -c "from forgeagent.ui.tui import ForgeAgentApp" to verify, then zip to Outputs/build-TIMESTAMP.zip

<!-- Add new tasks above this line. Agents check this section on each prompt. -->
