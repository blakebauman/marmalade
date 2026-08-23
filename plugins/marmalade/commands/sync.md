---
description: Find every way the diagrams, rendered images, and documentation have drifted apart, and fix what is mechanically fixable.
argument-hint: "[docs root]"
allowed-tools: Bash, Read, Grep, Glob, Agent
---

Check diagram/doc drift under `$ARGUMENTS` (default: the repository root).

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/docs_sync.py" --docs $ARGUMENTS
```

Five kinds of drift, detected by content hash rather than modification time:
**stale**, **unrendered**, **orphaned**, **broken** links, and **unused**
artifacts.

## Fixing

- stale and unrendered → re-run the export
- orphaned → delete the artifact
- broken → fix the path, or render the missing diagram
- unused → judgment call; link it or delete it

Apply the mechanical fixes after confirming with the user, then re-run to show a
clean result.

## The harder question

Drift detection catches "the render does not match the source". It cannot catch
"the source does not match the system". For any diagram whose source is older
than the code it describes, hand it to `marmalade:diagram-code-reviewer` rather
than assuming it is fine.

For a full toolchain audit — whether a contributor can actually find, edit, and
render these diagrams — use `marmalade:dx-reviewer`.
