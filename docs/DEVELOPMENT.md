# Development Files

This repository intentionally separates install/runtime files from development
history.

## Runtime Install Surface

These files are needed by a user installing Research Hub:

- `src/research_hub/`
- `skills/`
- `templates/`
- `scripts/install_workspace.sh`
- `scripts/fetch_skills.sh`
- `README.md`
- `docs/INSTALL.md`
- `docs/intake-dispatch.md`
- `docs/skill-map.md`
- `LICENSE`
- `pyproject.toml`

## Development Surface

These files are useful for maintainers, but should not be loaded by default
when an agent is only trying to use the tool:

- `tests/`
- `docs/dev/`
- `docs/integrations.md`
- `docs/oss-reuse.md`
- `docs/oss-ui-shortlist.md`
- `AGENTS.md`
- `CODEX_TASK.md`

The long Superpowers plans and specs live under `docs/dev/superpowers/`. They
are implementation history, not runtime instruction.

## Context Weight Policy

Keep `skills/*/SKILL.md` short. Skills should point agents to generated
`_research_context` files and CLI commands, not embed long architecture docs.

If a document is longer than roughly 200 lines, prefer:

- keep it under `docs/dev/`, or
- replace it with a short operator doc plus links.

Runtime docs should answer:

- how to install,
- how to run,
- how to connect distributed workspaces,
- what is automatic,
- what still requires manual scheduling or SSH setup.

