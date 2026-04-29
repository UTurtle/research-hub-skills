# research-hub-skills

Domain-neutral, index-first research workspace context layer for Codex and other AI agents.

The project does not require NAS. It can use either:

1. a local directory such as `.research_hub_local`,
2. a mounted NAS/HDD path such as `/mnt/research_hub`, or
3. a cloned Git state repository used as the shared hub between machines.

The core idea is simple: keep each research workspace unchanged, index its text-like files, generate `_research_context/`, and make agents read that context before doing work.

## Quick start

```bash
git clone https://github.com/UTurtle/research-hub-skills.git \
  .research-hub-skills

export PYTHONPATH="$PWD/.research-hub-skills/src:${PYTHONPATH:-}"

python -m research_hub.cli init --workspace-root . \
  --workspace-id my_project --host-id local

python -m research_hub.cli publish --workspace-root . \
  --workspace-id my_project --host-id local

python -m research_hub.cli pull-context --workspace-root . \
  --workspace-id my_project --host-id local
```

Then run Codex normally from the workspace root:

```bash
codex
```

## Shared Git hub mode without NAS

Create or clone a separate private state repository and use it as the hub path:

```bash
git clone https://github.com/<owner>/<private-research-hub-state>.git \
  .research_hub_state

python -m research_hub.cli publish --workspace-root . \
  --hub .research_hub_state \
  --workspace-id my_project_3090 \
  --host-id 3090

python -m research_hub.cli sync-push --hub .research_hub_state
```

On another machine:

```bash
git clone https://github.com/<owner>/<private-research-hub-state>.git \
  .research_hub_state

python -m research_hub.cli sync-pull --hub .research_hub_state
python -m research_hub.cli pull-context --workspace-root . \
  --hub .research_hub_state \
  --workspace-id my_project_4080 \
  --host-id 4080
```

This keeps the tool repository separate from private research state.

## What gets indexed

Included by default: `.md`, `.txt`, `.csv`, `.json`, `.jsonl`, `.yaml`, `.yml`, `.log`, `.py`, `.sh`.

Excluded by default: audio files, checkpoints, NumPy arrays, virtual environments, `.git`, `wandb`, caches, and `node_modules`.

## License

Apache License 2.0.
