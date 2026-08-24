---
type: llm
---
Grade the response against these criteria. Each is independently pass/fail.

An unaided model reliably picks `stateDiagram-v2` here and labels its
transitions, so those are no longer worth asking. These criteria test what
Marmalade's method adds on top.

- **A focal state is marked.** `assigned` is where both loops return and the only
  state a ticket can be resolved from; the diagram singles it out with a
  `classDef`, rather than rendering all six states identically.
- **The response names what it deliberately left out** — the fields, the
  timers-as-jobs, the notification side effects, the agent assignment mechanics —
  rather than presenting the diagram as a complete model of ticketing.
- **`accDescr` is a real description, not a restatement of the title.** It should
  let someone who cannot see the diagram follow the lifecycle: where a ticket
  starts, the two ways it ends, and that it can loop.
- **The two time-based rules are represented as transition conditions**, and the
  response is explicit that a state diagram cannot show elapsed time itself — the
  14-day and 30-day windows are guards, not states.
- **The response does not invent states** the prompt did not describe (no
  `in_progress`, no `pending_review`, no `archived`).
- **It states the density budget or node count it worked to**, or otherwise shows
  it made a deliberate size decision rather than drawing everything mentioned.
