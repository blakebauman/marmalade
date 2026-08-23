# Diagram type syntax reference

Per-type syntax, with the mistakes that actually happen. Read the section for the
type you are writing; skip the rest.

## flowchart

```
flowchart LR
    accTitle: Short name
    accDescr: One paragraph a reader gets if the image fails.

    A([Start]) -->|submits| B{Valid?}
    B -->|yes| C[Process order]
    B -->|no| D[(Error queue)]
    C --> E[[Fulfilment]]

    subgraph Boundary["Trust boundary"]
        C
        E
    end

    classDef focal fill:#dbeaf5,stroke:#0072B2,stroke-width:2px,color:#062033
    class B focal
```

Directions: `TB`/`TD` (top-down), `BT`, `LR`, `RL`. Use `LR` for pipelines and
`TB` for hierarchies — matching the reader's mental model beats saving space.

Edge forms: `-->` arrow, `---` open, `-.->` dotted, `==>` thick, `--o` circle
end, `--x` cross end. Length is set by dash count: `--->` is longer than `-->`,
which is how you nudge layout without a layout engine.

Gotchas: reserved ids (`end` above all), unquoted brackets in labels, labels
spanning lines, `subgraph` without `end`.

## sequenceDiagram

```
sequenceDiagram
    accTitle: Token refresh
    accDescr: The browser retries once after refreshing its token.

    participant B as Browser
    participant A as API

    B->>A: GET /invoices
    A-->>B: 401 token_expired
    alt refresh valid
        B->>A: GET /invoices (retry)
        A-->>B: 200
    else revoked
        Note over B: Redirect to login
    end
```

Arrows: `->>` solid with arrowhead (a call), `-->>` dashed (a return), `-x`
terminated, `->` solid no arrowhead. Blocks: `alt`/`else`, `opt`, `loop`, `par`,
`critical`, `break`. `activate`/`deactivate` or `+`/`-` suffixes show lifelines.

Declare participants explicitly and in reading order — implicit declaration
orders them by first appearance, which is rarely the order you want.

## stateDiagram-v2

```
stateDiagram-v2
    accTitle: Deployment lifecycle
    accDescr: Canary is the only state that can move backwards.

    [*] --> Queued
    Queued --> Building : runner picks up
    Building --> Canary : image pushed
    Canary --> Live : error rate under 1%
    Canary --> RollingBack : error spike
    Live --> [*]

    state Canary {
        [*] --> Warming
        Warming --> Serving
    }
```

`[*]` is both the start and the end pseudo-state. Transition labels go after `:`
— this is the labeling grammar the slop checker looks for. Composite states nest
with `state Name { }`. `<<choice>>` and `<<fork>>` give branch and parallel nodes.

## erDiagram

```
erDiagram
    CUSTOMER ||--o{ ORDER : "places"
    ORDER ||--|{ LINE_ITEM : "contains"

    CUSTOMER {
        uuid id PK
        citext email UK "not null"
    }
```

Cardinality is two tokens per side, read outward from the entity:

| Token | Means |
| :-- | :-- |
| `\|o` / `o\|` | zero or one |
| `\|\|` | exactly one |
| `}o` / `o{` | zero or more |
| `}\|` / `\|{` | one or more |

`--` is an identifying relationship, `..` non-identifying. Attribute keys are
`PK`, `FK`, `UK`, comma-separated. A trailing quoted string is a comment.

Generate these from a live database rather than by hand — see
[schema-to-erd](../../schema-to-erd/SKILL.md).

## classDiagram

```
classDiagram
    class Order {
        +UUID id
        +Money total
        +submit() bool
    }
    Order "1" --> "*" LineItem : contains
    Order ..|> Payable : implements
```

Relations: `<|--` inheritance, `*--` composition, `o--` aggregation, `-->`
association, `..>` dependency, `..|>` realization. Visibility: `+` public,
`-` private, `#` protected, `~` package.

## gantt

```
gantt
    title Migration
    dateFormat YYYY-MM-DD
    axisFormat %b %d
    section Cutover
        Dual write      :done,    dw, 2026-01-06, 14d
        Backfill        :active,  bf, after dw, 21d
        Flip reads      :crit,    fr, after bf, 3d
```

Task syntax: `label :tags, id, start, duration`. Tags: `done`, `active`, `crit`,
`milestone`. `after <id>` expresses a dependency without a hardcoded date, which
is what keeps the chart true when dates slip.

## gitGraph

```
gitGraph
    commit id: "baseline"
    branch release/2.1
    checkout release/2.1
    commit id: "cherry-pick fix"
    checkout main
    merge release/2.1
```

Useful for explaining a branching policy. Not useful for showing actual history —
`git log --graph` already does that, and stays true.

## Others worth knowing

- `quadrantChart` — two-axis positioning. Label the axes or it says nothing.
- `sankey-beta` — flow volumes. Needs real numbers; do not eyeball the widths.
- `timeline` — dated events, one line each.
- `mindmap` — indentation-driven hierarchy. Easy to let sprawl past budget.
- `architecture-beta` — grouped infrastructure with edge junctions.
- `C4Context` / `C4Container` — C4 model levels. Verbose; a flowchart with
  subgraphs is often clearer and always more portable.

Beta diagram types can change syntax between Mermaid minor versions. Pin your
Mermaid version if you depend on one.
