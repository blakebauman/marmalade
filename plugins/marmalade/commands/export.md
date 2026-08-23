---
description: Render Mermaid sources to SVG, PNG, or PDF using a theme preset, skipping anything already current.
argument-hint: "[path] [--format svg,png,pdf] [--theme light|dark|high-contrast|colorblind-safe|print]"
allowed-tools: Bash, Read, Glob
---

Export the diagrams at `$ARGUMENTS`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_export.py" $ARGUMENTS
```

Defaults come from the plugin configuration: the diagram directory, the export
directory, the theme, and the format. Pass `--check` to report staleness without
rendering — that is the CI form and it exits 1 when anything is out of date.

## Notes

- The exporter lints first and refuses to render a diagram with a syntax error.
  Fix the diagram; use `--force` only when you know why.
- Fenced `mermaid` blocks in Markdown are rendered too. Name them with
  `id=some-name` in the fence for stable filenames.
- If no renderer is available, run `/marmalade:doctor` and report the install
  command rather than guessing.
- Light and dark must be separate runs into separate directories — Mermaid bakes
  colors into the output.

Report what was rendered, what was skipped as already current, and anything that
failed with its error. If the run was slow because `npx` fetched Chromium,
mention that installing `@mermaid-js/mermaid-cli` globally avoids paying that
again.
