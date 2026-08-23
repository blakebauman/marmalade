# Evaluating Marmalade's skills

The question each eval answers: **does this skill make Claude produce a materially
better diagram than Claude with no plugin at all?**

Method adapted from the [agentskills.io evaluation
methodology](https://agentskills.io/skill-creation/evaluating-skills).

## Tracked vs. generated

- **Tracked (source):** `plugins/marmalade/evals/<case>/` — the prompt, the input
  files, and the graders. Author and commit these.
- **Generated (gitignored):** `plugins/marmalade/evals/results/` — transcripts,
  produced diagrams, scores. Reproducible; never committed.

## Running them

The cases are authored for the native `claude plugin eval` harness, which the
manifest points at via `experimental.evals`. That harness is **still in early
access** and currently refuses to run, so `scripts/run_evals.py` drives the same
case files in the meantime.

```bash
python3 scripts/run_evals.py --list          # what exists
python3 scripts/run_evals.py --yes           # run everything (costs tokens)
python3 scripts/run_evals.py --yes --case no-slop-density --runs 1
```

When `claude plugin eval` opens up, delete `scripts/run_evals.py`. The case files
do not change.

### How the ablation works

Both arms disable any *installed* Marmalade through a settings overlay; the
with-plugin arm then loads this working tree via `--plugin-dir`. This matters:
if you skip it, the baseline silently runs with the Marmalade the developer
already has installed, and every delta reads as zero for a reason that has
nothing to do with the skills.

Each run happens in a scratch directory outside the repo, so the repo's own
`CLAUDE.md` and `AGENTS.md` cannot leak into either arm.

Caveat: hooks are not exercised. The eval measures skills, agents and commands.

## Case layout

```
plugins/marmalade/evals/<case>/
  prompt.md          frontmatter (tags, runs, files) + the user's message
  files/             optional inputs, copied into the run directory
  graders/*.md       frontmatter `type:` + the criteria
```

Two grader types:

**`type: script`** — deterministic, free, immune to judge drift. This is
Marmalade's advantage over a prose-only skill collection: the plugin ships its
own scorers, so most of what we care about can be *measured*.

```markdown
---
type: script
command: python3 "${CLAUDE_PLUGIN_ROOT}/scripts/marmalade_slop.py" "${OUTPUT_DIR}" --json --min-score 80
expect: exit_zero
---
Every diagram written during the run must score at least 80 on the rubric.
```

`expect` is `exit_zero`, or `exit_zero_or_no_diagrams` for the adversarial case
where producing nothing is a legitimate pass.

**`type: llm`** — reserved for what genuinely needs judgment: did it pick the
right diagram *type*, is the abstraction level right, did it name what it left
out. Each bullet is graded independently pass/fail.

## Writing assertions that measure something

Assertions test **judgment anchored to this prompt's specifics**, never the
presence of a section.

Bad — passes on any output with the right shape:

> "Contains accTitle and accDescr"

Good — anchored, and an unaided run plausibly fails it:

> "It uses `stateDiagram-v2`, not a flowchart. The prompt describes named states
> with transitions and explicit start and end conditions — drawing it as a
> flowchart is the specific error this case tests for."

Rules for a case's assertion set:

- **Objectively gradeable** by a judge reading only the output. Never "is elegant".
- **Anchored to prompt specifics** — the named services, the stated constraints,
  the user's own framing.
- **At least two** an unaided-but-competent Claude would plausibly pass. Without
  these the suite is stacked and the delta is meaningless.
- **At least two** that test what Marmalade's method uniquely produces — the
  density budget, the named omissions, the focal emphasis, cardinality read from
  constraints rather than guessed.
- Keep the mechanical checks in the `script` grader where they belong, and do not
  let them dominate the judged set.

## Adversarial cases

`adversarial-no-diagram` is the sharpest case in the suite: a user asks for a
padded, colourful diagram of a five-step string function and pre-emptively tells
the model not to push back. **Complying is the failure.** At least one criterion
must fail if the model simply does as it is told.

Marmalade's whole thesis is the earn-its-place gate, so a suite without this case
would not be testing the thing the plugin exists to do.

## Reading the results

**Read the spread before the delta.** A single run per arm cannot separate signal
from run-to-run variance, which is why `runs` defaults to 3. The report flags any
case whose delta is smaller than the spread across its own repeats — treat those
as "no result", not "no effect".

**A with-plugin score of 1.00 is a problem, not a win.** At 1.00 the case has no
headroom: it cannot detect a regression, and it cannot tell a good diagram from
one that merely hit its marks.

**A delta of 0.00 means the case is not discriminating** — it does not
automatically mean the skill is useless. The first run of
`authoring-type-choice` scored 0.86 in both arms, yet the transcripts were
plainly different: the with-plugin arm wrote a linted `.mmd` into
`docs/diagrams/`, cited the rubric score, and named the focal state, while the
baseline emitted a single Markdown fence. The assertions were simply ones both
arms pass. That case needs harder criteria — which is exactly what the eval is
for.

The improvement loop: run it, find the assertions that pass in both arms, replace
them with ones that discriminate, and re-run. Drop assertions that pass in both;
investigate ones that fail in both.
