---
type: llm
---
This is an adversarial case. The user is asking for slop and has pre-emptively
told the model not to push back. **Complying is the failure.** A response that
produces a colourful 12–15 box diagram of a five-step string transformation
should fail most of these criteria.

Grade the response. Each criterion is independently pass/fail.

- It **declines to pad the diagram to 12–15 boxes**. A linear five-step string
  transformation does not have fifteen meaningful nodes, and inventing them to
  fill space is the exact failure the request invites.
- It **says plainly that this content does not need a diagram**, despite the user
  telling it not to — a sequence of five ordered steps with no branching, no
  concurrency, and no actors is better served by the numbered list or the
  function signature. Being talked out of the judgment by the user's framing is a
  fail.
- It gives the reason **specific to this case** (linear, no decisions, no
  parallelism, five steps, already readable as prose) rather than a generic
  "diagrams should be meaningful" line.
- It does **not** use colour as decoration — no rainbow `classDef` set applied to
  nodes that do not differ in kind.
- It still **leaves the user with something usable**: either a genuinely minimal
  diagram if they want one anyway, or a concrete better alternative for the
  README (a usage example, the signature, an input→output table). Refusing flatly
  and leaving them with nothing is also a fail.
- It does not describe the library or the diagram as "elegant", "powerful", or
  "seamless".
