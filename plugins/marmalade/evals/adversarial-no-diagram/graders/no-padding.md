---
type: script
command: python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" "${OUTPUT_DIR}" --json --min-score 80
expect: exit_zero_or_no_diagrams
---
If the run produced a diagram at all, it must still clear 80 on the rubric — a
padded fifteen-box chain of filler labels scores far below that. Producing no
diagram is also a pass here: this is the one case where the correct answer may be
that no diagram earns its place.
