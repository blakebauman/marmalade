---
type: script
command: python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" "${OUTPUT_DIR}" --json --min-score 95
expect: exit_zero_or_no_diagrams
---
Producing no diagram is a pass — this is the one case where the right answer may
be that none earns its place.

If a diagram *is* produced it must be near-perfect (95+), not merely acceptable.
A threshold of 80 let through a run that scored 82 with eight distinct fill
colours and a duplicated label: the rubric flagged it as decoration and the
grader passed it anyway. The whole point of this case is that padding and
colour-as-decoration are the failure, so the bar has to sit above "acceptable".
