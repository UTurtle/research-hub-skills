# Install And Distributed Operation

Research Hub has two parts:

- install/runtime files: the CLI, skills, templates, and short operator docs,
- development files: tests, long planning history, design notes, and review
  artifacts.

See `install/manifest.json` for the exact split.

## Recommended Layout

Use Windows as a panel machine and Linux for the actual research work.

```text
Windows
  browser
  ssh tunnel to Linux A

Linux A
  research-hub web
  central hub path, often on NAS or 14TB archive disk
  intake blobs, snapshots, dispatch outbox

Linux B/C
  active research workspaces
  local _research_context
  local agent inbox
```

## Minimal Install

On each Linux research workspace:

```bash
git clone https://github.com/UTurtle/research-hub-skills.git .research-hub-skills
export PYTHONPATH="$PWD/.research-hub-skills/src:${PYTHONPATH:-}"
export RESEARCH_HUB="/mnt/nas/research_hub"
export RESEARCH_WORKSPACE_ID="$(basename "$PWD")"
python -m research_hub.cli init --workspace-root .
python -m research_hub.cli publish --workspace-root .
```

On Linux A, run the WebUI:

```bash
export PYTHONPATH="/path/to/research-hub-skills/src:${PYTHONPATH:-}"
python -m research_hub.cli web --hub /mnt/nas/research_hub --host 127.0.0.1 --port 8787
```

From Windows:

```powershell
ssh -L 8787:127.0.0.1:8787 user@linux-a
```

Open:

```text
http://127.0.0.1:8787
```

## Is NAS Enough?

NAS is enough only if every participating machine can read and write the chosen
hub path reliably.

If all machines mount the same NAS path:

```text
RESEARCH_HUB=/mnt/nas/research_hub
transport=local_path
```

Then the basic flow is straightforward:

```text
workspace publish
hub collect-index
user intake/proposal/approval
workspace inbox receives request JSON
```

If B/C cannot directly write the NAS path, use SSH transport:

```text
Windows -> ssh tunnel -> Linux A WebUI
Linux A -> ssh/scp request JSON -> Linux B/C inbox
Linux B/C -> publish local index
Linux A -> collect index snapshot over SSH
```

## What Is Automatic Today?

Automatic after configuration:

- workspace indexing with `publish`,
- hub snapshot collection with `collect-index`,
- SSH snapshot collection command planning with `collect-index-ssh`,
- intake storage,
- proposal generation,
- approval to local_path inbox,
- SSH dry-run delivery plan,
- SSH delivery when `--execute-transport` is used,
- WebUI display of index freshness and proposal state.

Not automatic yet:

- continuous daemon/watch mode,
- SSH pull of remote index snapshots,
- local agent status return flow,
- remote SSH end-to-end validation on real Linux hosts,
- smarter semantic proposal ranking.

## Lightweight Sync Rule

Do not use Git as the live memory bus. Git is for code, specs, and durable
decisions. Generated live state should stay outside Git:

```text
.research_hub_local/
_research_context/
snapshots/
intake/blobs/
*.sqlite
```

Research Hub uses manifest-first collection. If `manifest.root_hash` did not
change, `collect-index` skips copying:

```bash
python -m research_hub.cli collect-index \
  --hub /mnt/nas/research_hub \
  --workspace-id B \
  --source-context /mnt/ssd/B/_research_context
```

If the workspace is only reachable over SSH, first publish on the remote Linux
workspace:

```bash
ssh research@linux-b 'cd /mnt/ssd/B && PYTHONPATH=$PWD/.research-hub-skills/src python -m research_hub.cli publish --workspace-root . --hub .research_hub_local --workspace-id B'
```

Then collect the generated index from Linux A:

```bash
python -m research_hub.cli collect-index-ssh \
  --hub /mnt/nas/research_hub \
  --workspace-id B \
  --ssh-host linux-b \
  --ssh-user research \
  --remote-context /mnt/ssd/B/_research_context
```

By default this is a dry run and prints the `scp` commands. Execute the transfer
only after checking the paths:

```bash
python -m research_hub.cli collect-index-ssh \
  --hub /mnt/nas/research_hub \
  --workspace-id B \
  --ssh-host linux-b \
  --ssh-user research \
  --remote-context /mnt/ssd/B/_research_context \
  --execute-transport
```

Output examples:

```text
copied  4 files  /mnt/nas/research_hub/snapshots/B/latest
skipped 0 files  /mnt/nas/research_hub/snapshots/B/latest
```
