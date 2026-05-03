# Research Hub Workspace

This workspace is connected to Research Hub.

Use this marker when the user asks to summarize documents, compare research
progress, inspect related work, produce reports, analyze results across
machines, or find context from other workspaces.

Generated context:

- `_research_context/manifest.json`
- `_research_context/START_HERE.md`
- `_research_context/documents.jsonl`
- `_research_context/document_chunks.jsonl`

Configuration:

- `RESEARCH_HUB`: set by the installer or environment.
- `RESEARCH_WORKSPACE_ID`: set by the installer or environment.

Rules:

- Do not move or rewrite original research files just to index them.
- Treat `_research_context/` and hub snapshots as generated projections.
- Preserve source paths when citing evidence.
- Ask for the hub/NAS path if cross-workspace context is needed and
  `RESEARCH_HUB` is unknown.
