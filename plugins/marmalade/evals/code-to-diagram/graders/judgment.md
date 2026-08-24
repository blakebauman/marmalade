---
type: llm
---
The package has 21 modules across four subpackages (`api`, `domain`, `adapters`,
`tasks`) plus `config` and `errors` at the root. Twenty-one nodes is well over any
sensible density budget, so the interesting judgment is what the response does
about that — not whether it can list imports.

Grade the response. Each criterion is independently pass/fail.

- **It does not draw all 21 modules.** Emitting a node per module is the failure
  this case tests for, however tidy the result looks.
- **It makes the collapse explicit**: the response says it aggregated to package
  level (or scanned a subtree) and why, rather than silently drawing a smaller
  graph and leaving the reader to assume it is complete.
- **The package-level shape is correct**: `api` and `tasks` both depend on
  `domain` and `adapters`; `domain` depends on nothing but `errors`; `adapters`
  depends on `config`. In particular `domain` must not be shown depending on
  `adapters` or `api` — that inversion is the thing the diagram exists to prove.
- **`config` and `errors` are handled deliberately** — either shown as the
  leaf dependencies they are, or excluded with a stated reason. Scattering edges
  to them from everything is noise.
- **Edge direction is stated and consistent** (dependant → dependency), so the
  reader can tell which way to read the arrows without guessing.
- **The response does not claim the diagram shows runtime behaviour.** These are
  static imports; a request path through this package is a different diagram.
- **It carries `accTitle` and `accDescr`**, and `accDescr` names the layering
  rather than saying "a module dependency diagram".
