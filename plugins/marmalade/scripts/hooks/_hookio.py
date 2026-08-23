"""Shared plumbing for marmalade hooks.

Hooks run inside someone's editing session. The contract every script here
follows: read stdin, do one small job, and never crash the session. Any
unexpected exception exits 0 silently.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))


def read_event() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def option(key: str, default: str = "") -> str:
    """Read a plugin userConfig value, which arrives as CLAUDE_PLUGIN_OPTION_<KEY>."""
    return os.environ.get(f"CLAUDE_PLUGIN_OPTION_{key.upper()}", default)


def flag(key: str, default: bool = True) -> bool:
    raw = option(key, "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def emit(payload: dict) -> None:
    print(json.dumps(payload))


def edited_paths(event: dict) -> list[str]:
    """File paths a Write/Edit-family tool call touched."""
    tool_input = event.get("tool_input") or {}
    paths: list[str] = []
    for key in ("file_path", "filePath", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            paths.append(value)
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict) and isinstance(edit.get("file_path"), str):
            paths.append(edit["file_path"])
    seen, unique = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def written_text(event: dict, path: str) -> str | None:
    """Best-effort content of a file after the tool call.

    Prefers reading from disk (PostToolUse), falls back to the tool input
    payload (PreToolUse, where the write has not happened yet).
    """
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass
    tool_input = event.get("tool_input") or {}
    for key in ("content", "new_string", "new_str"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return None


def is_diagram_carrier(path: str) -> bool:
    return path.lower().endswith((".mmd", ".mermaid", ".md", ".markdown", ".mdx", ".qmd"))
