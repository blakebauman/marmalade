#!/usr/bin/env python3
"""Lint Mermaid sources: `.mmd`/`.mermaid` files and fenced blocks in Markdown.

    marmalade_lint.py [paths...] [--json] [--errors-only] [--quiet]

With no paths, reads the diagram directory from MARMALADE_DIAGRAM_DIR (default
`docs/diagrams`) and walks it. Exit 1 if any error-severity finding was
reported, 0 otherwise; warnings never fail the run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from mermaid_lint import Finding, extract_blocks, lint  # noqa: E402

SCANNABLE = (".mmd", ".mermaid", ".md", ".markdown", ".mdx", ".qmd")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", ".next", "target", "__pycache__"}

SEVERITY_ICON = {"error": "✗", "warning": "!", "info": "·"}


def iter_paths(roots: list[str]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        p = Path(root)
        if p.is_file():
            found.append(p)
            continue
        if not p.is_dir():
            continue
        for child in sorted(p.rglob("*")):
            if any(part in SKIP_DIRS for part in child.parts):
                continue
            if child.is_file() and child.suffix.lower() in SCANNABLE:
                found.append(child)
    return found


def lint_path(path: Path) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    findings: list[Finding] = []
    for block in extract_blocks(str(path), text):
        findings.extend(lint(block))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint Mermaid diagram sources.")
    ap.add_argument("paths", nargs="*", help="Files or directories. Defaults to the configured diagram directory.")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    ap.add_argument("--errors-only", action="store_true", help="Suppress warnings and info.")
    ap.add_argument("--quiet", action="store_true", help="Print nothing; use the exit code.")
    args = ap.parse_args()

    roots = args.paths or [os.environ.get("MARMALADE_DIAGRAM_DIR", "docs/diagrams")]
    results: dict[str, list[Finding]] = {}
    for path in iter_paths(roots):
        found = lint_path(path)
        if args.errors_only:
            found = [f for f in found if f.severity == "error"]
        if found:
            results[str(path)] = found

    error_count = sum(1 for fs in results.values() for f in fs if f.severity == "error")
    warn_count = sum(1 for fs in results.values() for f in fs if f.severity == "warning")

    if args.quiet:
        return 1 if error_count else 0

    if args.json:
        payload = {
            "errors": error_count,
            "warnings": warn_count,
            "files": {
                path: [
                    {"line": f.line, "severity": f.severity, "code": f.code, "message": f.message, "hint": f.hint}
                    for f in fs
                ]
                for path, fs in results.items()
            },
        }
        print(json.dumps(payload, indent=2))
        return 1 if error_count else 0

    if not results:
        print("No Mermaid findings.")
        return 0

    for path, fs in results.items():
        print(f"\n{path}")
        for f in fs:
            icon = SEVERITY_ICON.get(f.severity, "·")
            print(f"  {icon} {path}:{f.line}  {f.code}  {f.message}")
            if f.hint:
                print(f"      → {f.hint}")
    print(f"\n{error_count} error(s), {warn_count} warning(s).")
    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
