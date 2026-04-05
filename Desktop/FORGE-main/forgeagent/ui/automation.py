"""Background automation pipelines for training, improvement, and deployment."""
from __future__ import annotations
import os
import re
import time
from pathlib import Path


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
    name = config.get("name") or f"forge-{config['focus']}"
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
    has_claude = bool(api_key)
    cases = BENCHMARK_CASES
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
