"""Filesystem and ID utilities."""
from __future__ import annotations
import json
import uuid
from pathlib import Path


def make_id() -> str:
    return str(uuid.uuid4())


def short_id() -> str:
    return uuid.uuid4().hex[:8]


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_json(path: str | Path, value: object) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def read_json(path: str | Path) -> dict | list | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def file_exists(path: str | Path) -> bool:
    return Path(path).exists()


def list_files(directory: str | Path) -> list[str]:
    try:
        return [f.name for f in Path(directory).iterdir()]
    except Exception:
        return []


def base36_now() -> str:
    import time
    return base36(int(time.time() * 1000))


def base36(n: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    result = []
    while n:
        result.append(chars[n % 36])
        n //= 36
    return "".join(reversed(result))
