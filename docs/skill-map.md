# Research Hub Skill Map

This document fixes the intended relationship between Superpowers process
skills, Codex/plugin skills, and the `research-hub-skills` package.

Process trail:

- Design: `docs/superpowers/specs/2026-04-30-research-hub-skill-map-design.md`
- Plan: `docs/superpowers/plans/2026-04-30-research-hub-skill-map.md`

The short version:

- Superpowers skills define how Codex should work.
- Research Hub skills define how Codex should read, index, and publish research
  workspace context.
- Optional profiles, such as `dcase2026`, add domain-specific interpretation
  without turning the core package into a domain-specific tool.

## Skill Ecosystem

```mermaid
flowchart TD
    A["Codex session"] --> B["Skill check"]

    B --> SP["Superpowers process skills"]
    B --> RH["research-hub-skills"]
    B --> PLUG["Other Codex/plugin skills"]

    SP --> SP1["using-superpowers<br/>check relevant skills first"]
    SP --> SP2["brainstorming<br/>shape unclear feature work"]
    SP --> SP3["writing-plans<br/>turn approved design into tasks"]
    SP --> SP4["test-driven-development<br/>test behavior before code"]
    SP --> SP5["verification-before-completion<br/>fresh evidence before claims"]
    SP --> SP6["github / yeet<br/>commit, push, PR workflow"]

    RH --> RHC["research-hub-context<br/>read generated context first"]
    RH --> RWI["research-workspace-index<br/>build workspace index"]
    RH --> RWP["research-workspace-publish<br/>publish to hub"]
    RH --> RLI["research-literature-index<br/>index related work evidence"]
    RH --> RDS["research-discussion-synthesis<br/>synthesize discussions"]
    RH --> RDP["research-documentation-patch<br/>patch docs with evidence"]

    PLUG --> GH["GitHub"]
    PLUG --> DOC["Docs / PDF / spreadsheets"]
    PLUG --> WEB["Browser / web app tools"]
    PLUG --> HF["Hugging Face"]

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
    CTX --> AGENT["Codex / research agent startup surface"]
```

## Publish Flow

```mermaid
sequenceDiagram
    participant User
    participant Codex
    participant Superpowers
    participant Skill as Research Hub Skill
    participant CLI as research-hub CLI
    participant Core as research_hub core
    participant Profile as optional profile
    participant Hub as Hub / _research_context

    User->>Codex: Ask to index, publish, or reason over a research workspace
    Codex->>Superpowers: Invoke relevant process skill first
    Superpowers-->>Codex: Workflow guardrails and verification expectations
    Codex->>Skill: Invoke relevant research-hub skill
    Skill->>CLI: research-hub publish --profile generic or dcase2026
    CLI->>Core: Scan text-like workspace files
    Core->>Profile: Enrich records when a non-generic profile is selected
    Profile-->>Core: Domain hints, claims, runs, metrics, statuses
    Core->>Hub: Write JSONL, SQLite, manifest, context projection
    CLI->>Hub: Build panel and agent context packs
    Codex->>Hub: Read generated context before raw folders
    Codex-->>User: Evidence-linked summary, next action, or patch
```

## Responsibilities

| Layer | Responsibility | Should not do |
| --- | --- | --- |
| Superpowers | Control the work process: brainstorm, plan, test, verify, publish. | Encode DCASE research semantics. |
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
