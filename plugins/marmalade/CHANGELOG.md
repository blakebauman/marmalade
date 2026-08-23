# Changelog

## 0.1.2

Calibrated against 39 hand-written diagrams across seven real repositories.

- **SLOP012 is now scoped to standalone `.mmd` files.** It fired on 35 of the 39
  and carried no information: a fenced block inherits its docs platform's theme,
  so there is no default-Mermaid look to complain about. Only a `.mmd` headed
  for export actually ships one. Clean count on the sample went from 12 to 19.
- README gains a *Seen on real diagrams* section with the survey results and a
  before/after worked example (70/100 → 100/100).

## 0.1.1

- Capitalise Marmalade in user-facing strings — hook messages, the doctor
  header, and a slop hint had been lowercased by the rename.

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
