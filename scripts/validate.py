#!/usr/bin/env python3
"""Validate the Marmalade plugin against Claude Code's plugin rules.

Checks the invariants that break installs silently:
- both manifests parse, name kebab-case, description within the manifest cap
- marketplace.json lists the plugin and agrees with plugin.json on version
- every agent has frontmatter, a 3-50 char kebab-case unique name, a
  description, a valid model, and real tool names
- every skill dir has a SKILL.md whose name matches the directory
- every ${CLAUDE_PLUGIN_ROOT} path in any shipped file resolves on disk
- every agent's `skills:` entry names a skill that exists
- every relative link out of a command resolves
- the export presets match the themes actually on disk
- the manifest filename in the code matches the one in the docs
- the duplicated README and LICENSE pairs are still identical

Usage: python3 scripts/validate.py   (exit 0 = ok, 1 = errors)
Stdlib only - CI runs this on python 3.9 with no pip step.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

PLUGIN = "plugins/marmalade"

# The current tool vocabulary. Note `Agent`, not the legacy `Task` - a skill
# that declares a tool name the harness does not know loses the pre-approval.
VALID_TOOLS = {
    "Agent", "Bash", "Edit", "Glob", "Grep", "NotebookEdit", "Read", "Skill",
    "SlashCommand", "TodoWrite", "WebFetch", "WebSearch", "Write",
}
VALID_MODELS = {"inherit", "sonnet", "opus", "haiku", "fable"}
MAX_MANIFEST_DESCRIPTION = 500
MAX_DESCRIPTION = 1024
KEBAB = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

errors: list[str] = []


def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def frontmatter(path: str):
    """Parse the flat `key: value` frontmatter Marmalade uses. No yaml dep."""
    m = re.match(r"^---\n(.*?)\n---", read(path), re.S)
    if not m:
        return None
    out = {}
    for line in m.group(1).split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not km:
            errors.append(f"{path}: frontmatter line is not `key: value`: {line!r}")
            continue
        out[km.group(1)] = km.group(2).strip()
    return out


def tool_list(raw: str) -> list[str]:
    return [t.strip() for t in raw.split(",") if t.strip()]


# --- manifests -------------------------------------------------------------
try:
    pj = json.loads(read(f"{PLUGIN}/.claude-plugin/plugin.json"))
except Exception as e:
    errors.append(f"{PLUGIN}/.claude-plugin/plugin.json: {e}")
    pj = {}
else:
    if not KEBAB.fullmatch(pj.get("name", "")):
        errors.append(f"plugin.json: name {pj.get('name')!r} must be kebab-case")
    desc = pj.get("description", "")
    if not desc:
        errors.append("plugin.json: missing description")
    elif len(desc) > MAX_MANIFEST_DESCRIPTION:
        errors.append(
            f"plugin.json: description is {len(desc)} chars (max {MAX_MANIFEST_DESCRIPTION})")

try:
    mk = json.loads(read(".claude-plugin/marketplace.json"))
except Exception as e:
    errors.append(f".claude-plugin/marketplace.json: {e}")
    mk = {}
else:
    if not KEBAB.fullmatch(mk.get("name", "")):
        errors.append(f"marketplace.json: name {mk.get('name')!r} must be kebab-case")
    if not mk.get("owner", {}).get("name"):
        errors.append("marketplace.json: missing owner.name")
    entries = mk.get("plugins") or []
    if not entries:
        errors.append("marketplace.json: plugins must list at least one plugin")
    names = [str(e.get("name", "")) for e in entries]
    for entry in entries:
        en = str(entry.get("name", ""))
        if not KEBAB.fullmatch(en):
            errors.append(f"marketplace.json: plugin name {en!r} must be kebab-case")
        src = entry.get("source")
        if not src:
            errors.append(f"marketplace.json: plugin {en!r} is missing source")
        elif isinstance(src, str) and not os.path.isdir(src.lstrip("./") or "."):
            errors.append(f"marketplace.json: plugin {en!r} source {src!r} is not a directory")
        if en == pj.get("name") and entry.get("version") != pj.get("version"):
            errors.append(
                f"marketplace.json: {en!r} version {entry.get('version')!r} does not "
                f"match plugin.json {pj.get('version')!r} - bump both")
    if pj.get("name") and pj["name"] not in names:
        errors.append(f"marketplace.json: no entry for plugin {pj['name']!r}")

# --- agents ----------------------------------------------------------------
skill_dirs = {os.path.basename(p.rstrip("/")) for p in glob.glob(f"{PLUGIN}/skills/*/")}
agent_names: list[str] = []

for f in sorted(glob.glob(f"{PLUGIN}/agents/*.md")):
    fm = frontmatter(f)
    if fm is None:
        errors.append(f"{f}: no frontmatter")
        continue
    n = fm.get("name", "")
    agent_names.append(n)
    if not (3 <= len(n) <= 50):
        errors.append(f"{f}: name {n!r} must be 3-50 characters")
    if not KEBAB.fullmatch(n):
        errors.append(f"{f}: name {n!r} must be kebab-case")
    if n and n != os.path.basename(f)[: -len(".md")]:
        errors.append(f"{f}: name {n!r} does not match its filename")
    if not fm.get("description"):
        errors.append(f"{f}: missing description")
    model = fm.get("model")
    if model and model not in VALID_MODELS and not model.startswith("claude-"):
        errors.append(f"{f}: model {model!r} invalid")
    for tool in tool_list(fm.get("tools", "")):
        if tool not in VALID_TOOLS:
            errors.append(f"{f}: tools names unknown tool {tool!r}")
    raw_skills = fm.get("skills", "")
    if raw_skills:
        try:
            declared = json.loads(raw_skills)
        except Exception:
            errors.append(f"{f}: skills is not a JSON array: {raw_skills!r}")
        else:
            for ref in declared:
                bare = ref.split(":", 1)[1] if ":" in ref else ref
                if bare not in skill_dirs:
                    errors.append(f"{f}: skills names {ref!r}, which is not a Marmalade skill")

dups = sorted({x for x in agent_names if agent_names.count(x) > 1})
if dups:
    errors.append(f"agents: duplicate names: {', '.join(dups)}")

# --- skills ----------------------------------------------------------------
for d in sorted(glob.glob(f"{PLUGIN}/skills/*/")):
    skill_md = os.path.join(d, "SKILL.md")
    if not os.path.isfile(skill_md):
        errors.append(f"{d}: missing SKILL.md")
        continue
    fm = frontmatter(skill_md)
    if fm is None:
        errors.append(f"{skill_md}: no frontmatter")
        continue
    want = os.path.basename(d.rstrip("/"))
    if not fm.get("name"):
        errors.append(f"{skill_md}: missing name")
    elif fm["name"] != want:
        errors.append(f"{skill_md}: name {fm['name']!r} does not match its directory {want!r}")
    if not fm.get("description"):
        errors.append(f"{skill_md}: missing description")
    for tool in tool_list(fm.get("allowed-tools", "")):
        if tool not in VALID_TOOLS:
            errors.append(f"{skill_md}: allowed-tools names unknown tool {tool!r}")

# --- commands --------------------------------------------------------------
for f in sorted(glob.glob(f"{PLUGIN}/commands/*.md")):
    fm = frontmatter(f)
    if fm is None:
        errors.append(f"{f}: no frontmatter")
        continue
    if not fm.get("description"):
        errors.append(f"{f}: missing description")
    for tool in tool_list(fm.get("allowed-tools", "")):
        if tool not in VALID_TOOLS:
            errors.append(f"{f}: allowed-tools names unknown tool {tool!r}")

# --- descriptions are loaded into every session ----------------------------
for f in sorted(glob.glob(f"{PLUGIN}/agents/*.md")) + sorted(glob.glob(f"{PLUGIN}/skills/*/SKILL.md")):
    fm = frontmatter(f) or {}
    d = " ".join(fm.get("description", "").split())
    if len(d) > MAX_DESCRIPTION:
        errors.append(f"{f}: description is {len(d)} chars (max {MAX_DESCRIPTION})")

# --- ${CLAUDE_PLUGIN_ROOT} paths must resolve ------------------------------
# A path that does not resolve fails silently once installed: the skill simply
# never loads its reference, and nothing says so.
PLUGIN_PATH = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")
shipped = []
for pattern in ("agents/*.md", "skills/*/*.md", "skills/*/*/*.md", "commands/*.md", "hooks/*.json"):
    shipped += glob.glob(f"{PLUGIN}/{pattern}")
for f in sorted(shipped):
    for rel in PLUGIN_PATH.findall(read(f)):
        if not os.path.exists(os.path.join(PLUGIN, rel.rstrip("."))):
            errors.append(f"{f}: ${{CLAUDE_PLUGIN_ROOT}}/{rel} does not exist")

# --- relative links out of commands and skills -----------------------------
REL_LINK = re.compile(r"\]\((\.\.?/[^)#\s]+)")
for f in sorted(glob.glob(f"{PLUGIN}/commands/*.md")) + sorted(glob.glob(f"{PLUGIN}/skills/*/SKILL.md")):
    for rel in REL_LINK.findall(read(f)):
        if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(f), rel))):
            errors.append(f"{f}: relative link {rel!r} does not resolve")

# --- export presets match the themes on disk -------------------------------
themes = {
    os.path.basename(p)[: -len(".json")]
    for p in glob.glob(f"{PLUGIN}/assets/themes/*.json")
    if not p.endswith(".template.json")
}
m = re.search(r"^PRESETS\s*=\s*\{(.*?)\}", read(f"{PLUGIN}/scripts/marmalade_export.py"), re.M | re.S)
if not m:
    errors.append("marmalade_export.py: could not find PRESETS")
else:
    presets = set(re.findall(r'"([^"]+)"', m.group(1)))
    if presets != themes:
        missing = ", ".join(sorted(themes - presets)) or "none"
        extra = ", ".join(sorted(presets - themes)) or "none"
        errors.append(
            f"marmalade_export.py PRESETS disagrees with assets/themes/: "
            f"on disk but not in PRESETS: {missing}; in PRESETS but not on disk: {extra}")

# --- the manifest filename in the code matches the docs --------------------
names = set(re.findall(r'MANIFEST_NAME\s*=\s*"([^"]+)"', read(f"{PLUGIN}/scripts/marmalade_export.py")))
names |= set(re.findall(r'MANIFEST_NAME\s*=\s*"([^"]+)"', read(f"{PLUGIN}/scripts/docs_sync.py")))
if len(names) > 1:
    errors.append(f"MANIFEST_NAME disagrees between scripts: {', '.join(sorted(names))}")
# CHANGELOG.md is excluded: it names old spellings to describe the fixes that
# changed them, which is exactly what a changelog is for.
for f in sorted(set(glob.glob(f"{PLUGIN}/**/*.md", recursive=True))):
    if os.path.basename(f) == "CHANGELOG.md":
        continue
    for spelled in set(re.findall(r"`(\.[A-Za-z]*[Mm]armalade-manifest\.json)`", read(f))):
        if spelled not in names:
            errors.append(
                f"{f}: documents the manifest as {spelled!r}, but the code writes "
                f"{', '.join(sorted(names))} - case matters on Linux")

# --- the hand-duplicated files are still identical -------------------------
for a, b in (("README.md", f"{PLUGIN}/README.md"), ("LICENSE", f"{PLUGIN}/LICENSE")):
    if os.path.isfile(a) and os.path.isfile(b) and read(a) != read(b):
        errors.append(f"{a} and {b} have drifted apart - they are kept byte-identical")

# --- report ----------------------------------------------------------------
if errors:
    print("Plugin validation FAILED:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print(
    f"Plugin validation passed: {len(glob.glob(f'{PLUGIN}/agents/*.md'))} agents, "
    f"{len(glob.glob(f'{PLUGIN}/skills/*/SKILL.md'))} skills, "
    f"{len(glob.glob(f'{PLUGIN}/commands/*.md'))} commands, all rules OK.")
