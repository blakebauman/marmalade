---
description: Apply a theme preset, or build and contrast-verify a brand theme for Mermaid diagrams.
argument-hint: "[preset name | 'brand' | path to config]"
allowed-tools: Read, Write, Edit, Bash, Glob
---

Theme request: **$ARGUMENTS**

Load the [mermaid-theming](../skills/mermaid-theming/SKILL.md) skill first.

## If a preset was named

Presets: `light`, `dark`, `high-contrast`, `colorblind-safe`, `print`. All five
pass WCAG AA. Render with it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_export.py" <path> --theme <preset>
```

## If a brand theme was asked for

1. Copy `${CLAUDE_PLUGIN_ROOT}/assets/themes/brand.template.json`.
2. Fill the six tokens from the brand: surface, ink, brand, brand tint, muted,
   font stack. Ask for the hex values if you do not have them — Mermaid accepts
   hex only, never color names.
3. Delete the `_comment` key.
4. **Verify before shipping.** Brand palettes routinely fail:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_contrast.py" <config.json>
```

Text pairs need 4.5:1, borders 3:1. When a pair fails, prefer tinting the fill
toward the surface and keeping the saturated brand color on the stroke — a
border only needs 3:1. Because Mermaid derives colors from a few roots, fixing
the primary pair often clears several rows; re-run the checker after each change
rather than reasoning about the derivation.

## Always

Remind the user that `themeVariables` only applies with `"theme": "base"` — any
other theme silently discards them, which is the most common theming
frustration. Report the contrast results, not just that you wrote the file.
