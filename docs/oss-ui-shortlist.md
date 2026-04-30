# OSS UI Shortlist For Research Hub Panel

This shortlist selects MIT/Apache-2.0 UI libraries that can be integrated as
optional, read-only panel adapters over Research Hub outputs.

## Selection Criteria

- License must be MIT or Apache-2.0.
- Must support static/local deployment (no mandatory cloud backend).
- Should work as an adapter over generated files (`JSONL` / `SQLite` exports).
- Keep core `research_hub` package dependency-free.

## Candidates

| Candidate | License | Best use in Research Hub | Integration risk |
| --- | --- | --- | --- |
| Tabulator | MIT | Tables for documents/claims/runs/source links with filtering and sorting. | Low |
| Apache ECharts | Apache-2.0 | Timeline, claim status trends, metric plots, and graph-style summaries. | Low |
| CoreUI Free React Admin Template | MIT | Optional richer dashboard shell if a React panel adapter is added. | Medium |
| Recharts | MIT | React-based chart layer for panel adapters. | Medium |
| visx | MIT | Advanced/custom visual layers for graph and provenance exploration. | Medium |

## Recommended First Choice

**Tabulator (MIT)** is the safest first integration target.

Why:

1. Aligns with file-first substrate and read-only panel goals.
2. Fast to integrate in a static HTML panel.
3. Strong table UX for the current core records:
   - `documents.jsonl`
   - `document_chunks.jsonl`
   - `claims.jsonl`
   - `runs.jsonl`
   - `source_links.jsonl`

## Integration Plan (Thin Adapter First)

1. Keep `research_hub` core unchanged.
2. Add optional panel adapter assets under `panel/vendor/`.
3. Build a read-only view for workspace/topic/claim/run lenses.
4. Preserve source provenance links in every panel view.
5. Keep fallback behavior: if panel adapter fails, `_research_context` outputs remain authoritative and usable.

## License Note

Before vendoring any UI source code, keep upstream attribution and license files
in the repository according to `docs/oss-reuse.md`.
