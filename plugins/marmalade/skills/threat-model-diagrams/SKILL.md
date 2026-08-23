---
name: threat-model-diagrams
description: Draw data flow diagrams with trust boundaries for threat modeling, and review diagrams for information that should not be published. Use when threat modeling, drawing a DFD, marking trust boundaries, doing a STRIDE analysis, or checking a diagram before it leaves the team.
license: MIT
compatibility: Requires Python 3.9+.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Threat model diagrams

Two jobs: draw the diagram a threat model needs, and make sure no diagram
publishes something it should not.

## The data flow diagram

A threat model DFD has four element kinds and one thing that matters more than
all of them: **the boundaries**.

| Element | Draw as |
| :-- | :-- |
| External entity — a user or system outside your control | `([Stadium])`, dashed border |
| Process — something you run that transforms data | `[Rectangle]` |
| Data store | `[(Cylinder)]` |
| Trust boundary | `subgraph` with a named zone |

```
flowchart LR
    subgraph Untrusted["Untrusted — public internet"]
        User([Uploader])
    end
    subgraph App["Application tier"]
        GW[API gateway]
        Scan[Malware scanner]
    end
    subgraph Data["Storage tier"]
        Bucket[(Object store)]
    end

    User -->|multipart upload| GW
    GW -->|size + MIME + auth check| Scan
    Scan -->|clean only| Bucket
    Scan -->|infected| Quar[(Quarantine)]

    classDef risk fill:#fbe4dc,stroke:#D55E00,stroke-width:2px,color:#5a2000
    class GW,Scan risk
```

**Every edge crossing a boundary is a finding waiting to happen.** Label each
crossing with the control that makes it safe — `size + MIME + auth check` — and
where there is no control, the missing label is the finding.

Start from `${CLAUDE_PLUGIN_ROOT}/assets/templates/threat-model.mmd`.

## Working through STRIDE

Walk each boundary crossing against the six categories, and let the diagram tell
you which apply:

| | Applies to | The diagram question |
| :-- | :-- | :-- |
| **S**poofing | External entities, processes | Is the source of this edge authenticated? |
| **T**ampering | Data flows, stores | Is this edge integrity-protected in transit and at rest? |
| **R**epudiation | Processes | Does anything log that this edge was traversed? |
| **I**nformation disclosure | Flows, stores | Who else can read this edge or this store? |
| **D**enial of service | Processes, flows | What happens when this edge is flooded? |
| **E**levation of privilege | Boundary crossings | Can input on this edge cause code to run on the other side? |

Elevation of privilege maps exactly onto boundary crossings, which is why the
boundaries are the part worth getting right.

Record findings next to the diagram, keyed to the edge they concern, so the
diagram and the analysis stay coupled.

## Diagrams publish. Treat them that way

An architecture diagram gets pasted into tickets, decks, screenshots, and vendor
questionnaires. It leaks differently from code: a hostname in a node label
travels much further than the same string in a config file, and it goes to people
who were never going to read your config.

The plugin scans every diagram write with a PreToolUse hook and blocks on:

- Credentials — AWS keys, GitHub and Slack tokens, Stripe keys, Google API keys,
  private key blocks, JWTs, `password=` assignments
- Connection strings carrying a password
- Internal DNS names — `.internal`, `.corp`, `.local`, `.lan`, `.intranet`
- Private IP addresses, excluding the RFC 5737 and RFC 3849 documentation ranges

Turn it off with the `secret_scan` plugin option only if you have a specific
reason.

The hook cannot catch judgment calls. Check these yourself before a diagram
leaves the team:

- **Unreleased product or project names** in node labels
- **Team and vendor names** that reveal org structure or a supplier relationship
- **Exact topology** — replica counts, shard counts, and specific instance types
  tell an attacker about capacity and blast radius
- **Which component is unmaintained.** A diagram that marks the legacy service is
  a map of where to attack
- **Auth mechanism specifics** — say "authenticated", not the header name and
  token format

Use placeholders that are obviously placeholders: `api.example.com`,
`203.0.113.10`, `<API_KEY>`. RFC 5737 addresses (`192.0.2.0/24`,
`198.51.100.0/24`, `203.0.113.0/24`) exist for exactly this and are allowlisted
by the scanner.

## Two diagrams, not one

The threat model DFD and the public architecture diagram have different
audiences and should be different files. The DFD wants every boundary crossing
and every control; the public one wants the shape. Trying to serve both produces
a diagram that is too detailed to share and too vague to analyze.

Related: [diagram-review](../diagram-review/SKILL.md) — question 5 is this.
