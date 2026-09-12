#!/usr/bin/env python3
"""Stop: notice when a diagram *this session changed* no longer matches its render.

Exported SVG/PNG files are the copies people actually look at, so a `.mmd` that
changes without a re-render makes the docs quietly lie.

The first version of this check compared every source in the tree on every turn.
In a repo that renders a subset of its diagrams -- the normal case -- that is the
same paragraph after every turn, forever, including in sessions that never opened
a diagram. A notice nobody can act on is one nobody reads, so this now speaks only
about sources the working tree has actually changed, says a given drift once per
session rather than once per turn, and turns off entirely with `drift_check`.

It never blocks.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hookio import emit, flag, option, read_event  # noqa: E402

RENDERED_EXT = (".svg", ".png", ".pdf")
SOURCE_EXT = (".mmd", ".mermaid")
MAX_LISTED = 6


def changed_sources(cwd: Path):
    """Diagram sources this working tree has modified, or None outside a git tree.

    Modified-or-untracked is the tool-agnostic way to ask "is someone working on
    this?" -- it holds whether the edit came from Write, a `sed` in a shell, or an
    editor in another window, where a record of Claude's own tool calls would not.
    """
    try:
        top = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if top.returncode != 0:
            return None
        root = Path(top.stdout.strip())
        names = []
        for args in (["diff", "--name-only", "HEAD"], ["ls-files", "--others", "--exclude-standard"]):
            proc = subprocess.run(
                ["git", "-C", str(cwd)] + args, capture_output=True, text=True, timeout=10
            )
            if proc.returncode == 0:
                names.extend(proc.stdout.splitlines())
    except (OSError, subprocess.SubprocessError):
        return None
    return {(root / name).resolve() for name in names if name.strip()}


def already_said(session_id: str, parts: list) -> bool:
    """True once a session has reported this exact drift set, so it is said once."""
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]
    state = Path(tempfile.gettempdir()) / f"marmalade-drift-{session_id}"
    try:
        seen = state.read_text(encoding="utf-8").split() if state.is_file() else []
        if digest in seen:
            return True
        with state.open("a", encoding="utf-8") as fh:
            fh.write(digest + "\n")
    except OSError:
        return False
    return False


def main() -> int:
    event = read_event()
    if not flag("drift_check", True):
        return 0

    cwd = Path(event.get("cwd") or os.getcwd())
    diagram_dir = cwd / option("diagram_dir", "docs/diagrams")
    export_dir = cwd / option("export_dir", "docs/diagrams/rendered")

    if not diagram_dir.is_dir():
        return 0

    touched = changed_sources(cwd)
    stale: list = []
    unrendered: list = []

    for source in sorted(diagram_dir.rglob("*")):
        if source.suffix.lower() not in SOURCE_EXT or not source.is_file():
            continue
        if touched is not None and source.resolve() not in touched:
            continue  # someone else's diagram, or one nobody is working on
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
            # Outside git there is no way to tell a diagram added this session from
            # one the repo has deliberately never rendered, so only the first is worth
            # a word and only a git tree can identify it.
            if touched is not None:
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
        parts.append(f"{len(unrendered)} new source(s) with no rendered output: {listed}{more}")

    if already_said(str(event.get("session_id") or "nosession"), parts):
        return 0

    emit({"systemMessage": "Marmalade drift check — " + " | ".join(parts) + ". Run /marmalade:export to refresh."})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
