"""One place where a Marmalade setting is resolved.

Precedence, highest first:

  1. an explicit command-line flag  (the caller applies it; it never reaches here)
  2. MARMALADE_<ENV> in the environment
  3. the /plugin userConfig value, exported by the harness as
     CLAUDE_PLUGIN_OPTION_<OPTION>
  4. the built-in default

Before this module the two channels were read by different halves of the plugin:
the hooks honoured userConfig, the CLI scripts honoured MARMALADE_*, and nothing
bridged them. A diagram_dir set in /plugin was obeyed by the drift hook and
ignored by export, slop, lint and sync. Resolve every setting through here.
"""

from __future__ import annotations

import os

TRUE = ("1", "true", "yes", "on")
FALSE = ("0", "false", "no", "off")


def setting(env: str, option: str, default: str = "") -> str:
    """Resolve one setting across both config channels."""
    for name in (f"MARMALADE_{env.upper()}", f"CLAUDE_PLUGIN_OPTION_{option.upper()}"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def flag(env: str, option: str, default: bool = True) -> bool:
    raw = setting(env, option, "").strip().lower()
    if raw in TRUE:
        return True
    if raw in FALSE:
        return False
    return default


def diagram_dir() -> str:
    return setting("DIAGRAM_DIR", "diagram_dir", "docs/diagrams")


def export_dir() -> str:
    return setting("EXPORT_DIR", "export_dir", "docs/diagrams/rendered")


def theme() -> str:
    return setting("THEME", "default_theme", "light")


def formats() -> list:
    """A `multiple` userConfig value may arrive comma-, space-, or newline-separated."""
    raw = setting("FORMATS", "export_formats", "svg")
    return [f.strip().lower() for f in raw.replace("\n", ",").replace(" ", ",").split(",") if f.strip()]


def detail(default: str) -> str:
    return setting("DETAIL", "detail", default)
