---
type: llm
---
Grade the response against these criteria. Each is independently pass/fail.

- Cardinality is **read from the constraints, not guessed**. `users.tenant_id` is
  `NOT NULL REFERENCES tenants(id)`, so tenants-to-users is one-to-many with a
  mandatory parent (`||--o{`); `projects.owner_id` is nullable, so that side is
  optional (`|o`). A response that marks every relationship `||--o{` fails this.
- **`project_members` is recognised as a join table** with a composite primary
  key, and the diagram says so — either by modelling it as the associative entity
  it is, or by rendering projects-to-users as many-to-many and naming
  `project_members` as the join. Silently drawing it as a third ordinary entity
  with two unexplained edges fails.
- The **self-referencing `manager_id`** edge on `users` is present. Dropping it is
  the most common omission and this criterion exists to catch it.
- Relationship edges carry **verbs** ("employs", "owns", "belongs to"), not bare
  connectors.
- The response does not invent tables, columns, or constraints that are absent
  from the SQL.
- It carries `accTitle` and `accDescr`.
