---
description: Check that everything Marmalade needs is installed and configured, and report what to do about anything missing.
allowed-tools: Bash, Read
---

## Environment report

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_doctor.py"`

## Your task

Read the report above and summarize it for the user in two or three sentences:
what is ready, what is missing, and the single next command to run if anything
is blocking. Do not restate the whole table — they can see it.

If a renderer is missing, give the install command. If the diagram directory does
not exist, offer to create it with a starter diagram from
`${CLAUDE_PLUGIN_ROOT}/assets/templates/`.
