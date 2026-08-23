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

from mermaid_lint import DIAGRAM_TYPES, extract_blocks  # noqa: E402

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
# A trailing /nn makes it a CIDR block: the shape of a network, not a machine on it.
CIDR_SUFFIX = re.compile(r"\s*/\s*\d{1,2}\b")


def private_ips(text: str) -> list[str]:
    """Private host addresses only.

    A CIDR range such as 10.20.0.0/16 is how a VPC is documented — RFC 1918
    ranges are private by definition, so flagging them would block every
    infrastructure diagram. A bare host address like 10.4.2.17 is a real machine
    and is what actually leaks.
    """
    found = []
    for match in IPV4.finditer(text):
        if CIDR_SUFFIX.match(text, match.end()):
            continue
        try:
            addr = ipaddress.ip_address(match.group(0))
        except ValueError:
            continue
        if any(addr in net for net in DOC_NETS):
            continue
        # Link-local covers the cloud metadata endpoint (169.254.169.254), which
        # is identical on every host everywhere and reveals nothing.
        if addr.is_link_local:
            continue
        if addr.is_private and not addr.is_loopback and not addr.is_unspecified:
            found.append(match.group(0))
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


def looks_like_mermaid(text: str) -> bool:
    """Whether a fragment that did not parse as a block is still diagram source."""
    if "```mermaid" in text.lower():
        return True
    for line in text.splitlines():
        stripped = line.strip()
        for keyword in DIAGRAM_TYPES:
            if stripped == keyword or stripped.startswith(keyword + " "):
                return True
    return False


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

    path = paths[0]
    blocks = extract_blocks(path, payload)
    if blocks:
        scan_text = "\n".join(b.source for b in blocks)
    elif path.lower().endswith((".mmd", ".mermaid")):
        # The whole file is a diagram, even if an Edit fragment does not parse.
        scan_text = payload
    elif looks_like_mermaid(payload):
        # An Edit fragment of a fenced diagram inside a Markdown file.
        scan_text = payload
    else:
        # Markdown carrying no diagram at all. This is a diagram scanner: prose,
        # shell examples, and local dev connection strings are not its business.
        return 0

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
