---
name: mermaid-authoring
description: Write correct, readable Mermaid source — choosing the right diagram type, using the syntax that renders, and avoiding the parse errors that bite most often. Use when creating or editing any .mmd file or `mermaid` block.
license: MIT
compatibility: Requires Python 3.9+ for the bundled validator.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Authoring Mermaid

Before writing a line, apply the [no-slop](../no-slop/SKILL.md) gate: does this
diagram earn its place, and what is the density budget?

## Choose the type from what prose is bad at

| The point you are making | Type |
| :-- | :-- |
| Branching, conditional paths, retries | `flowchart` |
| Who talks to whom, in what order | `sequenceDiagram` |
| Legal and illegal transitions of one thing | `stateDiagram-v2` |
| Entities and their cardinality | `erDiagram` |
| Structure of types and their relationships | `classDiagram` |
| Work over calendar time | `gantt` |
| Branch and release topology | `gitGraph` |
| Proportions of a whole (rarely worth it) | `pie` |
| Positioning on two axes | `quadrantChart` |
| Flow volumes between stages | `sankey-beta` |
| Nested containment of infrastructure | `architecture-beta` or `flowchart` with subgraphs |

Prefer `flowchart` over the legacy `graph` keyword — it gets the newer renderer,
better edge routing, and the newer shape set.

Start from a template rather than a blank file:
`${CLAUDE_PLUGIN_ROOT}/assets/templates/` has vetted `flowchart`, `sequence`,
`state`, `erd`, `architecture`, and `threat-model` examples, all scoring 100 on
the slop rubric.

## The frontmatter and accessibility header

Every diagram opens the same way:

```
---
title: Order submission
---
flowchart LR
    accTitle: Order submission
    accDescr: A submitted cart is authorized by the payment provider. Authorized
      orders go to the warehouse; declined orders enter a retry queue.
```

`title` drives the rendered caption. `accTitle` and `accDescr` are what a screen
reader announces, and writing `accDescr` is the fastest way to find out whether
your diagram actually has a point.

## The parse errors that bite

**`end` as a node id.** `A --> end` silently breaks the flowchart parser. `end`,
`graph`, `subgraph`, `class`, `click`, `style`, `linkStyle`, `classDef`,
`direction`, `default`, `call`, `href`, and `callback` are all reserved. Rename
the id — the label can still read "end".

**Brackets inside an unquoted label.** `A[array[0]]` fails. Quote it:
`A["array[0]"]`.

**A label spanning lines.** Node shapes must open and close on one line. Use
`<br/>` for a line break inside a label.

**Unmatched `subgraph` / `end`.** Every `subgraph` needs exactly one `end`.

**An invalid direction.** Only `TB`, `TD`, `BT`, `RL`, `LR`.

**Special characters.** `#` starts an entity code, so quote labels containing it.
Quotes inside labels need `&quot;`.

Validate before you ship:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_lint.py" docs/diagrams
```

The PostToolUse hook runs this automatically on every diagram you write, and
blocks on syntax errors when `strict_validation` is on.

Detailed per-type syntax lives in
[reference/diagram-types.md](reference/diagram-types.md).

## Shapes carry meaning

```
Svc[API service]           rectangle — a service or process you own
DB[(Postgres)]             cylinder  — durable state
Ok{Authorized?}            diamond   — a decision
Ext([Stripe API])          stadium   — external system, or a terminal
Sub[[Fulfilment]]          subroutine — detailed in its own diagram
```

Use them consistently and the reader parses the structure before reading a word.

## Subgraphs are boundaries, not folders

A `subgraph` should mean something: a trust boundary, a network, a deployment
unit, a team's ownership. Give it a quoted human label:

```
subgraph Edge["Edge — Cloudflare"]
    CDN[CDN] --> Worker[Edge worker]
end
```

Grouping nodes just because they are related visually is decoration.

## Edges say what they mean

```
A -->|publishes| B          labeled, directed
A -.->|async, best effort| B  dotted for weak or optional coupling
A ==>|hot path| B           thick for emphasis
A --- B                     undirected — rarely what you want
```

Label the verb or delete the edge.

## Where to go next

- [no-slop](../no-slop/SKILL.md) — the rubric this all serves
- [mermaid-theming](../mermaid-theming/SKILL.md) — the visual system
- [mermaid-export](../mermaid-export/SKILL.md) — rendering to SVG/PNG/PDF
- [diagram-a11y](../diagram-a11y/SKILL.md) — accessibility beyond `accDescr`
