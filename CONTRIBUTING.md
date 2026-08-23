# Contributing to Marmalade

Marmalade treats a diagram as an engineering artifact. The same standard applies
to the plugin itself: every rule below is machine-checked, so you can change
things confidently and let CI catch what you missed.

## Repository layout

```
.claude-plugin/marketplace.json     the marketplace entry (version must match plugin.json)
scripts/validate.py                 dev-only structural validator; never ships
plugins/marmalade/                  everything that ships
  .claude-plugin/plugin.json        the manifest, including the userConfig schema
  agents/*.md                       12 subagents
  skills/<name>/SKILL.md            10 skills; long material in <name>/reference/
  commands/*.md                     8 slash commands
  hooks/hooks.json                  4 hooks -> scripts/hooks/*.py
  scripts/                          the Python toolchain
    lib/                            shared: mermaid_lint, slop, config
    hooks/                          hook entry points + _hookio
  assets/themes/*.json              5 presets + brand.template.json
  assets/templates/*.mmd            7 exemplars, all scoring 100
```

## The rules (enforced by `scripts/validate.py` and CI)

**Manifests**

- Bump the version in **both** `plugins/marmalade/.claude-plugin/plugin.json` and
  the entry in `.claude-plugin/marketplace.json`. Drift between them is the
  failure mode that breaks installs.
- `name` kebab-case; `description` ≤ 500 characters.

**Agents** (`plugins/marmalade/agents/*.md`)

- `name` is kebab-case, 3–50 characters, unique, and matches the filename.
- `description` says *when to delegate*, with trigger phrases.
- `tools` names only real tools. `model: inherit` unless there is a reason.
- `skills:` is a JSON array of namespaced ids (`"marmalade:no-slop"`) that exist.
- Marmalade does not use `color`. Leave it off.

**Skills** (`plugins/marmalade/skills/<name>/SKILL.md`)

- `name` matches the directory name; `description` is required.
- `allowed-tools` names only real tools — the current vocabulary includes `Agent`,
  not the legacy `Task`.
- Keep `SKILL.md` lean. Long material goes in `<name>/reference/` (singular).
- **Every internal path is `${CLAUDE_PLUGIN_ROOT}`-prefixed.** A bare relative path
  resolves against the user's cwd once installed and silently fails to load. The
  validator requires the prefix and checks the file exists.

**Commands** (`plugins/marmalade/commands/*.md`)

- Prefer inline `` !`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/..."` `` over telling
  the model to run something. Deterministic output in the prompt beats a hope.
- Relative links into the skills tree must resolve.

**Configuration**

Two channels reach the plugin: `MARMALADE_*` environment variables and the
`/plugin` userConfig, which the harness exports as `CLAUDE_PLUGIN_OPTION_*`.
Resolve every setting through `plugins/marmalade/scripts/lib/config.py`, which
applies one precedence everywhere:

```
explicit CLI flag  >  MARMALADE_<KEY>  >  CLAUDE_PLUGIN_OPTION_<KEY>  >  default
```

Never read either variable directly. They were read by different halves of the
plugin once, and a `diagram_dir` set in `/plugin` was obeyed by the hooks and
ignored by export, slop, lint and sync.

**Hooks**

- A hook must **never crash the session**: wrap `main()` in
  `try/except: sys.exit(0)`. CI feeds each one empty and malformed stdin.
- Use the `_hookio` helpers for stdin, config, and path extraction.

**Toolchain**

- **Stdlib only**, Python 3.9 compatible. No third-party dependencies anywhere,
  including `scripts/`. CI runs on 3.9 with no pip step.
- Anything shared between two scripts belongs in `scripts/lib/`.

**Assets**

- Bundled templates must score **100** on the slop rubric.
- Theme presets must pass **WCAG AA** via `check_contrast.py`.
- `PRESETS` in `marmalade_export.py` must match the themes on disk.

**Duplicated files**

`README.md` / `plugins/marmalade/README.md` and the two `LICENSE` files are kept
byte-identical. Edit both; the validator compares them.

## Add a skill

1. `plugins/marmalade/skills/<name>/SKILL.md` with `name` (== the directory),
   `description`, `license`, `compatibility`, `allowed-tools`.
2. Long material in `<name>/reference/`, linked with `${CLAUDE_PLUGIN_ROOT}`.
3. Add it to any agent's `skills:` array that should load it, and to both READMEs.
4. Add an eval case under `plugins/marmalade/evals/` — see `docs/evaluating-skills.md`.

## Add an agent

1. `plugins/marmalade/agents/<name>.md`, frontmatter `name` (== the filename),
   `description`, `tools`, `skills`, `model: inherit`.
2. Read-only reviewers get `Read, Grep, Glob, Bash`; engineers that write get
   `Write, Edit` too.
3. Add it to both READMEs.

## Add a theme

1. `plugins/marmalade/assets/themes/<name>.json`, `theme: "base"` plus
   `themeVariables` (without `base`, the variables are silently discarded).
2. Add the name to `PRESETS` in `marmalade_export.py`.
3. `python3 plugins/marmalade/scripts/check_contrast.py plugins/marmalade/assets/themes/<name>.json`
4. Add it to the CI contrast loop in `.github/workflows/ci.yml` and to both READMEs.

## Validate and build locally

```bash
python3 scripts/validate.py

# the same artifact CI builds on a tag:
cd plugins/marmalade && zip -r ../../marmalade.plugin . -x "*.DS_Store"
```

## Releasing

1. Bump the version in both manifests.
2. Add a `plugins/marmalade/CHANGELOG.md` entry.
3. Tag `vX.Y.Z` and push it. `.github/workflows/release.yml` validates, builds
   `marmalade.plugin`, and attaches it to a GitHub Release with generated notes.

## Commit style

One focused change per PR, with a subject that says what changed and why —
"Calibrate SLOP012 against real diagrams", not "fix lint".
