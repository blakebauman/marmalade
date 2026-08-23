---
type: script
command: python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_lint.py" "${OUTPUT_DIR}" --errors-only
expect: exit_zero
---
The ERD must be valid Mermaid with no error-severity findings.
