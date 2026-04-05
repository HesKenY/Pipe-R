"""Model building: Modelfile generation and Ollama model creation."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass


TOOL_INSTRUCTIONS = """You have tools: bash, read_file, write_file, edit_file, list_dir, search_files, glob, web_fetch, task, datetime, memory_save, memory_search.
To call tools, respond with a fenced block:
```tool
{"toolCalls":[{"toolName":"bash","input":{"command":"ls -la"}}]}
```
You can chain multiple tool calls. After receiving results, analyze and continue.
Be concise, precise, and thorough."""

RECOMMENDED_BASES = [
    {"name": "qwen2.5-coder:7b", "size": "7B", "family": "Qwen"},
    {"name": "qwen2.5-coder:14b", "size": "14B", "family": "Qwen"},
    {"name": "qwen2.5-coder:32b", "size": "32B", "family": "Qwen"},
    {"name": "codellama:7b", "size": "7B", "family": "Llama"},
    {"name": "codellama:13b", "size": "13B", "family": "Llama"},
    {"name": "deepseek-coder-v2:16b", "size": "16B", "family": "DeepSeek"},
    {"name": "starcoder2:7b", "size": "7B", "family": "StarCoder"},
    {"name": "llama3.1:8b", "size": "8B", "family": "Llama"},
    {"name": "mistral:7b", "size": "7B", "family": "Mistral"},
    {"name": "gemma2:9b", "size": "9B", "family": "Gemma"},
    {"name": "phi3:14b", "size": "14B", "family": "Phi"},
]


@dataclass
class BuildResult:
    success: bool
    model_name: str
    message: str
    duration: float = 0.0


class ModelBuilder:
    def __init__(self, base_dir: str):
        self.profiles_dir = Path(base_dir) / "profiles"
        self.models_dir = Path(base_dir) / "models"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def create_profile(self, name: str, base_model: str, system_prompt: str | None = None,
                       description: str = "", temperature: float = 0.7, num_ctx: int = 32768,
                       dataset_name: str | None = None, tool_instructions: bool = True, **kwargs) -> dict:
        profile = {
            "name": name, "baseModel": base_model,
            "systemPrompt": system_prompt or f"You are {name}, a highly capable AI coding assistant. Use tools proactively.",
            "temperature": temperature, "numCtx": num_ctx, "topK": 40, "topP": 0.9,
            "repeatPenalty": 1.1, "description": description, "tags": [],
            "created": datetime.now().isoformat(), "built": False,
            "toolInstructions": tool_instructions, "datasetName": dataset_name,
        }
        (self.profiles_dir / f"{name}.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return profile

    def get_profile(self, name: str) -> dict | None:
        p = self.profiles_dir / f"{name}.json"
        return json.loads(p.read_text()) if p.exists() else None

    def list_profiles(self) -> list[dict]:
        results = []
        for f in self.profiles_dir.glob("*.json"):
            try:
                results.append(json.loads(f.read_text()))
            except Exception:
                pass
        return sorted(results, key=lambda x: x.get("created", ""), reverse=True)

    def delete_profile(self, name: str) -> bool:
        p = self.profiles_dir / f"{name}.json"
        if p.exists():
            p.unlink()
            return True
        return False

    def generate_modelfile(self, profile: dict, examples: list[dict] | None = None) -> str:
        lines = [f"FROM {profile['baseModel']}", ""]
        system = profile["systemPrompt"]
        if profile.get("toolInstructions", True):
            system += "\n\n" + TOOL_INSTRUCTIONS
        if examples:
            system += "\n\n## Example Interactions\n"
            for ex in examples[:10]:
                system += f"\nUser: {ex.get('prompt', '')[:200]}\nAssistant: {ex.get('completion', '')[:400]}\n"
        lines.append(f'SYSTEM """{system}"""')
        lines.append("")
        lines.append(f"PARAMETER num_ctx {profile.get('numCtx', 32768)}")
        lines.append(f"PARAMETER temperature {profile.get('temperature', 0.7)}")
        lines.append(f"PARAMETER top_k {profile.get('topK', 40)}")
        lines.append(f"PARAMETER top_p {profile.get('topP', 0.9)}")
        lines.append(f"PARAMETER repeat_penalty {profile.get('repeatPenalty', 1.1)}")
        if examples:
            lines.append("")
            for ex in examples[:20]:
                safe_p = ex.get("prompt", "").replace('"""', '""')
                safe_c = ex.get("completion", "").replace('"""', '""')
                lines.append(f'MESSAGE user """{safe_p}"""')
                lines.append(f'MESSAGE assistant """{safe_c}"""')
        return "\n".join(lines) + "\n"

    async def build_model(self, profile_name: str, dataset_manager=None) -> BuildResult:
        profile = self.get_profile(profile_name)
        if not profile:
            return BuildResult(False, profile_name, "Profile not found")
        examples = None
        if profile.get("datasetName") and dataset_manager:
            ds = dataset_manager.get_dataset(profile["datasetName"])
            if ds:
                examples = ds["examples"]
        modelfile = self.generate_modelfile(profile, examples)
        mf_path = self.models_dir / f"Modelfile-{profile['name']}"
        mf_path.write_text(modelfile, encoding="utf-8")
        import asyncio
        import time
        start = time.time()
        try:
            await asyncio.to_thread(
                subprocess.run,
                ["ollama", "create", profile["name"], "-f", str(mf_path)],
                capture_output=True, text=True, timeout=300, check=True,
            )
            profile["built"] = True
            (self.profiles_dir / f"{profile['name']}.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
            return BuildResult(True, profile["name"],
                               f'Model "{profile["name"]}" built from {profile["baseModel"]}',
                               time.time() - start)
        except Exception as e:
            return BuildResult(False, profile["name"], f"Build failed: {e}", time.time() - start)

    async def pull_base_model(self, model: str) -> dict:
        import asyncio
        try:
            await asyncio.to_thread(
                subprocess.run,
                ["ollama", "pull", model],
                capture_output=True, text=True, timeout=600, check=True,
            )
            return {"success": True, "message": f"Pulled {model}"}
        except Exception as e:
            return {"success": False, "message": f"Pull failed: {e}"}

    def list_local_models(self) -> list[dict]:
        try:
            r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
            lines = r.stdout.strip().split("\n")[1:]
            results = []
            for line in lines:
                parts = line.split()
                if parts:
                    results.append({"name": parts[0], "size": parts[2] if len(parts) > 2 else "", "modified": " ".join(parts[3:]) if len(parts) > 3 else ""})
            return results
        except Exception:
            return []

    def delete_model(self, name: str) -> dict:
        try:
            subprocess.run(["ollama", "rm", name], capture_output=True, text=True, timeout=30, check=True)
            return {"success": True, "message": f'Deleted "{name}"'}
        except Exception as e:
            return {"success": False, "message": f"Delete failed: {e}"}

    def get_recommended_bases(self) -> list[dict]:
        return RECOMMENDED_BASES

    def get_modelfile(self, name: str) -> str | None:
        p = self.models_dir / f"Modelfile-{name}"
        return p.read_text() if p.exists() else None
