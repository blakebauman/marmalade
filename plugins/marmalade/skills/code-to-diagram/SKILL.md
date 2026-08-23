---
name: code-to-diagram
description: Derive diagrams from a codebase — Python import graphs, request paths, CI/CD pipelines, infrastructure topology — with density budgets enforced so generated output does not become a hairball. Use when asked to diagram existing code, visualize dependencies, or document architecture from the source.
license: MIT
compatibility: Requires Python 3.9+. Import-graph analysis reads source with ast and executes nothing.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Code to diagram

Generated diagrams are the single largest source of Mermaid slop. Point a tool at
a codebase, get 200 nodes, ship a hairball. Everything here is built to refuse
that.

## Python import graphs

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/py_diagram.py" src/myapp --detail balanced
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/py_diagram.py" src/myapp --level package -o docs/diagrams/imports.mmd
```

Reads imports with `ast` — nothing is imported or executed. Only *internal*
imports are drawn; stdlib and third-party packages are noise in an architecture
diagram.

**The budget is enforced, not suggested.** At `--level auto` (the default), if the
module graph exceeds the detail budget the tool collapses to package level and
says so in `accDescr`. If it is still over budget after collapsing, it tells you
— and at that point the finding is about the code, not the diagram. A package
graph that cannot be drawn in 12 nodes is a package graph worth discussing.

The two highest fan-in nodes are marked `focal` automatically, with a comment
recording the counts. Fan-in is the useful signal in an import graph: it shows
what everything depends on, which is what breaks when it changes.

## The general method for any codebase

A tool can extract topology. It cannot decide what the diagram is about. Do this:

**1. Decide the question first.** "How does a request reach the database?" is a
diagram. "What is the architecture?" is not — it has no boundary, so it produces
everything.

**2. Find the real entry points.** Route tables, `main`, CLI definitions,
handlers, queue consumers, cron entries. Grep for the framework's registration
idiom rather than guessing.

**3. Trace one path, not all paths.** Follow a single representative request or
job end to end. That path is the diagram. Other paths are other diagrams.

**4. Name things as the code names them.** `OrderSubmissionHandler`, not
`Handler`. If the code's own name is `Manager`, that is a finding about the code
worth surfacing, not a label to launder.

**5. Cut to budget.** Delete what the audience already knows, collapse clusters,
drop the tier you are not discussing.

**6. Mark the focal set.** One or two nodes: the bottleneck, the thing that
changed, the thing that breaks.

## What to draw for what question

| Question | Type | Source of truth |
| :-- | :-- | :-- |
| How does a request reach storage? | `flowchart LR` | Route table, middleware chain, ORM calls |
| What talks to what, in order? | `sequenceDiagram` | Client calls, queue publishes, webhooks |
| What states can an order be in? | `stateDiagram-v2` | Status enum plus the transitions actually implemented |
| What does a deploy do? | `flowchart TB` | CI config — `.github/workflows`, `Jenkinsfile`, `.gitlab-ci.yml` |
| What runs where? | `flowchart` with subgraphs | Terraform, Helm charts, `docker-compose.yml` |
| How do these types relate? | `classDiagram` | Type definitions, not runtime objects |

## CI/CD pipelines

CI config is unusually good diagram material: it is declarative, it already has
a dependency graph, and the YAML is genuinely hard to read.

Read `needs:` / `depends_on:` / `requires:` to get the DAG, then draw jobs as
nodes and dependencies as edges. Label the edges with the condition when there is
one (`on: tag`, `if: main`). Mark the deploy job `focal` and any manual-approval
gate `risk`. Fan-out and fan-in points are what the reader is looking for.

## Infrastructure

From Terraform or Helm, draw the *boundaries*, not the resources. A reader wants
to know what is public, what is in the VPC, and what crosses between them —
`subgraph` per trust zone, with the crossings labeled. A node per `aws_*`
resource is a resource list, and a table reads better.

## Verify before you ship

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" docs/diagrams/imports.mmd
```

Generated diagrams fail SLOP002 (filler labels) and SLOP004 (unlabeled edges)
most often, because the extractor has no verbs and inherits whatever the code
calls things. Both are fixed by editing, and the editing is the part that makes
the diagram worth having.

**Generated is a starting point, never the deliverable.**
