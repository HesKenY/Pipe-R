"""Background automation pipelines for training, improvement, and deployment."""
from __future__ import annotations
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
        pull_result = await mb.pull_base_model(base_model)
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
    Improve an existing model by adding more training data and rebuilding.

    config keys: model_name, harvest_conversations (bool), scrape_topic (str|None)
    """
    dm = ctx["dataset_manager"]
    mb = ctx["model_builder"]
    ev = ctx["evaluator"]
    sc = ctx["scraper"]
    engine = ctx["engine"]

    model_name = config["model_name"]
    total = 5

    # Find existing profile and dataset
    profile = mb.get_profile(model_name)
    if not profile:
        return {"success": False, "error": f"Profile '{model_name}' not found"}

    ds = profile.get("datasetName") or f"{model_name}-data"
    try:
        dm.create_dataset(ds, f"Data for {model_name}")
    except ValueError:
        pass

    # Step 1: Evaluate current model (before)
    on_step(1, total, "Evaluating current model performance...")
    try:
        before = await ev.evaluate(model_name)
        before_score = before.get("avgScore", 0)
    except Exception:
        before_score = 0

    # Step 2: Harvest conversations
    added = 0
    if config.get("harvest_conversations", True):
        on_step(2, total, "Harvesting recent conversations...")
        try:
            added = dm.harvest_from_conversation(ds, engine.get_messages())
        except Exception:
            added = 0
    else:
        on_step(2, total, "Skipping conversation harvest.")

    # Step 3: Scrape more data
    scraped = 0
    topic = config.get("scrape_topic")
    if topic:
        on_step(3, total, f"Scraping more {topic} data...")
        try:
            results = await sc.scrape_topic(dm, ds, topic)
            scraped = sum(x.get("examples", 0) for x in results)
        except Exception:
            scraped = 0
    else:
        on_step(3, total, "Skipping additional scraping.")

    # Step 4: Rebuild model
    on_step(4, total, f"Rebuilding model '{model_name}'...")
    result = await mb.build_model(model_name, dm)
    if not result.success:
        return {"success": False, "error": result.message}

    # Step 5: Evaluate improved model (after)
    on_step(5, total, "Evaluating improved model...")
    try:
        after = await ev.evaluate(model_name)
        after_score = after.get("avgScore", 0)
    except Exception:
        after_score = 0

    return {
        "success": True,
        "model_name": model_name,
        "added_conversations": added,
        "added_scraped": scraped,
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
    focus_info = FOCUS_MAP.get(config.get("focus", "general"), FOCUS_MAP["general"])
    topic = focus_info["topic"]
    total = 7

    # Find existing profile
    profile = mb.get_profile(model_name)
    if not profile:
        return {"success": False, "error": f"Profile '{model_name}' not found"}

    base_model = profile["baseModel"]
    ds = profile.get("datasetName") or f"{model_name}-data"

    # Step 1: Wipe old dataset and recreate
    on_step(1, total, f"Wiping dataset '{ds}' and starting fresh...")
    dm.delete_dataset(ds)
    dm.create_dataset(ds, f"Retrained data for {model_name}")

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
    total = 7

    profile = mb.get_profile(model_name)
    if not profile:
        return {"success": False, "error": f"Profile '{model_name}' not found"}

    ds = profile.get("datasetName") or f"{model_name}-data"
    try:
        dm.create_dataset(ds, f"Data for {model_name}")
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
