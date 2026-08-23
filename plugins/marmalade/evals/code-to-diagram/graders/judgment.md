---
type: llm
---
Grade the response against these criteria. Each is independently pass/fail.

- The response **derives the graph from the source** rather than inventing a
  plausible-looking architecture. Every module it names exists under `scripts/`.
- It reflects the real shape: `lib/mermaid_lint.py` and `lib/slop.py` are the
  shared core that the CLI entry points depend on, and `slop` depends on
  `mermaid_lint` — not the reverse.
- The `hooks/` entry points are shown depending on `_hookio`, and `_hookio` on
  the shared `lib`.
- It holds a **density budget** — if the module-level graph is too dense it
  collapses to package level and says it did so, rather than emitting forty
  nodes.
- Edges represent **imports** and the direction is correct (dependant → dependency,
  stated consistently and explained).
- It does not present the diagram as covering runtime behaviour when it shows
  static imports.
