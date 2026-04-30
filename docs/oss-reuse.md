# Open Source Reuse Policy

Research Hub should reuse compatible open-source ideas and interfaces where
they help, but it should not blindly vendor large projects.

The preferred pattern is:

1. reuse architecture and interface ideas,
2. add lightweight adapters over Research Hub JSONL outputs,
3. only copy source code when the license is verified and attribution is added,
4. keep heavy vector, graph, and agent runtimes optional.

## Candidate Matrix

| Project | License status checked | How to use it | Reuse level |
| --- | --- | --- | --- |
| `huggingface/ml-intern` | No license file found during review. Do not copy code. | Architecture reference for agent loop, tool routing, context management, and ML workflow ownership. | Ideas only |
| `microsoft/graphrag` | MIT license. | Reference for graph/RAG export shape, graph-oriented retrieval, and optional downstream graph ingestion. | Adapter-compatible |
| `getzep/graphiti` | Apache-2.0 license. | Reference for temporal graph memory, provenance, and evolving facts. Potential downstream graph backend. | Adapter-compatible |
| `lancedb/lancedb` | Apache-2.0 license. | Potential embedded vector backend for `vector_records.jsonl`. | Optional dependency / adapter |

## Immediate Decisions

- Do not copy `ml-intern` code unless a compatible license is explicitly
  verified later.
- Do not add GraphRAG, Graphiti, or LanceDB as core dependencies.
- Do define exports that these projects or similar tools can ingest:
  - `retrieval/vector_records.jsonl`
  - `retrieval/graph_nodes.jsonl`
  - `retrieval/graph_edges.jsonl`
  - `agent_context/INDEX.json`
- Keep attribution in this document and in any future adapter file that copies
  or derives code.

## Integration Direction

```mermaid
flowchart TD
    RH["Research Hub<br/>portable evidence interface"] --> VEC["vector_records.jsonl"]
    RH --> GN["graph_nodes.jsonl"]
    RH --> GE["graph_edges.jsonl"]
    RH --> AC["agent_context/INDEX.json"]

    VEC --> LANCE["LanceDB adapter<br/>optional"]
    GN --> GRAPH["GraphRAG / Graphiti adapter<br/>optional"]
    GE --> GRAPH
    AC --> AGENT["ml-intern-style agent<br/>architecture reference"]

    AGENT --> RH
    LANCE --> QUERY["semantic library lens"]
    GRAPH --> QUERY2["graph / temporal lens"]
```

## Attribution Requirements

When code is copied or substantially adapted from another project:

1. preserve the upstream copyright notice,
2. add the upstream license file or relevant notice when required,
3. mention the source repository in the file header or adjacent documentation,
4. keep copied code isolated in an adapter module when possible,
5. avoid mixing incompatible licenses into the Apache-2.0 core.

For now, the implementation should use original code in this repository and
only design against compatible external interfaces.
