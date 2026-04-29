# Codex Task: Add Research Hub Skills v0.1

Target repo: `UTurtle/research-hub-skills`.

Goal: make the repo immediately usable as a domain-neutral, index-first
research workspace context layer.

Required behavior:

1. Keep the core domain-neutral.
2. Keep DCASE-specific rules under `profiles/dcase2026/` only.
3. Support no-NAS local mode with `.research_hub_local`.
4. Support shared path mode with `RESEARCH_HUB`.
5. Support Git state hub mode with `research-hub sync-push` and
   `research-hub sync-pull`.
6. Generate `_research_context/` in the active workspace.
7. Do not index raw audio, checkpoints, venvs, `.git`, caches, `wandb`, or
   `node_modules`.
8. Do not modify original workspace files except `AGENTS.md` during `init`.
9. Keep dependencies empty for v0.1.
10. Make `python -m research_hub.cli --help` work.

Smoke test:

```bash
python -m compileall src
rm -rf /tmp/rh-smoke /tmp/rh-hub
mkdir -p /tmp/rh-smoke
printf '# Note\nhello\n' > /tmp/rh-smoke/note.md
PYTHONPATH=src python -m research_hub.cli init \
  --workspace-root /tmp/rh-smoke --hub /tmp/rh-hub \
  --workspace-id smoke --host-id local
PYTHONPATH=src python -m research_hub.cli publish \
  --workspace-root /tmp/rh-smoke --hub /tmp/rh-hub \
  --workspace-id smoke --host-id local
PYTHONPATH=src python -m research_hub.cli pull-context \
  --workspace-root /tmp/rh-smoke --hub /tmp/rh-hub \
  --workspace-id smoke --host-id local
test -f /tmp/rh-smoke/_research_context/START_HERE.md
test -f /tmp/rh-smoke/_research_context/document_chunks.jsonl
```

Commit message:

`Add index-first research hub skills v0.1`
