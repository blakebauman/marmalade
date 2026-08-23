#!/usr/bin/env python3
"""Check a Mermaid theme config against WCAG contrast thresholds.

    check_contrast.py assets/themes/light.json
    check_contrast.py my-brand.json --level AAA

Diagram text is "non-text-adjacent small text" as far as a reader is concerned,
so this holds label/background pairs to 4.5:1 (AA) and border/background pairs
to 3:1, the non-text contrast threshold for a boundary a reader must perceive.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TEXT_AA, TEXT_AAA, NONTEXT = 4.5, 7.0, 3.0

# (foreground var, background var, kind) — the pairs a reader actually sees.
PAIRS = [
    ("primaryTextColor", "primaryColor", "text"),
    ("secondaryTextColor", "secondaryColor", "text"),
    ("tertiaryTextColor", "tertiaryColor", "text"),
    ("nodeTextColor", "mainBkg", "text"),
    ("textColor", "background", "text"),
    ("titleColor", "background", "text"),
    ("noteTextColor", "noteBkgColor", "text"),
    ("actorTextColor", "actorBkg", "text"),
    ("labelTextColor", "labelBoxBkgColor", "text"),
    ("errorTextColor", "errorBkgColor", "text"),
    ("primaryBorderColor", "primaryColor", "border"),
    ("secondaryBorderColor", "secondaryColor", "border"),
    ("nodeBorder", "background", "border"),
    ("lineColor", "background", "border"),
    ("clusterBorder", "clusterBkg", "border"),
    ("noteBorderColor", "noteBkgColor", "border"),
]


def parse_hex(value: str) -> tuple[float, float, float] | None:
    if not isinstance(value, str) or not value.startswith("#"):
        return None
    h = value[1:]
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    if len(h) not in (6, 8):
        return None
    try:
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return None


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float | None:
    a, b = parse_hex(fg), parse_hex(bg)
    if a is None or b is None:
        return None
    l1, l2 = relative_luminance(a), relative_luminance(b)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def main() -> int:
    ap = argparse.ArgumentParser(description="WCAG contrast audit for a Mermaid theme config.")
    ap.add_argument("config", help="Path to a Mermaid config JSON with a themeVariables block.")
    ap.add_argument("--level", choices=("AA", "AAA"), default="AA", help="Text threshold. Default AA (4.5:1).")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        data = json.loads(Path(args.config).read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Could not read {args.config}: {exc}")

    tv = data.get("themeVariables") or {}
    if not tv:
        raise SystemExit(f"{args.config} has no themeVariables block.")

    text_threshold = TEXT_AAA if args.level == "AAA" else TEXT_AA
    rows, failures, skipped = [], [], []

    for fg_key, bg_key, kind in PAIRS:
        fg, bg = tv.get(fg_key), tv.get(bg_key)
        if not fg or not bg:
            continue
        ratio = contrast(fg, bg)
        if ratio is None:
            skipped.append(f"{fg_key}/{bg_key} (non-hex value; Mermaid needs hex anyway)")
            continue
        threshold = text_threshold if kind == "text" else NONTEXT
        passed = ratio >= threshold
        rows.append((fg_key, bg_key, kind, ratio, threshold, passed))
        if not passed:
            failures.append((fg_key, bg_key, ratio, threshold))

    if args.json:
        print(json.dumps({
            "config": args.config, "level": args.level,
            "pairs": [{"foreground": f, "background": b, "kind": k,
                       "ratio": round(r, 2), "threshold": t, "pass": p} for f, b, k, r, t, p in rows],
            "failures": len(failures), "skipped": skipped,
        }, indent=2))
        return 1 if failures else 0

    print(f"{args.config} — WCAG {args.level} (text {text_threshold}:1, borders {NONTEXT}:1)\n")
    for fg_key, bg_key, kind, ratio, threshold, passed in rows:
        mark = "✓" if passed else "✗"
        print(f"  {mark} {ratio:5.2f}:1  {kind:<6} {fg_key} on {bg_key}")
    for note in skipped:
        print(f"  · skipped {note}")

    if failures:
        print(f"\n{len(failures)} pair(s) below threshold:")
        for fg_key, bg_key, ratio, threshold in failures:
            print(f"  {fg_key} on {bg_key}: {ratio:.2f}:1, needs {threshold}:1")
        print("\nDarken the foreground or lighten the background. Mermaid derives many colors from "
              "primaryColor, so fixing the primary pair often fixes several rows at once.")
        return 1

    print(f"\nAll {len(rows)} pair(s) pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
