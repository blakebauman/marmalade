#!/usr/bin/env python3
"""Run Marmalade's eval cases with a with/without-plugin ablation.

This is a stopgap. The cases under plugins/marmalade/evals/ are authored for the
native `claude plugin eval` harness, which is still in early access and refuses
to run. This script drives the same case files so the suite is usable now. When
`claude plugin eval` opens up, delete this file - the cases do not change.

Each case is a directory:

    plugins/marmalade/evals/<case>/
      prompt.md          frontmatter (tags, runs, files) + the user's message
      files/             optional inputs, copied into the run directory
      graders/*.md       frontmatter `type:` + criteria body
                           type: script  - command:/expect:, run against the output
                           type: llm     - criteria graded by a judge model

Both arms run with a settings overlay that disables any *installed* Marmalade,
so they differ only by `--plugin-dir` pointing at this working tree. Each run
happens in a scratch directory outside the repo, so the repo's own CLAUDE.md
cannot leak into either arm.

    python3 scripts/run_evals.py --list
    python3 scripts/run_evals.py --yes
    python3 scripts/run_evals.py --yes --case no-slop-density --runs 1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "marmalade"
EVALS = PLUGIN / "evals"
RESULTS = EVALS / "results"
ARMS = ("with_plugin", "without_plugin")
AGENT_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash", "Skill"]


def frontmatter(text: str):
    """Parse the flat `key: value` frontmatter the cases use. No yaml dependency."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).split("\n"):
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if km:
            meta[km.group(1)] = km.group(2).strip()
    return meta, m.group(2)


class Case:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.meta, self.prompt = frontmatter((path / "prompt.md").read_text())
        self.runs = int(self.meta.get("runs", 3))
        self.tags = [t.strip() for t in self.meta.get("tags", "").split(",") if t.strip()]
        self.graders = []
        for g in sorted((path / "graders").glob("*.md")):
            meta, body = frontmatter(g.read_text())
            self.graders.append({"name": g.stem, "meta": meta, "body": body.strip()})


def discover(case_filter=None, tag_filter=None):
    cases = []
    for d in sorted(EVALS.iterdir() if EVALS.is_dir() else []):
        if not (d / "prompt.md").is_file():
            continue
        c = Case(d)
        if case_filter and case_filter not in c.name:
            continue
        if tag_filter and tag_filter not in c.tags:
            continue
        cases.append(c)
    return cases


# Disable an installed Marmalade in BOTH arms, so the only difference is whether
# --plugin-dir loads this working tree. Without this the baseline silently has the
# plugin the user already installed, and every delta reads as zero.
_SETTINGS = None


def settings_overlay() -> str:
    global _SETTINGS
    if _SETTINGS is None:
        fd, path = tempfile.mkstemp(suffix=".json", prefix="marmalade-eval-")
        with os.fdopen(fd, "w") as fh:
            json.dump({"enabledPlugins": {"marmalade@marmalade": False}}, fh)
        _SETTINGS = path
    return _SETTINGS


def claude(prompt: str, cwd: Path, plugin: bool, timeout: int = 900):
    cmd = ["claude", "-p", prompt, "--settings", settings_overlay(),
           "--allowed-tools", *AGENT_TOOLS]
    if plugin:
        cmd += ["--plugin-dir", str(PLUGIN)]
    started = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "text": "", "error": f"timed out after {timeout}s", "seconds": timeout}
    return {
        "ok": proc.returncode == 0,
        "text": proc.stdout,
        "error": proc.stderr.strip()[:400] if proc.returncode else "",
        "seconds": round(time.time() - started, 1),
    }


def run_script_grader(grader, out_dir: Path) -> bool:
    cmd = grader["meta"].get("command", "")
    cmd = cmd.replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN)).replace("${OUTPUT_DIR}", str(out_dir))
    expect = grader["meta"].get("expect", "exit_zero")
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if expect == "exit_zero_or_no_diagrams":
        try:
            if not json.loads(proc.stdout).get("diagrams"):
                return True
        except Exception:
            pass
    return proc.returncode == 0


JUDGE = """You are grading one response against a list of pass/fail criteria.

Criteria:
{criteria}

The response being graded, including any files it wrote:
<response>
{output}
</response>

Return ONLY a JSON object, no prose, of the form:
{{"verdicts": [{{"criterion": "<first few words>", "passed": true|false, "why": "<one sentence>"}}]}}
One entry per criterion, in order."""


def run_llm_grader(grader, output: str) -> tuple:
    prompt = JUDGE.format(criteria=grader["body"], output=output[:60000])
    res = claude(prompt, cwd=Path(tempfile.gettempdir()), plugin=False, timeout=300)
    m = re.search(r"\{.*\}", res["text"], re.S)
    if not m:
        return 0, 0
    try:
        verdicts = json.loads(m.group(0))["verdicts"]
    except Exception:
        return 0, 0
    return sum(1 for v in verdicts if v.get("passed")), len(verdicts)


def collect_output(run_dir: Path, transcript: str) -> str:
    """The judge sees the assistant's reply plus anything it wrote to disk."""
    parts = [transcript]
    for f in sorted(run_dir.rglob("*")):
        if f.is_file() and f.suffix in (".mmd", ".mermaid", ".md") and f.stat().st_size < 40000:
            parts.append(f"\n--- file: {f.relative_to(run_dir)} ---\n{f.read_text(errors='replace')}")
    return "\n".join(parts)


def score_run(case: Case, run_dir: Path, transcript: str) -> float:
    passed = total = 0
    output = collect_output(run_dir, transcript)
    for g in case.graders:
        if g["meta"].get("type") == "script":
            total += 1
            passed += 1 if run_script_grader(g, run_dir) else 0
        else:
            p, t = run_llm_grader(g, output)
            passed += p
            total += t
    return passed / total if total else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", help="substring filter on the case name")
    ap.add_argument("--tag", help="only cases carrying this tag")
    ap.add_argument("--runs", type=int, help="override the per-case run count")
    ap.add_argument("--list", action="store_true", help="list the cases and exit")
    ap.add_argument("--yes", action="store_true",
                    help="actually run. Without it this only reports what it would do - "
                         "each run spawns a Claude session and costs tokens.")
    args = ap.parse_args()

    cases = discover(args.case, args.tag)
    if not cases:
        print("No matching eval cases.")
        return 1

    if args.list or not args.yes:
        total = sum((args.runs or c.runs) * 2 for c in cases)
        print(f"{len(cases)} case(s), {total} agent runs (both arms):\n")
        for c in cases:
            n = args.runs or c.runs
            kinds = ", ".join(sorted({g["meta"].get("type", "llm") for g in c.graders}))
            print(f"  {c.name:26s} runs={n} arms=2  graders: {len(c.graders)} ({kinds})")
        if not args.list:
            print("\nNothing ran. Re-run with --yes to execute.")
        return 0

    if not shutil.which("claude"):
        print("ERROR: `claude` is not on PATH.")
        return 2

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_root = RESULTS / stamp
    report = {"cases": []}

    for case in cases:
        n = args.runs or case.runs
        row = {"case": case.name, "runs": n, "arms": {}}
        for arm in ARMS:
            scores, seconds = [], []
            for i in range(1, n + 1):
                run_dir = out_root / case.name / arm / f"run-{i}"
                run_dir.mkdir(parents=True, exist_ok=True)
                # Work outside the repo so the repo's CLAUDE.md is not discovered.
                work = Path(tempfile.mkdtemp(prefix=f"marmalade-{case.name}-"))
                src = case.path / "files"
                if src.is_dir():
                    shutil.copytree(src, work / "files", dirs_exist_ok=True)
                print(f"  {case.name} / {arm} / run-{i} ...", flush=True)
                res = claude(case.prompt, work, plugin=(arm == "with_plugin"))
                if not res["ok"]:
                    print(f"    run failed: {res['error'] or 'non-zero exit'}")
                    shutil.rmtree(work, ignore_errors=True)
                    continue
                (work / "transcript.txt").write_text(res["text"])
                s = score_run(case, work, res["text"])
                shutil.copytree(work, run_dir, dirs_exist_ok=True)
                shutil.rmtree(work, ignore_errors=True)
                scores.append(s)
                seconds.append(res["seconds"])
                print(f"    score {s:.2f}  ({res['seconds']}s)")
            row["arms"][arm] = {
                "scores": [round(s, 3) for s in scores],
                "mean": round(statistics.mean(scores), 3) if scores else None,
                # Spread first: a delta smaller than the spread is not a result.
                "spread": round(max(scores) - min(scores), 3) if len(scores) > 1 else 0.0,
                "stddev": round(statistics.stdev(scores), 3) if len(scores) > 1 else 0.0,
                "seconds_mean": round(statistics.mean(seconds), 1) if seconds else None,
                "completed": len(scores),
            }
        a, b = row["arms"]["with_plugin"]["mean"], row["arms"]["without_plugin"]["mean"]
        row["delta"] = round(a - b, 3) if a is not None and b is not None else None
        report["cases"].append(row)

    (out_root / "report.json").write_text(json.dumps(report, indent=2))

    print(f"\n{'case':26s} {'with':>6s} {'without':>8s} {'delta':>7s} {'spread':>7s}")
    print("-" * 60)
    for r in report["cases"]:
        w, o = r["arms"]["with_plugin"], r["arms"]["without_plugin"]
        spread = max(w["spread"], o["spread"])
        fmt = lambda v: f"{v:.2f}" if v is not None else "  --"
        flag = "  <- delta within spread" if r["delta"] is not None and abs(r["delta"]) <= spread else ""
        print(f"{r['case']:26s} {fmt(w['mean']):>6s} {fmt(o['mean']):>8s} "
              f"{fmt(r['delta']):>7s} {spread:>7.2f}{flag}")
    print(f"\nFull report: {out_root / 'report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
