# Installing Marmalade

Marmalade is built as a Claude Code plugin. Most of what makes it useful — the
hooks, the slash commands, the subagent bench, the Python toolchain — only exists
inside Claude Code. The skills alone can be copied to other hosts, with real
caveats; see [What travels, and what doesn't](#what-travels-and-what-doesnt).

## Requirements

| | |
| --- | --- |
| Python 3.9+ | required — the whole toolchain |
| Node.js | only for rendering; `npx` fetches `@mermaid-js/mermaid-cli` on demand |
| `psql` | only for live ERD introspection; `--sql-file` works without it |

Run `/marmalade:doctor` after installing — it reports exactly what is missing and
the command to fix it.

## Claude Code — plugin (recommended)

```
/plugin marketplace add blakebauman/marmalade
/plugin install marmalade@marmalade
```

Marmalade depends on [impeccable](https://impeccable.style) for visual-design
critique, so add that marketplace too:

```
/plugin marketplace add pbakaus/impeccable
```

The shell equivalents:

```bash
claude plugin marketplace add blakebauman/marmalade
claude plugin install marmalade@marmalade
```

To update:

```
/plugin marketplace update marmalade
/reload-plugins
```

### Configuration

Marmalade ships a `userConfig` schema, so `/plugin` gives you a settings form for
the diagram directory, export directory, default theme, export formats, and the
two hook toggles. Every setting can also be overridden per-shell:

```bash
export MARMALADE_DIAGRAM_DIR=docs/architecture
export MARMALADE_EXPORT_DIR=docs/architecture/rendered
export MARMALADE_THEME=dark
```

Precedence is `explicit CLI flag > MARMALADE_* > /plugin userConfig > default`.

### Pinning Marmalade for a whole team or project

Commit `.claude/settings.json` so everyone on the repo gets the same version:

```json
{
  "extraKnownMarketplaces": {
    "marmalade": { "source": { "source": "github", "repo": "blakebauman/marmalade" } },
    "impeccable": { "source": { "source": "github", "repo": "pbakaus/impeccable" } }
  },
  "enabledPlugins": { "marmalade@marmalade": true }
}
```

### From a release artifact

Every `v*` tag publishes `marmalade.plugin` on the GitHub Release. Unzip it into
your plugins directory if you would rather pin a build than track a branch.

## Claude Code — manual copy (no plugin system)

Clone the repo and point at the plugin directory:

```bash
git clone https://github.com/blakebauman/marmalade.git ~/src/marmalade

# user scope — every project
ln -s ~/src/marmalade/plugins/marmalade/skills/* ~/.claude/skills/

# or project scope — this repo only
ln -s ~/src/marmalade/plugins/marmalade/skills/* .claude/skills/
```

Symlinking from one clone means `git pull` updates every project at once. Note
this gets you the **skills only** — not the hooks, commands, or subagents, which
the plugin manifest is what installs.

## Other hosts

The skills are Markdown with YAML frontmatter and can be copied into any host
that reads Agent Skills — Claude.ai and Claude Desktop (zip a single skill
folder), Cursor (`.cursor/skills`, project-scoped), Codex CLI
(`codex --enable skills`), Gemini CLI (`~/.gemini/skills`). Read the next section
first, because Marmalade degrades further than most skill collections do.

## What travels, and what doesn't

Be clear-eyed about this. Marmalade's skills are **not self-contained prose** —
they are instructions for driving a Python toolchain that lives at the plugin
root and is referenced as `${CLAUDE_PLUGIN_ROOT}/scripts/...`. Copy a single skill
folder to another host and the folder arrives, but:

- `${CLAUDE_PLUGIN_ROOT}` is not expanded, so every script path dangles. The
  linter, the slop scorer, the exporter, the contrast checker, and the ERD and
  import-graph generators are all unreachable.
- The 4 hooks (secret scan before write, validation after write, drift check on
  stop, session context) are Claude Code only.
- The 8 slash commands and 12 subagents are Claude Code only.
- The theme presets and templates live under `assets/`, outside the skill folder.

What you keep is the **judgment**: the no-slop rubric, the density budgets, the
diagram-type selection guidance, the labeling and emphasis discipline, the
accessibility checklist. That is genuinely most of the value for authoring by
hand — but nothing is verified, scored, or rendered for you.

If you want Marmalade on another host, copy the whole `plugins/marmalade` tree
rather than an individual skill, so at least the relative structure survives, and
expect to invoke the Python scripts yourself.
