---
type: llm
---
Grade the response against these criteria. Each is independently pass/fail.

- It uses **`stateDiagram-v2`**, not a flowchart. The prompt describes named
  states with transitions between them and explicit start and end conditions —
  that is a state machine, and drawing it as a flowchart is the specific error
  this case tests for.
- It includes the **`[*]` start and end terminals**, so `new` is reachable and
  `resolved` / `closed_no_response` are marked terminal.
- Every transition is **labeled with its trigger** (agent picks up, customer
  replies, 14 days elapse, reopened within 30 days) rather than being a bare
  arrow between two states.
- It represents the **cycles** — `assigned` ↔ `waiting_on_customer`, the
  escalation round trip, and the reopen edge from `resolved` back to `assigned`
  — rather than flattening the flow into a straight line.
- It carries **`accTitle` and `accDescr`**.
- The 14-day and 30-day conditions appear on the edges they govern, not only in
  surrounding prose.
