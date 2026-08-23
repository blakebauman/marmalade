---
type: llm
---
Grade the response against these criteria. Each is independently pass/fail.

- The diagram holds a **density budget**: it does not attempt to draw all
  fourteen things the prompt lists. It draws one coherent path and says what it
  deliberately left out.
- The omissions are **named explicitly** — the response states which elements it
  dropped (e.g. the metrics sidecar, the admin console, the nightly reconciler)
  and why they belong in a different diagram or none.
- Edges carry **verbs**, not bare arrows: "reserves", "publishes", "declines".
  An unlabeled edge between two nouns is the failure this criterion catches.
- There is a **focal point** — one node or path is visually emphasised via a
  classDef, rather than every node being an identical rectangle.
- The response does **not** claim the diagram shows the whole system when it
  shows one path.
- The words "Process", "Data", "Handler", "Service" do not appear as standalone
  node labels.
