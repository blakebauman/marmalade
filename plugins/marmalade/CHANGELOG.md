# Changelog

## 0.1.0

Initial release.

- **10 skills** — no-slop, mermaid-authoring, mermaid-theming, mermaid-export,
  diagram-review, diagram-a11y, schema-to-erd, code-to-diagram,
  threat-model-diagrams, docs-diagram-sync.
- **12 subagents** — mermaid-architect, diagram-ux-reviewer, ia-reviewer,
  a11y-reviewer, security-reviewer, diagram-code-reviewer, devops-diagrammer,
  python-diagrammer, postgres-erd-engineer, docs-sync-engineer,
  mermaid-export-engineer, dx-reviewer.
- **8 commands** — `/marmalade:draw`, `review`, `slop`, `export`, `theme`,
  `erd`, `sync`, `doctor`.
- **4 hooks** — SessionStart context probe, PreToolUse secret scan, PostToolUse
  Mermaid validation, Stop drift check.
- **Toolchain** — `marmalade_lint.py` (31 MMD checks), `marmalade_slop.py`
  (12 SLOP checks with density budgets), `marmalade_export.py` (SVG/PNG/PDF with
  a content-hash manifest), `pg_erd.py`, `py_diagram.py`, `docs_sync.py`,
  `check_contrast.py`, `marmalade_doctor.py`.
- **5 theme presets** — light, dark, high-contrast, colorblind-safe, print. All
  verified against WCAG AA, plus a brand template.
- **7 templates** — all scoring 100 on the slop rubric.
