---
name: research-hub-context
description: Use when working in a Research Hub workspace or when the user asks to summarize, compare, search, report on, or synthesize research documents, notes, related work, experiment results, claims, progress, or context across one or more local/remote workspaces. Trigger when the workspace contains _research_context, RESEARCH_HUB.md, a Research Hub manifest, hub snapshots, or the user mentions distributed workspaces, NAS, SSH, agents, reports, paper writing, related works, cross-workspace comparison, document aggregation, or overall research analysis.
---

# research-hub-context

Purpose: support runtime research work after installation. Use Research Hub as
an index-first map over scattered workspaces so agents and humans can treat
distributed research files like one library without moving original files.

Rules:

1. Keep original workspace files as the source of truth.
2. Prefer generated `_research_context/` before scanning raw files.
3. If `RESEARCH_HUB.md` exists, read it to find the configured hub path,
   workspace id, and operating notes.
4. For cross-workspace questions, inspect hub snapshots or ask for
   `RESEARCH_HUB` when the hub path is missing.
5. Preserve source paths and evidence links.
6. Do not invent missing metadata.
7. Mark uncertain fields as `unknown` or `needs_review`.
8. Do not add heavyweight dependencies for v0.1.
9. For DCASE2026, treat deployable, diagnostic, oracle, and negative claims as
   separate claim classes.

Startup order:

1. Read `RESEARCH_HUB.md` if present.
2. Read `_research_context/manifest.json`.
3. Read `_research_context/START_HERE.md`.
4. Search `_research_context/document_chunks.jsonl` and `documents.jsonl`.
5. Only then open raw workspace files needed for evidence.

Freshness:

- If the user asks whether new `.md` or `.txt` files are reflected, check the
  manifest timestamp and document count.
- If context is stale and a terminal/supervisor is available, run
  `python -m research_hub.cli watch --workspace-root <workspace> --hub <hub> --workspace-id <id>`.
  Use `--once` for a one-shot refresh.
- If the user asks for another workspace or whole-network analysis, run or
  propose `python -m research_hub.cli refresh-hub --hub <hub>` before reading
  hub snapshots. Use `--execute-transport` only when SSH paths are trusted.
- If recurring freshness is requested on a Linux workspace, install the user
  timer with `scripts/install_user_timer.sh`; default cadence is daily.
