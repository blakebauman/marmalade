---
description: Draft a new Mermaid diagram — picks the right type for the question, holds a density budget, and validates before handing it back.
argument-hint: "[what the diagram should show]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
---

Draw a diagram for: **$ARGUMENTS**

## Before drawing

Load the [no-slop](../skills/no-slop/SKILL.md) skill and apply its gate. Establish:

- **What question does this answer?** If the request has no question in it, ask
  for one — "the architecture" is not a diagram brief.
- **Who reads it?** This sets the budget: simplified (7 nodes), balanced (12),
  faithful (24).
- **Where does it live?** README, runbook, slide, design doc.

If a paragraph would teach more than a picture, say so and write the paragraph
instead. That is a successful outcome.

## Drawing

For anything non-trivial, delegate to `marmalade:mermaid-architect`, which owns
type selection and drafting. For a diagram derived from existing code,
infrastructure, or a database, use the matching specialist instead:
`marmalade:python-diagrammer`, `marmalade:devops-diagrammer`, or
`marmalade:postgres-erd-engineer`.

Start from a template in `${CLAUDE_PLUGIN_ROOT}/assets/templates/` rather than a
blank file.

## Before handing it back

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_lint.py" <file>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" <file> --detail <level>
```

Report the diagram, the type and why, the budget, what you deliberately left out,
and the slop score. Do not hand back a diagram you have not scored.
