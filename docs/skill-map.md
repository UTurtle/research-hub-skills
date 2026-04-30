# Research Hub Skill Map

This document fixes the intended relationship between the Research Hub skills,
the `research_hub` package, generated context, and optional profiles.

The short version:

- Research Hub skills define how Codex should read, index, and publish research
  workspace context.
- Optional profiles add domain-specific interpretation without turning the core
  package into a domain-specific tool.
- `dcase2026` is an appendix example of that profile mechanism.

For autonomous ML agent, personal wiki, vector store, and graph memory
integration patterns, see `docs/integrations.md`.

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
    CORE --> PROFILE["optional domain profile<br/>pluggable enrichment"]

    GENERIC --> GOUT["documents.jsonl<br/>document_chunks.jsonl<br/>search_index.sqlite"]

    PROFILE --> D1["domain entity inference<br/>runs / papers / trials / cases"]
    PROFILE --> D2["domain role inference"]
    PROFILE --> D3["claim classification"]
    PROFILE --> D4["metric / outcome extraction"]
    PROFILE --> D5["status hints"]

    D1 --> DOUT["DCASE enriched outputs"]
    D2 --> DOUT
    D3 --> DOUT
    D4 --> DOUT
    D5 --> DOUT

    DOUT --> O1["domain records<br/>runs.jsonl / papers.jsonl / trials.jsonl"]
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
    participant Profile as optional domain profile
    participant Hub as Hub / _research_context

    User->>Agent: Ask to index, publish, or reason over a research workspace
    Agent->>Skill: Invoke relevant research-hub skill
    Skill->>CLI: research-hub publish --profile generic or domain profile
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
| Domain profile | Infer domain entities, roles, metrics or outcomes, claim hints, and status hints. | Replace source files as the authority. |
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

## Appendix: DCASE2026 profile

```mermaid
flowchart TD
    BASE["Generic index record"] --> DCASE["dcase2026 profile"]
    DCASE --> B["branch inference<br/>main6 / main22 / main23 / main24"]
    DCASE --> R["run inference"]
    DCASE --> ROLE["document roles<br/>contract / status / result / summary"]
    DCASE --> M["metric extraction<br/>DCASE-like / harmonic / official"]
    DCASE --> C["claim hints<br/>deployable / diagnostic / oracle / negative"]

    B --> OUT["DCASE enriched context"]
    R --> OUT
    ROLE --> OUT
    M --> OUT
    C --> OUT

    OUT --> RUNS["runs.jsonl"]
    OUT --> CLAIMS["claims.jsonl"]
    OUT --> PACKS["agent_context/main6.json etc."]
```
