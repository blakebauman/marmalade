#!/usr/bin/env python3
"""SessionStart: tell Claude what the diagram setup in this repo actually is.

Stays silent in repos with no Mermaid, so it costs nothing in the sessions it
has nothing to say about.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hookio import emit, option, read_event  # noqa: E402

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", ".next", "target", "__pycache__"}
DOC_EXT = (".md", ".markdown", ".mdx", ".qmd")
CONFIG_NAMES = (
    ".mermaidrc", ".mermaidrc.json", "mermaid.config.json",
    ".marmalade.json", "mermaid.json", ".puppeteerrc.json",
)
MAX_WALK = 4000


def walk(root: Path):
    seen = 0
    for path in root.rglob("*"):
        if seen > MAX_WALK:
            return
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            seen += 1
            yield path


def main() -> int:
    event = read_event()
    cwd = Path(event.get("cwd") or os.getcwd())
    if not cwd.is_dir():
        return 0

    diagram_dir = option("diagram_dir", "docs/diagrams")
    export_dir = option("export_dir", "docs/diagrams/rendered")

    sources: list[Path] = []
    docs_with_diagrams: list[Path] = []
    configs: list[Path] = []

    for path in walk(cwd):
        name = path.name.lower()
        if path.suffix.lower() in (".mmd", ".mermaid"):
            sources.append(path)
        elif path.suffix.lower() in DOC_EXT:
            try:
                if "```mermaid" in path.read_text(encoding="utf-8", errors="ignore"):
                    docs_with_diagrams.append(path)
            except OSError:
                continue
        elif name in CONFIG_NAMES:
            configs.append(path)

    if not sources and not docs_with_diagrams:
        return 0  # nothing to say

    renderer = "mmdc" if shutil.which("mmdc") else ("npx @mermaid-js/mermaid-cli" if shutil.which("npx") else None)

    lines = ["marmalade — Mermaid setup detected in this repository:"]
    if sources:
        lines.append(f"  • {len(sources)} standalone .mmd/.mermaid source file(s)")
    if docs_with_diagrams:
        lines.append(f"  • {len(docs_with_diagrams)} Markdown file(s) containing ```mermaid blocks")
    if configs:
        lines.append(f"  • Mermaid config present: {', '.join(sorted({c.name for c in configs}))}")
    lines.append(f"  • Configured diagram dir: {diagram_dir}; export dir: {export_dir}")
    lines.append(
        f"  • Renderer available: {renderer}"
        if renderer
        else "  • No Mermaid renderer on PATH. Export needs `npm i -g @mermaid-js/mermaid-cli` or npx."
    )
    lines.append(
        "When editing these diagrams, prefer the marmalade skills (authoring, theming, review, export) over "
        "ad-hoc edits, and keep exported artifacts in step with their sources."
    )

    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n".join(lines),
            }
        }
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
