---
description: Score diagrams against the no-slop rubric — density budget, filler labels, unlabeled edges, focal emphasis, palette discipline — and report what to fix.
argument-hint: "[path] [--detail simplified|balanced|faithful]"
allowed-tools: Bash, Read, Grep, Glob
---

Score the diagrams at `$ARGUMENTS` (default: the configured diagram directory).

## Run

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" $ARGUMENTS
```

If no path was given, run it against the configured diagram directory. If a
`--detail` level was not given, use `balanced`.

## Then

Read the [no-slop](../skills/no-slop/SKILL.md) rubric and the
[SLOP code reference](../skills/no-slop/reference/slop-codes.md) before
interpreting results.

Report:

1. **The scores**, worst first. 90+ clean, 70–89 acceptable, 40–69 slop-leaning,
   under 40 slop.
2. **The three findings that cost the most**, with the concrete fix as a
   replacement line — not a description of a fix.
3. **Whether any diagram should be deleted rather than fixed.** A SLOP009 on a
   three-node chain usually means the answer is a sentence. Say so.

Offer to apply the fixes. Do not apply them without asking unless the user
already said to.
