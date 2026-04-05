"""Model evaluation and benchmarking."""
from __future__ import annotations
import json
import re
import time
from pathlib import Path
from datetime import datetime
from ..providers.ollama.client import OllamaClient
from ..providers.ollama.tool_protocol import parse_tool_calls
from ..utils.helpers import make_id
from ..core.interfaces import ChatMessage


BUILTIN_CASES = [
    {"id": "tool-1", "category": "tool-use", "prompt": "Read the file package.json",
     "validators": [{"type": "tool-called", "value": "read_file"}]},
    {"id": "tool-2", "category": "tool-use", "prompt": "List files in the current directory",
     "validators": [{"type": "tool-called", "value": "list_dir"}]},
    {"id": "tool-3", "category": "tool-use", "prompt": "Run npm test",
     "validators": [{"type": "tool-called", "value": "bash"}, {"type": "contains", "value": "test"}]},
    {"id": "tool-4", "category": "tool-use", "prompt": "Search for TODO comments in src",
     "validators": [{"type": "tool-called", "value": "search_files"}]},
    {"id": "tool-5", "category": "tool-use", "prompt": "Create a file called test.py with a hello function",
     "validators": [{"type": "tool-called", "value": "write_file"}]},
    {"id": "code-1", "category": "code-gen", "prompt": "Write a function that reverses a string",
     "validators": [{"type": "code-block", "value": ""}, {"type": "contains", "value": "reverse"}]},
    {"id": "code-2", "category": "code-gen", "prompt": "Write a function to check if a number is prime",
     "validators": [{"type": "code-block", "value": ""}, {"type": "regex", "value": "def |function|=>"}]},
    {"id": "reason-1", "category": "reasoning",
     "prompt": "array.find() on an empty array returns undefined. Why?",
     "validators": [{"type": "contains", "value": "undefined"}, {"type": "regex", "value": "empty|no.*match"}]},
    {"id": "reason-2", "category": "reasoning", "prompt": "Time complexity of binary search?",
     "validators": [{"type": "regex", "value": r"O\(log\s*n\)|logarithmic"}]},
    {"id": "instruct-1", "category": "instruction-follow", "prompt": 'Respond with just the word "hello"',
     "validators": [{"type": "contains", "value": "hello"}]},
    {"id": "multi-1", "category": "multi-step", "prompt": "Read package.json then tell me the entry point",
     "validators": [{"type": "tool-called", "value": "read_file"}]},
    {"id": "multi-2", "category": "multi-step", "prompt": "Check git status then show last 5 commits",
     "validators": [{"type": "tool-called", "value": "bash"}, {"type": "contains", "value": "git"}]},
]


class Evaluator:
    def __init__(self, base_dir: str, ollama_base_url: str):
        self.reports_dir = Path(base_dir) / "eval-reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.client = OllamaClient(ollama_base_url)

    async def evaluate(self, model_name: str, cases=None, on_progress=None) -> dict:
        eval_cases = cases or BUILTIN_CASES
        results = []
        for i, case in enumerate(eval_cases):
            start = time.time()
            try:
                response = await self.client.chat(
                    model=model_name,
                    messages=[
                        ChatMessage(make_id(), "system", "You are a coding assistant with tools.", datetime.now().isoformat()),
                        ChatMessage(make_id(), "user", case["prompt"], datetime.now().isoformat()),
                    ],
                    temperature=0.3,
                )
            except Exception as e:
                response = f"ERROR: {e}"
            latency = int((time.time() - start) * 1000)
            passed, score, details = self._validate(response, case)
            result = {"caseId": case["id"], "category": case["category"], "prompt": case["prompt"],
                      "response": response[:2000], "passed": passed, "score": score, "details": details, "latencyMs": latency}
            results.append(result)
            if on_progress:
                on_progress(i + 1, len(eval_cases), result)

        by_cat: dict[str, dict] = {}
        for r in results:
            cat = r["category"]
            if cat not in by_cat:
                by_cat[cat] = {"total": 0, "passed": 0, "score": 0}
            by_cat[cat]["total"] += 1
            if r["passed"]:
                by_cat[cat]["passed"] += 1
            by_cat[cat]["score"] += r["score"]
        for v in by_cat.values():
            v["score"] = round(v["score"] / v["total"]) if v["total"] else 0

        report = {
            "modelName": model_name, "timestamp": datetime.now().isoformat(),
            "totalCases": len(results), "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"]),
            "avgScore": round(sum(r["score"] for r in results) / len(results)) if results else 0,
            "avgLatencyMs": round(sum(r["latencyMs"] for r in results) / len(results)) if results else 0,
            "byCategory": by_cat, "results": results,
        }
        ts = datetime.now().isoformat().replace(":", "-").replace(".", "-")
        (self.reports_dir / f"eval-{model_name}-{ts}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    async def smoke_test(self, model_name: str) -> dict:
        start = time.time()
        can_chat = can_tool = False
        try:
            resp = await self.client.chat(model=model_name,
                messages=[ChatMessage(make_id(), "user", 'Say "ok"', datetime.now().isoformat())], temperature=0.1)
            can_chat = len(resp) > 0
            tool_resp = await self.client.chat(model=model_name,
                messages=[ChatMessage(make_id(), "user", "Read README.md using your read_file tool.", datetime.now().isoformat())], temperature=0.1)
            _, calls = parse_tool_calls(tool_resp)
            can_tool = len(calls) > 0
        except Exception:
            pass
        return {"alive": can_chat or can_tool, "canChat": can_chat, "canTool": can_tool, "latencyMs": int((time.time() - start) * 1000)}

    def list_reports(self) -> list[dict]:
        results = []
        for f in sorted(self.reports_dir.glob("*.json"), reverse=True):
            try:
                r = json.loads(f.read_text())
                results.append({"model": r["modelName"], "date": r["timestamp"], "score": r["avgScore"], "file": f.name})
            except Exception:
                pass
        return results

    def get_builtin_cases(self) -> list[dict]:
        return list(BUILTIN_CASES)

    def _validate(self, response: str, case: dict) -> tuple[bool, int, str]:
        checks = []
        for v in case.get("validators", []):
            vtype, val = v["type"], v.get("value", "")
            if vtype == "contains":
                checks.append((f'contains "{val}"', val.lower() in response.lower()))
            elif vtype == "tool-called":
                _, calls = parse_tool_calls(response)
                checks.append((f'tool "{val}"', any(c.tool_name == val for c in calls)))
            elif vtype == "no-tool":
                _, calls = parse_tool_calls(response)
                checks.append(("no-tool", len(calls) == 0))
            elif vtype == "regex":
                checks.append((f"regex /{val}/", bool(re.search(val, response, re.I))))
            elif vtype == "code-block":
                checks.append(("code-block", bool(re.search(r"```[\s\S]*?```", response))))
        passed_n = sum(1 for _, p in checks if p)
        total = len(checks)
        all_passed = passed_n == total
        score = round(passed_n / total * 100) if total else 0
        details = "; ".join(f"{'ok' if p else 'FAIL'} {name}" for name, p in checks)
        return all_passed, score, details
