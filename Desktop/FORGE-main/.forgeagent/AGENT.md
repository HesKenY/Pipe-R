# Agent Instructions — FORGE-main

Generated: 2026-04-05 14:02
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
- Total files: 125
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

- [ ] Create forgeagent/core/coordinator.py — a Coordinator class that manages multiple agents working on the same project. It should: assign tasks from AGENT.md to different models based on their strengths, track which agent is working on what, prevent file conflicts by locking files being edited, merge results when agents finish. Use the existing InstanceManager 6-slot system.
- [ ] Add a SWARM MODE button to the TUI sidebar Launch section — when clicked, it reads AGENT.md tasks, splits them across all installed models (up to 6), launches each in a terminal with its assigned subset of tasks. Each agent only sees its tasks in a filtered AGENT.md.
- [ ] Update forgeagent/deploy/agent_instructions.py — add split_tasks(tasks, n_agents) that divides tasks intelligently: group related tasks (same file mentions stay together), balance workload evenly, return list of task lists.
- [ ] Add conflict detection to the Coordinator — after all agents finish, scan their file changes for overlapping edits. Show conflicts in the TUI chat with file paths and line ranges. Offer a Merge button.
- [ ] Wire the Coordinator into the remote dashboard — show each agent slot with its assigned tasks, current progress, and status. Mobile can see all 6 agents working in parallel.
- [ ] Create forgeagent/core/pipeline.py — an AutoPipeline class that chains: train model -> run tasks -> evaluate -> retrain on failures -> repeat. Config: max_iterations, target_score, auto_improve=True. It reads AGENT.md, runs COMPLETE TODO, evaluates results, harvests failures as training data, rebuilds the model, and loops.
- [ ] Add a PIPELINE button to the TUI sidebar Build section (hero-alt style) — opens a PipelineWizard where user picks: model, max iterations (1-10), target eval score (0-100), auto-improve toggle. Returns config dict.
- [ ] Build PipelineWizard in forgeagent/ui/wizards.py — fields: model select, iteration count (Select 1-10), target score (Select 50-100 in steps of 10), auto-improve toggle (Switch). Styled with sci-fi theme colors.
- [ ] Add iteration tracking to the remote dashboard — show current iteration number, eval score trend (list of scores per iteration), estimated time remaining. Push updates from pipeline to remote state.
- [ ] Add failure harvesting to the pipeline — when a task fails or eval score drops, capture the prompt+error as a training example tagged "failure-recovery". Feed these back into the dataset before next retrain.
- [ ] Create forgeagent/tools/code_gen.py — a CodeGenTool that generates entire project scaffolds. Input: project_type (flask-api, react-app, cli-tool, python-package, fastapi-service), name, description. Outputs: full directory structure with boilerplate files. Register in tools/registry.py.
- [ ] Add a NEW PROJECT button to the TUI sidebar (hero-accent style) — opens a NewProjectWizard: project name input, project type select (Flask API, React App, CLI Tool, Python Package, FastAPI Service, Express API), output path with folder picker. On confirm, runs CodeGenTool then auto-deploys agents to the new project.
- [ ] Build the Flask API scaffold in code_gen.py — generates: app.py, requirements.txt, .env.example, tests/test_app.py, README.md, Dockerfile, .gitignore. All files should be production-quality with proper error handling, CORS, health endpoint.
- [ ] Build the Python Package scaffold in code_gen.py — generates: pyproject.toml, src/package_name/__init__.py, src/package_name/main.py, tests/test_main.py, README.md, .gitignore, LICENSE. Follows modern Python packaging standards.
- [ ] Add project templates to the remote dashboard — a CREATE PROJECT card with type dropdown and name input. Posts to /api/command with create_project:TYPE:NAME:PATH format. Wire into TUI command handler.
- [ ] After completing all tasks: run python -c "from forgeagent.ui.tui import ForgeAgentApp" to verify no import errors, then zip project to Outputs/build-TIMESTAMP.zip

<!-- Add new tasks above this line. Agents check this section on each prompt. -->
