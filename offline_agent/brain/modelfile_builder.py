"""
brain/modelfile_builder.py

Takes a validated model design + its built dataset and emits
an Ollama Modelfile ready for:

    ollama create ken-ai-v1 -f <modelfile>

Real fine-tuning isn't built into Ollama itself — so this
builder does the best thing you can do with a local stack
today: write a Modelfile that (a) inherits a strong base
(ken-ai:latest), (b) stamps the brain_index identity + rules
into the SYSTEM block, and (c) embeds a curated set of
high-quality Q/A pairs as MESSAGE priming rows.

When Ken wants a real fine-tune later (unsloth / llama.cpp /
axolotl), the same builder can emit a raw jsonl training
file — the `--format unsloth` flag handles that.

Usage:
    python brain/modelfile_builder.py <design_slug>
    python brain/modelfile_builder.py <design_slug> --name ken-ai-v1
    python brain/modelfile_builder.py <design_slug> --format unsloth
    python brain/modelfile_builder.py <design_slug> --dry
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
DESIGNS_DIR    = HERE / "model_designs"
DATASET_DIR    = HERE / "training" / "datasets"
MODELFILE_DIR  = HERE / "training" / "modelfiles"
BRAIN_INDEX    = HERE / "brain_index"

MODELFILE_DIR.mkdir(parents=True, exist_ok=True)


# ─── io helpers ───────────────────────────────────────────

def load_design(slug: str) -> dict:
    p = DESIGNS_DIR / slug / "design.json"
    if not p.exists():
        raise FileNotFoundError(f"no design at {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def latest_dataset_for(slug: str) -> Optional[Path]:
    """Find the newest dataset .jsonl for this design slug."""
    candidates = sorted(
        DATASET_DIR.glob(f"*-{slug}.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def read_baseline() -> tuple[str, str]:
    """Return identity.md + rules.md contents for the SYSTEM block."""
    ident = ""
    rules = ""
    ip = BRAIN_INDEX / "identity.md"
    rp = BRAIN_INDEX / "rules.md"
    if ip.exists():
        ident = ip.read_text(encoding="utf-8", errors="ignore")
    if rp.exists():
        rules = rp.read_text(encoding="utf-8", errors="ignore")
    return ident, rules


def condense_brain_text(text: str, *, max_lines: int = 18, max_chars: int = 2200) -> str:
    """
    Turn a markdown brain file into a compact plain-text block
    suitable for the SYSTEM prompt without dragging in full-file
    noise or giant paragraphs.
    """
    if not text:
        return ""

    lines: list[str] = []
    total = 0

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("<!--"):
            continue
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        if line.startswith("- "):
            line = line[2:].strip()
        if not line:
            continue
        if len(line) > 180:
            line = line[:177].rstrip() + "..."
        projected = total + len(line) + 3
        if projected > max_chars:
            break
        lines.append(f"- {line}")
        total = projected
        if len(lines) >= max_lines:
            break

    return "\n".join(lines)


# ─── row shaping ──────────────────────────────────────────

def extract_qa_pair(row: dict) -> Optional[tuple[str, str]]:
    """
    Try to pull a (user_prompt, assistant_response) pair out of
    a dataset row. Dataset rows come from multiple kinds:
      - drill_passing_rows: { source, kind, data: { prompt, response, grade, ... } }
      - dispatch_rows:      { source, kind, data: { prompt, response, approved, ... } }
      - narrative_context:  { source, kind, data: { content } } — not a Q/A pair
      - reference_context:  { source, kind, data: { path, content } } — not a Q/A pair

    Returns None for rows that aren't Q/A shaped.
    """
    kind = row.get("kind")
    data = row.get("data") or {}

    if kind in ("drill_passing_rows", "dispatch_rows"):
        prompt = data.get("prompt") or data.get("task") or data.get("input")
        if not prompt and data.get("drillId"):
            prompt = f"complete drill {data['drillId']}"
        response = (
            data.get("response")
            or data.get("output")
            or data.get("answer")
            or data.get("content")
        )
        if prompt and response and len(response) > 20:
            return (str(prompt).strip(), str(response).strip())

    return None


def score_row(row: dict) -> float:
    """
    Rank rows by usefulness. High-score rows go into MESSAGE
    priming, low-score rows get left out. Scoring heuristics:

      - grade.percent if present         → 0.0-1.0
      - approved == True                 → +0.2
      - success == True                  → +0.1
      - ken-voice model                  → +0.2
      - response length in 50-2000 chars → +0.1
      - fresh (last 14 days)             → +0.1
    """
    data = row.get("data") or {}
    score = 0.0

    grade = data.get("grade") or {}
    if isinstance(grade, dict):
        pct = grade.get("percent")
        if isinstance(pct, (int, float)):
            score += float(pct)
    elif isinstance(data.get("percent"), (int, float)):
        score += float(data["percent"])

    if data.get("approved") is True:
        score += 0.2
    if data.get("success") is True:
        score += 0.1
    if data.get("model") == "ken-ai:latest":
        score += 0.2
    if data.get("student") in ("ken-ai:latest", "kenai:v1"):
        score += 0.2
    if data.get("student") in ("qwen2.5-coder:14b", "forgeagent:latest", "cherp-piper:latest"):
        score += 0.05

    response = str(
        data.get("response") or data.get("output") or data.get("answer") or ""
    )
    if 50 <= len(response) <= 2000:
        score += 0.1
    elif len(response) > 2000:
        score -= 0.2  # too long — likely noise or tool dump

    ts = data.get("at") or data.get("timestamp") or data.get("savedAt")
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - dt
            if age.days <= 14:
                score += 0.1
        except Exception:
            pass

    return score


def build_brain_primers() -> list[tuple[str, str]]:
    """
    Deterministic few-shot rows derived from the brain contract.
    These keep core repo facts and permission behavior stable
    even while the live training corpus is still small.
    """
    return [
        (
            "list the six core files that live in brain/brain_index/ and what each one is for. one short line per file. lowercase.",
            "\n".join([
                "- identity.md: who the agent is and how it should speak.",
                "- rules.md: operating rules, safety limits, and repo guardrails.",
                "- tech_stack.md: ports, runtimes, models, and stack notes.",
                "- project_map.md: ken's projects and how they connect.",
                "- repo_map.md: clone layout, remotes, and branch context.",
                "- known_fixes.md: recurring bugs, fixes, and lessons learned.",
            ]),
        ),
        (
            "using the context above, list the six core files that live in brain/brain_index/ and what each one is for. one short lowercase bullet per file. do not invent filenames that are not in the context.",
            "\n".join([
                "- identity.md: agent identity and voice rules.",
                "- rules.md: operating rules and safety limits.",
                "- project_map.md: projects and how they connect.",
                "- repo_map.md: clone layout and git context.",
                "- known_fixes.md: recurring bugs and fixes.",
                "- tech_stack.md: models, runtimes, and ports.",
            ]),
        ),
        (
            "what do you do when your current permission mode is 0 (read only) and the task asks you to edit a file in workspace/? answer in 3-5 short lowercase lines.",
            "\n".join([
                "- mode 0 is read only.",
                "- propose the patch first.",
                "- ask to escalate before editing.",
                "- write only after confirmation.",
            ]),
        ),
        (
            "you're running inside Codex/offline_agent/. there's a parallel clone at C:/Users/Ken/Desktop/Claude. should you edit files in the Claude clone? answer yes or no with one-line reasoning in lowercase.",
            "no. edit the codex clone only. use git to sync shared state.",
        ),
        (
            "you're running inside codex/offline_agent/. there's a parallel clone at c:/users/ken/desktop/claude. answer in exactly two lowercase lines:\n\nANSWER: <yes or no>\nWHY: <6-14 words>\n\nsay no unless the context explicitly says to edit the other clone directly.",
            "ANSWER: no\nWHY: stay in codex; use git to sync shared state.",
        ),
        (
            "what do you do if a task asks you to write to c:/windows/system32? answer in 3 short lowercase lines.",
            "\n".join([
                "- refuse the write.",
                "- system paths stay blocked in every mode.",
                "- surface the risk and stop.",
            ]),
        ),
        (
            "you need to read the file brain/brain_index/identity.md. respond with exactly one json object in this shape and nothing else: {\"tool\":\"read_file\",\"params\":{\"path\":\"brain/brain_index/identity.md\"}}",
            "{\"tool\":\"read_file\",\"params\":{\"path\":\"brain/brain_index/identity.md\"}}",
        ),
        (
            "you finished the task 'add health pin thread to halo hunt'. respond with exactly one json object in this shape and nothing else: {\"done\":true,\"summary\":\"...\"}. summary must be 5-15 lowercase words.",
            "{\"done\":true,\"summary\":\"added health pin thread to halo hunt\"}",
        ),
    ]


# ─── builders ─────────────────────────────────────────────

MODELFILE_TEMPLATE = """# Ollama Modelfile for {model_name}
# generated by offline_agent/brain/modelfile_builder.py
# design: {design_slug} v{design_version}
# built:  {built_at}
# base:   {base_model}
# dataset: {dataset_file}
# priming rows: {prime_count} (score >= {min_score:.2f})

FROM {base_model}

# Lower temp for tactical responses. Ken's voice doesn't rely
# on creativity — it relies on directness.
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 32768

# ── SYSTEM block (identity + rules, condensed) ───────────
SYSTEM \"\"\"
{system_block}
\"\"\"

# ── MESSAGE priming rows ─────────────────────────────────
# High-scoring Q/A pairs from the curated dataset. These act
# as few-shot examples the model can pattern-match against.
{message_block}
"""


def build_system_block(design: dict, identity: str, rules: str) -> str:
    """Compress identity + rules + mission into a tight SYSTEM block."""
    identity_excerpt = condense_brain_text(identity, max_lines=14, max_chars=1400)
    rules_excerpt = condense_brain_text(rules, max_lines=16, max_chars=1600)
    parts = []
    parts.append(f"you are {design['name']}, running offline on ken's windows box.")
    parts.append("")
    parts.append(design["mission"])
    parts.append("")
    parts.append("voice rules (hard):")
    parts.append("- lowercase only")
    parts.append("- 4-10 words per line when writing short actions")
    parts.append("- no \"as an AI\"")
    parts.append("- no analogies, no \"think of it as\" / \"like a\"")
    parts.append("- no construction metaphors when talking about code")
    parts.append("- typos ok, direct beats hedging")
    parts.append("")
    parts.append("core principles:")
    parts.append("- read before writing. always.")
    parts.append("- propose before executing in mode 0. execute cleanly in mode 1+.")
    parts.append("- log every tool call to logs/actions.jsonl")
    parts.append("- never touch system paths (C:/Windows, ~/.ssh) regardless of mode")
    parts.append("- kill switch file wins over everything else")
    parts.append("")
    parts.append("you have a brain at brain/brain_index/*.md. baseline files")
    parts.append("identity.md and rules.md are injected into every turn. everything")
    parts.append("else is pulled via FTS top-K per query.")
    parts.append("")
    if identity_excerpt:
        parts.append("brain baseline: identity.md")
        parts.append(identity_excerpt)
        parts.append("")
    if rules_excerpt:
        parts.append("brain baseline: rules.md")
        parts.append(rules_excerpt)
        parts.append("")
    parts.append("when you emit a tool call, respond with EXACTLY one JSON object:")
    parts.append('  {"tool": "tool_name", "params": {"k": "v"}}')
    parts.append("when a task is done:")
    parts.append('  {"done": true, "summary": "..."}')
    parts.append("when you need clarification:")
    parts.append('  {"clarify": "your question"}')
    parts.append("otherwise respond in plain text.")
    # escape triple-quotes in case any rule text contained them
    return "\n".join(parts).replace('"""', '\\"\\"\\"')


def build_message_block(rows: list[dict], limit: int, min_score: float) -> tuple[str, int]:
    """
    Turn the top-N highest-scoring Q/A rows into MESSAGE
    directives. Ollama Modelfile syntax:

        MESSAGE user <prompt>
        MESSAGE assistant <response>
    """
    ranked = []
    for r in rows:
        qa = extract_qa_pair(r)
        if not qa:
            continue
        s = score_row(r)
        if s < min_score:
            continue
        ranked.append((s, qa))
    ranked.sort(key=lambda x: -x[0])
    ranked = ranked[:limit]

    lines = []
    prime_count = 0

    for prompt, response in build_brain_primers():
        p_clean = prompt.replace("\r", "").replace("\n", "\\n")
        r_clean = response.replace("\r", "").replace("\n", "\\n")
        lines.append(f"MESSAGE user {p_clean}")
        lines.append(f"MESSAGE assistant {r_clean}")
        lines.append("")
        prime_count += 1

    for score, (prompt, response) in ranked:
        # Collapse newlines so Modelfile parsing is happy — we
        # keep paragraph breaks as `\n` literal escapes.
        p_clean = prompt.replace("\r", "").replace("\n", "\\n")
        r_clean = response.replace("\r", "").replace("\n", "\\n")
        # Cap both to keep the Modelfile under a reasonable size
        if len(p_clean) > 800:
            p_clean = p_clean[:800] + "..."
        if len(r_clean) > 1200:
            r_clean = r_clean[:1200] + "..."
        lines.append(f"MESSAGE user {p_clean}")
        lines.append(f"MESSAGE assistant {r_clean}")
        lines.append("")
        prime_count += 1

    return "\n".join(lines), prime_count


def build_modelfile(
    design: dict,
    dataset_path: Path,
    model_name: str,
    base_model: Optional[str] = None,
    prime_limit: int = 30,
    min_score: float = 0.6,
) -> tuple[Path, dict]:
    identity, rules = read_baseline()
    if base_model is None:
        base_model = design.get("runtime_plan", {}).get("base", "ken-ai:latest")
        # strip any " (qwen2.5-coder:14b + profile)" annotation
        base_model = base_model.split(" ")[0].strip() or "ken-ai:latest"

    rows = []
    if dataset_path.exists():
        for line in dataset_path.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue

    system_block = build_system_block(design, identity, rules)
    message_block, prime_count = build_message_block(rows, prime_limit, min_score)

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    modelfile_text = MODELFILE_TEMPLATE.format(
        model_name=model_name,
        design_slug=design["slug"],
        design_version=design.get("version", "0.0.0"),
        built_at=built_at,
        base_model=base_model,
        dataset_file=dataset_path.name if dataset_path else "(none)",
        prime_count=prime_count,
        min_score=min_score,
        system_block=system_block,
        message_block=message_block or "# (no priming rows passed the score threshold)",
    )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    out_path = MODELFILE_DIR / f"{ts}-{model_name}.Modelfile"
    out_path.write_text(modelfile_text, encoding="utf-8")

    stats = {
        "model_name":  model_name,
        "base_model":  base_model,
        "dataset":     str(dataset_path.relative_to(PROJECT_ROOT)) if dataset_path and dataset_path.exists() else None,
        "total_rows":  len(rows),
        "prime_count": prime_count,
        "min_score":   min_score,
        "modelfile":   str(out_path.relative_to(PROJECT_ROOT)),
        "built_at":    built_at,
    }
    return out_path, stats


def build_unsloth_dataset(design: dict, dataset_path: Path, model_name: str) -> Path:
    """
    Alternate emitter for real fine-tune pipelines.
    Writes instruction/input/output triples in unsloth format:

        {"instruction": "...", "input": "...", "output": "..."}
    """
    out_path = MODELFILE_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S')}-{model_name}.unsloth.jsonl"
    rows_written = 0
    with out_path.open("w", encoding="utf-8") as f:
        for line in dataset_path.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            qa = extract_qa_pair(row)
            if not qa:
                continue
            prompt, response = qa
            f.write(json.dumps({
                "instruction": prompt,
                "input":       "",
                "output":      response,
            }) + "\n")
            rows_written += 1
    return out_path


# ─── cli ──────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="design slug under brain/model_designs/")
    ap.add_argument("--name", default=None, help="output model name (default: <slug>-v1)")
    ap.add_argument("--base", default=None, help="base ollama model")
    ap.add_argument("--limit", type=int, default=30, help="max priming rows")
    ap.add_argument("--min-score", type=float, default=0.6)
    ap.add_argument("--format", choices=("ollama", "unsloth"), default="ollama")
    ap.add_argument("--dry", action="store_true", help="print stats without writing")
    args = ap.parse_args()

    design = load_design(args.slug)
    dataset_path = latest_dataset_for(args.slug)
    if not dataset_path:
        print(f"no dataset built for {args.slug} yet — run `python brain/model_designer.py full {args.slug}` first")
        return 1

    model_name = args.name or f"{args.slug.replace('-', '')}v1"

    if args.format == "unsloth":
        out = build_unsloth_dataset(design, dataset_path, model_name)
        print(f"unsloth dataset: {out.relative_to(PROJECT_ROOT)}")
        return 0

    out_path, stats = build_modelfile(
        design, dataset_path, model_name,
        base_model=args.base,
        prime_limit=args.limit,
        min_score=args.min_score,
    )
    print(json.dumps(stats, indent=2))
    if not args.dry:
        print(f"\nnext step:")
        print(f"  ollama create {model_name} -f {out_path.relative_to(PROJECT_ROOT)}")
        print(f"  ollama run {model_name} \"say hi in your own voice\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
