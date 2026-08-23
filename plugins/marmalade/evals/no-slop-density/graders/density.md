---
type: script
command: python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" "${OUTPUT_DIR}" --json --min-score 80
expect: exit_zero
---
Every diagram written during the run must score at least 80 on the no-slop
rubric. This is the deterministic floor: over-budget node counts, filler labels,
unlabeled edges, and default styling all pull the score below it.
