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
from urllib.parse import unquote

SEP = "\x1f"  # unit separator: safe against commas and quotes in identifiers

COLUMN_SQL = """
SELECT c.table_name, c.column_name, c.data_type, c.udt_name, c.is_nullable, c.ordinal_position
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE c.table_schema = {schema} AND t.table_type = 'BASE TABLE'
ORDER BY c.table_name, c.ordinal_position;
"""

# Keys are read from pg_catalog, not information_schema: the information_schema
# constraint views list only tables the role owns or can write to, so a
# read-only role — the right one to point at a real database — would get a
# diagram with no keys and no relationships and nothing to say why.
# One row per constraint, columns in key order, so a composite key stays whole.
CONSTRAINT_SQL = """
SELECT cl.relname, con.conname, con.contype,
       (SELECT string_agg(a.attname, chr(30) ORDER BY k.ord)
          FROM unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord)
          JOIN pg_catalog.pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum),
       COALESCE(pns.nspname, ''), COALESCE(pcl.relname, '')
FROM pg_catalog.pg_constraint con
JOIN pg_catalog.pg_class cl ON cl.oid = con.conrelid
JOIN pg_catalog.pg_namespace ns ON ns.oid = cl.relnamespace
LEFT JOIN pg_catalog.pg_class pcl ON pcl.oid = con.confrelid
LEFT JOIN pg_catalog.pg_namespace pns ON pns.oid = pcl.relnamespace
WHERE ns.nspname = {schema} AND con.contype IN ('p', 'u', 'f')
ORDER BY cl.relname, con.conname;
"""
COLS_SEP = "\x1e"


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
    # Every PRIMARY KEY and UNIQUE constraint, as the set of columns it covers.
    unique_sets: list[frozenset] = field(default_factory=list)

    def column(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)

    def add_key(self, columns: list[str], primary: bool) -> None:
        self.unique_sets.append(frozenset(columns))
        for name in columns:
            col = self.column(name)
            if not col:
                continue
            if primary:
                col.pk = True
                col.nullable = False  # a primary key column is NOT NULL by definition
            else:
                col.unique = True


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


def relation(tables: dict[str, Table], child: str, columns: list[str], parent: str, label: str) -> Relation:
    """Cardinality of one foreign key, from the constraints around it.

    The child side is "exactly one" only when the foreign key columns are, as a
    set, a whole PRIMARY KEY or UNIQUE constraint. A column that is merely one
    part of a composite key — every join table — is still many-to-one.
    """
    table = tables.get(child)
    cols = [table.column(c) for c in columns] if table else []
    for col in cols:
        if col:
            col.fk = True
    return Relation(
        parent=parent,
        child=child,
        label=label,
        parent_optional=any(col is not None and col.nullable for col in cols),
        child_unique=bool(table) and frozenset(columns) in table.unique_sets,
    )


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


def fk_label(constraint: str) -> str:
    return re.sub(r"^fk_|_fkey$", "", constraint) or "references"


# --- live introspection ------------------------------------------------------


def sql_literal(value: str) -> str:
    """Quote a value as a SQL string literal."""
    return "'" + value.replace("\x00", "").replace("'", "''") + "'"


def split_password(dsn: str) -> tuple[str, str | None]:
    """Take the password out of a DSN so it is not passed on a command line.

    Arguments are visible to every user on the machine through the process
    list; the environment is not. The password goes to psql as PGPASSWORD.
    """
    if re.match(r"^postgres(?:ql)?://", dsn, re.IGNORECASE):
        m = re.match(r"^([a-z]+://)([^/@?#]*)@(.*)$", dsn, re.IGNORECASE | re.DOTALL)
        if m and ":" in m.group(2):
            user, password = m.group(2).split(":", 1)
            return f"{m.group(1)}{user}@{m.group(3)}", unquote(password)
        return dsn, None
    m = re.search(r"(?:^|\s)password\s*=\s*('(?:[^'\\]|\\.)*'|\S+)", dsn)
    if not m:
        return dsn, None
    value = m.group(1)
    if value.startswith("'"):
        value = re.sub(r"\\(.)", r"\1", value[1:-1])
    return (dsn[:m.start()] + " " + dsn[m.end():]).strip(), value


def psql_rows(dsn: str, sql: str) -> list[list[str]]:
    safe_dsn, password = split_password(dsn)
    env = dict(os.environ)
    if password is not None:
        env["PGPASSWORD"] = password
    cmd = ["psql", safe_dsn, "-X", "-A", "-t", "-F", SEP, "-v", "ON_ERROR_STOP=1", "-c", sql]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    except FileNotFoundError:
        raise SystemExit("`psql` is not on PATH. Install the Postgres client, or use --sql-file.")
    except subprocess.TimeoutExpired:
        raise SystemExit("psql timed out after 60s.")
    if proc.returncode != 0:
        raise SystemExit(f"psql failed:\n{proc.stderr.strip()}")
    # Not splitlines(): that also splits on the separators used inside a row.
    return [line.split(SEP) for line in proc.stdout.split("\n") if line.strip()]


def introspect(dsn: str, schema: str) -> tuple[dict[str, Table], list[Relation]]:
    quoted = sql_literal(schema)
    tables: dict[str, Table] = {}
    for row in psql_rows(dsn, COLUMN_SQL.format(schema=quoted)):
        table, column, data_type, udt, nullable, _pos = row
        tables.setdefault(table, Table(table)).columns.append(
            Column(name=column, type=simplify_type(data_type, udt), nullable=(nullable == "YES"))
        )

    foreign: list[tuple[str, list[str], str, str]] = []
    for row in psql_rows(dsn, CONSTRAINT_SQL.format(schema=quoted)):
        table, constraint, kind, cols, parent_schema, parent = row
        columns = [c for c in cols.split(COLS_SEP) if c]
        if kind == "f":
            if parent_schema == schema:  # a parent in another schema is not in this diagram
                foreign.append((table, columns, parent, constraint))
        elif table in tables:
            tables[table].add_key(columns, primary=(kind == "p"))

    # Foreign keys last: their cardinality depends on every key being known.
    relations = [relation(tables, child, cols, parent, fk_label(name)) for child, cols, parent, name in foreign]
    return tables, relations


# --- DDL file parsing --------------------------------------------------------

_NAME = r"(?:\"?[\w]+\"?\.)?\"?([\w]+)\"?"
CREATE_TABLE = re.compile(
    r"CREATE\s+(?:UNLOGGED\s+|TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    + _NAME + r"\s*\((.*?)\)\s*(?:INHERITS|PARTITION|WITH|TABLESPACE|;)",
    re.IGNORECASE | re.DOTALL,
)
# pg_dump writes every key this way, after the tables.
ALTER_CONSTRAINT = re.compile(
    r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?" + _NAME + r"\s+ADD\s+(?:CONSTRAINT\s+\"?([\w]+)\"?\s+)?"
    r"(PRIMARY\s+KEY|UNIQUE|FOREIGN\s+KEY)\s*\(([^)]*)\)(?:\s*REFERENCES\s+" + _NAME + r")?",
    re.IGNORECASE | re.DOTALL,
)
INLINE_FK = re.compile(r"\bREFERENCES\s+" + _NAME, re.IGNORECASE)
TABLE_CONSTRAINT = re.compile(r"^(?:PRIMARY\s+KEY|CONSTRAINT|UNIQUE|FOREIGN\s+KEY|CHECK|EXCLUDE|LIKE)\b", re.IGNORECASE)
CONSTRAINT_NAME = re.compile(r"^CONSTRAINT\s+\"?([\w]+)\"?", re.IGNORECASE)
KEY_COLUMNS = re.compile(r"(PRIMARY\s+KEY|UNIQUE|FOREIGN\s+KEY)\s*\(([^)]*)\)", re.IGNORECASE)


# Longest first: "timestamp with time zone" before "time with time zone" is moot,
# but "character varying" must be tried before a bare "character".
MULTIWORD_TYPES = (
    ("character varying", "varchar"),
    ("double precision", "float8"),
    ("timestamp with time zone", "timestamptz"),
    ("timestamp without time zone", "timestamp"),
    ("time with time zone", "timetz"),
    ("time without time zone", "time"),
)


def column_list(text: str) -> list[str]:
    return [c.strip().strip('"') for c in text.split(",") if c.strip()]


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
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"--[^\n]*", "", text)
    tables: dict[str, Table] = {}
    # (child table, child columns, parent table, label), resolved once every key is known.
    foreign: list[tuple[str, list[str], str, str]] = []

    for match in CREATE_TABLE.finditer(text + ";"):
        name, body = match.group(1), match.group(2)
        table = tables.setdefault(name, Table(name))
        keys: list[tuple[list[str], bool]] = []

        for part in split_columns(body):
            if TABLE_CONSTRAINT.match(part):
                named = CONSTRAINT_NAME.match(part)
                key = KEY_COLUMNS.search(part)
                if not key:
                    continue
                kind, columns = re.sub(r"\s+", " ", key.group(1).upper()), column_list(key.group(2))
                if kind == "FOREIGN KEY":
                    ref = INLINE_FK.search(part)
                    if ref:
                        foreign.append((name, columns, ref.group(1),
                                        fk_label(named.group(1)) if named else "references"))
                else:
                    keys.append((columns, kind == "PRIMARY KEY"))
                continue

            tokens = part.split()
            if len(tokens) < 2:
                continue
            col_name = tokens[0].strip('"')
            col_type = re.sub(r"[^\w\[\]]+", "_", tokens[1].split("(")[0])
            spelled = " ".join(tokens[1:]).lower()
            for long_name, short in MULTIWORD_TYPES:
                if spelled.startswith(long_name):
                    col_type = short
                    break
            # Constraint keywords are looked for after the name and type, so a
            # column called `unique_code` is a column and not a UNIQUE constraint.
            rest = " ".join(tokens[2:])
            table.columns.append(
                Column(name=col_name, type=col_type, nullable=not re.search(r"\bNOT\s+NULL\b", rest, re.IGNORECASE))
            )
            if re.search(r"\bPRIMARY\s+KEY\b", rest, re.IGNORECASE):
                keys.append(([col_name], True))
            elif re.search(r"\bUNIQUE\b", rest, re.IGNORECASE):
                keys.append(([col_name], False))
            ref = INLINE_FK.search(rest)
            if ref:
                foreign.append((name, [col_name], ref.group(1), "references"))

        for columns, primary in keys:
            table.add_key(columns, primary)

    for match in ALTER_CONSTRAINT.finditer(text):
        child, constraint, kind, cols, parent = match.groups()
        kind, columns = re.sub(r"\s+", " ", kind.upper()), column_list(cols)
        if kind == "FOREIGN KEY":
            if parent:
                foreign.append((child, columns, parent, fk_label(constraint) if constraint else "references"))
        elif child in tables:
            tables[child].add_key(columns, primary=(kind == "PRIMARY KEY"))

    relations = [relation(tables, child, cols, parent, label) for child, cols, parent, label in foreign]
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
            comment = "" if col.nullable or col.pk else ' "not null"'
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
