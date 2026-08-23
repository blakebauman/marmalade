---
tags: mermaid-authoring
runs: 3
---
Document how a support ticket moves through our system: it opens as `new`, an
agent picks it up so it becomes `assigned`, it can go to `waiting_on_customer`
and come back to `assigned` any number of times, an agent can escalate it to
`escalated` which routes to a senior agent and back to `assigned`, and it ends
either `resolved` or `closed_no_response` if the customer never replies within
14 days. Resolved tickets can be reopened within 30 days back to `assigned`.
