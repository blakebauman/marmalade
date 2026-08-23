"""Structural linter and block extractor for Mermaid sources.

Pure standard library. Never raises on malformed input: callers are hooks that
must not break a session. Two public entry points:

    extract_blocks(path, text) -> list[Block]
    lint(block)               -> list[Finding]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- Diagram grammar surface -------------------------------------------------

# Header keyword -> canonical diagram type. Ordered longest-first at match time
# so `stateDiagram-v2` wins over `stateDiagram`.
DIAGRAM_TYPES = {
    "flowchart": "flowchart",
    "graph": "flowchart",
    "sequenceDiagram": "sequence",
    "classDiagram-v2": "class",
    "classDiagram": "class",
    "stateDiagram-v2": "state",
    "stateDiagram": "state",
    "erDiagram": "er",
    "journey": "journey",
    "gantt": "gantt",
    "pie": "pie",
    "quadrantChart": "quadrant",
    "requirementDiagram": "requirement",
    "gitGraph": "git",
    "mindmap": "mindmap",
    "timeline": "timeline",
    "zenuml": "zenuml",
    "sankey-beta": "sankey",
    "xychart-beta": "xychart",
    "block-beta": "block",
    "packet-beta": "packet",
    "packet": "packet",
    "kanban": "kanban",
    "architecture-beta": "architecture",
    "radar-beta": "radar",
    "treemap-beta": "treemap",
    "C4Context": "c4",
    "C4Container": "c4",
    "C4Component": "c4",
    "C4Dynamic": "c4",
    "C4Deployment": "c4",
}

FLOWCHART_DIRECTIONS = {"TB", "TD", "BT", "RL", "LR"}

# Words Mermaid's flowchart grammar treats specially; using one as a bare node
# id is the single most common cause of a silent parse failure.
FLOWCHART_RESERVED = {
    "end", "graph", "subgraph", "class", "click", "style", "linkStyle",
    "classDef", "direction", "default", "call", "href", "callback",
}

# Node shape delimiters: opening token -> closing token.
SHAPE_PAIRS = [
    ("[[", "]]"), ("[(", ")]"), ("[/", "/]"), ("[\\", "\\]"),
    ("((", "))"), ("((", "))"), ("({", "})"), ("(-", "-)"),
    (">", "]"), ("{{", "}}"), ("[", "]"), ("(", ")"), ("{", "}"),
]

BLOCK_FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*mermaid\b([^\n]*)$", re.IGNORECASE)
INIT_DIRECTIVE = re.compile(r"%%\{\s*init\s*:")
FRONTMATTER_FENCE = re.compile(r"^---\s*$")


@dataclass
class Block:
    """One Mermaid source region, with the offset needed to map back to a file."""

    path: str
    source: str
    line_offset: int = 0  # 0-based line index in the containing file
    origin: str = "file"  # "file" | "markdown-fence"
    fence_info: str = ""

    @property
    def lines(self) -> list[str]:
        return self.source.splitlines()


@dataclass
class Finding:
    line: int  # 1-based, already offset into the containing file
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str
    hint: str = ""


@dataclass
class _Parsed:
    diagram_type: str | None = None
    header_line: int = 0
    header_raw: str = ""
    body: list[tuple[int, str]] = field(default_factory=list)  # (0-based idx, text)
    has_frontmatter: bool = False
    has_init_directive: bool = False
    accessible_title: bool = False
    accessible_descr: bool = False


# --- Extraction --------------------------------------------------------------


def extract_blocks(path: str, text: str) -> list[Block]:
    """Return every Mermaid region in `text`.

    A `.mmd`/`.mermaid` file is one block. A Markdown file yields one block per
    ```mermaid fence, each carrying the fence's line offset.
    """
    lower = path.lower()
    if lower.endswith((".mmd", ".mermaid")):
        return [Block(path=path, source=text, line_offset=0, origin="file")]
    if not lower.endswith((".md", ".markdown", ".mdx", ".qmd", ".rst")):
        return []

    blocks: list[Block] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = BLOCK_FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        fence = m.group(2)
        info = (m.group(3) or "").strip()
        closer = re.compile(r"^\s*" + fence[0] + "{" + str(len(fence)) + ",}\\s*$")
        j = i + 1
        body: list[str] = []
        while j < len(lines) and not closer.match(lines[j]):
            body.append(lines[j])
            j += 1
        if j < len(lines):  # unterminated fences are the writer's problem, not ours
            blocks.append(
                Block(
                    path=path,
                    source="\n".join(body),
                    line_offset=i + 1,
                    origin="markdown-fence",
                    fence_info=info,
                )
            )
        i = j + 1
    return blocks


# --- Parsing -----------------------------------------------------------------


def _strip_comment(line: str) -> str:
    """Drop a trailing `%%` comment, but keep `%%{init:...}%%` directives."""
    if INIT_DIRECTIVE.search(line):
        return line
    idx = line.find("%%")
    return line if idx < 0 else line[:idx]


def _parse(block: Block) -> _Parsed:
    out = _Parsed()
    lines = block.lines
    i = 0

    # YAML frontmatter config block
    if i < len(lines) and FRONTMATTER_FENCE.match(lines[i].strip()):
        out.has_frontmatter = True
        i += 1
        while i < len(lines) and not FRONTMATTER_FENCE.match(lines[i].strip()):
            i += 1
        i += 1

    seen_header_candidate = False
    for idx in range(i, len(lines)):
        raw = lines[idx]
        if INIT_DIRECTIVE.search(raw):
            out.has_init_directive = True
        stripped = _strip_comment(raw).strip()
        if not stripped:
            continue
        if stripped.startswith("%%"):
            continue
        if out.diagram_type is None and not seen_header_candidate:
            # Only the first non-comment line is a header candidate. Without this
            # guard, a file with no valid header keeps overwriting header_line and
            # the body stays empty, so every body-level check silently no-ops.
            seen_header_candidate = True
            out.header_line = idx
            out.header_raw = stripped
            for kw in sorted(DIAGRAM_TYPES, key=len, reverse=True):
                if stripped == kw or stripped.startswith(kw + " ") or stripped.startswith(kw + ":"):
                    out.diagram_type = DIAGRAM_TYPES[kw]
                    break
            continue
        if stripped.startswith("accTitle"):
            out.accessible_title = True
        if stripped.startswith("accDescr"):
            out.accessible_descr = True
        out.body.append((idx, stripped))
    return out


# --- Checks ------------------------------------------------------------------


def _mask_labels(text: str) -> str:
    """Blank out quoted strings so delimiter counting ignores label content."""
    out, in_q, quote = [], False, ""
    for ch in text:
        if in_q:
            out.append(" ")
            if ch == quote:
                in_q, quote = False, ""
            continue
        if ch in ('"', "'"):
            in_q, quote = True, ch
            out.append(" ")
            continue
        out.append(ch)
    return "".join(out)


def _check_header(block: Block, p: _Parsed) -> list[Finding]:
    f: list[Finding] = []
    ln = block.line_offset

    if p.diagram_type is None:
        # A file containing only classDef/class/style lines is a reusable style
        # partial meant to be pasted into a diagram, not a diagram missing a header.
        if p.body and all(
            (line.split()[0] if line.split() else "") in ("classDef", "class", "style", "linkStyle")
            for _idx, line in p.body
        ):
            return f
        known = ", ".join(sorted({k for k in DIAGRAM_TYPES})[:8])
        f.append(
            Finding(
                line=ln + p.header_line + 1,
                severity="error",
                code="MMD001",
                message=(
                    f"No recognizable diagram header. Found {p.header_raw[:60]!r}."
                    if p.header_raw
                    else "Diagram is empty."
                ),
                hint=f"The first non-comment line must name a diagram type ({known}, ...).",
            )
        )
        return f

    if p.diagram_type == "flowchart":
        parts = p.header_raw.split()
        if len(parts) > 1:
            direction = parts[1].rstrip(";:")
            if direction not in FLOWCHART_DIRECTIONS:
                f.append(
                    Finding(
                        line=ln + p.header_line + 1,
                        severity="error",
                        code="MMD002",
                        message=f"{direction!r} is not a valid flowchart direction.",
                        hint="Use one of TB, TD, BT, RL, LR.",
                    )
                )
        if p.header_raw.split()[0] == "graph":
            f.append(
                Finding(
                    line=ln + p.header_line + 1,
                    severity="info",
                    code="MMD101",
                    message="`graph` is the legacy flowchart keyword.",
                    hint="Prefer `flowchart` — it gets the newer renderer, better edge routing, and new shapes.",
                )
            )
    return f


# Families whose blocks legitimately span lines: an erDiagram attribute block,
# a classDiagram body, a composite state. Per-line bracket balance is a
# flowchart rule and reports nonsense on these.
_MULTILINE_BLOCK_TYPES = {"er", "class", "state", "requirement", "c4", "mindmap", "kanban", "architecture"}


def _check_delimiters(block: Block, p: _Parsed) -> list[Finding]:
    f: list[Finding] = []
    ln = block.line_offset
    check_brackets = p.diagram_type not in _MULTILINE_BLOCK_TYPES
    for idx, text in p.body:
        masked = _mask_labels(text)
        if text.count('"') % 2:
            f.append(
                Finding(
                    line=ln + idx + 1,
                    severity="error",
                    code="MMD010",
                    message="Unbalanced double quote.",
                    hint='Every label opened with " must be closed on the same line.',
                )
            )
        if not check_brackets:
            continue
        for open_ch, close_ch in (("[", "]"), ("(", ")"), ("{", "}")):
            if masked.count(open_ch) != masked.count(close_ch):
                f.append(
                    Finding(
                        line=ln + idx + 1,
                        severity="error",
                        code="MMD011",
                        message=f"Unbalanced {open_ch}{close_ch} outside of a quoted label.",
                        hint="Node shapes must open and close on one line; quote labels that contain brackets.",
                    )
                )
                break
    return f


def _check_subgraphs(block: Block, p: _Parsed) -> list[Finding]:
    if p.diagram_type not in ("flowchart", "block"):
        return []
    f: list[Finding] = []
    ln = block.line_offset
    stack: list[int] = []
    for idx, text in p.body:
        head = text.split()[0] if text.split() else ""
        if head == "subgraph":
            stack.append(idx)
        elif text == "end" or head == "end":
            if not stack:
                f.append(
                    Finding(
                        line=ln + idx + 1,
                        severity="error",
                        code="MMD020",
                        message="`end` with no open `subgraph`.",
                        hint="Remove it, or add the matching `subgraph` above.",
                    )
                )
            else:
                stack.pop()
    for idx in stack:
        f.append(
            Finding(
                line=ln + idx + 1,
                severity="error",
                code="MMD021",
                message="`subgraph` is never closed.",
                hint="Add a matching `end` line.",
            )
        )
    return f


_EDGE = re.compile(r"(-{2,}>|-{3,}|={2,}>|-\.->|\.-|<-{2,}>|-{2,}o|-{2,}x|~{3,})")
_NODE_DEF = re.compile(r"(?<![\w-])([A-Za-z_][\w-]*)\s*(?=[\[({>])")


_EDGE_LABEL = re.compile(r"\|[^|]*\|")


def _flowchart_node_ids(text: str) -> list[str]:
    """Every node id referenced on a flowchart line, shaped or bare.

    `A[Start] --> stop` yields ["A", "stop"], so a reserved word used as a bare
    edge target is caught as well as one used as a shape definition.
    """
    masked = _EDGE_LABEL.sub(" ", _mask_labels(text))
    ids = list(_NODE_DEF.findall(masked))
    for segment in _EDGE.split(masked):
        if _EDGE.fullmatch(segment.strip()):
            continue
        # Keep only the id: drop any shape body and trailing punctuation.
        head = re.split(r"[\[({>&]", segment.strip(), maxsplit=1)[0]
        head = head.strip().rstrip(";:")
        if re.fullmatch(r"[A-Za-z_][\w-]*", head):
            ids.append(head)
    return ids


def _check_flowchart_ids(block: Block, p: _Parsed) -> list[Finding]:
    if p.diagram_type != "flowchart":
        return []
    f: list[Finding] = []
    ln = block.line_offset
    for idx, text in p.body:
        first = text.split()[0] if text.split() else ""
        if first in ("subgraph", "style", "classDef", "class", "click", "linkStyle", "direction", "end"):
            continue
        for node_id in _flowchart_node_ids(text):
            if node_id in FLOWCHART_RESERVED:
                f.append(
                    Finding(
                        line=ln + idx + 1,
                        severity="error",
                        code="MMD030",
                        message=f"{node_id!r} is a reserved flowchart keyword used as a node id.",
                        hint=f"Rename the id (for example `{node_id}Node`); the label can still read {node_id!r}.",
                    )
                )
        # `A --> ` with nothing after it parses as a dangling edge
        if _EDGE.search(text) and _EDGE.split(text)[-1].strip() in ("", ";"):
            f.append(
                Finding(
                    line=ln + idx + 1,
                    severity="error",
                    code="MMD031",
                    message="Edge has no target node.",
                    hint="Every arrow needs a node on both sides.",
                )
            )
    return f


def _check_quality(block: Block, p: _Parsed) -> list[Finding]:
    """Legibility and reviewability warnings — not parse errors."""
    f: list[Finding] = []
    ln = block.line_offset
    if p.diagram_type is None:
        return f

    node_ids: set[str] = set()
    edge_count = 0
    for _idx, text in p.body:
        masked = _mask_labels(text)
        if _EDGE.search(masked):
            edge_count += 1
        node_ids.update(_NODE_DEF.findall(masked))

    if len(node_ids) > 25:
        f.append(
            Finding(
                line=ln + p.header_line + 1,
                severity="warning",
                code="MMD200",
                message=f"{len(node_ids)} nodes in one diagram.",
                hint="Past ~25 nodes a reader stops tracing paths. Split by subsystem, or collapse a region into one node that links to its own diagram.",
            )
        )
    if edge_count > 40:
        f.append(
            Finding(
                line=ln + p.header_line + 1,
                severity="warning",
                code="MMD201",
                message=f"{edge_count} edges in one diagram.",
                hint="Dense edge sets read as noise. Consider a sequence diagram for ordered flows, or group edges behind subgraph boundaries.",
            )
        )
    if not p.accessible_title:
        f.append(
            Finding(
                line=ln + p.header_line + 1,
                severity="warning",
                code="MMD210",
                message="No `accTitle` — the diagram has no accessible name.",
                hint="Add `accTitle: <short name>` so screen readers announce the diagram instead of a bare SVG.",
            )
        )
    if not p.accessible_descr:
        f.append(
            Finding(
                line=ln + p.header_line + 1,
                severity="warning",
                code="MMD211",
                message="No `accDescr` — the diagram has no text alternative.",
                hint="Add `accDescr: <what the diagram shows>` (or an accDescr { } block) so the content survives without vision.",
            )
        )
    if p.has_init_directive:
        f.append(
            Finding(
                line=ln + p.header_line + 1,
                severity="info",
                code="MMD220",
                message="Inline `%%{init}%%` directive pins theme settings into the source.",
                hint="Prefer a shared config file passed at render time, so one theme change updates every diagram.",
            )
        )
    return f


CHECKS = (_check_header, _check_delimiters, _check_subgraphs, _check_flowchart_ids, _check_quality)


def lint(block: Block) -> list[Finding]:
    """Run every check over one block. Returns findings sorted by line."""
    try:
        parsed = _parse(block)
    except Exception as exc:  # never let a hook die on weird input
        return [Finding(line=1, severity="warning", code="MMD000", message=f"Linter could not parse block: {exc}")]

    findings: list[Finding] = []
    for check in CHECKS:
        try:
            findings.extend(check(block, parsed))
        except Exception:
            continue
    return sorted(findings, key=lambda x: (x.line, x.code))


def diagram_type(block: Block) -> str | None:
    try:
        return _parse(block).diagram_type
    except Exception:
        return None
