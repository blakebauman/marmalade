#!/usr/bin/env python3
"""PostToolUse: lint Mermaid that Claude just wrote.

Syntax errors block (when strict_validation is on) so a broken diagram is fixed
in the same turn rather than discovered at render time. Legibility and
accessibility warnings surface as a notice and never block.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hookio import edited_paths, emit, flag, is_diagram_carrier, read_event, written_text  # noqa: E402

from mermaid_lint import extract_blocks, lint  # noqa: E402

MAX_REPORTED = 12


def _lint_cli() -> str:
    """Absolute path to the lint CLI, for a message the reader can copy and run."""
    return str(Path(__file__).resolve().parent.parent / "marmalade_lint.py")


def edit_fragments(event: dict):
    """The replacement strings of an Edit, or None for a whole-file write."""
    tool_input = event.get("tool_input") or {}
    if isinstance(tool_input.get("content"), str):
        return None
    fragments = [tool_input.get(k) for k in ("new_string", "new_str")]
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict):
            fragments.append(edit.get("new_string"))
    fragments = [f for f in fragments if isinstance(f, str)]
    return fragments or None


def touched_by(block, fragments) -> bool:
    """Whether an edit plausibly changed this fenced block.

    A Markdown file can hold many diagrams. An edit to one of them, or to the
    prose between them, must not be blocked over an error that was already
    sitting in another.
    """
    if fragments is None or block.origin == "file":
        return True
    block_lines = {line.strip() for line in block.lines if line.strip()}
    for fragment in fragments:
        if any(line.strip() in block_lines for line in fragment.splitlines() if line.strip()):
            return True
    return False


def main() -> int:
    event = read_event()
    strict = flag("strict_validation", True)

    errors: list[str] = []
    warnings: list[str] = []
    fragments = edit_fragments(event)

    for path in edited_paths(event):
        if not is_diagram_carrier(path):
            continue
        text = written_text(event, path)
        if text is None:
            continue
        for block in extract_blocks(path, text):
            ours = touched_by(block, fragments)
            for f in lint(block):
                line = f"{path}:{f.line}  {f.code}  {f.message}"
                if f.hint:
                    line += f"\n    → {f.hint}"
                if f.severity == "error" and ours:
                    errors.append(line)
                elif f.severity == "error":
                    warnings.append(line + "  (already present; not from this edit)")
                elif f.severity == "warning":
                    warnings.append(line)

    if not errors and not warnings:
        return 0

    if errors and strict:
        detail = "\n".join(errors[:MAX_REPORTED])
        more = f"\n(+{len(errors) - MAX_REPORTED} more)" if len(errors) > MAX_REPORTED else ""
        emit(
            {
                "decision": "block",
                "reason": (
                    "Mermaid validation failed — this diagram will not render:\n"
                    f"{detail}{more}\n\n"
                    f"Fix the source and write it again. Run `{_lint_cli()} <file>` to recheck."
                ),
            }
        )
        return 0

    parts = []
    if errors:
        parts.append(f"{len(errors)} Mermaid syntax error(s): " + "; ".join(e.splitlines()[0] for e in errors[:3]))
    if warnings:
        parts.append(
            f"{len(warnings)} Mermaid quality warning(s): "
            + "; ".join(w.splitlines()[0] for w in warnings[:3])
        )
    emit({"systemMessage": "marmalade: " + " | ".join(parts)})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
