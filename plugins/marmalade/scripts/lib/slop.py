"""Detect Mermaid slop: diagrams that parse fine and still teach nothing.

The lint library in `mermaid_lint.py` answers "will this render?". This answers
"should this exist, and does it look like a person made a decision?" — the two
failure modes of machine-generated diagrams.

Every check is deterministic and returns a SLOP0xx finding. Nothing here is a
syntax error; a slop finding is a design judgment with a stated threshold, so a
reviewer can disagree with a number rather than argue with a vibe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mermaid_lint import Block, Finding, _mask_labels, _parse  # noqa: F401

# Density budgets, borrowed from editorial diagram practice: a reader tracking
# more than a dozen labelled things is reading a table, not a diagram.
BUDGETS = {
    "simplified": 7,   # a slide, an executive, a landing page
    "balanced": 12,    # the default for docs
    "faithful": 24,    # a reference diagram someone will study
}
DEFAULT_DETAIL = "balanced"

# Labels that describe the diagram's own machinery instead of the system.
FILLER_LABELS = {
    "process", "processing", "data", "system", "service", "component", "module",
    "handler", "manager", "helper", "util", "utils", "logic", "layer", "thing",
    "input", "output", "step", "step 1", "step 2", "step 3", "start", "end",
    "begin", "finish", "todo", "tbd", "etc", "other", "misc", "stuff", "item",
    "node", "box", "block", "element", "entity", "object", "task", "action",
}

# Words that make a label sound technical without adding information.
HEDGE_WORDS = {"various", "multiple", "several", "some", "many", "etc.", "and more", "..."}

_CLASSDEF = re.compile(r"^\s*classDef\s+([\w-]+)\s+(.*)$")
_STYLE = re.compile(r"^\s*style\s+([\w-]+)\s+(.*)$")
_FILL = re.compile(r"fill\s*:\s*(#[0-9a-fA-F]{3,8}|[a-zA-Z]+)")
_STROKE_WIDTH = re.compile(r"stroke-width\s*:\s*([\d.]+)")
_LABEL = re.compile(r"[\[({>]{1,2}\s*[\"']?(.*?)[\"']?\s*[\])}]{1,2}")
_EDGE_LABEL = re.compile(r"\|\s*[\"']?([^|\"']*)[\"']?\s*\|")
_EDGE = re.compile(r"(-{2,}>|-{3,}|={2,}>|-\.->|<-{2,}>|-{2,}o|-{2,}x)")
_EMOJI = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F000-\U0001F2FF" "\U0000FE0F" "]"
)


@dataclass
class SlopReport:
    findings: list[Finding]
    node_count: int
    edge_count: int
    detail: str
    budget: int

    @property
    def score(self) -> int:
        """0-100. Starts at 100; each finding costs by severity."""
        cost = {"error": 18, "warning": 9, "info": 3}
        total = sum(cost.get(f.severity, 3) for f in self.findings)
        return max(0, 100 - total)


def _labels(body: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Node labels only.

    Edge operators are blanked first: the `>` in `-->` is otherwise read as the
    opening delimiter of Mermaid's odd-node shape, which swallows the next node
    id into the label.
    """
    out: list[tuple[int, str]] = []
    for idx, text in body:
        first = text.split()[0] if text.split() else ""
        if first in ("classDef", "class", "style", "linkStyle", "click"):
            continue
        cleaned = _EDGE.sub(lambda m: " " * len(m.group(0)), text)
        cleaned = _EDGE_LABEL.sub(lambda m: " " * len(m.group(0)), cleaned)
        for match in _LABEL.finditer(cleaned):
            label = match.group(1).strip().strip("\"'")
            if label:
                out.append((idx, label))
    return out


def _nodes(body: list[tuple[int, str]]) -> set[str]:
    ids: set[str] = set()
    for _idx, text in body:
        first = text.split()[0] if text.split() else ""
        if first in ("classDef", "class", "style", "linkStyle", "click", "direction", "subgraph", "end"):
            continue
        masked = _mask_labels(text)
        ids.update(re.findall(r"(?<![\w-])([A-Za-z_][\w-]*)\s*(?=[\[({>])", masked))
        for segment in _EDGE.split(masked):
            if _EDGE.fullmatch(segment.strip()):
                continue
            head = re.split(r"[\[({>&|]", segment.strip(), maxsplit=1)[0].strip().rstrip(";:")
            if re.fullmatch(r"[A-Za-z_][\w-]*", head):
                ids.add(head)
    return ids


def check(block: Block, detail: str = DEFAULT_DETAIL) -> SlopReport:
    parsed = _parse(block)
    ln = block.line_offset
    header = ln + parsed.header_line + 1
    body = parsed.body
    findings: list[Finding] = []

    nodes = _nodes(body)
    labels = _labels(body)
    edge_lines = [(i, t) for i, t in body if _EDGE.search(_mask_labels(t))]
    budget = BUDGETS.get(detail, BUDGETS[DEFAULT_DETAIL])

    # --- SLOP001: over budget -------------------------------------------------
    if len(nodes) > budget:
        findings.append(
            Finding(
                line=header,
                severity="error" if len(nodes) > budget * 1.5 else "warning",
                code="SLOP001",
                message=f"{len(nodes)} nodes against a '{detail}' budget of {budget}.",
                hint=(
                    "Cut to the budget or change the budget deliberately. The usual cut: collapse a cluster "
                    "into one node that links to its own diagram, and delete anything the reader already knows."
                ),
            )
        )

    # --- SLOP002: filler labels ----------------------------------------------
    filler = [(i, l) for i, l in labels if l.strip().lower().strip(".:") in FILLER_LABELS]
    for idx, label in filler[:8]:
        findings.append(
            Finding(
                line=ln + idx + 1,
                severity="warning",
                code="SLOP002",
                message=f"Label {label!r} names a shape, not a thing in the system.",
                hint="Say what it actually is — 'Stripe webhook receiver', not 'Handler'. If you can't name it, it probably should not be a node.",
            )
        )

    # --- SLOP003: hedge words -------------------------------------------------
    for idx, label in labels:
        low = label.lower()
        if any(h in low for h in HEDGE_WORDS):
            findings.append(
                Finding(
                    line=ln + idx + 1,
                    severity="warning",
                    code="SLOP003",
                    message=f"Label {label!r} hedges instead of naming.",
                    hint="'Various services' is a note that the author did not decide. Name the two that matter, or draw one node called what they have in common.",
                )
            )
            break

    # --- SLOP004: unlabeled edges --------------------------------------------
    # Each diagram family labels edges differently: flowcharts use |pipes| or
    # `-- text -->`, sequence and state diagrams use `: text` after the arrow,
    # ER diagrams use `: "text"`. Families with no edge-label grammar are skipped.
    if edge_lines and parsed.diagram_type in ("flowchart", "block", "sequence", "state", "er", "class"):
        if parsed.diagram_type in ("flowchart", "block"):
            def _is_labeled(t: str) -> bool:
                return bool(_EDGE_LABEL.search(t)) or bool(re.search(r"-{2,}\s+\S.*?-{2,}>", t))
        else:
            def _is_labeled(t: str) -> bool:
                after = _EDGE.split(t)[-1]
                return ":" in after and after.split(":", 1)[1].strip() != ""

        labeled = sum(1 for _i, t in edge_lines if _is_labeled(t))
        ratio = labeled / len(edge_lines)
        if ratio < 0.34 and len(edge_lines) >= 4:
            findings.append(
                Finding(
                    line=header,
                    severity="warning",
                    code="SLOP004",
                    message=f"Only {labeled} of {len(edge_lines)} edges say what they mean.",
                    hint="An unlabeled arrow asserts 'related somehow'. Label the verb — 'publishes', 'reads from', 'falls back to' — or drop the edge.",
                )
            )

    # --- SLOP005: one shape for everything -----------------------------------
    shapes = set()
    for _idx, text in body:
        for token in ("[[", "[(", "((", "{{", "([", "[/", "[\\", ">", "[", "(", "{"):
            if token in text:
                shapes.add(token)
                break
    if parsed.diagram_type in ("flowchart", "block") and len(nodes) >= 6 and len(shapes) <= 1:
        findings.append(
            Finding(
                line=header,
                severity="warning",
                code="SLOP005",
                message="Every node is the same shape.",
                hint="Shape is free encoding. Give stores a cylinder `[(…)]`, decisions a diamond `{…}`, external systems a stadium `([…])` — then the reader parses the diagram before reading a word.",
            )
        )

    # --- SLOP006: rainbow classDefs / no focal point --------------------------
    fills: list[str] = []
    class_names: list[str] = []
    for _idx, text in body:
        m = _CLASSDEF.match(text) or _STYLE.match(text)
        if not m:
            continue
        class_names.append(m.group(1))
        fill = _FILL.search(m.group(2))
        if fill:
            fills.append(fill.group(1).lower())
    distinct_fills = {f for f in fills if f not in ("none", "transparent")}
    if len(distinct_fills) > 3:
        findings.append(
            Finding(
                line=header,
                severity="warning",
                code="SLOP006",
                message=f"{len(distinct_fills)} distinct fill colors.",
                hint="More than three fills reads as decoration. One neutral for the system, one accent for the 1–2 nodes the diagram is actually about, one muted for context.",
            )
        )

    # --- SLOP007: no emphasis at all -----------------------------------------
    if parsed.diagram_type in ("flowchart", "block", "state", "class") and len(nodes) >= 8 and not fills and not parsed.has_frontmatter:
        findings.append(
            Finding(
                line=header,
                severity="warning",
                code="SLOP007",
                message="Nothing in the diagram is emphasized.",
                hint="A diagram with no focal point makes the reader do the ranking. Mark the 1–2 nodes that carry the point with `class X focal` and let the rest sit back.",
            )
        )

    # --- SLOP008: emoji as meaning -------------------------------------------
    emoji_labels = [(i, l) for i, l in labels if _EMOJI.search(l)]
    if len(emoji_labels) >= 3:
        findings.append(
            Finding(
                line=ln + emoji_labels[0][0] + 1,
                severity="warning",
                code="SLOP008",
                message=f"{len(emoji_labels)} labels carry emoji.",
                hint="Emoji render inconsistently across PNG/PDF exports and carry no meaning for a screen reader. Use shape and position to encode kind.",
            )
        )

    # --- SLOP009: linear chain that should be a sentence ----------------------
    if 2 <= len(nodes) <= 4 and len(edge_lines) <= 3 and parsed.diagram_type == "flowchart":
        branching = any(len(_EDGE.findall(t)) > 1 for _i, t in edge_lines)
        if not branching:
            findings.append(
                Finding(
                    line=header,
                    severity="info",
                    code="SLOP009",
                    message=f"A straight chain of {len(nodes)} nodes with no branch.",
                    hint="A diagram earns its place when it shows something prose cannot — a branch, a cycle, a boundary, a shape. A → B → C is a sentence. Consider writing the sentence.",
                )
            )

    # --- SLOP010: duplicate labels -------------------------------------------
    seen_labels: dict[str, int] = {}
    for idx, label in labels:
        key = label.strip().lower()
        if key in seen_labels and len(key) > 2:
            findings.append(
                Finding(
                    line=ln + idx + 1,
                    severity="warning",
                    code="SLOP010",
                    message=f"Label {label!r} appears more than once.",
                    hint="Two nodes with one name means either they are the same node drawn twice, or the names are wrong. Both are worth fixing.",
                )
            )
            break
        seen_labels[key] = idx

    # --- SLOP011: novel-length labels ----------------------------------------
    long_labels = [(i, l) for i, l in labels if len(l) > 60]
    for idx, label in long_labels[:3]:
        findings.append(
            Finding(
                line=ln + idx + 1,
                severity="warning",
                code="SLOP011",
                message=f"Label is {len(label)} characters.",
                hint="A node label is a name, not a sentence. Move the explanation to prose beside the diagram, or into `accDescr`.",
            )
        )

    # --- SLOP012: default styling, shipped -----------------------------------
    if not parsed.has_frontmatter and not fills and not parsed.has_init_directive and len(nodes) >= 5:
        findings.append(
            Finding(
                line=header,
                severity="info",
                code="SLOP012",
                message="Diagram carries no theme or title metadata.",
                hint="Default Mermaid is a recognizable look. Add a `--- title: … ---` frontmatter block and render with a marmalade theme preset so it reads as part of your docs, not as output.",
            )
        )

    return SlopReport(
        findings=sorted(findings, key=lambda f: (f.line, f.code)),
        node_count=len(nodes),
        edge_count=len(edge_lines),
        detail=detail,
        budget=budget,
    )
