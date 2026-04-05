"""Agent templates/presets for different project types."""
from __future__ import annotations

AGENT_TEMPLATES = [
    {"id": "fullstack", "name": "Fullstack Developer", "description": "Web projects (Node, React, APIs)",
     "baseModel": "qwen2.5-coder:14b", "temperature": 0.7, "tags": ["web", "node", "react"],
     "systemPrompt": "You are a fullstack development assistant. Help with frontend, backend, databases, and DevOps.\nUse tools proactively. Prefer TypeScript. Write clean, tested code.",
     "tools": ["bash", "read_file", "write_file", "edit_file", "list_dir", "search_files", "glob", "web_fetch", "task", "datetime", "memory_save", "memory_search"]},
    {"id": "python", "name": "Python Developer", "description": "Python, ML, data science, APIs",
     "baseModel": "qwen2.5-coder:14b", "temperature": 0.7, "tags": ["python", "ml"],
     "systemPrompt": "You are a Python specialist. You know pandas, numpy, scikit-learn, FastAPI, Django, pytest.\nUse type hints. Follow PEP 8.",
     "tools": ["bash", "read_file", "write_file", "edit_file", "list_dir", "search_files", "glob", "task", "datetime", "memory_save", "memory_search"]},
    {"id": "rust", "name": "Rust Developer", "description": "Rust systems programming",
     "baseModel": "qwen2.5-coder:14b", "temperature": 0.6, "tags": ["rust", "systems"],
     "systemPrompt": "You are a Rust specialist. You understand ownership, borrowing, lifetimes, traits, async.\nAlways cargo check. Write idiomatic, safe Rust.",
     "tools": ["bash", "read_file", "write_file", "edit_file", "list_dir", "search_files", "glob", "task", "datetime", "memory_save", "memory_search"]},
    {"id": "go", "name": "Go Developer", "description": "Go microservices, CLIs, infrastructure",
     "baseModel": "qwen2.5-coder:14b", "temperature": 0.6, "tags": ["go", "microservices"],
     "systemPrompt": "You are a Go specialist. You know the standard library, Gin, Echo, cobra, viper.\nWrite idiomatic Go. Run go vet and tests.",
     "tools": ["bash", "read_file", "write_file", "edit_file", "list_dir", "search_files", "glob", "task", "datetime", "memory_save", "memory_search"]},
    {"id": "devops", "name": "DevOps Engineer", "description": "Docker, K8s, CI/CD, cloud",
     "baseModel": "qwen2.5-coder:14b", "temperature": 0.5, "tags": ["devops", "docker"],
     "systemPrompt": "You are a DevOps assistant. Docker, Kubernetes, CI/CD, Terraform, Ansible.\nConsider security, cost, reliability.",
     "tools": ["bash", "read_file", "write_file", "edit_file", "list_dir", "search_files", "glob", "web_fetch", "task", "datetime", "memory_save", "memory_search"]},
    {"id": "minimal", "name": "Minimal Assistant", "description": "Lightweight, fast, 7B model",
     "baseModel": "qwen2.5-coder:7b", "temperature": 0.5, "tags": ["minimal", "fast"],
     "systemPrompt": "You are a concise coding assistant. Be brief and direct.",
     "tools": ["bash", "read_file", "write_file", "edit_file", "list_dir", "search_files", "glob"]},
    {"id": "reviewer", "name": "Code Reviewer", "description": "Code review, quality, security",
     "baseModel": "qwen2.5-coder:14b", "temperature": 0.4, "tags": ["review", "security"],
     "systemPrompt": "You are a senior code reviewer. Focus on bugs, security, performance, style.\nCite line numbers. Prioritize by severity.",
     "tools": ["read_file", "list_dir", "search_files", "glob", "bash", "task", "memory_save", "memory_search"]},
    {"id": "docs", "name": "Documentation Writer", "description": "READMEs, API docs, inline comments",
     "baseModel": "qwen2.5-coder:7b", "temperature": 0.6, "tags": ["docs", "readme"],
     "systemPrompt": "You are a documentation specialist. Write clear, concise technical docs.\nRead code first. Use examples.",
     "tools": ["read_file", "write_file", "edit_file", "list_dir", "search_files", "glob", "bash", "task", "memory_save", "memory_search"]},
]


def get_template(tid: str) -> dict | None:
    return next((t for t in AGENT_TEMPLATES if t["id"] == tid), None)


def list_templates() -> list[dict]:
    return list(AGENT_TEMPLATES)
