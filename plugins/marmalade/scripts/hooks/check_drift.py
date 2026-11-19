#!/usr/bin/env python3
"""Stop: notice when a rendered diagram no longer matches its source.

Exported SVG/PNG files are the copies people actually look at. When a `.mmd`
changes and nobody re-renders, the docs quietly start lying. This says so at
the end of a turn — it never blocks.

When the export manifest is present, drift is judged the way the exporter
judges it: by content hash. Modification times are only a fallback for a
directory that was never exported through Marmalade, because a fresh clone
gives every file the same arbitrary timestamp.

The same finding is reported once per session, not at the end of every turn.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _hookio import emit, option, read_event  # noqa: E402

from fswalk import sorted_files  # noqa: E402

RENDERED_EXT = (".svg", ".png", ".pdf")
SOURCE_EXT = (".mmd", ".mermaid")
MAX_LISTED = 6


def rel(path: Path, cwd: Path) -> str:
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)


def drift_by_manifest(cwd: Path, diagram_dir: Path, export_dir: Path, entries: dict):
    from marmalade_export import build_jobs, collect, dedupe_stems

    jobs = build_jobs(collect([str(diagram_dir)]))
    dedupe_stems(jobs)
    stale: list[str] = []
    unrendered: list[str] = []
    for job in jobs:
        keys = [
            job.stem + ext for ext in RENDERED_EXT
            if (job.stem + ext) in entries or (export_dir / (job.stem + ext)).is_file()
        ]
        source = rel(job.source_path, cwd)
        if not keys:
            unrendered.append(source if job.block.origin == "file" else f"{source} ({job.stem})")
            continue
        for key in keys:
            recorded = entries.get(key) or {}
            if recorded.get("digest") != job.digest or not (export_dir / key).is_file():
                stale.append(f"{source} → {rel(export_dir / key, cwd)}")
    return stale, unrendered


def drift_by_mtime(cwd: Path, diagram_dir: Path, export_dir: Path):
    stale: list[str] = []
    unrendered: list[str] = []
    for source in sorted_files(diagram_dir, SOURCE_EXT):
        try:
            src_mtime = source.stat().st_mtime
        except OSError:
            continue
        renders = [
            base / (source.stem + ext)
            for ext in RENDERED_EXT
            for base in (export_dir, source.parent)
            if (base / (source.stem + ext)).is_file()
        ]
        if not renders:
            unrendered.append(rel(source, cwd))
            continue
        for render in renders:
            try:
                if render.stat().st_mtime < src_mtime - 1:
                    stale.append(f"{rel(source, cwd)} → {rel(render, cwd)}")
            except OSError:
                continue
    return stale, unrendered


def already_reported(event: dict, message: str) -> bool:
    """True when this exact finding was already shown in this session."""
    session = str(event.get("session_id") or "")
    if not session:
        return False
    key = hashlib.sha256(session.encode("utf-8")).hexdigest()[:16]
    marker = Path(tempfile.gettempdir()) / f"marmalade-drift-{key}"
    digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
    try:
        if marker.read_text(encoding="utf-8") == digest:
            return True
    except OSError:
        pass
    try:
        marker.write_text(digest, encoding="utf-8")
    except OSError:
        pass
    return False


def main() -> int:
    event = read_event()
    cwd = Path(event.get("cwd") or os.getcwd())
    diagram_dir = cwd / option("diagram_dir", "docs/diagrams")
    export_dir = cwd / option("export_dir", "docs/diagrams/rendered")

    if not diagram_dir.is_dir():
        return 0

    from marmalade_export import MANIFEST_NAME

    try:
        manifest = json.loads((export_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
        entries = manifest.get("entries")
    except Exception:
        entries = None

    if isinstance(entries, dict):
        stale, unrendered = drift_by_manifest(cwd, diagram_dir, export_dir, entries)
    else:
        stale, unrendered = drift_by_mtime(cwd, diagram_dir, export_dir)

    if not stale and not unrendered:
        return 0

    parts = []
    if stale:
        listed = "; ".join(stale[:MAX_LISTED])
        more = f" (+{len(stale) - MAX_LISTED} more)" if len(stale) > MAX_LISTED else ""
        parts.append(f"{len(stale)} rendered diagram(s) out of date with their source: {listed}{more}")
    if unrendered:
        listed = ", ".join(unrendered[:MAX_LISTED])
        more = f" (+{len(unrendered) - MAX_LISTED} more)" if len(unrendered) > MAX_LISTED else ""
        parts.append(f"{len(unrendered)} source(s) with no rendered output: {listed}{more}")

    message = "Marmalade drift check — " + " | ".join(parts) + ". Run /marmalade:export to refresh."
    if already_reported(event, message):
        return 0
    emit({"systemMessage": message})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
