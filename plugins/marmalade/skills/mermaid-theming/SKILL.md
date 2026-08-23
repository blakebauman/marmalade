---
name: mermaid-theming
description: Build and apply a Mermaid visual system — theme presets, themeVariables, brand tokens, light/dark pairs, and contrast-verified palettes. Use when a diagram needs to match a brand, when choosing or authoring a theme, or when diagrams look like default Mermaid output.
license: MIT
compatibility: Requires Python 3.9+ for the contrast checker.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Theming Mermaid

Default Mermaid is a recognizable look, and increasingly it reads as "nobody
edited this". A theme is the cheapest way to make a diagram belong to your
documentation instead of sitting on top of it.

## Use a preset first

Five presets ship with this plugin, all verified against WCAG AA:

| Preset | For |
| :-- | :-- |
| `light` | Default. Docs sites, READMEs on light backgrounds |
| `dark` | Dark-mode docs, terminals, dark slide decks |
| `high-contrast` | Maximum legibility — projection, low vision, bad monitors |
| `colorblind-safe` | Okabe–Ito palette. Use when color carries meaning |
| `print` | Greyscale-safe, neutral. Handouts and PDFs |

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_export.py" docs/diagrams --theme dark
```

Ship light and dark as separate artifacts rather than trying to make one SVG work
on both — Mermaid bakes colors into the output.

## How Mermaid theming actually works

Two layers, and confusing them is the usual source of frustration:

1. **The theme** — `default`, `neutral`, `dark`, `forest`, `base`. Only `base` is
   customizable. Any config that sets `themeVariables` must set
   `"theme": "base"`, or the variables are ignored.
2. **`themeVariables`** — the token map. Mermaid *derives* most colors from a
   few roots, so setting `primaryColor` moves `primaryBorderColor`,
   `primaryTextColor`, and several diagram-specific colors with it.

Mermaid accepts **hex only**. `red` does not work; `#ff0000` does.

Three places to apply a theme, in increasing order of preference:

- **Inline `%%{init: {...}}%%`** — pins styling into the source. Avoid: one theme
  change then means editing every diagram.
- **Frontmatter `config:` block** — per-diagram override. Fine for a genuine
  one-off.
- **A config file at render time** (`mmdc -c theme.json`) — the right default.
  One file, every diagram, one change to restyle the docs.

## The token set worth setting

Set these and let Mermaid derive the rest:

```json
{
  "theme": "base",
  "fontFamily": "ui-sans-serif, -apple-system, \"Segoe UI\", Roboto, sans-serif",
  "themeVariables": {
    "darkMode": false,
    "background": "#ffffff",
    "primaryColor": "#e8effb",
    "primaryTextColor": "#10203a",
    "primaryBorderColor": "#3f6fd1",
    "lineColor": "#5a6272",
    "textColor": "#10203a",
    "mainBkg": "#e8effb",
    "nodeBorder": "#3f6fd1",
    "clusterBkg": "#f6f7f9",
    "clusterBorder": "#878d9c",
    "edgeLabelBackground": "#ffffff"
  }
}
```

The full variable list, grouped by diagram family, is in
[reference/theme-variables.md](reference/theme-variables.md).

## Brand onboarding

To build a branded theme:

1. Copy `${CLAUDE_PLUGIN_ROOT}/assets/themes/brand.template.json`.
2. Fill six tokens from the brand: `TOKEN_SURFACE` (page background),
   `TOKEN_INK` (body text), `TOKEN_BRAND` (primary brand color, used for
   borders), `TOKEN_BRAND_TINT` (a ~10% tint of it, used for fills),
   `TOKEN_MUTED` (secondary text and lines), `TOKEN_FONT_STACK`.
3. Delete the `_comment` key.
4. **Verify contrast before shipping.** Brand palettes routinely fail:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_contrast.py" my-brand.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_contrast.py" my-brand.json --level AAA
```

Text pairs must clear 4.5:1, borders 3:1. When a pair fails, darken the
foreground or lighten the background — and because Mermaid derives colors,
fixing the primary pair often fixes several rows at once.

A brand color that fails as a *fill* often passes as a *border*. That is usually
the right move: tint the fill, keep the saturated brand color on the stroke.

## One accent, and the five roles

Theme variables set the baseline. Emphasis is per-diagram, through `classDef`.
Use the five canonical roles in
`${CLAUDE_PLUGIN_ROOT}/assets/templates/classdefs.mmd` and no others:

```
classDef focal    fill:#dbeaf5,stroke:#0072B2,stroke-width:2px,color:#062033
classDef primary  fill:#f4f6f9,stroke:#5a6272,stroke-width:1px,color:#10203a
classDef external fill:#ffffff,stroke:#767676,stroke-width:1px,stroke-dasharray:4 3,color:#3b414d
classDef store    fill:#f4f6f9,stroke:#4a7a52,stroke-width:1px,color:#14261a
classDef risk     fill:#fbe4dc,stroke:#D55E00,stroke-width:2px,color:#5a2000
```

`focal` goes on one or two nodes, never more. That constraint is the whole point:
it forces you to decide what the diagram is about.

## Never encode meaning in color alone

Roughly 1 in 12 men has a color vision deficiency, and every diagram eventually
gets printed in greyscale. Pair color with a second channel — shape, border
style, position, or a label. The `colorblind-safe` preset uses the Okabe–Ito
palette, which stays distinguishable under the common deficiencies, but it is a
floor, not a substitute for redundant encoding.

## Custom CSS

`mmdc -C custom.css` injects CSS into the render. Useful for typography and
hover states in SVG output. Two caveats: inline CSS can be blocked by a host's
Content-Security-Policy, and CSS does not survive PNG or PDF rasterization any
better than themeVariables do — so put anything structural in the config file.
