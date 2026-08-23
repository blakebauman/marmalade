#!/usr/bin/env python3
"""Report every way the diagrams and the docs have drifted apart.

    docs_sync.py --diagrams docs/diagrams --rendered docs/diagrams/rendered --docs .

Five kinds of drift, all detected by content rather than by timestamp:

  stale      a rendered artifact whose source hash no longer matches
  unrendered a source with no rendered artifact at all
  orphaned   a rendered artifact whose source is gone
  broken     a doc that references a rendered image that does not exist
  unused     a rendered artifact no doc references

Exit 1 if anything drifted, so this runs as a CI gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from mermaid_lint import extract_blocks  # noqa: E402

MANIFEST_NAME = ".marmalade-manifest.json"
RENDERED_EXT = (".svg", ".png", ".pdf")
DOC_EXT = (".md", ".markdown", ".mdx", ".qmd", ".rst", ".html")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", ".next", "target", "__pycache__"}

IMAGE_REF = re.compile(r"!\[[^\]]*\]\(([^)\s]+)|<img[^>]+src=[\"']([^\"']+)[\"']|:::\s*image\s+source=[\"']([^\"']+)")


def walk(root: Path, exts: tuple[str, ...]) -> list[Path]:
    out = []
    if not root.is_dir():
        return out
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in exts:
            out.append(path)
    return out


def source_digests(diagram_dir: Path) -> dict[str, str]:
    """stem -> content hash, matching how marmalade_export names its outputs."""
    digests: dict[str, str] = {}
    for path in walk(diagram_dir, (".mmd", ".mermaid")):
        for block in extract_blocks(str(path), path.read_text(encoding="utf-8", errors="replace")):
            digests[path.stem] = hashlib.sha256(block.source.encode("utf-8")).hexdigest()[:16]
    return digests


def main() -> int:
    ap = argparse.ArgumentParser(description="Detect drift between Mermaid sources, renders, and docs.")
    ap.add_argument("--diagrams", default=os.environ.get("MARMALADE_DIAGRAM_DIR", "docs/diagrams"))
    ap.add_argument("--rendered", default=os.environ.get("MARMALADE_EXPORT_DIR", "docs/diagrams/rendered"))
    ap.add_argument("--docs", default=".", help="Root to scan for documents referencing rendered images.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    diagram_dir, rendered_dir, docs_root = Path(args.diagrams), Path(args.rendered), Path(args.docs)

    digests = source_digests(diagram_dir)
    try:
        manifest = json.loads((rendered_dir / MANIFEST_NAME).read_text(encoding="utf-8")).get("entries", {})
    except Exception:
        manifest = {}

    artifacts = [p for p in walk(rendered_dir, RENDERED_EXT)]
    artifact_names = {p.name for p in artifacts}

    stale, unrendered, orphaned = [], [], []

    for stem, digest in sorted(digests.items()):
        matching = [name for name in artifact_names if Path(name).stem == stem]
        if not matching:
            unrendered.append(stem)
            continue
        for name in matching:
            recorded = manifest.get(name, {}).get("digest")
            if recorded is None:
                stale.append(f"{name} (not in manifest — rendered outside marmalade, or manifest deleted)")
            elif recorded != digest:
                stale.append(f"{name} (source changed since render)")

    for path in artifacts:
        if path.stem not in digests and path.name in manifest:
            orphaned.append(path.name)

    referenced: set[str] = set()
    broken: list[str] = []
    for doc in walk(docs_root, DOC_EXT):
        try:
            text = doc.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in IMAGE_REF.finditer(text):
            ref = next((g for g in match.groups() if g), None)
            if not ref or ref.startswith(("http://", "https://", "data:")):
                continue
            name = Path(ref.split("#")[0].split("?")[0]).name
            if not name.lower().endswith(RENDERED_EXT):
                continue
            referenced.add(name)
            target = (doc.parent / ref).resolve()
            if not target.exists() and name not in artifact_names:
                broken.append(f"{doc}: {ref}")

    unused = sorted(artifact_names - referenced) if referenced else []

    result = {
        "stale": stale, "unrendered": unrendered, "orphaned": orphaned,
        "broken_references": broken, "unreferenced_artifacts": unused,
    }
    drifted = any(result[k] for k in ("stale", "unrendered", "orphaned", "broken_references"))

    if args.json:
        print(json.dumps({**result, "in_sync": not drifted}, indent=2))
        return 1 if drifted else 0

    headings = {
        "stale": "Rendered artifacts out of date with their source",
        "unrendered": "Sources with no rendered artifact",
        "orphaned": "Rendered artifacts whose source is gone",
        "broken_references": "Documents pointing at images that do not exist",
        "unreferenced_artifacts": "Rendered artifacts no document references",
    }
    for key, heading in headings.items():
        items = result[key]
        if not items:
            continue
        print(f"\n{heading} ({len(items)}):")
        for item in items[:20]:
            print(f"  • {item}")
        if len(items) > 20:
            print(f"  … and {len(items) - 20} more")

    if not drifted and not unused:
        print("Diagrams, renders, and docs are in sync.")
    elif not drifted:
        print("\nNo drift. Unreferenced artifacts above are informational — delete them or link them.")
    else:
        print("\nRun the export to fix stale and unrendered entries; delete orphans; fix broken links by hand.")
    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main())
