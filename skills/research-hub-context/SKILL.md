---
name: research-hub-context
description: Use when starting work in a research workspace that has generated _research_context files, especially to read indexed state before scanning raw files.
---

# research-hub-context

Purpose: support a domain-neutral, index-first research workspace hub. If a
DCASE2026 profile is present, use the generated runs, claims, metrics, and
agent context packs as reading aids while keeping original files authoritative.

Rules:

1. Keep original workspace files as the source of truth.
2. Prefer generated `_research_context/` for agent startup.
3. Preserve source paths and evidence links.
4. Do not invent missing metadata.
5. Mark uncertain fields as `unknown` or `needs_review`.
6. Do not add heavyweight dependencies for v0.1.
7. For DCASE2026, treat deployable, diagnostic, oracle, and negative claims as
   separate claim classes.
