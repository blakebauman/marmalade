---
description: Generate an entity-relationship diagram from a Postgres database or a SQL DDL file, with cardinality read from the catalog.
argument-hint: "[--dsn ... | --sql-file ...] [--include glob,glob]"
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, Agent
---

Generate an ERD: **$ARGUMENTS**

Delegate to `marmalade:postgres-erd-engineer`, which owns generation, scoping,
and the schema findings an ERD exposes.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pg_erd.py" --dsn "$DATABASE_URL" --schema public
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pg_erd.py" --sql-file schema.sql
```

With no DSN and no file, look for `DATABASE_URL`, then for a migrations
directory to read as DDL. Ask before connecting to anything that looks like a
production database.

**Scope it.** A production schema has more tables than any diagram should show.
Use `--include` / `--exclude` to draw the subsystem, `--no-attributes` above
about fifteen tables. A billing ERD and an identity ERD beat one 70-table poster.

**Then edit it.** The catalog does not know about soft references without FK
constraints, what a relationship means, or which tables are bookkeeping noise.
Replace constraint names with verbs, add unenforced relationships by hand and
mark them as unenforced.

Report the diagram, the exact command that produced it, and — separately — the
schema findings the ERD exposed: one-to-one relationships, nullable FKs on
required relationships, islands, and FK cycles.
