---
description: Review diagrams across correctness, information architecture, visual hierarchy, accessibility, and disclosure — convening the specialist reviewers the diagram warrants.
argument-hint: "[path or 'diff']"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

Review the diagrams at `$ARGUMENTS`. With no argument, review the diagrams
changed in the current diff; if the tree is clean, review the configured diagram
directory.

## 1. Machine pass first

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_lint.py" <path>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" <path>
```

Report the findings before offering any opinion. A diagram scoring under 40 is
slop — say so and fix the mechanical problems before debating anything subtler.

## 2. Convene the bench

Follow the [diagram-review](../skills/diagram-review/SKILL.md) skill. Dispatch
only the reviewers the diagram warrants, in parallel:

| Agent | Question |
| :-- | :-- |
| `marmalade:diagram-code-reviewer` | Is it true? |
| `marmalade:ia-reviewer` | Is it structured right? |
| `marmalade:diagram-ux-reviewer` | Can a stranger read it in 30 seconds? |
| `marmalade:a11y-reviewer` | Does it work without sight or color? |
| `marmalade:security-reviewer` | Does it leak? |

A three-node state diagram does not need five reviewers. A system architecture
diagram going into onboarding docs does.

When the `impeccable` plugin is available, use `/impeccable critique` for
anything customer-facing and fold its findings in rather than duplicating them.

## 3. Synthesize

Group by severity — **wrong**, **unreadable**, **slop**, **polish** — deduplicate
across reviewers, and give each fix as a replacement line or diff. End with a
verdict: ship, ship after the listed fixes, or redraw. If the honest answer is
"delete this and write two sentences", say that.
