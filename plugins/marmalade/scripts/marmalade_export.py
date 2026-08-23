#!/usr/bin/env python3
"""Render Mermaid sources to SVG / PNG / PDF, deterministically and in bulk.

    marmalade_export.py [paths...] --format svg,png --theme dark --out docs/diagrams/rendered

Handles both standalone `.mmd` files and ```mermaid fences inside Markdown. Every
run lints first and refuses to render a diagram that will not parse, then writes a
manifest keyed by source content hash so drift is detectable by content rather
than by timestamp.

Rendering shells out to mermaid-cli (`mmdc`), preferring one on PATH and falling
back to `npx -y -p @mermaid-js/mermaid-cli mmdc`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from mermaid_lint import Block, extract_blocks, lint  # noqa: E402

THEME_DIR = Path(__file__).resolve().parent.parent / "assets" / "themes"
PRESETS = {"light", "dark", "high-contrast", "colorblind-safe", "print"}
MANIFEST_NAME = ".Marmalade-manifest.json"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", ".next", "target", "__pycache__"}
SCANNABLE = (".mmd", ".mermaid", ".md", ".markdown", ".mdx", ".qmd")

# ```mermaid id=checkout  →  the block renders to checkout.svg instead of doc-1.svg
FENCE_ID = re.compile(r"\b(?:id|name)\s*=\s*[\"']?([A-Za-z0-9._-]+)")
FM_TITLE = re.compile(r"^\s*title\s*:\s*(.+?)\s*$", re.MULTILINE)


@dataclass
class Job:
    block: Block
    stem: str          # output basename without extension
    source_path: Path
    digest: str


# --- discovery ---------------------------------------------------------------


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "diagram"


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


def build_jobs(files: list[Path]) -> list[Job]:
    jobs: list[Job] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        blocks = extract_blocks(str(path), text)
        for index, block in enumerate(blocks, start=1):
            digest = hashlib.sha256(block.source.encode("utf-8")).hexdigest()[:16]
            if block.origin == "file":
                stem = path.stem
            else:
                explicit = FENCE_ID.search(block.fence_info)
                title = FM_TITLE.search(block.source)
                if explicit:
                    stem = slugify(explicit.group(1))
                elif title:
                    stem = f"{path.stem}-{slugify(title.group(1))}"
                elif len(blocks) == 1:
                    stem = path.stem
                else:
                    stem = f"{path.stem}-{index}"
            jobs.append(Job(block=block, stem=stem, source_path=path, digest=digest))
    return jobs


def dedupe_stems(jobs: list[Job]) -> None:
    """Two blocks that would write the same file get a numeric suffix instead."""
    seen: dict[str, int] = {}
    for job in jobs:
        count = seen.get(job.stem, 0) + 1
        seen[job.stem] = count
        if count > 1:
            job.stem = f"{job.stem}-{count}"


# --- renderer ----------------------------------------------------------------


def resolve_theme(name: str) -> Path:
    if name in PRESETS:
        return THEME_DIR / f"{name}.json"
    path = Path(name)
    if path.is_file():
        return path
    raise SystemExit(
        f"Unknown theme {name!r}. Use a preset ({', '.join(sorted(PRESETS))}) or a path to a Mermaid config JSON."
    )


def theme_background(config: Path, override: str | None) -> str:
    if override:
        return override
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
        return data.get("themeVariables", {}).get("background") or "white"
    except Exception:
        return "white"


def renderer_command() -> list[str] | None:
    if shutil.which("mmdc"):
        return ["mmdc"]
    if shutil.which("npx"):
        return ["npx", "-y", "-p", "@mermaid-js/mermaid-cli", "mmdc"]
    return None


def render(
    base_cmd: list[str],
    source: str,
    out_path: Path,
    config: Path,
    background: str,
    scale: float,
    width: int | None,
    css: Path | None,
    puppeteer: Path | None,
) -> tuple[bool, str]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False, encoding="utf-8") as tmp:
        tmp.write(source)
        tmp_path = Path(tmp.name)
    cmd = base_cmd + [
        "-i", str(tmp_path),
        "-o", str(out_path),
        "-c", str(config),
        "-b", background,
        "-s", str(scale),
        "-q",
    ]
    if width:
        cmd += ["-w", str(width)]
    if css:
        cmd += ["-C", str(css)]
    if puppeteer:
        cmd += ["-p", str(puppeteer)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return False, "mermaid-cli timed out after 180s"
    except OSError as exc:
        return False, f"could not launch mermaid-cli: {exc}"
    finally:
        tmp_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return False, detail[-1] if detail else f"mermaid-cli exited {proc.returncode}"
    return True, ""


# --- manifest ----------------------------------------------------------------


def load_manifest(out_dir: Path) -> dict:
    path = out_dir / MANIFEST_NAME
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "entries": {}}


def save_manifest(out_dir: Path, manifest: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# --- main --------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="Render Mermaid sources to SVG/PNG/PDF.")
    ap.add_argument("paths", nargs="*", help="Files or directories. Defaults to the configured diagram directory.")
    ap.add_argument("--format", default=None, help="Comma-separated: svg,png,pdf. Default svg.")
    ap.add_argument("--theme", default=None, help="Preset name or path to a Mermaid config JSON.")
    ap.add_argument("--out", default=None, help="Output directory.")
    ap.add_argument("--background", default=None, help="Background color, or 'transparent'.")
    ap.add_argument("--scale", type=float, default=2.0, help="Raster scale factor for PNG. Default 2.")
    ap.add_argument("--width", type=int, default=None, help="Viewport width in px.")
    ap.add_argument("--css", default=None, help="Extra CSS file passed to mermaid-cli.")
    ap.add_argument("--puppeteer-config", default=None, help="Puppeteer config JSON (sandbox flags, CI).")
    ap.add_argument("--check", action="store_true", help="Report what is stale; render nothing. Exit 1 if stale.")
    ap.add_argument("--force", action="store_true", help="Render even when the linter reports errors.")
    ap.add_argument("--json", action="store_true", help="Emit a machine-readable result.")
    args = ap.parse_args()

    roots = args.paths or [os.environ.get("MARMALADE_DIAGRAM_DIR", "docs/diagrams")]
    out_dir = Path(args.out or os.environ.get("MARMALADE_EXPORT_DIR", "docs/diagrams/rendered"))
    theme_name = args.theme or os.environ.get("MARMALADE_THEME", "light")
    formats = [f.strip().lower() for f in (args.format or os.environ.get("MARMALADE_FORMATS", "svg")).split(",") if f.strip()]

    bad_formats = [f for f in formats if f not in ("svg", "png", "pdf")]
    if bad_formats:
        print(f"Unsupported format(s): {', '.join(bad_formats)}. mermaid-cli renders svg, png, pdf.", file=sys.stderr)
        return 2

    config = resolve_theme(theme_name)
    background = theme_background(config, args.background)

    jobs = build_jobs(collect(roots))
    dedupe_stems(jobs)
    if not jobs:
        print(f"No Mermaid sources found under: {', '.join(roots)}")
        return 0

    # Lint gate — a diagram that will not parse should never reach the renderer.
    blocked: list[str] = []
    for job in jobs:
        errors = [f for f in lint(job.block) if f.severity == "error"]
        for f in errors:
            blocked.append(f"{job.source_path}:{f.line}  {f.code}  {f.message}")
    if blocked and not args.force:
        print("Refusing to render — these diagrams have syntax errors:\n", file=sys.stderr)
        for line in blocked[:20]:
            print(f"  {line}", file=sys.stderr)
        print("\nFix them, or pass --force to render anyway.", file=sys.stderr)
        return 1

    manifest = load_manifest(out_dir)
    entries = manifest.setdefault("entries", {})

    stale: list[str] = []
    for job in jobs:
        for fmt in formats:
            key = f"{job.stem}.{fmt}"
            recorded = entries.get(key, {})
            target = out_dir / key
            if recorded.get("digest") != job.digest or recorded.get("theme") != theme_name or not target.exists():
                stale.append(key)

    if args.check:
        if args.json:
            print(json.dumps({"stale": stale, "total": len(jobs) * len(formats)}, indent=2))
        elif stale:
            print(f"{len(stale)} rendered artifact(s) out of date:")
            for key in stale[:30]:
                print(f"  • {key}")
        else:
            print("All rendered artifacts are current.")
        return 1 if stale else 0

    base_cmd = renderer_command()
    if base_cmd is None:
        print(
            "No Mermaid renderer available. Install one of:\n"
            "  npm install -g @mermaid-js/mermaid-cli    (provides `mmdc`)\n"
            "  # or make `npx` available so Marmalade can run mermaid-cli on demand",
            file=sys.stderr,
        )
        return 2

    css = Path(args.css) if args.css else None
    puppeteer = Path(args.puppeteer_config) if args.puppeteer_config else None

    rendered: list[str] = []
    failed: list[tuple[str, str]] = []
    for job in jobs:
        for fmt in formats:
            key = f"{job.stem}.{fmt}"
            if key not in stale:
                continue
            ok, err = render(
                base_cmd, job.block.source, out_dir / key, config, background, args.scale, args.width, css, puppeteer
            )
            if ok:
                rendered.append(key)
                entries[key] = {
                    "source": str(job.source_path),
                    "digest": job.digest,
                    "theme": theme_name,
                    "origin": job.block.origin,
                    "line_offset": job.block.line_offset,
                }
            else:
                failed.append((key, err))

    manifest["version"] = 1
    manifest["theme"] = theme_name
    save_manifest(out_dir, manifest)

    if args.json:
        print(json.dumps({"rendered": rendered, "failed": [{"target": k, "error": e} for k, e in failed],
                          "skipped": len(jobs) * len(formats) - len(stale), "out_dir": str(out_dir)}, indent=2))
    else:
        print(f"Rendered {len(rendered)} artifact(s) into {out_dir} using theme '{theme_name}'.")
        for key in rendered:
            print(f"  ✓ {key}")
        skipped = len(jobs) * len(formats) - len(stale)
        if skipped:
            print(f"  ({skipped} already current)")
        for key, err in failed:
            print(f"  ✗ {key}: {err}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
