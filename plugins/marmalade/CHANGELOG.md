# Changelog

## Unreleased

- **Fixed: the release artifact was not loadable.** `release.yml` published
  `marmalade.plugin`, but `claude --plugin-dir` and `--plugin-url` accept a
  directory or a `.zip` and silently load nothing from an archive named anything
  else. The artifact is now `marmalade.zip`. The 0.1.4 release has been given a
  working asset.

## 0.1.4

- **`/marmalade:status`** — a read-only report on this project's diagram health:
  inventory, drift, rubric scores, and the one next command. `/marmalade:doctor`
  checks the environment; this checks the diagrams.
- **Config is resolved in one place.** `scripts/lib/config.py` applies a single
  precedence — explicit flag, then `MARMALADE_*`, then the `/plugin` userConfig,
  then the default. Previously the hooks honoured userConfig and the CLI scripts
  honoured `MARMALADE_*` with nothing bridging them, so a `diagram_dir` set in
  `/plugin` was obeyed by the drift hook and ignored by export, slop, lint and
  sync.
- **Fixed: the render manifest filename.** The code wrote
  `.Marmalade-manifest.json` while the docs said `.marmalade-manifest.json`; on a
  case-sensitive filesystem anyone following the docs never found it. The
  lowercase spelling is now correct everywhere. Existing users get one extra
  re-render as the old manifest is ignored.
- **`scripts/validate.py`** — structural validation of the plugin itself: manifest
  agreement, frontmatter, `${CLAUDE_PLUGIN_ROOT}` paths that actually resolve,
  agent-to-skill references, preset/theme agreement, and the duplicated
  README/LICENSE pairs. Wired into CI, replacing the ad-hoc JSON and version
  checks.
- **Eval suite** — five cases under `plugins/marmalade/evals/`, including an
  adversarial case where padding the diagram is the failure. Deterministic
  graders shell out to the slop scorer and linter; `scripts/run_evals.py` runs
  them with a with/without-plugin ablation until `claude plugin eval` leaves
  early access.
- **Releases** — pushing a `v*` tag now builds `marmalade.plugin` and attaches it
  to a GitHub Release.
- **Docs** — `CONTRIBUTING.md`, `AGENTS.md`, `docs/install.md`, and
  `docs/evaluating-skills.md`.

## 0.1.3

Two false positives in the secret scanner, both found by running it over 75 real
documentation files. It flagged 6; it now flags 0, with every true positive still
blocking.

- **A CIDR block is not a host address.** `10.20.0.0/16` is how a VPC is
  documented — RFC 1918 ranges are private by definition — so flagging it blocked
  edits to every infrastructure diagram, including the ones this plugin's own
  devops-diagrammer produces. A bare host like `10.4.2.17` still blocks.
- **Prose is not a diagram.** With no Mermaid block found, the scanner fell back
  to scanning the whole document, so a local dev DSN or an unrelated shell
  example in a Markdown file blocked the edit. It now scans standalone `.mmd`
  files whole, Markdown only inside its fences, and skips documents carrying no
  diagram at all. Edit fragments that look like Mermaid are still scanned.
- Link-local addresses are allowed: `169.254.169.254` is the cloud metadata
  endpoint, identical everywhere, and reveals nothing.
- All eleven cases are now CI regression tests.

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
