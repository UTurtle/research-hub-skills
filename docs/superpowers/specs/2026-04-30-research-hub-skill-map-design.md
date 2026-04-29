# Research Hub Skill Map Design

## Goal

Document how Superpowers process skills, Codex/plugin skills, and
`research-hub-skills` relate to each other, then make that relationship visible
through a persistent Mermaid-backed reference document.

## User Intent

The user wanted more than an inline Mermaid answer. The repository should carry
a durable explanation of the skill ecosystem, and the work should follow the
Superpowers process rather than merely mentioning it.

## Chosen Approach

Use a lightweight documentation-only design:

1. Keep `docs/skill-map.md` as the human-facing reference.
2. Add this design document under `docs/superpowers/specs/`.
3. Add an implementation plan under `docs/superpowers/plans/`.
4. Link `docs/skill-map.md` back to the Superpowers spec and plan.

This avoids changing package behavior while making the intended workflow
auditable in the repository.

## Alternatives Considered

### Inline Answer Only

This is too weak because the explanation disappears into chat history and does
not help future contributors.

### README-Only Integration

This would make the root README heavier. The skill map is detailed enough to
deserve its own document, with the README free to stay focused on installation
and usage.

### Dedicated Documentation Page With Spec And Plan

This is the selected approach. It keeps the rendered Mermaid diagrams close to
the package docs and keeps the Superpowers process trail explicit.

## Architecture

The documentation has three layers:

- `docs/skill-map.md`: the stable reader-facing map and policy.
- `docs/superpowers/specs/2026-04-30-research-hub-skill-map-design.md`: why the
  document exists and what design constraints govern it.
- `docs/superpowers/plans/2026-04-30-research-hub-skill-map.md`: the execution
  checklist used to add or revise the document.

The diagrams should distinguish process skills from domain skills. Superpowers
skills govern how Codex works. Research Hub skills govern how research context
is read, indexed, published, and interpreted. Optional profiles such as
`dcase2026` add domain-specific interpretation without changing the generic
core.

## Data Flow

The skill map should show two flows:

1. Skill ecosystem: Codex checks relevant skills, then uses Superpowers,
   Research Hub, and other plugin skills according to responsibility.
2. Publish flow: a user request triggers Superpowers workflow, then Research Hub
   indexing, optional profile enrichment, hub output generation, and agent
   reading from `_research_context/`.

## Error Handling

The document must state that generated profile hints are navigation aids. Source
workspace files remain authoritative when there is any conflict.

## Testing And Verification

This is a documentation-only change. Verification should include:

- `git diff --check`
- reading the added Markdown files for broken references and unfinished
  placeholders
- `git status --short --branch` after push

Python tests are not required for this documentation-only change because no code
paths are modified.

## Scope

This design covers only the persistent skill map documentation and its
Superpowers process trail. It does not alter `research_hub` runtime behavior,
profile inference, tests, packaging, or install scripts.
