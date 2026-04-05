"""Training data collection, curation, and export."""
from __future__ import annotations
import json
import re
import random
import string
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class TrainingExample:
    id: str
    prompt: str
    completion: str
    tags: list[str] = field(default_factory=list)
    source: str = "manual"
    system: str | None = None
    tool_calls: list[dict] | None = None
    created: str = ""

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().isoformat()
        if not self.id:
            self.id = _uid()


def _uid() -> str:
    import time
    return hex(int(time.time() * 1000))[2:] + "".join(random.choices(string.ascii_lowercase, k=4))


class DatasetManager:
    def __init__(self, base_dir: str):
        self.datasets_dir = Path(base_dir) / "datasets"
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    # ── Create / Delete ─────────────────────────────
    def create_dataset(self, name: str, description: str = "") -> dict:
        d = self.datasets_dir / name
        if d.exists():
            raise ValueError(f'Dataset "{name}" already exists')
        d.mkdir(parents=True)
        meta = {"name": name, "description": description, "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat(), "exampleCount": 0, "tags": []}
        (d / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        (d / "examples.jsonl").write_text("", encoding="utf-8")
        return meta

    def delete_dataset(self, name: str) -> bool:
        d = self.datasets_dir / name
        if not d.exists():
            return False
        import shutil
        shutil.rmtree(d)
        return True

    # ── List / Get ──────────────────────────────────
    def list_datasets(self) -> list[dict]:
        results = []
        for d in sorted(self.datasets_dir.iterdir()):
            mf = d / "meta.json"
            if mf.exists():
                results.append(json.loads(mf.read_text()))
        return sorted(results, key=lambda x: x.get("updated", ""), reverse=True)

    def get_dataset(self, name: str) -> dict | None:
        d = self.datasets_dir / name
        mf = d / "meta.json"
        if not mf.exists():
            return None
        meta = json.loads(mf.read_text())
        examples = []
        ef = d / "examples.jsonl"
        if ef.exists():
            for line in ef.read_text().strip().split("\n"):
                if line.strip():
                    try:
                        examples.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return {"meta": meta, "examples": examples}

    # ── Add Examples ────────────────────────────────
    def add_example(self, dataset_name: str, ex: TrainingExample) -> None:
        d = self.datasets_dir / dataset_name
        if not d.exists():
            raise ValueError(f'Dataset "{dataset_name}" not found')
        with open(d / "examples.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": ex.id, "prompt": ex.prompt, "completion": ex.completion,
                                "tags": ex.tags, "source": ex.source, "system": ex.system,
                                "tool_calls": ex.tool_calls, "created": ex.created}) + "\n")
        self._update_meta(dataset_name, ex.tags)

    def add_manual_example(self, dataset_name: str, prompt: str, completion: str, tags: list[str] | None = None) -> TrainingExample:
        ex = TrainingExample(id=_uid(), prompt=prompt, completion=completion, tags=tags or [], source="manual")
        self.add_example(dataset_name, ex)
        return ex

    # ── Harvest from Conversation ───────────────────
    def harvest_from_conversation(self, dataset_name: str, messages: list, system_prompt: str | None = None) -> int:
        count = 0
        prompt = ""
        for msg in messages:
            role = msg.role if hasattr(msg, "role") else msg.get("role", "")
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            if role == "user":
                prompt = content
            elif role == "assistant" and prompt and len(prompt) > 5 and len(content) > 5:
                self.add_example(dataset_name, TrainingExample(
                    id=_uid(), prompt=prompt, completion=content,
                    tags=["conversation"], source="conversation", system=system_prompt))
                count += 1
                prompt = ""
        return count

    # ── Harvest from Codebase ───────────────────────
    def harvest_from_codebase(self, dataset_name: str, cwd: str, extensions: list[str] | None = None, max_files: int = 50) -> int:
        exts = extensions or [".py", ".ts", ".js", ".go", ".rs", ".java"]
        count = 0
        root = Path(cwd)
        for fp in self._walk_files(root, exts, max_files):
            content = fp.read_text(encoding="utf-8", errors="replace")
            if len(content) < 50 or len(content) > 50000:
                continue
            rel = str(fp.relative_to(root)).replace("\\", "/")
            self.add_example(dataset_name, TrainingExample(
                id=_uid(), prompt=f"Read and analyze the file {rel}",
                completion=f"Here's the file {rel}:\n\n```\n{content[:4000]}\n```",
                tags=["codebase"], source="codebase"))
            count += 1
        return count

    # ── Generate Synthetic Tool-Use Examples ────────
    def generate_tool_use_examples(self, dataset_name: str, count: int = 20) -> int:
        patterns = [
            ("List the files in the current directory",
             'I\'ll list the directory.\n\n```tool\n{"toolCalls":[{"toolName":"list_dir","input":{"path":"."}}]}\n```',
             ["tool-use", "list_dir"]),
            ("Read the file package.json",
             'I\'ll read that file.\n\n```tool\n{"toolCalls":[{"toolName":"read_file","input":{"path":"package.json"}}]}\n```',
             ["tool-use", "read_file"]),
            ("Create a file called hello.py with a greeting function",
             'I\'ll create hello.py.\n\n```tool\n{"toolCalls":[{"toolName":"write_file","input":{"path":"hello.py","content":"def greet(name):\\n    return f\\"Hello, {name}!\\"\\n"}}]}\n```',
             ["tool-use", "write_file"]),
            ("Run the tests",
             'I\'ll run the test suite.\n\n```tool\n{"toolCalls":[{"toolName":"bash","input":{"command":"python -m pytest"}}]}\n```',
             ["tool-use", "bash"]),
            ("Search for TODO comments in the codebase",
             'I\'ll search for TODOs.\n\n```tool\n{"toolCalls":[{"toolName":"search_files","input":{"pattern":"TODO","path":"."}}]}\n```',
             ["tool-use", "search_files"]),
            ("Find all Python files in src/",
             'I\'ll find .py files.\n\n```tool\n{"toolCalls":[{"toolName":"glob","input":{"pattern":"*.py","path":"src"}}]}\n```',
             ["tool-use", "glob"]),
            ("What time is it?",
             'Let me check.\n\n```tool\n{"toolCalls":[{"toolName":"datetime","input":{}}]}\n```',
             ["tool-use", "datetime"]),
            ("Add a task to fix the login bug",
             'I\'ll add that task.\n\n```tool\n{"toolCalls":[{"toolName":"task","input":{"action":"add","text":"Fix the login bug"}}]}\n```',
             ["tool-use", "task"]),
            ("Remember that the API key is stored in .env",
             'I\'ll save that.\n\n```tool\n{"toolCalls":[{"toolName":"memory_save","input":{"section":"Config","content":"API key is in .env"}}]}\n```',
             ["tool-use", "memory_save"]),
            ("Check if we noted anything about the database",
             'I\'ll search memory.\n\n```tool\n{"toolCalls":[{"toolName":"memory_search","input":{"query":"database"}}]}\n```',
             ["tool-use", "memory_search"]),
            ("Check the git log for recent changes",
             'I\'ll check git history.\n\n```tool\n{"toolCalls":[{"toolName":"bash","input":{"command":"git log --oneline -10"}}]}\n```',
             ["tool-use", "bash", "git"]),
            ("Install flask and create a basic server",
             'I\'ll install flask and create the server.\n\n```tool\n{"toolCalls":[{"toolName":"bash","input":{"command":"pip install flask"}},{"toolName":"write_file","input":{"path":"app.py","content":"from flask import Flask\\napp = Flask(__name__)\\n\\n@app.route(\\"/\\")\\ndef index():\\n    return {\\"status\\": \\"ok\\"}\\n\\nif __name__ == \\"__main__\\":\\n    app.run(debug=True)\\n"}}]}\n```',
             ["tool-use", "multi-tool", "bash", "write_file"]),
            ("Show me what changed and run the build",
             'I\'ll check changes and build.\n\n```tool\n{"toolCalls":[{"toolName":"bash","input":{"command":"git diff --stat"}},{"toolName":"bash","input":{"command":"python -m build"}}]}\n```',
             ["tool-use", "multi-tool", "bash"]),
            ("Replace old_func with new_func in utils.py",
             'I\'ll update utils.py.\n\n```tool\n{"toolCalls":[{"toolName":"edit_file","input":{"path":"utils.py","old_text":"old_func","new_text":"new_func"}}]}\n```',
             ["tool-use", "edit_file"]),
            ("Show directory structure of src recursively",
             'I\'ll list src recursively.\n\n```tool\n{"toolCalls":[{"toolName":"list_dir","input":{"path":"src","recursive":true}}]}\n```',
             ["tool-use", "list_dir"]),
            ("What tasks do we have pending?",
             'I\'ll check tasks.\n\n```tool\n{"toolCalls":[{"toolName":"task","input":{"action":"list"}}]}\n```',
             ["tool-use", "task"]),
            ("Fetch the PyPI info for the requests package",
             'I\'ll fetch the package info.\n\n```tool\n{"toolCalls":[{"toolName":"web_fetch","input":{"url":"https://pypi.org/pypi/requests/json"}}]}\n```',
             ["tool-use", "web_fetch"]),
            ("Create a tests directory with a basic test file",
             'I\'ll set up the test structure.\n\n```tool\n{"toolCalls":[{"toolName":"bash","input":{"command":"mkdir -p tests"}},{"toolName":"write_file","input":{"path":"tests/test_basic.py","content":"def test_pass():\\n    assert 1 + 1 == 2\\n"}}]}\n```',
             ["tool-use", "multi-tool", "bash", "write_file"]),
            ("Read the config file and check port settings",
             'I\'ll read the config.\n\n```tool\n{"toolCalls":[{"toolName":"read_file","input":{"path":"config.json"}}]}\n```',
             ["tool-use", "read_file", "analysis"]),
            ("Mark task 3 as done",
             'Done.\n\n```tool\n{"toolCalls":[{"toolName":"task","input":{"action":"done","text":"3"}}]}\n```',
             ["tool-use", "task"]),
        ]
        actual = min(count, len(patterns))
        for i in range(actual):
            p, c, tags = patterns[i]
            self.add_example(dataset_name, TrainingExample(id=_uid(), prompt=p, completion=c, tags=tags, source="synthetic"))
        return actual

    # ── Import from file ───────────────────────────
    def import_from_file(self, dataset_name: str, file_path: str) -> int:
        """Import training examples from a JSONL or JSON file.

        Supports formats:
        - JSONL with {"messages": [...]} (OpenAI/ChatML format)
        - JSONL with {"prompt": "...", "completion": "..."} (Alpaca-like)
        - JSONL with {"instruction": "...", "output": "..."} (Alpaca format)
        - JSON array of any of the above
        - Plain JSONL with {"role": "user/assistant", ...} pairs
        """
        fp = Path(file_path)
        if not fp.exists():
            raise FileNotFoundError(f"File not found: {fp}")

        content = fp.read_text(encoding="utf-8", errors="replace").strip()
        count = 0

        # Try JSON array first
        records = []
        if content.startswith("["):
            try:
                records = json.loads(content)
            except json.JSONDecodeError:
                pass

        # Otherwise treat as JSONL
        if not records:
            for line in content.split("\n"):
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        for record in records:
            prompt = ""
            completion = ""
            tags = ["imported"]

            # Format: {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
            if "messages" in record:
                msgs = record["messages"]
                user_parts = []
                assistant_parts = []
                for m in msgs:
                    role = m.get("role", "")
                    content_text = m.get("content", "")
                    if role == "user":
                        user_parts.append(content_text)
                    elif role == "assistant":
                        assistant_parts.append(content_text)
                prompt = "\n".join(user_parts)
                completion = "\n".join(assistant_parts)

            # Format: {"conversations": [...]} (ChatML/ShareGPT)
            elif "conversations" in record:
                msgs = record["conversations"]
                user_parts = []
                assistant_parts = []
                for m in msgs:
                    role = m.get("role", m.get("from", ""))
                    content_text = m.get("content", m.get("value", ""))
                    if role in ("user", "human"):
                        user_parts.append(content_text)
                    elif role in ("assistant", "gpt"):
                        assistant_parts.append(content_text)
                prompt = "\n".join(user_parts)
                completion = "\n".join(assistant_parts)

            # Format: {"prompt": "...", "completion": "..."}
            elif "prompt" in record and "completion" in record:
                prompt = record["prompt"]
                completion = record["completion"]

            # Format: {"instruction": "...", "output": "..."} (Alpaca)
            elif "instruction" in record and "output" in record:
                prompt = record["instruction"]
                if record.get("input"):
                    prompt += "\n" + record["input"]
                completion = record["output"]

            # Format: {"question": "...", "answer": "..."}
            elif "question" in record and "answer" in record:
                prompt = record["question"]
                completion = record["answer"]

            if prompt and completion and len(prompt) > 3 and len(completion) > 3:
                self.add_example(dataset_name, TrainingExample(
                    id=_uid(), prompt=prompt[:4000], completion=completion[:4000],
                    tags=tags, source="imported",
                ))
                count += 1

        return count

    # ── Export ──────────────────────────────────────
    def export_dataset(self, name: str, fmt: str = "jsonl") -> str:
        ds = self.get_dataset(name)
        if not ds:
            raise ValueError(f'Dataset "{name}" not found')
        out_dir = self.datasets_dir / name / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        examples = ds["examples"]

        if fmt == "jsonl":
            path = out_dir / f"{name}.jsonl"
            lines = []
            for e in examples:
                msgs = []
                if e.get("system"):
                    msgs.append({"role": "system", "content": e["system"]})
                msgs.append({"role": "user", "content": e["prompt"]})
                msgs.append({"role": "assistant", "content": e["completion"]})
                lines.append(json.dumps({"messages": msgs}))
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return str(path)
        elif fmt == "alpaca":
            path = out_dir / f"{name}-alpaca.json"
            data = [{"instruction": e["prompt"], "input": "", "output": e["completion"]} for e in examples]
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return str(path)
        elif fmt == "chatml":
            path = out_dir / f"{name}-chatml.jsonl"
            lines = []
            for e in examples:
                msgs = []
                if e.get("system"):
                    msgs.append({"role": "system", "content": e["system"]})
                msgs.append({"role": "user", "content": e["prompt"]})
                msgs.append({"role": "assistant", "content": e["completion"]})
                lines.append(json.dumps({"conversations": msgs}))
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return str(path)
        elif fmt == "openai":
            path = out_dir / f"{name}-openai.jsonl"
            lines = []
            for e in examples:
                msgs = []
                if e.get("system"):
                    msgs.append({"role": "system", "content": e["system"]})
                msgs.append({"role": "user", "content": e["prompt"]})
                msgs.append({"role": "assistant", "content": e["completion"]})
                lines.append(json.dumps({"messages": msgs}))
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return str(path)
        raise ValueError(f"Unknown format: {fmt}")

    # ── Helpers ─────────────────────────────────────
    def _update_meta(self, name: str, tags: list[str]) -> None:
        mf = self.datasets_dir / name / "meta.json"
        meta = json.loads(mf.read_text())
        meta["exampleCount"] = meta.get("exampleCount", 0) + 1
        meta["updated"] = datetime.now().isoformat()
        for t in tags:
            if t not in meta.get("tags", []):
                meta.setdefault("tags", []).append(t)
        mf.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def _walk_files(self, root: Path, exts: list[str], max_files: int) -> list[Path]:
        results = []
        def walk(d: Path, depth: int):
            if depth > 4 or len(results) >= max_files:
                return
            try:
                for e in d.iterdir():
                    if e.name.startswith(".") or e.name in ("node_modules", "dist", "__pycache__", ".git"):
                        continue
                    if e.is_dir():
                        walk(e, depth + 1)
                    elif any(e.name.endswith(ext) for ext in exts):
                        results.append(e)
                        if len(results) >= max_files:
                            return
            except PermissionError:
                pass
        walk(root, 0)
        return results
