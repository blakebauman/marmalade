#!/usr/bin/env python3
"""Generate a Mermaid import graph from a Python package — within a density budget.

    py_diagram.py src/myapp --detail balanced
    py_diagram.py src/myapp --level package -o docs/diagrams/imports.mmd

Auto-generated diagrams are the single largest source of Mermaid slop: dump every
module and every edge and you get a hairball nobody reads. This tool refuses to
do that. When the module graph exceeds the detail budget it collapses to package
level automatically and says so, rather than emitting 200 nodes.

Standard library only — imports are read with `ast`, nothing is executed.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from collections import defaultdict
from pathlib import Path

BUDGETS = {"simplified": 7, "balanced": 12, "faithful": 24}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "build", "dist", ".tox", ".mypy_cache"}


def module_name(path: Path, root: Path, prefix: str) -> str:
    """Dotted module name, prefixed with the package name when root is a package.

    Pointing at `src/myapp` where `myapp/__init__.py` exists means source files
    import each other as `myapp.core.service`, so the graph has to be keyed that
    way or every internal import resolves to the wrong node.
    """
    rel = path.relative_to(root).with_suffix("")
    parts = [p for p in rel.parts if p != "__init__"]
    if prefix:
        parts = [prefix] + parts
    return ".".join(parts) if parts else root.name


def collect_modules(root: Path) -> tuple[dict[str, Path], set[str]]:
    """Returns (module name -> path, set of names that are packages)."""
    prefix = root.name if (root / "__init__.py").is_file() else ""
    modules: dict[str, Path] = {}
    packages: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        name = module_name(path, root, prefix)
        modules[name] = path
        if path.name == "__init__.py":
            packages.add(name)
    return modules, packages


def imports_of(path: Path, own_module: str, known: set[str], is_package: bool) -> set[str]:
    """Internal imports only — third-party and stdlib are noise in an architecture diagram."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except (SyntaxError, OSError):
        return set()

    found: set[str] = set()
    own_parts = own_module.split(".")

    def record(name: str) -> None:
        # Longest known prefix wins: `a.b.c` resolves to module `a.b` if that exists.
        parts = name.split(".")
        for i in range(len(parts), 0, -1):
            candidate = ".".join(parts[:i])
            if candidate in known:
                found.add(candidate)
                return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                record(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import
                # level 1 means "my package": that is own_module for an
                # __init__.py, and the parent for a regular module.
                anchor = own_parts if is_package else own_parts[:-1]
                base = anchor[: max(0, len(anchor) - (node.level - 1))]
                target = ".".join(base + ([node.module] if node.module else []))
                record(target)
                for alias in node.names:
                    record(f"{target}.{alias.name}" if target else alias.name)
            elif node.module:
                record(node.module)
                for alias in node.names:
                    record(f"{node.module}.{alias.name}")

    found.discard(own_module)
    return found


def to_package(module: str, depth: int) -> str:
    parts = module.split(".")
    return ".".join(parts[:depth]) if len(parts) > depth else module


def node_id(name: str) -> str:
    return "n_" + "".join(c if c.isalnum() else "_" for c in name)


def render(edges: dict[str, set[str]], nodes: list[str], *, title: str, level: str,
           collapsed_from: int | None, budget: int) -> str:
    lines = ["---", f"title: {title}", "---", "flowchart LR", f"    accTitle: {title}"]
    descr = (
        f"Internal import graph at {level} level: {len(nodes)} units and "
        f"{sum(len(v) for v in edges.values())} dependencies."
    )
    if collapsed_from:
        descr += f" Collapsed from {collapsed_from} modules to stay within a budget of {budget}."
    lines.append(f"    accDescr: {descr}")
    lines.append("")

    # Fan-in is the useful signal in an import graph: what everything depends on.
    fan_in: dict[str, int] = defaultdict(int)
    for targets in edges.values():
        for t in targets:
            fan_in[t] += 1
    hubs = sorted(fan_in, key=lambda n: -fan_in[n])[:2]

    for name in nodes:
        lines.append(f"    {node_id(name)}[{name}]")
    lines.append("")
    for source in sorted(edges):
        for target in sorted(edges[source]):
            lines.append(f"    {node_id(source)} --> {node_id(target)}")

    lines.append("")
    lines.append("    classDef focal fill:#dbeaf5,stroke:#0072B2,stroke-width:2px,color:#062033")
    if hubs:
        lines.append(f"    class {','.join(node_id(h) for h in hubs)} focal")
        lines.append(f"    %% focal = highest fan-in: {', '.join(f'{h} ({fan_in[h]})' for h in hubs)}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Python import graph to Mermaid, budget-enforced.")
    ap.add_argument("root", help="Package or source directory to scan.")
    ap.add_argument("--detail", default="balanced", choices=sorted(BUDGETS), help="Density budget. Default balanced.")
    ap.add_argument("--level", choices=("auto", "module", "package"), default="auto",
                    help="Granularity. 'auto' collapses to package when the module graph busts the budget.")
    ap.add_argument("--package-depth", type=int, default=1, help="Dotted-path depth when collapsing. Default 1.")
    ap.add_argument("--title", default=None)
    ap.add_argument("-o", "--output", help="Write here instead of stdout.")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"{args.root} is not a directory.")

    modules, packages = collect_modules(root)
    if not modules:
        raise SystemExit(f"No .py files under {args.root}.")

    known = set(modules)
    raw: dict[str, set[str]] = {}
    for name, path in modules.items():
        targets = imports_of(path, name, known, name in packages)
        if targets:
            raw[name] = targets

    budget = BUDGETS[args.detail]
    level = args.level
    collapsed_from = None

    if level == "auto":
        level = "module" if len(modules) <= budget else "package"
        if level == "package":
            collapsed_from = len(modules)
    elif level == "package":
        collapsed_from = len(modules)

    if level == "package":
        depth = args.package_depth
        edges: dict[str, set[str]] = defaultdict(set)
        for source, targets in raw.items():
            s = to_package(source, depth)
            for t in targets:
                tp = to_package(t, depth)
                if tp != s:
                    edges[s].add(tp)
        nodes = sorted({to_package(m, depth) for m in modules})
    else:
        edges = {k: set(v) for k, v in raw.items()}
        nodes = sorted(modules)

    over = len(nodes) - budget
    output = render(
        edges, nodes,
        title=args.title or f"{root.name} import graph",
        level=level, collapsed_from=collapsed_from, budget=budget,
    )

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote {args.output} — {len(nodes)} nodes at {level} level.", file=sys.stderr)
    else:
        sys.stdout.write(output)

    if over > 0:
        print(
            f"\nStill {len(nodes)} nodes against a '{args.detail}' budget of {budget}. "
            f"This graph is too tangled to draw honestly at this level — either raise --package-depth, "
            f"scan a subdirectory, or treat the excess as a finding about the code rather than the diagram.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
