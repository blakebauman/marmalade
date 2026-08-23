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


def main() -> int:
    event = read_event()
    strict = flag("strict_validation", True)

    errors: list[str] = []
    warnings: list[str] = []

    for path in edited_paths(event):
        if not is_diagram_carrier(path):
            continue
        text = written_text(event, path)
        if text is None:
            continue
        for block in extract_blocks(path, text):
            for f in lint(block):
                line = f"{path}:{f.line}  {f.code}  {f.message}"
                if f.hint:
                    line += f"\n    → {f.hint}"
                (errors if f.severity == "error" else warnings if f.severity == "warning" else []).append(line)

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
