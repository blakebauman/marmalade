#!/usr/bin/env python3
"""PreToolUse: stop credentials and internal topology from landing in a diagram.

Architecture diagrams get pasted into READMEs, tickets, and slide decks, so they
leak differently from code: a real hostname or a bearer token in a node label
travels further than the same string in a config file. This scans only the
Mermaid regions of a write, and denies the call when it finds one.
"""

from __future__ import annotations

import ipaddress
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hookio import edited_paths, emit, flag, is_diagram_carrier, read_event  # noqa: E402

from mermaid_lint import extract_blocks  # noqa: E402

# (label, pattern, why it matters). Ordered most-specific first.
PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "a live AWS key"),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"), "a GitHub token"),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "a Slack token"),
    ("Stripe secret key", re.compile(r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}\b"), "a Stripe key"),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "a Google API key"),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "a signed token"),
    (
        "connection string with password",
        re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]{3,}@", re.IGNORECASE),
        "a password embedded in a URI",
    ),
    (
        "inline credential",
        re.compile(
            r"\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|client[_-]?secret)\b\s*[:=]\s*"
            r"[\"']?[A-Za-z0-9/+_.-]{8,}",
            re.IGNORECASE,
        ),
        "a hardcoded credential",
    ),
    (
        "internal hostname",
        re.compile(r"\b[a-z0-9][a-z0-9-]{1,62}\.(?:internal|intranet|corp|local|lan|home\.arpa)\b", re.IGNORECASE),
        "an internal DNS name that maps your private network",
    ),
]

# Documentation-safe placeholder ranges (RFC 5737 / RFC 3849) are fine to draw.
DOC_NETS = [
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("2001:db8::/32"),
]
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def private_ips(text: str) -> list[str]:
    found = []
    for candidate in IPV4.findall(text):
        try:
            addr = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if any(addr in net for net in DOC_NETS):
            continue
        if addr.is_private and not addr.is_loopback and not addr.is_unspecified:
            found.append(candidate)
    return found


def scan(text: str) -> list[str]:
    hits: list[str] = []
    for label, pattern, why in PATTERNS:
        if pattern.search(text):
            hits.append(f"{label} — looks like {why}")
    ips = sorted(set(private_ips(text)))
    if ips:
        hits.append(
            f"private IP address(es) {', '.join(ips[:4])} — real internal addressing, not documentation placeholders"
        )
    return hits


def main() -> int:
    if not flag("secret_scan", True):
        return 0

    event = read_event()
    tool_input = event.get("tool_input") or {}
    candidates = [tool_input.get(k) for k in ("content", "new_string", "new_str")]
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict):
            candidates.append(edit.get("new_string"))
    payload = "\n".join(c for c in candidates if isinstance(c, str))
    if not payload.strip():
        return 0

    paths = edited_paths(event) or ["untitled.mmd"]
    if not any(is_diagram_carrier(p) for p in paths):
        return 0

    blocks = extract_blocks(paths[0], payload)
    # An Edit replaces a fragment, so a bare fragment may not parse as a block.
    scan_text = "\n".join(b.source for b in blocks) if blocks else payload

    hits = scan(scan_text)
    if not hits:
        return 0

    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "Marmalade blocked this diagram write — it contains material that should not ship in a diagram:\n"
                    + "\n".join(f"  • {h}" for h in hits)
                    + "\n\nDiagrams get pasted into tickets, READMEs, and decks, so treat this as a publish, not a "
                    "local file. Replace the value with a placeholder (`<API_KEY>`, `db.example.com`, an RFC 5737 "
                    "address like 203.0.113.10) and write again. If the value is genuinely a fake fixture, say so "
                    "and rewrite it in an obviously-fake form."
                ),
            }
        }
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
