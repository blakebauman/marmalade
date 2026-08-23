#!/usr/bin/env python3
"""Stop: notice when a rendered diagram no longer matches its source.

Exported SVG/PNG files are the copies people actually look at. When a `.mmd`
changes and nobody re-renders, the docs quietly start lying. This compares
modification times at the end of a turn and says so — it never blocks.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hookio import emit, option, read_event  # noqa: E402

RENDERED_EXT = (".svg", ".png", ".pdf")
MAX_LISTED = 6


def main() -> int:
    event = read_event()
    cwd = Path(event.get("cwd") or os.getcwd())
    diagram_dir = cwd / option("diagram_dir", "docs/diagrams")
    export_dir = cwd / option("export_dir", "docs/diagrams/rendered")

    if not diagram_dir.is_dir():
        return 0

    stale: list[str] = []
    unrendered: list[str] = []

    for source in sorted(diagram_dir.rglob("*")):
        if source.suffix.lower() not in (".mmd", ".mermaid") or not source.is_file():
            continue
        try:
            src_mtime = source.stat().st_mtime
        except OSError:
            continue

        renders = []
        for ext in RENDERED_EXT:
            for base in (export_dir, source.parent):
                candidate = base / (source.stem + ext)
                if candidate.is_file():
                    renders.append(candidate)

        if not renders:
            unrendered.append(str(source.relative_to(cwd)))
            continue
        for render in renders:
            try:
                if render.stat().st_mtime < src_mtime - 1:
                    stale.append(f"{source.relative_to(cwd)} → {render.relative_to(cwd)}")
            except OSError:
                continue

    if not stale and not unrendered:
        return 0

    parts = []
    if stale:
        listed = "; ".join(stale[:MAX_LISTED])
        more = f" (+{len(stale) - MAX_LISTED} more)" if len(stale) > MAX_LISTED else ""
        parts.append(f"{len(stale)} rendered diagram(s) older than their source: {listed}{more}")
    if unrendered:
        listed = ", ".join(unrendered[:MAX_LISTED])
        more = f" (+{len(unrendered) - MAX_LISTED} more)" if len(unrendered) > MAX_LISTED else ""
        parts.append(f"{len(unrendered)} source(s) with no rendered output: {listed}{more}")

    emit({"systemMessage": "Marmalade drift check — " + " | ".join(parts) + ". Run /marmalade:export to refresh."})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
