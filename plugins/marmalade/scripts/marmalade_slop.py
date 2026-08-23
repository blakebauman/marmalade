#!/usr/bin/env python3
"""Score Mermaid diagrams against the no-slop rubric.

    marmalade_slop.py docs/diagrams --detail balanced --min-score 70

Detail levels set the node budget: simplified (7), balanced (12), faithful (24).
Exit 1 when any diagram scores below --min-score, so this works as a CI gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from mermaid_lint import extract_blocks  # noqa: E402
from slop import BUDGETS, DEFAULT_DETAIL, check  # noqa: E402

SCANNABLE = (".mmd", ".mermaid", ".md", ".markdown", ".mdx", ".qmd")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", ".next", "target", "__pycache__"}
ICON = {"error": "✗", "warning": "!", "info": "·"}


def collect(roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        p = Path(root)
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            for child in sorted(p.rglob("*")):
                if any(part in SKIP_DIRS for part in child.parts):
                    continue
                if child.is_file() and child.suffix.lower() in SCANNABLE:
                    files.append(child)
    return files


def verdict(score: int) -> str:
    if score >= 90:
        return "clean"
    if score >= 70:
        return "acceptable"
    if score >= 40:
        return "slop-leaning"
    return "slop"


def main() -> int:
    ap = argparse.ArgumentParser(description="Score Mermaid diagrams against the no-slop rubric.")
    ap.add_argument("paths", nargs="*", help="Files or directories. Defaults to the configured diagram directory.")
    ap.add_argument("--detail", default=os.environ.get("MARMALADE_DETAIL", DEFAULT_DETAIL),
                    choices=sorted(BUDGETS), help=f"Density budget. Default {DEFAULT_DETAIL}.")
    ap.add_argument("--min-score", type=int, default=0, help="Exit 1 if any diagram scores below this.")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable results.")
    ap.add_argument("--quiet", action="store_true", help="Only print diagrams that fall below --min-score.")
    args = ap.parse_args()

    roots = args.paths or [os.environ.get("MARMALADE_DIAGRAM_DIR", "docs/diagrams")]
    results = []

    for path in collect(roots):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for index, block in enumerate(extract_blocks(str(path), text), start=1):
            report = check(block, args.detail)
            label = str(path) if block.origin == "file" else f"{path}#{index}"
            results.append((label, report))

    if not results:
        print(f"No Mermaid diagrams found under: {', '.join(roots)}")
        return 0

    failing = [(label, r) for label, r in results if r.score < args.min_score]

    if args.json:
        print(json.dumps({
            "detail": args.detail,
            "budget": BUDGETS[args.detail],
            "diagrams": [
                {
                    "id": label,
                    "score": r.score,
                    "verdict": verdict(r.score),
                    "nodes": r.node_count,
                    "edges": r.edge_count,
                    "findings": [
                        {"line": f.line, "severity": f.severity, "code": f.code,
                         "message": f.message, "hint": f.hint}
                        for f in r.findings
                    ],
                }
                for label, r in results
            ],
        }, indent=2))
        return 1 if failing else 0

    shown = failing if args.quiet else results
    for label, report in shown:
        print(f"\n{label}  —  {report.score}/100 ({verdict(report.score)}), "
              f"{report.node_count} nodes / {report.edge_count} edges, budget {report.budget}")
        for f in report.findings:
            print(f"  {ICON.get(f.severity, '·')} line {f.line}  {f.code}  {f.message}")
            if f.hint:
                print(f"      → {f.hint}")
        if not report.findings:
            print("  (no findings)")

    average = sum(r.score for _l, r in results) // len(results)
    print(f"\n{len(results)} diagram(s), average {average}/100.")
    if failing:
        print(f"{len(failing)} below the --min-score of {args.min_score}: "
              + ", ".join(label for label, _ in failing[:8]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
