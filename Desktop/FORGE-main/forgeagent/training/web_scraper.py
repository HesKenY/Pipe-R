"""Web scraping for training data collection."""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
from datetime import datetime
from .dataset_manager import DatasetManager, TrainingExample, _uid

CURATED_SOURCES: dict[str, list[dict]] = {
    "typescript": [
        {"url": "https://raw.githubusercontent.com/microsoft/TypeScript/main/README.md", "type": "docs", "label": "TypeScript README"},
        {"url": "https://raw.githubusercontent.com/sindresorhus/type-fest/main/readme.md", "type": "docs", "label": "type-fest"},
    ],
    "node": [
        {"url": "https://raw.githubusercontent.com/nodejs/node/main/README.md", "type": "docs", "label": "Node.js README"},
        {"url": "https://raw.githubusercontent.com/expressjs/express/master/Readme.md", "type": "docs", "label": "Express"},
    ],
    "python": [
        {"url": "https://raw.githubusercontent.com/tiangolo/fastapi/master/README.md", "type": "docs", "label": "FastAPI"},
        {"url": "https://raw.githubusercontent.com/pallets/flask/main/README.md", "type": "docs", "label": "Flask"},
    ],
    "react": [
        {"url": "https://raw.githubusercontent.com/facebook/react/main/README.md", "type": "docs", "label": "React"},
        {"url": "https://raw.githubusercontent.com/vercel/next.js/canary/readme.md", "type": "docs", "label": "Next.js"},
    ],
    "rust": [
        {"url": "https://raw.githubusercontent.com/tokio-rs/tokio/master/README.md", "type": "docs", "label": "Tokio"},
        {"url": "https://raw.githubusercontent.com/serde-rs/serde/master/README.md", "type": "docs", "label": "Serde"},
    ],
    "devops": [
        {"url": "https://raw.githubusercontent.com/docker/compose/main/README.md", "type": "docs", "label": "Docker Compose"},
        {"url": "https://raw.githubusercontent.com/hashicorp/terraform/main/README.md", "type": "docs", "label": "Terraform"},
    ],
}


class WebScrapeCollector:
    def __init__(self, base_dir: str):
        self.cache_dir = Path(base_dir) / "scrape-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_url(self, url: str, force: bool = False) -> str:
        cache_key = hashlib.sha256(url.encode()).hexdigest()[:40]
        cache_path = self.cache_dir / f"{cache_key}.txt"
        if not force and cache_path.exists():
            return cache_path.read_text(encoding="utf-8")
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers={"User-Agent": "ForgeAgent/3.0"})
            resp.raise_for_status()
            text = resp.text
            cache_path.write_text(text, encoding="utf-8")
            return text

    async def scrape_to_dataset(self, dm: DatasetManager, dataset_name: str, source: dict) -> dict:
        try:
            content = await self.fetch_url(source["url"])
            examples = self._parse_markdown(content, source)
            for ex in examples:
                dm.add_example(dataset_name, ex)
            return {"source": source, "examples": len(examples)}
        except Exception as e:
            return {"source": source, "examples": 0, "error": str(e)}

    async def scrape_topic(self, dm: DatasetManager, dataset_name: str, topic: str, on_progress=None) -> list[dict]:
        sources = CURATED_SOURCES.get(topic)
        if not sources:
            raise ValueError(f"Unknown topic: {topic}. Available: {', '.join(CURATED_SOURCES)}")
        results = []
        for i, src in enumerate(sources):
            r = await self.scrape_to_dataset(dm, dataset_name, src)
            results.append(r)
            if on_progress:
                on_progress(i + 1, len(sources), r)
        return results

    async def scrape_github_repo(self, dm: DatasetManager, dataset_name: str, repo_url: str) -> list[dict]:
        import re
        m = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
        if not m:
            raise ValueError("Invalid GitHub URL")
        owner, repo = m.group(1), m.group(2)
        sources = [
            {"url": f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md", "type": "docs", "label": f"{repo} README"},
            {"url": f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md", "type": "docs", "label": f"{repo} README"},
        ]
        results = []
        for src in sources:
            try:
                r = await self.scrape_to_dataset(dm, dataset_name, src)
                if not r.get("error"):
                    results.append(r)
            except Exception:
                pass
        return results

    def get_topics(self) -> list[str]:
        return list(CURATED_SOURCES.keys())

    def _parse_markdown(self, md: str, source: dict) -> list[TrainingExample]:
        examples = []
        sections = md.split("\n## ")
        for section in sections:
            if len(section.strip()) < 50:
                continue
            lines = section.split("\n")
            heading = lines[0].strip().lstrip("#").strip() or "Overview"
            body = "\n".join(lines[1:]).strip()
            if len(body) < 30:
                continue
            label = source.get("label", source.get("url", ""))
            has_code = "```" in body
            if has_code:
                prompt = f"How do I use {heading.lower()} from {label}?"
            else:
                prompt = f"Explain {heading.lower()} in {label}."
            examples.append(TrainingExample(
                id=_uid(), prompt=prompt, completion=body[:3000],
                tags=["docs", "scraped"], source="codebase",
            ))
        return examples
