#!/usr/bin/env python3
"""Generate a Mermaid erDiagram from a live Postgres database or a DDL file.

    pg_erd.py --dsn "$DATABASE_URL" --schema public
    pg_erd.py --sql-file schema.sql
    pg_erd.py --dsn "$DATABASE_URL" --include "orders*,customers" --no-attributes

Live mode shells out to `psql`, so it needs no Python driver. Cardinality is
derived from the catalog rather than guessed: a NOT NULL foreign key gives
`||` on the parent side, a nullable one gives `|o`, and a foreign key that is
also UNIQUE collapses the child side from `o{` to `||`.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field

SEP = "\x1f"  # unit separator: safe against commas and quotes in identifiers

COLUMN_SQL = """
SELECT c.table_name, c.column_name, c.data_type, c.udt_name, c.is_nullable, c.ordinal_position
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE c.table_schema = '{schema}' AND t.table_type = 'BASE TABLE'
ORDER BY c.table_name, c.ordinal_position;
"""

CONSTRAINT_SQL = """
SELECT tc.table_name, kcu.column_name, tc.constraint_type
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema
WHERE tc.table_schema = '{schema}' AND tc.constraint_type IN ('PRIMARY KEY','UNIQUE')
ORDER BY tc.table_name;
"""

FK_SQL = """
SELECT tc.table_name       AS child_table,
       kcu.column_name     AS child_column,
       ccu.table_name      AS parent_table,
       ccu.column_name     AS parent_column,
       tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
WHERE tc.table_schema = '{schema}' AND tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name;
"""


@dataclass
class Column:
    name: str
    type: str
    nullable: bool
    pk: bool = False
    unique: bool = False
    fk: bool = False


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)

    def column(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)


@dataclass
class Relation:
    parent: str
    child: str
    label: str
    parent_optional: bool
    child_unique: bool

    def render(self) -> str:
        left = "|o" if self.parent_optional else "||"
        right = "||" if self.child_unique else "o{"
        return f"    {ident(self.parent)} {left}--{right} {ident(self.child)} : \"{self.label}\""


def ident(name: str) -> str:
    """Mermaid entity names allow letters, digits, underscore, and dash unquoted."""
    return name if re.fullmatch(r"[A-Za-z_][\w-]*", name) else f'"{name}"'


def simplify_type(data_type: str, udt: str) -> str:
    mapping = {
        "character varying": "varchar",
        "character": "char",
        "timestamp with time zone": "timestamptz",
        "timestamp without time zone": "timestamp",
        "time with time zone": "timetz",
        "time without time zone": "time",
        "double precision": "float8",
        "USER-DEFINED": udt,
        "ARRAY": f"{udt.lstrip('_')}[]",
    }
    out = mapping.get(data_type, data_type)
    return re.sub(r"[^\w\[\]]+", "_", out)


# --- live introspection ------------------------------------------------------


def psql_rows(dsn: str, sql: str) -> list[list[str]]:
    cmd = ["psql", dsn, "-X", "-A", "-t", "-F", SEP, "-v", "ON_ERROR_STOP=1", "-c", sql]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise SystemExit("`psql` is not on PATH. Install the Postgres client, or use --sql-file.")
    except subprocess.TimeoutExpired:
        raise SystemExit("psql timed out after 60s.")
    if proc.returncode != 0:
        raise SystemExit(f"psql failed:\n{proc.stderr.strip()}")
    return [line.split(SEP) for line in proc.stdout.splitlines() if line.strip()]


def introspect(dsn: str, schema: str) -> tuple[dict[str, Table], list[Relation]]:
    tables: dict[str, Table] = {}
    for row in psql_rows(dsn, COLUMN_SQL.format(schema=schema)):
        table, column, data_type, udt, nullable, _pos = row
        tables.setdefault(table, Table(table)).columns.append(
            Column(name=column, type=simplify_type(data_type, udt), nullable=(nullable == "YES"))
        )

    for row in psql_rows(dsn, CONSTRAINT_SQL.format(schema=schema)):
        table, column, kind = row
        col = tables.get(table, Table(table)).column(column)
        if not col:
            continue
        if kind == "PRIMARY KEY":
            col.pk = True
        else:
            col.unique = True

    relations: list[Relation] = []
    for row in psql_rows(dsn, FK_SQL.format(schema=schema)):
        child_t, child_c, parent_t, _parent_c, constraint = row
        col = tables.get(child_t, Table(child_t)).column(child_c)
        if col:
            col.fk = True
        relations.append(
            Relation(
                parent=parent_t,
                child=child_t,
                label=re.sub(r"^fk_|_fkey$", "", constraint) or "references",
                parent_optional=bool(col and col.nullable),
                child_unique=bool(col and (col.unique or col.pk)),
            )
        )
    return tables, relations


# --- DDL file parsing --------------------------------------------------------

CREATE_TABLE = re.compile(
    r"CREATE\s+(?:UNLOGGED\s+|TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?:\"?[\w]+\"?\.)?\"?([\w]+)\"?\s*\((.*?)\)\s*(?:INHERITS|PARTITION|WITH|TABLESPACE|;)",
    re.IGNORECASE | re.DOTALL,
)
ALTER_FK = re.compile(
    r"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:\"?[\w]+\"?\.)?\"?([\w]+)\"?\s+ADD\s+CONSTRAINT\s+\"?([\w]+)\"?\s+"
    r"FOREIGN\s+KEY\s*\(\s*\"?([\w]+)\"?\s*\)\s*REFERENCES\s+(?:\"?[\w]+\"?\.)?\"?([\w]+)\"?",
    re.IGNORECASE | re.DOTALL,
)
INLINE_FK = re.compile(r"REFERENCES\s+(?:\"?[\w]+\"?\.)?\"?([\w]+)\"?", re.IGNORECASE)


def split_columns(body: str) -> list[str]:
    parts, depth, current = [], 0, []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(ch)
    parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def parse_ddl(text: str) -> tuple[dict[str, Table], list[Relation]]:
    text = re.sub(r"--[^\n]*", "", text)
    tables: dict[str, Table] = {}
    relations: list[Relation] = []

    for match in CREATE_TABLE.finditer(text + ";"):
        name, body = match.group(1), match.group(2)
        table = tables.setdefault(name, Table(name))
        table_level_pk: list[str] = []
        table_level_unique: list[str] = []

        for part in split_columns(body):
            upper = part.upper()
            if upper.startswith(("PRIMARY KEY", "CONSTRAINT", "UNIQUE", "FOREIGN KEY", "CHECK", "EXCLUDE")):
                if "PRIMARY KEY" in upper:
                    table_level_pk += re.findall(r"[\w]+", part.split("(", 1)[-1].split(")")[0])
                elif upper.startswith("UNIQUE") or " UNIQUE" in upper:
                    table_level_unique += re.findall(r"[\w]+", part.split("(", 1)[-1].split(")")[0])
                if "FOREIGN KEY" in upper:
                    cols = re.search(r"FOREIGN\s+KEY\s*\(\s*\"?([\w]+)\"?\s*\)", part, re.IGNORECASE)
                    ref = INLINE_FK.search(part)
                    if cols and ref:
                        relations.append(
                            Relation(parent=ref.group(1), child=name, label="references",
                                     parent_optional=True, child_unique=False)
                        )
                continue

            tokens = part.split()
            if len(tokens) < 2:
                continue
            col_name = tokens[0].strip('"')
            col_type = re.sub(r"[^\w\[\]]+", "_", tokens[1].split("(")[0])
            col = Column(
                name=col_name,
                type=col_type,
                nullable="NOT NULL" not in upper,
                pk="PRIMARY KEY" in upper,
                unique="UNIQUE" in upper,
            )
            ref = INLINE_FK.search(part)
            if ref:
                col.fk = True
                relations.append(
                    Relation(parent=ref.group(1), child=name, label="references",
                             parent_optional=col.nullable, child_unique=col.unique or col.pk)
                )
            table.columns.append(col)

        for col_name in table_level_pk:
            col = table.column(col_name)
            if col:
                col.pk = True
        for col_name in table_level_unique:
            col = table.column(col_name)
            if col:
                col.unique = True

    for match in ALTER_FK.finditer(text):
        child_t, constraint, child_c, parent_t = match.groups()
        col = tables.get(child_t, Table(child_t)).column(child_c)
        if col:
            col.fk = True
        relations.append(
            Relation(parent=parent_t, child=child_t,
                     label=re.sub(r"^fk_|_fkey$", "", constraint) or "references",
                     parent_optional=bool(col and col.nullable),
                     child_unique=bool(col and (col.unique or col.pk)))
        )
    return tables, relations


# --- rendering ---------------------------------------------------------------


def key_marker(col: Column) -> str:
    marks = []
    if col.pk:
        marks.append("PK")
    if col.fk:
        marks.append("FK")
    if col.unique and not col.pk:
        marks.append("UK")
    return ",".join(marks)


def render(tables: dict[str, Table], relations: list[Relation], *, title: str,
           attributes: bool, max_attrs: int) -> str:
    lines = ["---", f"title: {title}", "---", "erDiagram"]
    lines.append(f"    accTitle: {title}")
    lines.append(
        f"    accDescr: Entity relationship diagram covering {len(tables)} tables "
        f"and {len(relations)} foreign key relationships."
    )

    for name in sorted(tables):
        table = tables[name]
        if not attributes:
            lines.append(f"    {ident(name)} {{}}")
            continue
        lines.append(f"    {ident(name)} {{")
        shown = table.columns[:max_attrs] if max_attrs else table.columns
        for col in shown:
            marker = key_marker(col)
            suffix = f" {marker}" if marker else ""
            comment = "" if col.nullable else ' "not null"'
            lines.append(f"        {col.type} {col.name}{suffix}{comment}")
        hidden = len(table.columns) - len(shown)
        if hidden > 0:
            lines.append(f'        _ and_{hidden}_more "columns omitted"')
        lines.append("    }")

    # One edge per (parent, child) pair. A schema that declares the same foreign
    # key inline and again via ALTER TABLE must not draw two identical arrows;
    # the named constraint wins because it reads better as a label.
    best: dict[tuple[str, str], Relation] = {}
    for rel in relations:
        if rel.parent not in tables or rel.child not in tables:
            continue  # a reference out of the selected schema/filter
        key = (rel.parent, rel.child)
        current = best.get(key)
        if current is None or (current.label == "references" and rel.label != "references"):
            best[key] = rel
    for key in sorted(best):
        lines.append(best[key].render())

    return "\n".join(lines) + "\n"


def apply_filters(tables: dict[str, Table], include: str, exclude: str) -> dict[str, Table]:
    names = list(tables)
    if include:
        patterns = [p.strip() for p in include.split(",") if p.strip()]
        names = [n for n in names if any(fnmatch.fnmatch(n, p) for p in patterns)]
    if exclude:
        patterns = [p.strip() for p in exclude.split(",") if p.strip()]
        names = [n for n in names if not any(fnmatch.fnmatch(n, p) for p in patterns)]
    return {n: tables[n] for n in names}


def main() -> int:
    ap = argparse.ArgumentParser(description="Postgres schema to Mermaid erDiagram.")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--dsn", default=os.environ.get("DATABASE_URL"), help="Postgres connection string.")
    src.add_argument("--sql-file", help="Read DDL from a .sql file instead of a live database.")
    ap.add_argument("--schema", default="public", help="Schema to introspect. Default public.")
    ap.add_argument("--include", default="", help="Comma-separated glob patterns of table names to keep.")
    ap.add_argument("--exclude", default="", help="Comma-separated glob patterns of table names to drop.")
    ap.add_argument("--no-attributes", action="store_true", help="Entities only — useful above ~15 tables.")
    ap.add_argument("--max-attributes", type=int, default=12, help="Columns shown per entity. 0 for all.")
    ap.add_argument("--title", default=None, help="Diagram title.")
    ap.add_argument("-o", "--output", help="Write to this file instead of stdout.")
    args = ap.parse_args()

    if args.sql_file:
        try:
            text = open(args.sql_file, encoding="utf-8", errors="replace").read()
        except OSError as exc:
            raise SystemExit(f"Could not read {args.sql_file}: {exc}")
        tables, relations = parse_ddl(text)
        default_title = f"Schema from {os.path.basename(args.sql_file)}"
    else:
        if not args.dsn:
            raise SystemExit("Provide --dsn, set DATABASE_URL, or use --sql-file.")
        tables, relations = introspect(args.dsn, args.schema)
        default_title = f"{args.schema} schema"

    if not tables:
        raise SystemExit("No tables found. Check --schema, the DSN, or the DDL file.")

    tables = apply_filters(tables, args.include, args.exclude)
    if not tables:
        raise SystemExit("Filters excluded every table.")

    output = render(
        tables, relations,
        title=args.title or default_title,
        attributes=not args.no_attributes,
        max_attrs=args.max_attributes,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output)
        print(f"Wrote {args.output} — {len(tables)} entities, {len(relations)} relationships.", file=sys.stderr)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
