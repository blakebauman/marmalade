---
name: diagram-a11y
description: Make Mermaid diagrams usable without vision and without color perception — accTitle/accDescr, contrast thresholds, redundant encoding, and the text alternative that carries the content. Use when reviewing diagrams for accessibility, fixing contrast, or when a diagram encodes meaning in color.
license: MIT
compatibility: Requires Python 3.9+ for the contrast checker.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Accessible diagrams

A diagram is the least accessible thing in most documentation. It carries the
architecture, and it is the one element that conveys nothing to a screen reader
by default. Three obligations, in order of how often they are skipped.

## 1. The text alternative — non-negotiable

Every diagram carries both:

```
accTitle: Order submission
accDescr: A submitted cart is authorized by the payment provider. Authorized
  orders go to the warehouse pick list; declined orders enter a retry queue that
  re-attempts once after five minutes before being abandoned.
```

Mermaid renders these into the SVG's `<title>` and `<desc>`, wired to the
diagram's accessible name. Without them a screen reader announces "image" or
reads out node ids.

**`accTitle`** is a short name — what you would call the diagram in conversation.

**`accDescr`** is the paragraph a reader gets if the image never loads. Describe
the *content and its shape*, not the picture: "authorized orders go to the
warehouse; declined orders retry once" — not "three boxes connected by arrows".

For multi-line descriptions:

```
accDescr {
    The upload path crosses two trust boundaries. Untrusted browser traffic
    enters at the API gateway, where size, MIME type, and auth are checked.
    Clean files reach the object store; infected files are quarantined.
}
```

Writing `accDescr` is also a design tool. If it is hard to write, the diagram
does not have a clear point yet — fix the diagram, not the description.

## 2. Contrast

Diagram text must clear **4.5:1** against its own fill, and borders **3:1**
against the surface behind them. Borders matter as much as text: a border a
reader cannot perceive means a node with no edges.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_contrast.py" assets/themes/light.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_contrast.py" my-brand.json --level AAA
```

All five bundled presets pass AA. Brand palettes usually do not on first try —
the common failure is a mid-tone brand color used as both fill and text.

When a pair fails, prefer changing the *fill* rather than the text: tint the fill
toward the surface and keep the saturated brand color on the stroke, where it
only has to clear 3:1.

## 3. Never encode meaning in color alone

WCAG 1.4.1. Roughly 1 in 12 men has a color vision deficiency, and every diagram
eventually gets printed in greyscale or screenshotted through a filter.

Pair every color distinction with a second channel:

| Meaning | Color | Plus |
| :-- | :-- | :-- |
| Focal / the point | Accent fill | Thicker stroke (`stroke-width:2px`) |
| External system | Muted | Dashed border (`stroke-dasharray:4 3`) |
| Durable state | Any | Cylinder shape `[(…)]` |
| Failure path | Warm accent | The edge label says why |
| Decision | Any | Diamond shape `{…}` |

The `colorblind-safe` preset uses the Okabe–Ito palette, which stays
distinguishable under deuteranopia, protanopia, and tritanopia. It is a floor,
not a replacement for redundant encoding.

## Beyond the diagram

**Contrast is not the only reason a diagram is unreadable.** Over the density
budget, a diagram is inaccessible to everyone. See
[no-slop](../no-slop/SKILL.md).

**Do not use an image where text works.** A three-node chain rendered as PNG is
strictly worse for every reader than the sentence it encodes.

**Keep the source next to the render.** A reader who cannot parse the image can
often read the Mermaid source, which is plain text and diffable. Link to it, or
keep the fenced block in the document rather than only shipping the PNG.

**Give the image an alt attribute too.** `accDescr` lives inside the SVG; a
Markdown `![...]()` alt is what a reader gets when the SVG is embedded as an
image. Use a short pointer — `![Order submission flow](order-flow.svg)` — and let
`accDescr` carry the detail.

**Do not autoplay motion.** Nothing in Mermaid animates by default; if you add
CSS animation via `--css`, honor `prefers-reduced-motion`.

## Checking a whole repository

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_lint.py" docs/
```

MMD210 and MMD211 flag every diagram missing `accTitle` or `accDescr`. They are
warnings rather than errors so they never block a write, but a repository with
open MMD210s has diagrams nobody can read without seeing them.
