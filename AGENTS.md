# AGENTS.md

Guidance for AI coding agents (Claude Code, etc.) working in this repository.

This repo is the **Marmalade** plugin — skills, subagents, commands, hooks and a
Python toolchain for treating Mermaid diagrams as engineering artifacts. Follow
`CONTRIBUTING.md` in full. The invariants below are enforced by
`scripts/validate.py` and CI; a change that breaks one fails the build.

## Layout

The plugin is **nested**, not at the repo root:

- `plugins/marmalade/` — everything that ships to a user
- `scripts/` (repo root) — dev tooling only; never shipped
- `.claude-plugin/marketplace.json` (repo root) + `plugins/marmalade/.claude-plugin/plugin.json`

## The invariants

- **Version in both manifests.** Bump `plugins/marmalade/.claude-plugin/plugin.json`
  *and* the matching entry in `.claude-plugin/marketplace.json`. The validator
  fails if they disagree — that drift is what breaks installs.
- **Manifest description ≤ 500 characters.** Agent and skill descriptions ≤ 1024;
  they are loaded into every session, so they cost tokens and can be truncated.
- **Agent names** are kebab-case, 3–50 chars, unique, and match the filename.
- **Skill `name` matches its directory name.** Every `skills/<name>/` needs a
  `SKILL.md` with `name` and `description`.
- **`${CLAUDE_PLUGIN_ROOT}` on every internal path.** A bare `reference/foo.md`
  resolves against the *user's* cwd once installed and silently fails to load.
  The validator requires the prefix and checks the target exists. Note the
  directory is `reference/` (singular) in this plugin.
- **`tools` and `allowed-tools` name real tools.** The current vocabulary includes
  `Agent` — not the legacy `Task`. An unknown name silently loses the
  pre-approval.
- **An agent's `skills:` array** must name skills that exist, namespaced
  (`"marmalade:no-slop"`).
- **Config goes through `scripts/lib/config.py`.** There are two channels —
  `MARMALADE_*` env vars and the `/plugin` userConfig exported as
  `CLAUDE_PLUGIN_OPTION_*`. Resolve every setting through `config.setting()` so a
  hook and a CLI script in the same repo never disagree. Never read either
  environment variable directly.
- **Hooks must never crash the session.** Every hook wraps `main()` in
  `try/except: sys.exit(0)`. CI feeds each one empty and malformed stdin and
  requires exit 0.
- **Bundled templates score 100** on the slop rubric, and **theme presets pass
  WCAG AA**. Both are CI gates. `brand.template.json` is excluded — its values are
  `TOKEN_*` placeholders.
- **`PRESETS` in `marmalade_export.py` matches `assets/themes/*.json`.**
- **Stdlib only.** The scripts have no third-party dependencies and CI runs them
  on Python 3.9 with no pip step. Keep it that way — including in `scripts/`.
- **`README.md` and `plugins/marmalade/README.md` are byte-identical**, as are the
  two `LICENSE` files. Edit both, or the validator fails.

Before committing, always run:

```bash
python3 scripts/validate.py
```

Keep `SKILL.md` files lean and put long material in `reference/`. When you add or
rename a skill, agent, command or theme, update `README.md` (**both copies**) and
`plugins/marmalade/CHANGELOG.md` to match.

Slash commands live in `plugins/marmalade/commands/*.md` and are the plugin's
entry points. They execute the Python toolchain directly with inline
`` !`...` `` rather than asking the model to run it — prefer that idiom, since it
puts deterministic output in front of the model instead of hoping it shells out.
