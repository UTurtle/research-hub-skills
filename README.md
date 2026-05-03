# research-hub-skills

Domain-neutral, index-first research workspace context layer for Codex and
other AI agents.

This project does not require NAS, but a NAS or archive disk is a convenient
hub location when Linux workspaces can mount it. The recommended default is:

1. keep original files in each workspace,
2. publish lightweight `_research_context` indexes locally,
3. collect only changed index snapshots into a hub path,
4. fetch source files lazily only when an agent needs them.

See `docs/INSTALL.md` for distributed operation with Windows as a panel machine
and Linux machines as hub/workspaces.

## File Split

Install/runtime files:

- `src/research_hub/`
- `skills/`
- `templates/`
- `scripts/`
- `docs/INSTALL.md`
- `docs/intake-dispatch.md`

Development-only files:

- `tests/`
- `docs/dev/`
- long planning/spec history

See `install/manifest.json` and `docs/DEVELOPMENT.md`.

## Architecture

```mermaid
flowchart TD
    WS["Research workspace<br/>original files stay in place"] --> IDX["research-hub publish"]
    IDX --> CORE["research_hub core<br/>file scan, chunks, SQLite FTS"]

    CORE --> GEN["generic profile<br/>domain-neutral default"]
    CORE --> PROF["optional domain profile<br/>pluggable enrichment"]

    GEN --> G1["documents.jsonl"]
    GEN --> G2["document_chunks.jsonl"]
    GEN --> G3["search_index.sqlite"]

    PROF --> P1["domain entities<br/>runs / papers / trials / cases"]
    PROF --> P2["domain roles<br/>contract / result / protocol / summary"]
    PROF --> P3["domain signals<br/>metrics / scores / outcomes"]
    PROF --> P4["claim and status hints"]

    P1 --> EOUT["profile-enriched index"]
    P2 --> EOUT
    P3 --> EOUT
    P4 --> EOUT

    EOUT --> R1["domain records<br/>runs.jsonl / papers.jsonl / trials.jsonl"]
    EOUT --> R2["claims.jsonl"]
    EOUT --> R3["manifest.json"]

    G1 --> CTX["_research_context/"]
    G2 --> CTX
    G3 --> CTX
    R1 --> CTX
    R2 --> CTX
    R3 --> CTX

    CTX --> AGENT["Codex / research agents<br/>startup reading surface"]
    CTX --> PANEL["panel/index.html<br/>human reading surface"]
    PANEL --> PACKS["agent_context/&lt;branch&gt;.json"]
```

The generated context and panel are projections. The original workspace files
remain the source of truth.

The `dcase2026` profile is the first concrete domain profile. Other domains can
reuse the same slot to infer their own entities, evidence records, metrics, and
claim boundaries.

See `docs/integrations.md` for how this context layer can support
`ml-intern`-style autonomous ML agents, personal wikis, vector stores, and graph
memory backends.

## Agent Install Contract

If an agent is asked to install this repo or its skill, it should install the
Codex skill first, then ask for any missing setup values before connecting the
current workspace:

- `RESEARCH_HUB`: NAS/archive path, for example `/mnt/nas/research_hub`
- `RESEARCH_WORKSPACE_ID`: short workspace name, for example `A`, `B`, or
  `dcase2026`

After those values are known, run
`.research-hub-skills/scripts/install_workspace.sh` for the current workspace.

## One-command workspace install

```bash
curl -fsSL https://raw.githubusercontent.com/UTurtle/research-hub-skills/main/install.sh | bash
```

Without `curl`, use Git directly:

```bash
git clone https://github.com/UTurtle/research-hub-skills.git .research-hub-skills
bash .research-hub-skills/scripts/install_codex_skills.sh
codex
```

The installed `research-hub-install` skill tells Codex to ask for the hub/NAS
path and workspace id before running the workspace installer.

For a prompt-free distributed setup, set `RESEARCH_HUB` to the mounted hub/NAS
path and `RESEARCH_WORKSPACE_ID` to the workspace name before installing:

```bash
export RESEARCH_HUB="/mnt/nas/research_hub"
export RESEARCH_WORKSPACE_ID="$(basename "$PWD")"
bash .research-hub-skills/scripts/install_workspace.sh
```

## Manual use

```bash
export PYTHONPATH="$PWD/.research-hub-skills/src:${PYTHONPATH:-}"
export RESEARCH_HUB="${RESEARCH_HUB:-$PWD/.research_hub_local}"
export RESEARCH_WORKSPACE_ID="${RESEARCH_WORKSPACE_ID:-$(basename "$PWD")}"
export RESEARCH_HOST_ID="${RESEARCH_HOST_ID:-local}"

python -m research_hub.cli init --workspace-root .
python -m research_hub.cli publish --workspace-root .
python -m research_hub.cli pull-context --workspace-root .
python -m research_hub.cli open --workspace-root .
```

Keep a workspace context updated while a terminal or supervisor is running:

```bash
python -m research_hub.cli watch \
  --hub /mnt/nas/research_hub \
  --workspace-root . \
  --workspace-id "$RESEARCH_WORKSPACE_ID" \
  --interval 30
```

Collect a workspace index snapshot into the hub:

```bash
python -m research_hub.cli collect-index \
  --hub /mnt/nas/research_hub \
  --workspace-id B \
  --source-context /mnt/ssd/B/_research_context
python -m research_hub.cli index-status --hub /mnt/nas/research_hub
```

If the snapshot hash did not change, collection is skipped.

Run the tiny WebUI on the hub machine:

```bash
python -m research_hub.cli web \
  --hub /mnt/nas/research_hub \
  --host 127.0.0.1 \
  --port 8787
```

From Windows:

```powershell
ssh -L 8787:127.0.0.1:8787 user@linux-a
```

## Domain profiles

Profiles enrich the generic index with domain-specific interpretation. The core
package remains domain-neutral; profiles are optional.

```mermaid
flowchart LR
    BASE["Base index record<br/>path, sha1, mtime, chunks"] --> SELECT{"Selected profile"}

    SELECT -->|"generic"| GENERIC["No domain assumptions"]
    SELECT -->|"dcase2026"| DCASE["branches, runs, metrics, claims"]
    SELECT -->|"paper-review"| PAPERS["papers, methods, datasets, baselines"]
    SELECT -->|"ml-experiment"| ML["experiments, configs, ablations, artifacts"]
    SELECT -->|"robotics-lab"| ROBOT["trials, robots, sensors, environments"]

    GENERIC --> CTX["_research_context/"]
    DCASE --> CTX
    PAPERS --> CTX
    ML --> CTX
    ROBOT --> CTX
```

### Appendix: DCASE2026 profile

The default profile stays domain-neutral. For DCASE2026-style workspaces, add
`--profile dcase2026` to enrich the index with inferred branches, runs,
document roles, metrics, claim hints, and status hints.

```bash
python -m research_hub.cli publish --workspace-root . \
  --profile dcase2026
python -m research_hub.cli pull-context --workspace-root . \
  --profile dcase2026
```

Profile outputs include:

- `runs.jsonl`
- `claims.jsonl`
- `manifest.json`
- `panel/index.html`
- `_research_context/agent_context/<branch>.json`

The generated records are navigation aids only. Source workspace files remain
authoritative, and uncertain claims should stay marked as `unknown` or
`needs_review`.

## Git State Hub Mode

Git state hub mode exists, but it is not recommended for live generated
indexes. Git is best for code, specs, and durable decisions. Use SSH, local
paths, or mounted storage for generated index snapshots and inbox/status JSON.

If you still want to use a separate private state repository for small approved
state:

```bash
git clone https://github.com/<owner>/<private-research-hub-state>.git \
  .research_hub_state
research-hub publish --hub .research_hub_state
research-hub sync-push --hub .research_hub_state
```

On another machine:

```bash
git clone https://github.com/<owner>/<private-research-hub-state>.git \
  .research_hub_state
research-hub sync-pull --hub .research_hub_state
research-hub pull-context --hub .research_hub_state
```

## Default indexed files

Included: `.md`, `.txt`, `.csv`, `.json`, `.jsonl`, `.yaml`, `.yml`,
`.log`, `.py`, `.sh`, `.toml`, `.ini`, `.cfg`.

Excluded: audio files, checkpoints, NumPy arrays, virtual environments,
`.git`, `wandb`, caches, and `node_modules`.

## License

Apache License 2.0.
