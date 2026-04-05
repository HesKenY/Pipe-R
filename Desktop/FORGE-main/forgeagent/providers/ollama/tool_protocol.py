"""Tool call parsing and instruction building for Ollama models."""
from __future__ import annotations
import json
import re
from ...core.interfaces import Tool, ToolCall


def build_tool_instructions(tools: list[Tool]) -> str:
    if not tools:
        return ""
    schemas = []
    for t in tools:
        d = t.definition
        schemas.append(f"### {d.name}\n{d.description}\nSchema: {json.dumps(d.input_schema)}")

    return "\n".join([
        "## Tool Use — CRITICAL",
        "You MUST use tools to complete tasks. Do NOT just describe what to do — actually DO it using tools.",
        "ALWAYS respond with a tool call block to take action. Never explain without acting.",
        "",
        "To call tools, wrap JSON in a ```tool fenced block:",
        "",
        "```tool",
        '{"toolCalls":[{"toolName":"tool_name","input":{"key":"value"}}]}',
        "```",
        "",
        "RULES:",
        "- To create or modify code: use write_file or edit_file. Do NOT just show code in your response.",
        "- To run commands: use bash. Do NOT just say 'run this command'.",
        "- To read files before editing: use read_file first.",
        "- To find files: use list_dir, glob, or search_files.",
        "- You can call multiple tools in one response.",
        "- After receiving tool results, call more tools or give a final summary.",
        "- If a task says 'create a file', you MUST use write_file to actually create it.",
        "",
        "## Available Tools",
        "\n\n".join(schemas),
    ])


def parse_tool_calls(raw: str) -> tuple[str | None, list[ToolCall]]:
    """Parse tool calls from model output. Returns (assistant_text, tool_calls)."""
    # Try ```tool fenced block
    match = re.search(r"```tool\s*\n?([\s\S]*?)```", raw)
    if match:
        before = raw[:raw.index("```tool")].strip()
        try:
            parsed = json.loads(match.group(1).strip())
            # Single tool shorthand
            if "toolName" in parsed and "toolCalls" not in parsed:
                return (
                    before or parsed.get("assistant"),
                    [ToolCall(tool_name=parsed["toolName"], input=parsed.get("input", {}))],
                )
            calls = [
                ToolCall(tool_name=tc["toolName"], input=tc.get("input", {}))
                for tc in parsed.get("toolCalls", [])
            ]
            return before or parsed.get("assistant"), calls
        except (json.JSONDecodeError, KeyError):
            return raw, []

    # Try raw JSON
    trimmed = raw.strip()
    if trimmed.startswith("{") and "toolCalls" in trimmed:
        try:
            parsed = json.loads(trimmed)
            calls = [
                ToolCall(tool_name=tc["toolName"], input=tc.get("input", {}))
                for tc in parsed.get("toolCalls", [])
            ]
            return parsed.get("assistant"), calls
        except (json.JSONDecodeError, KeyError):
            pass

    return raw, []
