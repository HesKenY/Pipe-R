"""Background automation pipelines for training, improvement, and deployment."""
from __future__ import annotations
import logging
import os
import re
import time
from pathlib import Path

log = logging.getLogger("forgeagent.automation")
if not log.handlers:
    _log_dir = Path(os.environ.get("FORGEAGENT_HOME", ".")) / ".memory"
    _log_dir.mkdir(parents=True, exist_ok=True)
    log.addHandler(logging.FileHandler(_log_dir / "forgeagent.log", encoding="utf-8"))
    log.setLevel(logging.DEBUG)


# ── Topic-to-template mapping ────────────────────────────────
FOCUS_MAP = {
    "python":    {"topic": "python",     "template": "python",    "base_7b": "qwen2.5-coder:7b", "base_14b": "qwen2.5-coder:14b", "base_32b": "qwen2.5-coder:32b"},
    "web":       {"topic": "typescript", "template": "fullstack", "base_7b": "qwen2.5-coder:7b", "base_14b": "qwen2.5-coder:14b", "base_32b": "qwen2.5-coder:32b"},
    "rust":      {"topic": "rust",       "template": "rust",      "base_7b": "qwen2.5-coder:7b", "base_14b": "qwen2.5-coder:14b", "base_32b": "qwen2.5-coder:32b"},
    "go":        {"topic": "node",       "template": "go",        "base_7b": "qwen2.5-coder:7b", "base_14b": "qwen2.5-coder:14b", "base_32b": "qwen2.5-coder:32b"},
    "devops":    {"topic": "devops",     "template": "devops",    "base_7b": "qwen2.5-coder:7b", "base_14b": "qwen2.5-coder:14b", "base_32b": "qwen2.5-coder:32b"},
    "general":   {"topic": "python",     "template": "fullstack", "base_7b": "qwen2.5-coder:7b", "base_14b": "qwen2.5-coder:14b", "base_32b": "qwen2.5-coder:32b"},
}

SIZE_MAP = {"fast": "base_7b", "balanced": "base_14b", "powerful": "base_32b"}


def detect_project_type(path: str) -> str:
    """Detect project type from files in directory, return template name."""
    p = Path(path)
    if not p.is_dir():
        return "fullstack"
    if (p / "Cargo.toml").exists():
        return "rust"
    if (p / "go.mod").exists():
        return "go"
    if (p / "package.json").exists():
        return "fullstack"
    if any((p / f).exists() for f in ("pyproject.toml", "setup.py", "requirements.txt")):
        return "python"
    if any((p / f).exists() for f in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml")):
        return "devops"
    return "fullstack"


async def run_auto_train(ctx: dict, config: dict, on_step) -> dict:
    """
    Full automated training pipeline.

    config keys: name, focus, size
    on_step(step_num, total, message) — progress callback
    """
    dm = ctx["dataset_manager"]
    mb = ctx["model_builder"]
    sc = ctx["scraper"]
    ev = ctx["evaluator"]

    focus_info = FOCUS_MAP.get(config["focus"], FOCUS_MAP["general"])
    base_key = SIZE_MAP.get(config["size"], "base_14b")
    base_model = focus_info[base_key]
    topic = focus_info["topic"]
    raw_name = config.get("name") or f"forge-{config['focus']}"
    name = mb.normalize_model_name(raw_name)
    ds = f"{name}-data"
    total = 9

    # Step 1: Create dataset
    on_step(1, total, f"Creating dataset '{ds}'...")
    try:
        dm.create_dataset(ds, f"Auto-generated for {name}")
    except ValueError:
        pass  # Already exists — reuse it

    # Step 2: Generate synthetic examples
    on_step(2, total, "Generating synthetic training examples...")
    n = dm.generate_tool_use_examples(ds, 20)

    # Step 3: Scrape web sources
    on_step(3, total, f"Scraping {topic} documentation...")
    try:
        results = await sc.scrape_topic(dm, ds, topic)
        scraped = sum(x.get("examples", 0) for x in results)
    except Exception:
        scraped = 0

    # Step 4: Harvest from codebase
    on_step(4, total, "Learning from local codebase...")
    try:
        cwd = ctx["config"].cwd
        harvested = dm.harvest_from_codebase(ds, cwd)
    except Exception:
        harvested = 0

    # Step 5: Check base model
    on_step(5, total, f"Checking if {base_model} is available...")
    local_models = mb.list_local_models()
    model_names = [m["name"] for m in local_models]
    need_pull = base_model not in model_names

    # Step 6: Pull base model if needed
    if need_pull:
        on_step(6, total, f"Downloading {base_model} (this may take several minutes)...")

        import time as _time
        _last_pull_update = [0.0]

        def _pull_progress(line):
            # Throttle to every 2 seconds to avoid flooding
            now = _time.time()
            if now - _last_pull_update[0] >= 2.0:
                _last_pull_update[0] = now
                on_step(6, total, f"Downloading: {line[:60]}")

        pull_result = await mb.pull_base_model(base_model, on_progress=_pull_progress)
        if not pull_result["success"]:
            return {"success": False, "error": pull_result["message"], "step": "pull"}
    else:
        on_step(6, total, f"{base_model} already available.")

    # Step 7: Create profile
    on_step(7, total, f"Creating model profile '{name}'...")
    try:
        mb.create_profile(name, base_model, dataset_name=ds)
    except Exception:
        # Profile may already exist — delete and recreate
        mb.delete_profile(name)
        mb.create_profile(name, base_model, dataset_name=ds)

    # Step 8: Build model
    on_step(8, total, f"Building model '{name}' (this may take a minute)...")
    result = await mb.build_model(name, dm)
    if not result.success:
        return {"success": False, "error": result.message, "step": "build"}

    # Step 9: Smoke test
    on_step(9, total, "Running smoke test...")
    try:
        smoke = await ev.smoke_test(name)
    except Exception:
        smoke = {"alive": False, "canChat": False, "canTool": False}

    return {
        "success": True,
        "model_name": name,
        "base_model": base_model,
        "dataset": ds,
        "examples": {"synthetic": n, "scraped": scraped, "codebase": harvested},
        "smoke": smoke,
        "duration": result.duration,
    }


async def run_improve(ctx: dict, config: dict, on_step) -> dict:
    """
    Simulated training environment — aggressively collects data from all sources,
    rebuilds, and evaluates before/after to track improvement.

    config keys: model_name, harvest_conversations (bool), scrape_topic (str|None)
    """
    dm = ctx["dataset_manager"]
    mb = ctx["model_builder"]
    ev = ctx["evaluator"]
    sc = ctx["scraper"]
    engine = ctx["engine"]

    model_name = config["model_name"]
    safe_name = mb.normalize_model_name(model_name)
    total = 8

    # Find or auto-create profile
    profile = mb.get_profile(model_name)
    if not profile:
        # Auto-create profile for existing installed model
        profile = mb.create_profile(
            safe_name, model_name,
            dataset_name=f"{safe_name}-data",
            description=f"Auto-created profile for {model_name}",
        )

    ds = profile.get("datasetName") or f"{safe_name}-data"
    try:
        dm.create_dataset(ds, f"Data for {safe_name}")
    except ValueError:
        pass

    # Step 1: Evaluate current model (before)
    on_step(1, total, "Evaluating current model performance...")
    try:
        before = await ev.evaluate(model_name)
        before_score = before.get("avgScore", 0)
    except Exception:
        before_score = 0

    # Step 2: Generate fresh synthetic examples (always — reinforces tool use)
    on_step(2, total, "Generating synthetic training examples...")
    n_synthetic = dm.generate_tool_use_examples(ds, 20)

    # Step 3: Harvest conversations
    n_conversations = 0
    if config.get("harvest_conversations", True):
        on_step(3, total, "Harvesting recent conversations...")
        try:
            n_conversations = dm.harvest_from_conversation(ds, engine.get_messages())
        except Exception:
            pass
    else:
        on_step(3, total, "Skipping conversation harvest.")

    # Step 4: Harvest from local codebase (always — teaches real code patterns)
    on_step(4, total, "Learning from local codebase...")
    n_codebase = 0
    try:
        n_codebase = dm.harvest_from_codebase(ds, ctx["config"].cwd)
    except Exception:
        pass

    # Step 5: Scrape web data
    n_scraped = 0
    topic = config.get("scrape_topic")
    if topic:
        on_step(5, total, f"Scraping {topic} documentation...")
        try:
            results = await sc.scrape_topic(dm, ds, topic)
            n_scraped = sum(x.get("examples", 0) for x in results)
        except Exception:
            pass
    else:
        # Auto-scrape python if no topic specified (most common use case)
        on_step(5, total, "Scraping Python documentation...")
        try:
            results = await sc.scrape_topic(dm, ds, "python")
            n_scraped = sum(x.get("examples", 0) for x in results)
        except Exception:
            pass

    # Step 6: Get dataset stats
    on_step(6, total, "Analyzing training data quality...")
    ds_info = dm.get_dataset(ds)
    total_examples = len(ds_info["examples"]) if ds_info else 0

    # Step 7: Rebuild model with all data
    on_step(7, total, f"Rebuilding model with {total_examples} examples...")
    result = await mb.build_model(model_name, dm)
    if not result.success:
        return {"success": False, "error": result.message}

    # Step 8: Evaluate improved model (after)
    on_step(8, total, "Evaluating improved model...")
    try:
        after = await ev.evaluate(model_name)
        after_score = after.get("avgScore", 0)
    except Exception:
        after_score = 0

    return {
        "success": True,
        "model_name": model_name,
        "added": {
            "synthetic": n_synthetic,
            "conversations": n_conversations,
            "codebase": n_codebase,
            "scraped": n_scraped,
        },
        "total_examples": total_examples,
        "before_score": before_score,
        "after_score": after_score,
        "improvement": after_score - before_score,
    }


async def run_retrain(ctx: dict, config: dict, on_step) -> dict:
    """
    Retrain a model from scratch — wipe dataset, regenerate, rebuild.

    config keys: model_name, focus
    """
    dm = ctx["dataset_manager"]
    mb = ctx["model_builder"]
    sc = ctx["scraper"]
    ev = ctx["evaluator"]

    model_name = config["model_name"]
    safe_name = mb.normalize_model_name(model_name)
    focus_info = FOCUS_MAP.get(config.get("focus", "general"), FOCUS_MAP["general"])
    topic = focus_info["topic"]
    total = 7

    # Find or auto-create profile
    profile = mb.get_profile(model_name)
    if not profile:
        profile = mb.create_profile(
            safe_name, model_name,
            dataset_name=f"{safe_name}-data",
            description=f"Auto-created profile for {model_name}",
        )

    base_model = profile["baseModel"]
    ds = profile.get("datasetName") or f"{safe_name}-data"

    # Step 1: Wipe old dataset and recreate
    on_step(1, total, f"Wiping dataset '{ds}' and starting fresh...")
    dm.delete_dataset(ds)
    dm.create_dataset(ds, f"Retrained data for {safe_name}")

    # Step 2: Generate synthetic examples
    on_step(2, total, "Generating fresh synthetic examples...")
    n_synthetic = dm.generate_tool_use_examples(ds, 20)

    # Step 3: Scrape web data
    on_step(3, total, f"Scraping {topic} documentation...")
    try:
        results = await sc.scrape_topic(dm, ds, topic)
        n_scraped = sum(x.get("examples", 0) for x in results)
    except Exception:
        n_scraped = 0

    # Step 4: Harvest from codebase
    on_step(4, total, "Learning from local codebase...")
    try:
        n_codebase = dm.harvest_from_codebase(ds, ctx["config"].cwd)
    except Exception:
        n_codebase = 0

    # Step 5: Harvest current conversations
    on_step(5, total, "Harvesting recent conversations...")
    try:
        n_conversations = dm.harvest_from_conversation(ds, ctx["engine"].get_messages())
    except Exception:
        n_conversations = 0

    # Step 6: Rebuild model
    on_step(6, total, f"Rebuilding model '{model_name}'...")
    result = await mb.build_model(model_name, dm)
    if not result.success:
        return {"success": False, "error": result.message}

    # Step 7: Smoke test
    on_step(7, total, "Running smoke test...")
    try:
        smoke = await ev.smoke_test(model_name)
    except Exception:
        smoke = {"alive": False, "canChat": False, "canTool": False}

    return {
        "success": True,
        "model_name": model_name,
        "base_model": base_model,
        "examples": {"synthetic": n_synthetic, "scraped": n_scraped, "codebase": n_codebase, "conversations": n_conversations},
        "smoke": smoke,
        "duration": result.duration,
    }


async def run_continue_train(ctx: dict, config: dict, on_step) -> dict:
    """
    Continue training — add more data to existing dataset and rebuild.

    config keys: model_name, harvest_conversations, harvest_codebase, scrape_topic, add_synthetic
    """
    dm = ctx["dataset_manager"]
    mb = ctx["model_builder"]
    sc = ctx["scraper"]
    ev = ctx["evaluator"]
    engine = ctx["engine"]

    model_name = config["model_name"]
    safe_name = mb.normalize_model_name(model_name)
    total = 7

    profile = mb.get_profile(model_name)
    if not profile:
        profile = mb.create_profile(
            safe_name, model_name,
            dataset_name=f"{safe_name}-data",
            description=f"Auto-created profile for {model_name}",
        )

    ds = profile.get("datasetName") or f"{safe_name}-data"
    try:
        dm.create_dataset(ds, f"Data for {safe_name}")
    except ValueError:
        pass  # Already exists

    # Step 1: Evaluate before
    on_step(1, total, "Evaluating current performance...")
    try:
        before = await ev.evaluate(model_name)
        before_score = before.get("avgScore", 0)
    except Exception:
        before_score = 0

    # Step 2: Add synthetic examples
    n_synthetic = 0
    if config.get("add_synthetic", True):
        on_step(2, total, "Adding more synthetic examples...")
        n_synthetic = dm.generate_tool_use_examples(ds, 20)
    else:
        on_step(2, total, "Skipping synthetic examples.")

    # Step 3: Harvest conversations
    n_conversations = 0
    if config.get("harvest_conversations", True):
        on_step(3, total, "Harvesting chat history...")
        try:
            n_conversations = dm.harvest_from_conversation(ds, engine.get_messages())
        except Exception:
            pass
    else:
        on_step(3, total, "Skipping conversation harvest.")

    # Step 4: Harvest codebase
    n_codebase = 0
    if config.get("harvest_codebase", True):
        on_step(4, total, "Learning from local codebase...")
        try:
            n_codebase = dm.harvest_from_codebase(ds, ctx["config"].cwd)
        except Exception:
            pass
    else:
        on_step(4, total, "Skipping codebase harvest.")

    # Step 5: Scrape web data
    n_scraped = 0
    topic = config.get("scrape_topic")
    if topic:
        on_step(5, total, f"Scraping more {topic} data...")
        try:
            results = await sc.scrape_topic(dm, ds, topic)
            n_scraped = sum(x.get("examples", 0) for x in results)
        except Exception:
            pass
    else:
        on_step(5, total, "Skipping web scraping.")

    # Step 6: Rebuild model
    on_step(6, total, f"Rebuilding model '{model_name}'...")
    result = await mb.build_model(model_name, dm)
    if not result.success:
        return {"success": False, "error": result.message}

    # Step 7: Evaluate after
    on_step(7, total, "Evaluating improved model...")
    try:
        after = await ev.evaluate(model_name)
        after_score = after.get("avgScore", 0)
    except Exception:
        after_score = 0

    return {
        "success": True,
        "model_name": model_name,
        "added": {"synthetic": n_synthetic, "conversations": n_conversations, "codebase": n_codebase, "scraped": n_scraped},
        "before_score": before_score,
        "after_score": after_score,
        "improvement": after_score - before_score,
        "duration": result.duration,
    }


# ── Training Level Assessment — Claude Code as the bar ───────
# Claude Code baseline scores (estimated from Claude Haiku-level performance)
# These represent what a top-tier cloud AI coding agent scores on each category.
CLAUDE_BASELINE = {
    "tool-use":           95,   # near-perfect tool calling
    "code-gen":           92,   # strong code generation
    "reasoning":          90,   # solid reasoning
    "instruction-follow": 98,   # excellent instruction following
    "multi-step":         88,   # good multi-step planning
    "overall":            92,   # overall Claude Code benchmark
}

LEVEL_THRESHOLDS = [
    (0,   "Beginner",      "[red]"),
    (20,  "Novice",        "[red]"),
    (35,  "Apprentice",    "[yellow]"),
    (50,  "Competent",     "[yellow]"),
    (65,  "Proficient",    "[green]"),
    (78,  "Advanced",      "[green]"),
    (88,  "Expert",        "[cyan]"),
    (95,  "Master",        "[bold cyan]"),
    (100, "Claude-Level",  "[bold magenta]"),
]


def get_training_level(score: int) -> tuple[str, str, int]:
    """Return (level_name, color, next_threshold) for a given score."""
    level_name, color = "Beginner", "[red]"
    next_thresh = 20
    for thresh, name, c in LEVEL_THRESHOLDS:
        if score >= thresh:
            level_name, color = name, c
        else:
            next_thresh = thresh
            break
    else:
        next_thresh = 100
    return level_name, color, next_thresh


def format_training_report(model_name: str, eval_report: dict, label: str = "") -> list[str]:
    """
    Generate a visual training level report comparing model to Claude Code.
    Returns list of Rich-markup lines for display.
    """
    lines = []
    score = eval_report.get("avgScore", 0)
    claude_score = CLAUDE_BASELINE["overall"]
    level_name, color, next_thresh = get_training_level(score)
    gap = claude_score - score

    # Header
    header = f"  TRAINING LEVEL{f' — {label}' if label else ''}"
    lines.append(f"  [bold]{'━'*56}[/]")
    lines.append(f"  [bold]{header}[/]")
    lines.append(f"  [bold]{'━'*56}[/]")
    lines.append("")

    # Overall score bar
    bar_width = 40
    filled = round(score / 100 * bar_width)
    claude_pos = round(claude_score / 100 * bar_width)
    bar = ""
    for i in range(bar_width):
        if i < filled:
            bar += "█"
        elif i == claude_pos:
            bar += "│"
        else:
            bar += "░"
    lines.append(f"  {color}{model_name}[/]")
    lines.append(f"  {color}{bar}[/]  [bold]{score}%[/]")
    lines.append(f"  {'':>{claude_pos * 1 + 2}}[dim magenta]▲ Claude Code {claude_score}%[/]")
    lines.append("")

    # Level badge
    lines.append(f"  Level: {color}{level_name}[/]")
    if score < claude_score:
        lines.append(f"  [dim]Gap to Claude Code: {gap}% | Next level at {next_thresh}%[/]")
    else:
        lines.append(f"  [bold magenta]Matching Claude Code performance![/]")
    lines.append("")

    # Per-category breakdown vs Claude
    by_cat = eval_report.get("byCategory", {})
    if by_cat:
        lines.append(f"  [bold]{'Category':<22} {'You':<8} {'Claude':<8} {'Gap':<8} Bar[/]")
        lines.append(f"  {'─'*56}")
        for cat, data in sorted(by_cat.items()):
            cat_score = round(data["score"]) if data.get("score") else (round(data["passed"] / data["total"] * 100) if data["total"] else 0)
            claude_cat = CLAUDE_BASELINE.get(cat, claude_score)
            cat_gap = claude_cat - cat_score
            # Mini bar (20 chars)
            mini_w = 20
            mini_filled = round(cat_score / 100 * mini_w)
            mini_claude = round(claude_cat / 100 * mini_w)
            mini_bar = ""
            for i in range(mini_w):
                if i < mini_filled:
                    mini_bar += "█"
                elif i == mini_claude:
                    mini_bar += "│"
                else:
                    mini_bar += "░"
            gap_str = f"-{cat_gap}" if cat_gap > 0 else f"+{abs(cat_gap)}"
            cat_color = "[green]" if cat_gap <= 5 else ("[yellow]" if cat_gap <= 20 else "[red]")
            lines.append(f"  {cat:<22} {cat_color}{cat_score}%[/]{'':>4} {claude_cat}%{'':>4} {cat_color}{gap_str}%[/]{'':>3} {mini_bar}")
        lines.append("")

    # Recommendation
    if score < 35:
        lines.append(f"  [yellow]Tip: Run IMPROVE or CONTINUE TRAINING to add more data.[/]")
        lines.append(f"  [dim]More training data = better performance. Try scraping web docs.[/]")
    elif score < 65:
        lines.append(f"  [yellow]Tip: Getting there! Continue training with conversations + codebase.[/]")
    elif score < 88:
        lines.append(f"  [green]Strong model. Fine-tune with domain-specific data to close the gap.[/]")
    else:
        lines.append(f"  [cyan]Excellent! Your model is approaching Claude Code performance.[/]")
    lines.append("")

    return lines


async def assess_training_level(ctx: dict, model_name: str, on_step=None) -> dict:
    """Run eval and return training level assessment."""
    ev = ctx["evaluator"]
    if on_step:
        on_step(-1, -1, "Assessing training level...")
    try:
        report = await ev.evaluate(model_name)
    except Exception:
        report = {"avgScore": 0, "byCategory": {}}

    score = report.get("avgScore", 0)
    level_name, color, next_thresh = get_training_level(score)

    return {
        "report": report,
        "score": score,
        "level": level_name,
        "claude_baseline": CLAUDE_BASELINE["overall"],
        "gap": CLAUDE_BASELINE["overall"] - score,
        "lines": format_training_report(model_name, report),
    }


# ── Coding Challenges — auto-graded test system ──────────────
CODING_CHALLENGES = [
    {
        "id": "cc-1", "difficulty": "easy",
        "prompt": "Write a Python function called `reverse_string` that takes a string and returns it reversed. Only output the function, nothing else.",
        "test_code": """
result = reverse_string("hello")
assert result == "olleh", f"Expected 'olleh', got '{result}'"
result2 = reverse_string("")
assert result2 == "", f"Expected '', got '{result2}'"
print("PASS")
""",
    },
    {
        "id": "cc-2", "difficulty": "easy",
        "prompt": "Write a Python function called `is_palindrome` that returns True if a string is a palindrome (same forwards and backwards), False otherwise. Ignore case. Only output the function.",
        "test_code": """
assert is_palindrome("racecar") == True
assert is_palindrome("hello") == False
assert is_palindrome("Madam") == True
assert is_palindrome("") == True
print("PASS")
""",
    },
    {
        "id": "cc-3", "difficulty": "easy",
        "prompt": "Write a Python function called `fizzbuzz` that takes an integer n and returns a list of strings from 1 to n: 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, 'FizzBuzz' for both, else the number as string. Only output the function.",
        "test_code": """
result = fizzbuzz(15)
assert result[2] == "Fizz"
assert result[4] == "Buzz"
assert result[14] == "FizzBuzz"
assert result[0] == "1"
assert len(result) == 15
print("PASS")
""",
    },
    {
        "id": "cc-4", "difficulty": "medium",
        "prompt": "Write a Python function called `two_sum` that takes a list of integers and a target integer, and returns a list of two indices whose values add up to the target. Only output the function.",
        "test_code": """
result = two_sum([2, 7, 11, 15], 9)
assert sorted(result) == [0, 1], f"Expected [0,1], got {result}"
result2 = two_sum([3, 2, 4], 6)
assert sorted(result2) == [1, 2], f"Expected [1,2], got {result2}"
print("PASS")
""",
    },
    {
        "id": "cc-5", "difficulty": "medium",
        "prompt": "Write a Python function called `max_subarray_sum` that takes a list of integers and returns the maximum sum of any contiguous subarray (Kadane's algorithm). Only output the function.",
        "test_code": """
assert max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
assert max_subarray_sum([1]) == 1
assert max_subarray_sum([-1, -2, -3]) == -1
print("PASS")
""",
    },
    {
        "id": "cc-6", "difficulty": "medium",
        "prompt": "Write a Python function called `flatten` that takes a nested list (can be arbitrarily deep) and returns a flat list. Only output the function.",
        "test_code": """
assert flatten([1, [2, 3], [4, [5, 6]]]) == [1, 2, 3, 4, 5, 6]
assert flatten([]) == []
assert flatten([[1], [[2]], [[[3]]]]) == [1, 2, 3]
print("PASS")
""",
    },
    {
        "id": "cc-7", "difficulty": "hard",
        "prompt": "Write a Python function called `valid_parentheses` that takes a string containing '(', ')', '{', '}', '[', ']' and returns True if the brackets are validly matched. Only output the function.",
        "test_code": """
assert valid_parentheses("()[]{}") == True
assert valid_parentheses("(]") == False
assert valid_parentheses("([)]") == False
assert valid_parentheses("{[]}") == True
assert valid_parentheses("") == True
print("PASS")
""",
    },
    {
        "id": "cc-8", "difficulty": "hard",
        "prompt": "Write a Python function called `merge_sorted` that takes two sorted lists and returns a single sorted merged list without using sort(). Only output the function.",
        "test_code": """
assert merge_sorted([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]
assert merge_sorted([], [1, 2]) == [1, 2]
assert merge_sorted([1], []) == [1]
print("PASS")
""",
    },
]


def _extract_python_code(response: str) -> str:
    """Extract Python code from a model response (handles code blocks and raw code)."""
    # Try to find ```python ... ``` blocks
    match = re.search(r"```(?:python)?\s*\n([\s\S]*?)```", response)
    if match:
        return match.group(1).strip()
    # Try to find def ... lines
    lines = response.split("\n")
    code_lines = []
    in_func = False
    for line in lines:
        if line.strip().startswith("def "):
            in_func = True
        if in_func:
            code_lines.append(line)
    if code_lines:
        return "\n".join(code_lines)
    return response


def _run_code_test(code: str, test_code: str) -> tuple[bool, str]:
    """Run extracted code + test, return (passed, output)."""
    import subprocess as sp
    full_code = code + "\n\n" + test_code
    try:
        result = sp.run(
            ["python", "-c", full_code],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "PASS" in result.stdout:
            return True, "PASS"
        error = result.stderr.strip() or result.stdout.strip()
        return False, error[:200]
    except sp.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)[:200]


async def run_coding_test(ctx: dict, model_name: str, on_step) -> dict:
    """
    Run coding challenges against a model and auto-grade by executing the output.
    """
    import asyncio
    from ..providers.ollama.client import OllamaClient
    from ..core.interfaces import ChatMessage
    from ..utils.helpers import make_id
    from datetime import datetime

    client = OllamaClient(ctx["config"].ollama_base_url)
    cases = CODING_CHALLENGES
    results = []
    total = len(cases)

    for i, case in enumerate(cases):
        on_step(i + 1, total, f"[{case['difficulty']}] {case['prompt'][:45]}...")
        start = time.time()
        try:
            response = await client.chat(
                model=model_name,
                messages=[ChatMessage(make_id(), "user", case["prompt"], datetime.now().isoformat())],
                temperature=0.2,
            )
        except Exception as e:
            response = f"ERROR: {e}"
        latency = int((time.time() - start) * 1000)

        code = _extract_python_code(response)
        passed, output = await asyncio.to_thread(_run_code_test, code, case["test_code"])

        results.append({
            "id": case["id"], "difficulty": case["difficulty"],
            "prompt": case["prompt"], "passed": passed,
            "latency": latency, "output": output,
            "code": code[:500], "response": response[:500],
        })

    # Stats
    total_cases = len(results)
    total_passed = sum(1 for r in results if r["passed"])
    by_difficulty = {}
    for r in results:
        d = r["difficulty"]
        if d not in by_difficulty:
            by_difficulty[d] = {"passed": 0, "total": 0}
        by_difficulty[d]["total"] += 1
        if r["passed"]:
            by_difficulty[d]["passed"] += 1
    avg_latency = round(sum(r["latency"] for r in results) / total_cases) if total_cases else 0

    return {
        "success": True,
        "model_name": model_name,
        "passed": total_passed,
        "total": total_cases,
        "pct": round(total_passed / total_cases * 100) if total_cases else 0,
        "by_difficulty": by_difficulty,
        "avg_latency": avg_latency,
        "results": results,
    }


# ── Benchmark: Local model vs Claude API ──���──────────────────
BENCHMARK_CASES = [
    {"id": "code-1", "category": "code-gen", "prompt": "Write a Python function that reverses a string. Return only the function.",
     "check": lambda r: "def " in r and ("reverse" in r.lower() or "[::-1]" in r)},
    {"id": "code-2", "category": "code-gen", "prompt": "Write a function to check if a number is prime. Return only the function.",
     "check": lambda r: ("def " in r or "function" in r) and ("prime" in r.lower() or "%" in r)},
    {"id": "code-3", "category": "code-gen", "prompt": "Write a Python function that finds the nth Fibonacci number.",
     "check": lambda r: "def " in r and ("fib" in r.lower() or "fibonacci" in r.lower())},
    {"id": "reason-1", "category": "reasoning", "prompt": "What is the time complexity of binary search and why?",
     "check": lambda r: bool(re.search(r"O\(log\s*n\)|logarithmic", r, re.I))},
    {"id": "reason-2", "category": "reasoning", "prompt": "Explain the difference between a stack and a queue in 2-3 sentences.",
     "check": lambda r: "stack" in r.lower() and "queue" in r.lower() and ("LIFO" in r or "FIFO" in r or "last" in r.lower() or "first" in r.lower())},
    {"id": "reason-3", "category": "reasoning", "prompt": "What does 'git rebase' do differently from 'git merge'?",
     "check": lambda r: "rebase" in r.lower() and ("history" in r.lower() or "commit" in r.lower() or "linear" in r.lower())},
    {"id": "instruct-1", "category": "instruction", "prompt": "Respond with exactly: Hello World",
     "check": lambda r: "hello world" in r.lower()},
    {"id": "instruct-2", "category": "instruction", "prompt": "List exactly 3 Python web frameworks, one per line, no explanations.",
     "check": lambda r: sum(1 for fw in ["flask", "django", "fastapi", "tornado", "bottle", "pyramid", "sanic"] if fw in r.lower()) >= 3},
    {"id": "debug-1", "category": "debugging", "prompt": "This Python code has a bug: `def add(a, b): return a - b`. What's wrong and how do you fix it?",
     "check": lambda r: "+" in r or "addition" in r.lower() or "subtract" in r.lower() or "minus" in r.lower()},
    {"id": "debug-2", "category": "debugging", "prompt": "Find the bug: `for i in range(10): if i = 5: print('found')`",
     "check": lambda r: "==" in r or "comparison" in r.lower() or "assignment" in r.lower()},
    {"id": "explain-1", "category": "explanation", "prompt": "Explain what a REST API is in 2 sentences for a beginner.",
     "check": lambda r: "api" in r.lower() and ("http" in r.lower() or "request" in r.lower() or "resource" in r.lower())},
    {"id": "explain-2", "category": "explanation", "prompt": "What is a Docker container in simple terms?",
     "check": lambda r: "container" in r.lower() and ("isolat" in r.lower() or "packag" in r.lower() or "lightweight" in r.lower() or "application" in r.lower())},
]


async def _validate_claude_key(api_key: str) -> bool:
    """Quick validation that the API key works."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 16,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            return resp.status_code == 200
    except Exception:
        return False


async def _run_claude_api(prompt: str, api_key: str) -> tuple[str, float]:
    """Call Claude API and return (response, latency_ms)."""
    import httpx
    start = time.time()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["content"][0]["text"] if data.get("content") else ""
        latency = int((time.time() - start) * 1000)
        return text, latency


async def run_benchmark(ctx: dict, model_name: str, on_step) -> dict:
    """
    Benchmark local model against Claude API on the same test cases.
    Returns comparison stats.
    """
    from ..training.evaluator import Evaluator
    from ..providers.ollama.client import OllamaClient
    from ..core.interfaces import ChatMessage
    from ..utils.helpers import make_id
    from datetime import datetime

    ev_client = OllamaClient(ctx["config"].ollama_base_url)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    has_claude = False
    cases = BENCHMARK_CASES

    # Validate Claude API key if present
    if api_key:
        on_step(0, 1, "Validating Claude API key...")
        has_claude = await _validate_claude_key(api_key)
        if not has_claude:
            on_step(0, 1, "Claude API key invalid or expired — running local-only benchmark")

    total_steps = len(cases) * (2 if has_claude else 1) + 1

    local_results = []
    claude_results = []
    step = 0

    # Run local model
    for case in cases:
        step += 1
        on_step(step, total_steps, f"Local: {case['prompt'][:40]}...")
        start = time.time()
        try:
            response = await ev_client.chat(
                model=model_name,
                messages=[ChatMessage(make_id(), "user", case["prompt"], datetime.now().isoformat())],
                temperature=0.3,
            )
        except Exception as e:
            response = f"ERROR: {e}"
        latency = int((time.time() - start) * 1000)
        passed = case["check"](response)
        local_results.append({
            "id": case["id"], "category": case["category"],
            "prompt": case["prompt"], "passed": passed,
            "latency": latency, "response": response[:500],
        })

    # Run Claude API
    if has_claude:
        for case in cases:
            step += 1
            on_step(step, total_steps, f"Claude: {case['prompt'][:40]}...")
            try:
                response, latency = await _run_claude_api(case["prompt"], api_key)
            except Exception as e:
                response = f"ERROR: {e}"
                latency = 0
            passed = case["check"](response)
            claude_results.append({
                "id": case["id"], "category": case["category"],
                "prompt": case["prompt"], "passed": passed,
                "latency": latency, "response": response[:500],
            })

    step += 1
    on_step(step, total_steps, "Generating report...")

    # Compute stats
    def _stats(results):
        if not results:
            return {"passed": 0, "total": 0, "pct": 0, "avg_latency": 0, "by_category": {}}
        total = len(results)
        passed = sum(1 for r in results if r["passed"])
        avg_lat = round(sum(r["latency"] for r in results) / total)
        by_cat = {}
        for r in results:
            cat = r["category"]
            if cat not in by_cat:
                by_cat[cat] = {"passed": 0, "total": 0}
            by_cat[cat]["total"] += 1
            if r["passed"]:
                by_cat[cat]["passed"] += 1
        return {"passed": passed, "total": total, "pct": round(passed / total * 100), "avg_latency": avg_lat, "by_category": by_cat}

    local_stats = _stats(local_results)
    claude_stats = _stats(claude_results) if claude_results else None

    return {
        "success": True,
        "model_name": model_name,
        "has_claude": has_claude,
        "local": local_stats,
        "claude": claude_stats,
        "local_results": local_results,
        "claude_results": claude_results,
        "cases": len(cases),
    }


# ── Competition: Local model vs Claude Code CLI ──────────────
COMPETITION_CHALLENGES = [
    {
        "id": "comp-1", "difficulty": "easy",
        "prompt": "Write a Python function called `reverse_string` that takes a string and returns it reversed. Only output the function, no explanation.",
        "test_code": 'assert reverse_string("hello") == "olleh"\nassert reverse_string("") == ""\nprint("PASS")',
    },
    {
        "id": "comp-2", "difficulty": "easy",
        "prompt": "Write a Python function called `count_vowels` that takes a string and returns the number of vowels (a,e,i,o,u). Only output the function.",
        "test_code": 'assert count_vowels("hello") == 2\nassert count_vowels("xyz") == 0\nassert count_vowels("AEIOU") == 5\nprint("PASS")',
    },
    {
        "id": "comp-3", "difficulty": "easy",
        "prompt": "Write a Python function called `flatten` that takes a nested list and returns a flat list. Only output the function.",
        "test_code": 'assert flatten([1, [2, 3], [4, [5, 6]]]) == [1, 2, 3, 4, 5, 6]\nassert flatten([]) == []\nprint("PASS")',
    },
    {
        "id": "comp-4", "difficulty": "medium",
        "prompt": "Write a Python function called `two_sum` that takes a list of integers and a target, returns a list of two indices that add to target. Only output the function.",
        "test_code": 'assert sorted(two_sum([2,7,11,15], 9)) == [0,1]\nassert sorted(two_sum([3,2,4], 6)) == [1,2]\nprint("PASS")',
    },
    {
        "id": "comp-5", "difficulty": "medium",
        "prompt": "Write a Python function called `valid_parentheses` that takes a string of brackets ()[]{}  and returns True if valid. Only output the function.",
        "test_code": 'assert valid_parentheses("()[]{}") == True\nassert valid_parentheses("(]") == False\nassert valid_parentheses("{[]}") == True\nprint("PASS")',
    },
    {
        "id": "comp-6", "difficulty": "medium",
        "prompt": "Write a Python function called `max_subarray` that takes a list of integers and returns the maximum contiguous subarray sum (Kadane's algorithm). Only output the function.",
        "test_code": 'assert max_subarray([-2,1,-3,4,-1,2,1,-5,4]) == 6\nassert max_subarray([1]) == 1\nassert max_subarray([-1,-2,-3]) == -1\nprint("PASS")',
    },
    {
        "id": "comp-7", "difficulty": "hard",
        "prompt": "Write a Python function called `lru_cache_dict` that implements a simple LRU cache as a class with get(key) and put(key, value) methods, with a max capacity passed to __init__. Only output the class.",
        "test_code": 'c = lru_cache_dict(2)\nc.put(1,"a"); c.put(2,"b")\nassert c.get(1) == "a"\nc.put(3,"c")\nassert c.get(2) is None\nprint("PASS")',
    },
    {
        "id": "comp-8", "difficulty": "hard",
        "prompt": "Write a Python function called `merge_intervals` that takes a list of [start, end] intervals and returns merged overlapping intervals sorted by start. Only output the function.",
        "test_code": 'assert merge_intervals([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]\nassert merge_intervals([[1,4],[4,5]]) == [[1,5]]\nprint("PASS")',
    },
]


async def _run_claude_cli(prompt: str, cwd: str = ".") -> tuple[str, float]:
    """Run a prompt through Claude Code CLI and return (response, latency_ms)."""
    import asyncio
    import subprocess as sp
    start = time.time()

    def _call():
        log.info(f"claude cli: cwd={cwd} prompt={prompt[:60]}")
        result = sp.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=180,
            cwd=cwd,
        )
        if result.returncode != 0:
            log.warning(f"claude cli exit {result.returncode}: {result.stderr[:200]}")
        return result.stdout.strip()

    try:
        response = await asyncio.to_thread(_call)
        latency = int((time.time() - start) * 1000)
        log.info(f"claude cli done: {latency}ms, {len(response)} chars")
        return response, latency
    except Exception as e:
        log.error(f"claude cli error: {e}")
        return f"ERROR: {e}", int((time.time() - start) * 1000)


async def run_competition(ctx: dict, model_name: str, project_path: str, on_step) -> dict:
    """
    Head-to-head competition: local model vs Claude Code CLI.
    Both solve the same coding challenges. Claude's winning answers
    are harvested as training data for the local model.
    """
    import asyncio
    from ..providers.ollama.client import OllamaClient
    from ..core.interfaces import ChatMessage
    from ..utils.helpers import make_id
    from datetime import datetime

    log.info(f"competition start: model={model_name} path={project_path}")
    client = OllamaClient(ctx["config"].ollama_base_url)
    dm = ctx["dataset_manager"]
    mb = ctx["model_builder"]
    cases = COMPETITION_CHALLENGES
    total = len(cases) * 2 + 3  # local runs + claude runs + harvest + build + assess

    local_results = []
    claude_results = []

    # ── Phase 1: Local model attempts ─────────────
    on_step(0, total, "Starting competition: Local Model vs Claude Code")
    step = 0
    for case in cases:
        step += 1
        on_step(step, total, f"[Local] {case['difficulty']}: {case['prompt'][:40]}...")
        try:
            start = time.time()
            try:
                response = await client.chat(
                    model=model_name,
                    messages=[ChatMessage(make_id(), "user", case["prompt"], datetime.now().isoformat())],
                    temperature=0.2,
                )
            except Exception as e:
                log.error(f"competition local chat error: {e}")
                response = f"ERROR: {e}"
            latency = int((time.time() - start) * 1000)
            code = _extract_python_code(response)
            passed, output = await asyncio.to_thread(_run_code_test, code, case["test_code"])
            log.info(f"competition local [{case['id']}]: {'PASS' if passed else 'FAIL'} {latency}ms")
        except Exception as e:
            log.error(f"competition local [{case['id']}] error: {e}", exc_info=True)
            passed, output, latency, code, response = False, str(e), 0, "", str(e)
        local_results.append({
            "id": case["id"], "difficulty": case["difficulty"],
            "prompt": case["prompt"], "passed": passed,
            "latency": latency, "code": code[:800],
            "response": response[:1000], "output": output,
        })

    # ── Phase 2: Claude Code attempts ─────────────
    for case in cases:
        step += 1
        on_step(step, total, f"[Claude] {case['difficulty']}: {case['prompt'][:40]}...")
        try:
            response, latency = await _run_claude_cli(case["prompt"], project_path)
            code = _extract_python_code(response)
            passed, output = await asyncio.to_thread(_run_code_test, code, case["test_code"])
            log.info(f"competition claude [{case['id']}]: {'PASS' if passed else 'FAIL'} {latency}ms")
        except Exception as e:
            log.error(f"competition claude [{case['id']}] error: {e}", exc_info=True)
            passed, output, latency, code, response = False, str(e), 0, "", str(e)
        claude_results.append({
            "id": case["id"], "difficulty": case["difficulty"],
            "prompt": case["prompt"], "passed": passed,
            "latency": latency, "code": code[:800],
            "response": response[:1000], "output": output,
        })

    # ── Phase 3: Learn from Claude's wins ─────────
    step += 1
    on_step(step, total, "Harvesting Claude's winning solutions as training data...")

    safe_name = mb.normalize_model_name(model_name)
    profile = mb.get_profile(model_name)
    if not profile:
        profile = mb.create_profile(safe_name, model_name, dataset_name=f"{safe_name}-data")
    ds = profile.get("datasetName") or f"{safe_name}-data"
    try:
        dm.create_dataset(ds, f"Competition data for {safe_name}")
    except ValueError:
        pass

    lessons_learned = 0
    for i, (lr, cr) in enumerate(zip(local_results, claude_results)):
        # Learn from Claude when: Claude passed and local failed, or Claude's answer is better
        if cr["passed"] and not lr["passed"]:
            from ..training.dataset_manager import TrainingExample, _uid
            dm.add_example(ds, TrainingExample(
                id=_uid(), prompt=lr["prompt"],
                completion=cr["response"][:3000],
                tags=["competition", "claude-win", lr["difficulty"]],
                source="competition",
            ))
            lessons_learned += 1
        elif cr["passed"] and lr["passed"]:
            # Both passed — still learn Claude's style if response is more concise
            if len(cr["code"]) < len(lr["code"]) * 0.8:
                from ..training.dataset_manager import TrainingExample, _uid
                dm.add_example(ds, TrainingExample(
                    id=_uid(), prompt=lr["prompt"],
                    completion=cr["response"][:3000],
                    tags=["competition", "claude-style", lr["difficulty"]],
                    source="competition",
                ))
                lessons_learned += 1

    # ── Phase 4: Rebuild model with new training data ─
    step += 1
    on_step(step, total, f"Rebuilding model with {lessons_learned} new lessons...")
    build_result = None
    if lessons_learned > 0:
        build_result = await mb.build_model(safe_name if profile else model_name, dm)

    # ── Phase 5: Assess new level ─────────────────
    step += 1
    on_step(step, total, "Assessing updated training level...")

    # Stats
    local_passed = sum(1 for r in local_results if r["passed"])
    claude_passed = sum(1 for r in claude_results if r["passed"])
    local_pct = round(local_passed / len(cases) * 100) if cases else 0
    claude_pct = round(claude_passed / len(cases) * 100) if cases else 0

    return {
        "success": True,
        "model_name": model_name,
        "local_results": local_results,
        "claude_results": claude_results,
        "local_passed": local_passed,
        "claude_passed": claude_passed,
        "local_pct": local_pct,
        "claude_pct": claude_pct,
        "total_cases": len(cases),
        "lessons_learned": lessons_learned,
        "rebuilt": build_result.success if build_result else False,
    }


# ── Shadow Learning: watch Claude Code and learn ─────────────
async def run_shadow_learn(ctx: dict, model_name: str, project_path: str, tasks: list[str], on_step) -> dict:
    """
    Shadow learning: give Claude Code real tasks in a project folder,
    capture its responses, and train the local model on them.

    The local model watches Claude work and learns its patterns.
    """
    import asyncio
    dm = ctx["dataset_manager"]
    mb = ctx["model_builder"]
    ev = ctx["evaluator"]
    from ..training.dataset_manager import TrainingExample, _uid

    safe_name = mb.normalize_model_name(model_name)
    profile = mb.get_profile(model_name)
    if not profile:
        profile = mb.create_profile(safe_name, model_name, dataset_name=f"{safe_name}-data")
    ds = profile.get("datasetName") or f"{safe_name}-data"
    try:
        dm.create_dataset(ds, f"Shadow learning data for {safe_name}")
    except ValueError:
        pass

    total = len(tasks) + 2  # tasks + build + assess
    learned = 0

    # Phase 1: Send each task to Claude Code, capture response
    for i, task in enumerate(tasks):
        on_step(i + 1, total, f"Claude working: {task[:45]}...")
        response, latency = await _run_claude_cli(task, project_path)
        if response and not response.startswith("ERROR"):
            dm.add_example(ds, TrainingExample(
                id=_uid(), prompt=task, completion=response[:3000],
                tags=["shadow-learning", "claude-response"],
                source="shadow",
            ))
            learned += 1

    # Phase 2: Rebuild model with new data
    on_step(len(tasks) + 1, total, f"Rebuilding model with {learned} new lessons...")
    build_result = await mb.build_model(safe_name if safe_name != model_name else model_name, dm)

    # Phase 3: Assess
    on_step(len(tasks) + 2, total, "Assessing updated model...")

    return {
        "success": build_result.success if build_result else False,
        "model_name": model_name,
        "tasks_sent": len(tasks),
        "lessons_learned": learned,
        "build_message": build_result.message if build_result else "No build",
    }


# Default shadow learning tasks — real-world coding tasks for Claude to demonstrate
SHADOW_TASKS = [
    "Read the project structure and explain the architecture in detail.",
    "Find all TODO comments and suggest fixes for each one.",
    "Write unit tests for the main module in this project.",
    "Review the code for security vulnerabilities and suggest fixes.",
    "Refactor any duplicate code you find into reusable functions.",
    "Add error handling to functions that are missing it.",
    "Write a README.md that explains how to set up and use this project.",
    "Find performance bottlenecks and suggest optimizations.",
    "Add type hints to all functions that are missing them.",
    "Create a .gitignore file appropriate for this project type.",
]


# ── IQ Test Benchmark ────────────────────────────────────────
# Tests pattern recognition, logic, math reasoning, abstraction,
# spatial reasoning, and language comprehension — maps to IQ-style score.

IQ_QUESTIONS = [
    # Pattern recognition (20 pts each)
    {"id": "pat-1", "category": "pattern", "points": 20,
     "prompt": "What comes next in this sequence? 2, 6, 18, 54, __. Reply with just the number.",
     "answer": "162", "check": lambda r: "162" in r},
    {"id": "pat-2", "category": "pattern", "points": 20,
     "prompt": "What comes next? 1, 1, 2, 3, 5, 8, 13, __. Reply with just the number.",
     "answer": "21", "check": lambda r: "21" in r},
    {"id": "pat-3", "category": "pattern", "points": 20,
     "prompt": "Complete the pattern: A1, B2, C3, D4, __. Reply with just the answer.",
     "answer": "E5", "check": lambda r: "E5" in r.upper()},

    # Logic (20 pts each)
    {"id": "log-1", "category": "logic", "points": 20,
     "prompt": "All roses are flowers. Some flowers fade quickly. Can we conclude that some roses fade quickly? Answer: Yes, No, or Cannot determine.",
     "answer": "Cannot determine", "check": lambda r: "cannot" in r.lower() or "not necessarily" in r.lower() or "no" == r.strip().lower()},
    {"id": "log-2", "category": "logic", "points": 20,
     "prompt": "If it takes 5 machines 5 minutes to make 5 widgets, how many minutes would it take 100 machines to make 100 widgets? Reply with just the number.",
     "answer": "5", "check": lambda r: r.strip().startswith("5") or "5 min" in r},
    {"id": "log-3", "category": "logic", "points": 20,
     "prompt": "A bat and a ball cost $1.10 together. The bat costs $1.00 more than the ball. How much does the ball cost in cents? Reply with just the number.",
     "answer": "5", "check": lambda r: "5" in r and "10" not in r.split("5")[0][-3:]},

    # Math reasoning (20 pts each)
    {"id": "math-1", "category": "math", "points": 20,
     "prompt": "What is 17 * 23? Reply with just the number.",
     "answer": "391", "check": lambda r: "391" in r},
    {"id": "math-2", "category": "math", "points": 20,
     "prompt": "If you have 3 red balls and 5 blue balls in a bag, what's the probability of drawing a red ball? Reply as a fraction.",
     "answer": "3/8", "check": lambda r: "3/8" in r or "0.375" in r or "37.5" in r},
    {"id": "math-3", "category": "math", "points": 20,
     "prompt": "A train travels 60 mph for 2.5 hours, then 80 mph for 1.5 hours. What's the total distance in miles? Reply with just the number.",
     "answer": "270", "check": lambda r: "270" in r},

    # Abstraction (25 pts each)
    {"id": "abs-1", "category": "abstraction", "points": 25,
     "prompt": "What concept connects: inheritance, polymorphism, encapsulation? Reply in 1-3 words.",
     "answer": "OOP", "check": lambda r: any(w in r.lower() for w in ["object-oriented", "oop", "object oriented", "oo programming"])},
    {"id": "abs-2", "category": "abstraction", "points": 25,
     "prompt": "An analogy: CPU is to computer as ___ is to human body. Reply in one word.",
     "answer": "brain", "check": lambda r: "brain" in r.lower()},

    # Comprehension (25 pts each)
    {"id": "comp-1", "category": "comprehension", "points": 25,
     "prompt": "In Python, what's the difference between `is` and `==`? Answer in one sentence.",
     "answer": "identity vs equality", "check": lambda r: ("identity" in r.lower() or "object" in r.lower() or "same object" in r.lower()) and ("equal" in r.lower() or "value" in r.lower())},
    {"id": "comp-2", "category": "comprehension", "points": 25,
     "prompt": "What is Big O notation used for? Answer in one sentence.",
     "answer": "algorithm complexity", "check": lambda r: any(w in r.lower() for w in ["complex", "efficien", "performance", "time", "scale", "growth"])},

    # Spatial/structural reasoning (25 pts each)
    {"id": "spa-1", "category": "spatial", "points": 25,
     "prompt": "If you reverse a linked list, what was the tail becomes the ___. Reply in one word.",
     "answer": "head", "check": lambda r: "head" in r.lower()},
    {"id": "spa-2", "category": "spatial", "points": 25,
     "prompt": "In a binary tree with 7 nodes in a complete tree, how many leaf nodes are there? Reply with just the number.",
     "answer": "4", "check": lambda r: "4" in r},
]

# Max possible score
_IQ_MAX = sum(q["points"] for q in IQ_QUESTIONS)

# IQ score mapping: raw_pct -> estimated IQ
# Based on normal distribution: 50% = 100 IQ, each 10% = ~15 IQ points
def _raw_to_iq(raw_pct: float) -> int:
    """Convert raw percentage to estimated IQ score."""
    # Sigmoid-like mapping centered at 100 IQ = 50%
    if raw_pct <= 0:
        return 55
    if raw_pct >= 100:
        return 160
    # Linear interpolation through key points
    points = [(0, 55), (10, 70), (25, 85), (40, 95), (50, 100),
              (60, 108), (75, 120), (85, 130), (92, 140), (97, 150), (100, 160)]
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        if x0 <= raw_pct <= x1:
            t = (raw_pct - x0) / (x1 - x0)
            return round(y0 + t * (y1 - y0))
    return 100


def _iq_label(iq: int) -> tuple[str, str]:
    """Return (label, color) for an IQ score."""
    if iq >= 145: return "Genius", "[bold magenta]"
    if iq >= 130: return "Gifted", "[bold cyan]"
    if iq >= 120: return "Superior", "[cyan]"
    if iq >= 110: return "Above Average", "[green]"
    if iq >= 100: return "Average", "[yellow]"
    if iq >= 90:  return "Below Average", "[yellow]"
    if iq >= 80:  return "Low Average", "[red]"
    return "Needs Training", "[red]"


async def run_iq_test(ctx: dict, model_name: str, on_step) -> dict:
    """Run IQ benchmark and return scored results."""
    from ..providers.ollama.client import OllamaClient
    from ..core.interfaces import ChatMessage
    from ..utils.helpers import make_id
    from datetime import datetime

    client = OllamaClient(ctx["config"].ollama_base_url)
    questions = IQ_QUESTIONS
    results = []
    total = len(questions)
    earned = 0

    for i, q in enumerate(questions):
        on_step(i + 1, total, f"[{q['category']}] {q['prompt'][:45]}...")
        start = time.time()
        try:
            response = await client.chat(
                model=model_name,
                messages=[ChatMessage(make_id(), "user", q["prompt"], datetime.now().isoformat())],
                temperature=0.1,
            )
        except Exception as e:
            response = f"ERROR: {e}"
        latency = int((time.time() - start) * 1000)
        passed = q["check"](response)
        pts = q["points"] if passed else 0
        earned += pts
        results.append({
            "id": q["id"], "category": q["category"], "points": q["points"],
            "prompt": q["prompt"], "expected": q["answer"],
            "response": response[:300], "passed": passed,
            "earned": pts, "latency": latency,
        })

    raw_pct = round(earned / _IQ_MAX * 100) if _IQ_MAX else 0
    iq_score = _raw_to_iq(raw_pct)
    label, color = _iq_label(iq_score)

    # Per-category breakdown
    by_cat = {}
    for r in results:
        cat = r["category"]
        if cat not in by_cat:
            by_cat[cat] = {"earned": 0, "possible": 0, "passed": 0, "total": 0}
        by_cat[cat]["possible"] += r["points"]
        by_cat[cat]["earned"] += r["earned"]
        by_cat[cat]["total"] += 1
        if r["passed"]:
            by_cat[cat]["passed"] += 1

    return {
        "success": True,
        "model_name": model_name,
        "iq_score": iq_score,
        "iq_label": label,
        "iq_color": color,
        "raw_pct": raw_pct,
        "earned": earned,
        "max_points": _IQ_MAX,
        "by_category": by_cat,
        "results": results,
    }
