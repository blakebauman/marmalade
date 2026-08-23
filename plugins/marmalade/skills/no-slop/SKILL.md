---
name: no-slop
description: The rubric that separates a diagram worth drawing from Mermaid slop. Use whenever creating, generating, reviewing, or accepting a Mermaid diagram — before writing the source, and again before shipping it. Covers the earn-its-place gate, density budgets, focal emphasis, labeling discipline, and the twelve SLOP codes.
license: MIT
compatibility: Requires Python 3.9+. Diagram rendering additionally requires Node.js with @mermaid-js/mermaid-cli or npx.
allowed-tools: Read, Grep, Glob, Bash
---

# No slop

Mermaid makes it trivial to produce a diagram. That is the problem. A model asked
for "a diagram of the system" will reliably emit fifteen identical rectangles
labeled `Service`, `Handler`, and `Data`, joined by unlabeled arrows, in the
default theme. It parses. It renders. It teaches nothing. That is slop.

This skill is the standard everything else in this plugin enforces. Apply it
before writing a diagram and again before shipping one.

## The gate: does this diagram earn its place?

Ask, out loud, before writing any Mermaid:

> **Would a reader learn more from this diagram than from a well-written paragraph?**

A diagram earns its place when it shows something prose is bad at:

| Prose is bad at | So draw |
| :-- | :-- |
| Branching and conditionals | flowchart with labeled decision edges |
| Ordering across participants | sequenceDiagram |
| Cycles and feedback | flowchart or stateDiagram with a back edge |
| Cardinality between entities | erDiagram |
| Boundaries and containment | subgraphs |
| Lifecycle with illegal transitions | stateDiagram-v2 |

A diagram does **not** earn its place when it is:

- A list. Write a list.
- A before/after comparison. Write a table.
- A linear chain, `A → B → C`, with no branch. Write the sentence.
- A single box. Write the noun.
- A restatement of the section heading above it.

Say so when the answer is no. Refusing to draw is a valid, and often correct,
outcome. Offer the paragraph instead.

## Density budget

Pick a detail level up front and hold to it. The number is the count of labeled
nodes, and it is not a soft target.

| Detail | Budget | For |
| :-- | --: | :-- |
| `simplified` | 7 | A slide, an executive, a landing page, a README hero |
| `balanced` | 12 | The default. Docs, design reviews, onboarding |
| `faithful` | 24 | A reference diagram someone will sit and study |

When over budget, cut in this order:

1. **Delete what the reader already knows.** No "Browser" node in a diagram for
   frontend engineers.
2. **Collapse a cluster into one node that links to its own diagram.** Two
   readable diagrams beat one unreadable one.
3. **Drop the tier you are not talking about.** An auth-flow diagram does not
   need the analytics pipeline.
4. **Only then** consider raising the budget, and say why in the commit message.

The highest-quality edit is almost always deletion.

## One accent, one point

A diagram is *about* something. Mark it.

- **One accent color**, on **one or two nodes**. That is the focal set.
- Everything else is neutral — the system you own — or muted with a dashed
  border — something you call but do not control.
- More than three fill colors reads as decoration, not encoding.

Use the canonical roles in `${CLAUDE_PLUGIN_ROOT}/assets/templates/classdefs.mmd`:
`focal`, `primary`, `external`, `store`, `risk`. Five roles, no more, so a reader
learns the vocabulary once and carries it across every diagram in the repo.

## Labeling discipline

**Nodes are named things, not shapes.** `Stripe webhook receiver`, not `Handler`.
If you cannot name a node, it probably should not be a node.

**Edges are verbs.** An unlabeled arrow asserts "related somehow", which is not a
claim worth drawing. Label it — `publishes`, `reads from`, `falls back to`,
`after 5 min` — or delete the edge.

**Never hedge.** "Various services", "multiple sources", "etc." are notes that
the author did not decide. Name the two that matter, or draw one node called
what they have in common.

**Labels are names, not sentences.** Over ~60 characters, the explanation belongs
in prose beside the diagram or in `accDescr`.

## Shape is free encoding

Mermaid gives you shapes at no cost. Use them consistently and the reader parses
the diagram before reading a single word.

| Shape | Means |
| :-- | :-- |
| `[Rectangle]` | A service or process you own |
| `[(Cylinder)]` | Durable state — a database, a bucket, a queue |
| `{Diamond}` | A decision or branch point |
| `([Stadium])` | An external system, or a start/end terminal |
| `[[Subroutine]]` | A step defined in detail elsewhere |
| `subgraph` | A trust, network, or ownership boundary |

Eight nodes all drawn as rectangles means eight opportunities discarded.

## Always: the accessible pair

Every diagram carries `accTitle` and `accDescr`. Not optional, not a nice-to-have.

```
accTitle: Order submission
accDescr: A submitted cart is authorized by the payment provider. Authorized orders
  go to the warehouse; declined orders enter a retry queue that re-attempts once
  after five minutes before being abandoned.
```

Write `accDescr` as the paragraph a reader would get if the image failed to load.
Writing it is also the fastest way to discover that your diagram has no point —
if the description is hard to write, the diagram is unclear.

## Run the check

The rubric is enforced deterministically. Every finding names a threshold, so a
reviewer argues with a number rather than a vibe.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" docs/diagrams --detail balanced
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" docs/diagrams --min-score 70   # CI gate
```

Scores: 90+ clean, 70–89 acceptable, 40–69 slop-leaning, under 40 slop.

The twelve codes are catalogued in [reference/slop-codes.md](reference/slop-codes.md),
each with what triggers it and how to fix it. Read that file when a finding needs
explaining or disputing.

## Order of work

1. Apply the gate. If it fails, say so and write the paragraph.
2. Pick the diagram type from what prose is bad at, not from habit.
3. Pick a detail level and hold the budget.
4. Draft with real names and verb edges.
5. Add `accTitle` / `accDescr`.
6. Mark the focal set — one or two nodes.
7. Run `marmalade_slop.py`. Fix findings or justify them explicitly.
8. Render with a theme preset, never with Mermaid defaults.

Related: [mermaid-authoring](../mermaid-authoring/SKILL.md) for syntax,
[mermaid-theming](../mermaid-theming/SKILL.md) for the visual system,
[diagram-review](../diagram-review/SKILL.md) to convene the reviewer bench.
