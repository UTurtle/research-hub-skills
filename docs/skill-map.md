# Research Hub Skill Map

This document fixes the intended relationship between the Research Hub skills,
the `research_hub` package, generated context, and optional profiles.

The short version:

- Research Hub skills define how Codex should read, index, and publish research
  workspace context.
- Optional profiles, such as `dcase2026`, add domain-specific interpretation
  without turning the core package into a domain-specific tool.

## Skill Ecosystem

```mermaid
flowchart TD
    A["Research workspace"] --> RAW["Original files<br/>md / txt / csv / json / yaml / logs / py / sh"]
    RAW --> RH["research-hub-skills"]

    RH --> RHC["research-hub-context<br/>read generated context first"]
    RH --> RWI["research-workspace-index<br/>build workspace index"]
    RH --> RWP["research-workspace-publish<br/>publish to hub"]
    RH --> RLI["research-literature-index<br/>index related work evidence"]
    RH --> RDS["research-discussion-synthesis<br/>synthesize discussions"]
    RH --> RDP["research-documentation-patch<br/>patch docs with evidence"]

    RWI --> CORE["research_hub core"]
    RWP --> CORE
    RHC --> CTX["_research_context/"]

    CORE --> GENERIC["generic profile<br/>default, domain-neutral"]
    CORE --> DCASE["dcase2026 profile<br/>optional DCASE enrichment"]

    GENERIC --> GOUT["documents.jsonl<br/>document_chunks.jsonl<br/>search_index.sqlite"]

    DCASE --> D1["branch inference<br/>main6 / main22 / main23 / main24"]
    DCASE --> D2["run inference"]
    DCASE --> D3["claim classification<br/>deployable / diagnostic / oracle / negative"]
    DCASE --> D4["metric extraction"]
    DCASE --> D5["status hints"]

    D1 --> DOUT["DCASE enriched outputs"]
    D2 --> DOUT
    D3 --> DOUT
    D4 --> DOUT
    D5 --> DOUT

    DOUT --> O1["runs.jsonl"]
    DOUT --> O2["claims.jsonl"]
    DOUT --> O3["manifest.json"]
    DOUT --> O4["panel/index.html"]
    DOUT --> O5["panel/agent_context/&lt;branch&gt;.json"]

    GOUT --> CTX
    DOUT --> CTX
    CTX --> AGENT["Codex / research agent<br/>startup reading surface"]
    O4 --> PANEL["Human-readable panel"]
    O5 --> BRANCHCTX["Branch-specific agent packs"]
```

## Publish Flow

```mermaid
sequenceDiagram
    participant User
    participant Agent as Codex / research agent
    participant Skill as Research Hub Skill
    participant CLI as research-hub CLI
    participant Core as research_hub core
    participant Profile as optional profile
    participant Hub as Hub / _research_context

    User->>Agent: Ask to index, publish, or reason over a research workspace
    Agent->>Skill: Invoke relevant research-hub skill
    Skill->>CLI: research-hub publish --profile generic or dcase2026
    CLI->>Core: Scan text-like workspace files
    Core->>Profile: Enrich records when a non-generic profile is selected
    Profile-->>Core: Domain hints, claims, runs, metrics, statuses
    Core->>Hub: Write JSONL, SQLite, manifest, context projection
    CLI->>Hub: Build panel and agent context packs
    Agent->>Hub: Read generated context before raw folders
    Agent-->>User: Evidence-linked summary, next action, or patch
```

## Responsibilities

| Layer | Responsibility | Should not do |
| --- | --- | --- |
| Research Hub skills | Tell agents how to read, index, publish, synthesize, and patch research context. | Replace source evidence with generated summaries. |
| Research Hub core | Index files, chunk text, build SQLite search, publish generated context. | Make domain-specific claims by default. |
| Generic profile | Preserve the domain-neutral default behavior. | Add branch, run, or claim assumptions. |
| `dcase2026` profile | Infer DCASE branches, runs, document roles, metrics, claim hints, and status hints. | Replace source files as the authority. |
| `_research_context/` | Give agents a generated startup reading surface. | Become the source of truth. |

## Invocation Policy

Use the default profile unless the workspace is explicitly DCASE2026-style:

```bash
research-hub publish --workspace-root . --profile generic
```

Use the DCASE2026 profile when branch/run/claim interpretation is useful:

```bash
research-hub publish --workspace-root . --profile dcase2026
```

When a DCASE profile output conflicts with source evidence, the source evidence
wins. Generated fields such as `claim_type_hint`, `status_hint`, and inferred
`branch` are navigation aids, not final research claims.
