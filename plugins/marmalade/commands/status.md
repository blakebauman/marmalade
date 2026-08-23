---
description: Report the state of this project's diagrams — inventory, drift, scores, and what to fix next.
argument-hint: "[diagram dir] [--docs root]"
allowed-tools: Bash, Read, Glob
---

## Inventory and drift

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/docs_sync.py" --json 2>&1 | head -80`

## Rubric scores

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" --json 2>&1 | head -120`

## Lint findings

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_lint.py" --json 2>&1 | head -80`

## Your task

This is a **read-only status pass**. Do not fix anything, do not render anything,
and do not write a diagram. Report, then stop.

Read the three reports above and give the user a short, scannable picture:

1. **What exists.** How many diagram sources, how many rendered artifacts, where
   they live. One line.
2. **What drifted.** From the sync report: `stale` (source changed since the
   render), `unrendered`, `orphaned` (artifact whose source is gone),
   `broken_references` (a doc pointing at a missing image), and
   `unreferenced_artifacts`. Name the files — do not just give counts. If
   `in_sync` is true, say so in one line and move on.
3. **What is weakest.** From the rubric report: the lowest-scoring diagrams with
   their scores and verdicts, and the single most common finding code across the
   set. Do not list every diagram — name the three worst and the pattern.
4. **What is broken or inaccessible.** From the lint report: errors first, then
   whether `accTitle`/`accDescr` are missing anywhere (MMD210/MMD211), since that
   is the accessibility floor.
5. **The next step.** One concrete command, and why it is the one that matters
   most right now.

If the diagram directory does not exist or holds no sources, say that plainly and
point at `/marmalade:draw` to author the first one — do not report empty tables.

If a report failed to run rather than returning empty results, say which one and
what the error was; do not silently present partial state as complete. For an
environment problem — a missing renderer, a missing `psql` — point at
`/marmalade:doctor`, which is the environment check; this command reports on the
diagrams themselves.
