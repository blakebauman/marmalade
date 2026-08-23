# SLOP code reference

Every code names a threshold. A finding is a design judgment you can disagree
with by arguing about the number — not a style opinion.

Run: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" <path> --detail balanced`

Score starts at 100. Each finding costs 18 (error), 9 (warning), or 3 (info).

---

## SLOP001 — over the density budget

**Triggers** when node count exceeds the detail budget (7 / 12 / 24). Escalates
from warning to error past 1.5× the budget.

**Why it matters.** Past roughly a dozen labeled things a reader stops tracing
paths and starts skimming, which is the same as not reading the diagram.

**Fix.** Delete what the audience already knows. Collapse a cluster into one node
that links to its own diagram. Drop the tier the diagram is not about. Raising
the budget is the last resort and should be stated deliberately.

---

## SLOP002 — filler label

**Triggers** when a node label is one of ~40 generic words: `Process`, `Data`,
`System`, `Service`, `Handler`, `Module`, `Component`, `Layer`, `Step 1`, `Node`,
`Item`, and so on.

**Why it matters.** These name the shape rather than the thing. They are what a
generator emits when it does not know the domain, and they are the clearest
single signal of a machine-authored diagram.

**Fix.** Name the actual thing: `Stripe webhook receiver`, not `Handler`. If you
cannot name it, it probably should not be a node.

---

## SLOP003 — hedging label

**Triggers** on `various`, `multiple`, `several`, `some`, `many`, `etc.`,
`and more`, `...` inside a label.

**Why it matters.** A hedge is a note that the author did not decide. The reader
inherits the indecision.

**Fix.** Name the two that matter, or draw one node called what they have in
common. `Payment providers` beats `Various services`.

---

## SLOP004 — unlabeled edges

**Triggers** when fewer than a third of edges carry a label, and there are at
least four edges. Diagram-type aware: flowcharts want `|label|` or
`-- text -->`, sequence and state diagrams want `: text`, ER diagrams want
`: "text"`. Families with no edge-label grammar are skipped.

**Why it matters.** An unlabeled arrow asserts "related somehow". That is rarely
the claim worth drawing, and it hides whether the relationship is a call, a
dependency, a data flow, or a fallback.

**Fix.** Label the verb: `publishes`, `reads from`, `falls back to`,
`after 5 min`. If no verb fits, the edge is probably noise — delete it.

---

## SLOP005 — one shape for everything

**Triggers** on flowcharts and block diagrams with 6+ nodes that use a single
node shape.

**Why it matters.** Shape is free encoding that survives greyscale printing and
color blindness. Discarding it makes the reader read every label to learn what
kind of thing each node is.

**Fix.** `[(cylinder)]` for state, `{diamond}` for decisions, `([stadium])` for
external systems, `[[subroutine]]` for "detailed elsewhere".

---

## SLOP006 — rainbow palette

**Triggers** on more than three distinct fill colors across `classDef` and
`style` lines.

**Why it matters.** Past three fills, color stops being encoding and becomes
decoration. Readers try to decode a legend that does not exist.

**Fix.** One neutral for the system you own, one accent for the focal set, one
muted for external context. Use the five canonical roles in
`assets/templates/classdefs.mmd`.

---

## SLOP007 — nothing emphasized

**Triggers** on 8+ nodes with no `classDef` or `style` and no frontmatter, in
diagram families that support styling.

**Why it matters.** A diagram with no focal point makes the reader do the
ranking. The author knows which node the diagram is about; the diagram should say.

**Fix.** `class PaymentAuth focal` on the one or two nodes that carry the point.

---

## SLOP008 — emoji labels

**Triggers** on three or more labels containing emoji.

**Why it matters.** Emoji render inconsistently across PNG and PDF export paths,
depend on the rendering host's font stack, and carry no meaning for a screen
reader. They read as decoration standing in for encoding.

**Fix.** Encode kind with shape and position instead.

---

## SLOP009 — straight chain (info)

**Triggers** on a flowchart of 2–4 nodes and ≤3 edges with no branching.

**Why it matters.** `A → B → C` is a sentence rendered as an image: slower to
read, impossible to search, and it breaks in the terminal.

**Fix.** Write the sentence, or find the branch/cycle/boundary that made you want
a picture and draw that instead.

---

## SLOP010 — duplicate labels

**Triggers** when the same label text appears on more than one node.

**Why it matters.** Either they are the same node drawn twice — in which case the
diagram is lying about the topology — or the names are wrong.

**Fix.** Merge the nodes, or distinguish the names.

---

## SLOP011 — novel-length label

**Triggers** on any label over 60 characters.

**Why it matters.** Long labels force the renderer to wrap unpredictably, blow up
node geometry, and turn the diagram into a paragraph with boxes around it.

**Fix.** A node label is a name. Move the explanation into prose beside the
diagram or into `accDescr`.

---

## SLOP012 — default styling shipped (info)

**Triggers** on 5+ nodes with no frontmatter, no `classDef`, and no `%%{init}%%`.

**Why it matters.** Default Mermaid is a recognizable look, and increasingly it is
recognizable specifically as unedited generated output.

**Fix.** Add a `--- title: … ---` block and render with a marmalade theme preset so
the diagram reads as part of your documentation rather than as output pasted into it.
