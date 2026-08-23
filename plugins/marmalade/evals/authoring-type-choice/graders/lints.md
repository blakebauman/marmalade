---
type: script
command: python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_lint.py" "${OUTPUT_DIR}" --errors-only
expect: exit_zero
---
Whatever is produced must be syntactically valid Mermaid with no error-severity
findings.
