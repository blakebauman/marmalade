---
name: diagram-review
description: Run a structured review of one or more diagrams across UX, information architecture, accessibility, security, and domain correctness, and convene the right specialist subagents. Use when asked to review, critique, audit, or improve a diagram, or before merging diagram changes.
license: MIT
compatibility: Requires Python 3.9+. Design critique delegates to the impeccable plugin when installed.
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Reviewing a diagram

A diagram review is not "does it look nice". It is five separate questions, and
they fail independently.

## Always start with the machine pass

Deterministic findings first, so human judgment is spent on what a script cannot
see:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_lint.py" <path>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" <path> --detail balanced
```

Report the score and the findings before offering an opinion. A diagram scoring
under 40 is slop; say so plainly and fix the mechanical problems before debating
anything subtler.

## The five questions

**1. Is it true?** Does the diagram match the system as built? Check the source:
read the routes, the schema, the CI config. A beautiful wrong diagram is worse
than no diagram, because it gets trusted. This is the question most reviews skip.

**2. Does it earn its place?** Would a paragraph teach more? Apply the
[no-slop](../no-slop/SKILL.md) gate. Be willing to conclude the diagram should
be deleted.

**3. Can a stranger read it in thirty seconds?** Where does the eye land first,
and is that the point? Is there a focal set of one or two nodes? Is reading
order — left-to-right for pipelines, top-down for hierarchies — matched to the
mental model?

**4. Is it readable without vision or color?** `accTitle` and `accDescr` present
and meaningful. Contrast passing. No meaning carried by color alone. See
[diagram-a11y](../diagram-a11y/SKILL.md).

**5. Does it leak?** Real hostnames, private IPs, credentials, internal team
names, unreleased product names. Diagrams travel further than code — into
tickets, decks, and screenshots. See
[threat-model-diagrams](../threat-model-diagrams/SKILL.md).

## Convene the bench

For a substantial review, dispatch the specialists in parallel rather than
answering all five yourself. Each returns findings; you synthesize.

| Agent | Answers |
| :-- | :-- |
| `marmalade:diagram-ux-reviewer` | Question 3 — visual hierarchy, focal point, reading order |
| `marmalade:ia-reviewer` | Question 3 — grouping, naming, abstraction level, what belongs in which diagram |
| `marmalade:a11y-reviewer` | Question 4 |
| `marmalade:security-reviewer` | Question 5, plus trust-boundary correctness |
| `marmalade:diagram-code-reviewer` | Question 1, against the actual source tree |
| `marmalade:dx-reviewer` | Whether the diagram toolchain is something a contributor can actually run |

Only convene the ones the diagram warrants. A three-node state diagram does not
need six reviewers; a system architecture diagram going into onboarding docs does.

When the [impeccable](https://impeccable.style) plugin is installed — it is a
declared dependency — `/impeccable critique` and `/impeccable audit` bring a
sharper visual-design lens than a general review. Use it for anything that will
be seen by people outside the team.

## Reporting

Group by severity, and be concrete:

- **Wrong** — the diagram misstates the system. Cite the file that proves it.
- **Unreadable** — a specific reader will fail on it. Say which reader and where.
- **Slop** — cite the SLOP code and its threshold.
- **Polish** — worth doing, does not block.

For each finding give the fix as a diff or a replacement line, not a description
of a fix. "Label the edge from Auth to Retry as `after 5 min`" beats "edges
should be labeled".

End with a verdict: ship, ship after the listed fixes, or redraw. If the honest
answer is "delete this and write two sentences", say that.

## Reviewing a change rather than a file

For a diff, focus on what moved:

```bash
git diff --name-only HEAD | grep -E '\.(mmd|mermaid|md)$'
```

Then ask the question that only applies to changes: **did the system change, or
did only the drawing change?** A diagram edit with no corresponding code change
is either a correction of a previously-wrong diagram — worth noting why — or
churn.
