#!/usr/bin/env python3
"""Check that everything Marmalade needs is present, and say what to do if not."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
import config  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
OK, WARN, FAIL = "✓", "!", "✗"


def probe_version(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    except Exception:
        return None
    return (proc.stdout or proc.stderr).strip().splitlines()[0] if proc.returncode == 0 else None


def main() -> int:
    rows: list[tuple[str, str, str]] = []
    failures = 0

    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    rows.append((OK if sys.version_info >= (3, 9) else FAIL, "Python", f"{py} (need 3.9+)"))
    if sys.version_info < (3, 9):
        failures += 1

    if shutil.which("mmdc"):
        rows.append((OK, "mermaid-cli", f"mmdc on PATH — {probe_version(['mmdc', '--version']) or 'version unknown'}"))
    elif shutil.which("npx"):
        rows.append((WARN, "mermaid-cli", "not installed; npx will fetch it per render (slow first run). "
                                          "Install with: npm install -g @mermaid-js/mermaid-cli"))
    else:
        rows.append((FAIL, "mermaid-cli", "no mmdc and no npx — export is unavailable. "
                                          "Install Node.js, then: npm install -g @mermaid-js/mermaid-cli"))
        failures += 1

    rows.append((OK, "psql", "on PATH — live ERD generation available")
                if shutil.which("psql")
                else (WARN, "psql", "not found — pg_erd.py works with --sql-file only"))

    themes = sorted(p.stem for p in [p for p in (PLUGIN_ROOT / "assets" / "themes").glob("*.json") if not p.name.endswith(".template.json")])
    rows.append((OK if themes else FAIL, "theme presets", ", ".join(themes) or "missing"))
    if not themes:
        failures += 1

    templates = sorted(p.name for p in (PLUGIN_ROOT / "assets" / "templates").glob("*.mmd"))
    rows.append((OK if templates else FAIL, "templates", f"{len(templates)} available"))

    for key, env, default in (("diagram_dir", "DIAGRAM_DIR", "docs/diagrams"),
                              ("export_dir", "EXPORT_DIR", "docs/diagrams/rendered"),
                              ("default_theme", "THEME", "light")):
        value = config.setting(env, key, "")
        rows.append((OK, f"config: {key}", value or f"{default} (default)"))

    cwd = Path.cwd()
    diagram_dir = cwd / config.diagram_dir()
    if diagram_dir.is_dir():
        count = len(list(diagram_dir.rglob("*.mmd"))) + len(list(diagram_dir.rglob("*.mermaid")))
        rows.append((OK, "diagram directory", f"{diagram_dir} — {count} source file(s)"))
    else:
        rows.append((WARN, "diagram directory", f"{diagram_dir} does not exist yet"))

    width = max(len(label) for _s, label, _d in rows)
    print("Marmalade doctor\n")
    for status, label, detail in rows:
        print(f"  {status} {label.ljust(width)}  {detail}")

    if failures:
        print(f"\n{failures} blocking problem(s). Fix those before running an export.")
        return 1
    print("\nReady.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
