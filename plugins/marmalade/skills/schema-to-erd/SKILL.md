---
name: schema-to-erd
description: Generate an entity-relationship diagram from a live Postgres database or a SQL DDL file, with cardinality derived from the catalog rather than guessed. Use when asked to diagram a database, visualize a schema, produce an ERD, or document data relationships.
license: MIT
compatibility: Requires Python 3.9+. Live introspection requires psql on PATH.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Schema to ERD

```bash
# From a live database
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pg_erd.py" --dsn "$DATABASE_URL" --schema public

# From a DDL file, no database needed
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pg_erd.py" --sql-file schema.sql

# A focused subgraph, written to a file
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pg_erd.py" --dsn "$DATABASE_URL" \
  --include "orders*,customers,line_items" -o docs/diagrams/billing-erd.mmd
```

## Cardinality is derived, not guessed

This is the part hand-drawn ERDs get wrong. The generator reads the catalog:

| Catalog fact | Renders as |
| :-- | :-- |
| FK column is `NOT NULL` | `\|\|` on the parent side — exactly one |
| FK column is nullable | `\|o` on the parent side — zero or one |
| FK column is also `UNIQUE` or the PK | `\|\|` on the child side — one-to-one |
| Plain FK | `o{` on the child side — zero or more |

So a nullable, non-unique FK renders `PARENT |o--o{ CHILD`, and a PK-that-is-also-FK
renders `PARENT |o--|| CHILD` — a genuine one-to-one, which is usually worth
questioning in review.

Duplicate declarations — an inline `REFERENCES` plus a later
`ALTER TABLE ADD CONSTRAINT` — collapse to one edge, preferring the named
constraint as the label.

## Keep it under budget

A production schema has more tables than any single diagram should show. The
generated output is Mermaid source; apply the [no-slop](../no-slop/SKILL.md)
budget to it like anything else.

- `--include` / `--exclude` take comma-separated glob patterns. **Draw the
  subsystem, not the database.** A billing ERD and an identity ERD beat one
  70-table poster.
- `--no-attributes` gives entities and relationships only — right above roughly
  fifteen tables, where column lists stop being legible anyway.
- `--max-attributes N` (default 12) truncates long tables and prints an explicit
  "columns omitted" row rather than silently lying.

Then check it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" docs/diagrams/billing-erd.mmd
```

## What generation cannot know

Regenerate the ERD, then **edit it**. The catalog does not record:

- **Soft references.** A `tenant_id` with no FK constraint is a real
  relationship the diagram will miss. Add the edge by hand and label it as
  unenforced — that gap is often the most useful thing on the diagram.
- **Why a relationship exists.** `orders_customer_id` is a constraint name, not
  an explanation. Replace it with the verb: `places`, `bills`, `supersedes`.
- **Which tables matter.** Join tables, audit logs, and migration bookkeeping are
  usually noise for the reader. Exclude them.
- **Polymorphic associations.** A `subject_type` / `subject_id` pair has no FK
  and will not appear at all.

The generator's job is to get the topology right so you can spend your effort on
meaning.

## Committing it

Treat the ERD as generated-then-edited: commit the `.mmd`, note the generating
command at the top of the file, and re-run it after migrations. The
[docs-diagram-sync](../docs-diagram-sync/SKILL.md) skill catches when the
committed diagram has drifted from a re-render.

For a live Neon or Postgres database in this session, the schema can also be read
through an MCP connection if one is configured; `--sql-file` against a migration
directory works with no database access at all.

## Reading the result critically

An ERD is a design review artifact. Things worth flagging when one appears:

- A one-to-one relationship — why is this not one table?
- A table with no FKs in or out — is it actually part of this system?
- A nullable FK on a required relationship — the constraint disagrees with the
  intent.
- A cycle in the FK graph — check the insertion order actually works.
