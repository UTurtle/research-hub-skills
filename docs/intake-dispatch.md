# Intake Dispatch Protocol

Research Hub is an agent-driven lazy workspace skill. The hub records uploads,
proposes routes, waits for human approval, and writes inbox requests. It does
not directly edit A/B/C workspace source paths.

## Minimal Commands

```powershell
$hub = "C:\research_hub"
research-hub registry-init --hub $hub
research-hub registry-add --hub $hub --workspace-id A --machine-role 3090 --storage-role archive_hdd --root-hint C:\workspace\A --inbox-path C:\research_hub\inbox\A --can-store-library-blobs --can-run-training --capability cuda --capability dcase2026
research-hub intake-add --hub $hub --source-path C:\research_materials\related_work.md --title "Related work" --kind related_work_note
research-hub dispatch-propose --hub $hub --item-id intake-20260501010101-related-work-12345678
research-hub dispatch-approve --hub $hub --proposal-id proposal-20260501010102-12345678 --workspace-id A
research-hub hub-panel --hub $hub
```

## Tiny WebUI

For SSH tunnel or tailnet use, run the tiny server-rendered WebUI on the hub
machine:

```powershell
research-hub web --hub C:\research_hub --host 127.0.0.1 --port 8787
```

Then connect from another machine through SSH:

```powershell
ssh -L 8787:127.0.0.1:8787 user@hub-machine
```

Open:

```text
http://127.0.0.1:8787
```

The WebUI is intentionally small. It can:

- show registered workspaces,
- add a workspace,
- add intake from a hub-visible file, folder, or ZIP path,
- generate proposals,
- approve one proposal target,
- show proposal and inbox-driving state.

It does not require FastAPI, React, a database server, or a browser-exposed
daemon. By default it binds to `127.0.0.1` for tunnel-first usage. If exposed on
a tailnet address, use `--token <value>` and pass the same value as `?token=...`
or `X-Research-Hub-Token`.

## Recommended Windows And Linux Layout

The preferred research layout is:

- Windows machine: browser and approval panel only.
- Linux A: hub, WebUI process, 3090/14TB archive, intake blob store.
- Linux B/C: active GPU research workspaces, local inboxes, local agents.

Windows connects to Linux A through an SSH tunnel. Linux A dispatches small
request JSON files to Linux B/C through SSH.

```text
Windows browser
  -> ssh -L 8787:127.0.0.1:8787 linux-a
Linux A hub/archive/WebUI
  -> ssh/scp request JSON
Linux B/C inbox/local agent/GPU workspace
```

## SSH Workspace Transport

`registry-add` supports `local_path` and `ssh` transports.

Local path is the simplest mode:

```powershell
research-hub registry-add --hub C:\research_hub --workspace-id B --machine-role 4080 --storage-role research_ssd --root-hint /mnt/ssd/B --inbox-path C:\research_hub\inbox\B --can-run-training --capability torch
```

SSH mode records Linux destination information:

```powershell
research-hub registry-add --hub C:\research_hub --workspace-id B --machine-role 4080 --storage-role research_ssd --root-hint /mnt/ssd/B --inbox-path /home/research/.research_hub/inbox --transport ssh --ssh-host linux-b --ssh-user research --remote-inbox /home/research/.research_hub/inbox --hub-ssh-host linux-a --hub-ssh-user research --hub-ssh-root /data/research_hub --can-run-training --capability cuda --capability torch
```

By default, SSH dispatch is a dry run in the audit record. It records the
`ssh mkdir` and `scp` commands that would deliver the request, without executing
remote commands. To actually push a request to a remote Linux inbox, approve with:

```powershell
research-hub dispatch-approve --hub C:\research_hub --proposal-id proposal-20260501010102-12345678 --workspace-id B --execute-transport
```

This keeps the first workflow safe: configure and inspect the generated command
plan first, then enable execution once SSH keys and remote inbox paths are known.

## Lightweight Index Collection

Do not use Git as the live memory/index bus. Git is appropriate for code,
approved plans, specs, and durable decisions, but generated live indexes can
grow quickly and slow research work down.

The lightweight path is manifest-first collection:

```powershell
research-hub publish --workspace-root /mnt/ssd/B --hub /tmp/local_hub --workspace-id B
research-hub collect-index --hub C:\research_hub --workspace-id B --source-context /mnt/ssd/B/_research_context
research-hub index-status --hub C:\research_hub
```

For SSH-only workspaces, collect the remote `_research_context` directly:

```powershell
research-hub collect-index-ssh --hub C:\research_hub --workspace-id B --ssh-host linux-b --ssh-user research --remote-context /mnt/ssd/B/_research_context
```

The first run is a dry run that prints the `scp` plan. Add
`--execute-transport` after verifying the path.

`collect-index` reads only `manifest.json` first. If the `root_hash` matches the
latest collected snapshot, it skips copying. If the hash changed, it copies the
small generated context files into:

```text
<hub>/snapshots/<workspace_id>/latest/
```

The WebUI shows an Index Freshness table from:

```text
<hub>/snapshots/STATUS.json
```

Recommended transport policy:

- request/status JSON: SSH/SCP,
- workspace index snapshots: manifest-first collect, later rsync-over-SSH,
- source files: stay in the original workspace and are fetched lazily,
- Git: decisions/specs/code only, not generated live indexes.

## Safety Rules

- Intake copies user material into the hub and never writes to original
  workspace roots.
- Zip uploads are extracted only inside the hub blob store.
- Proposals are suggestions and do not dispatch work.
- Approval creates hub outbox records and workspace inbox records.
- Local agents decide concrete edits only after reading an inbox request.
- Large blobs stay on archive storage unless explicitly approved otherwise.

## Agent Inbox Contract

Workspace agents should watch or inspect:

```text
<workspace-inbox>/pending/<request-id>.json
```

Each request includes:

- `request_id`
- `proposal_id`
- `item_id`
- `workspace_id`
- `action`
- `source_refs`
- `instructions`
- `status`

The local agent may then create its own implementation plan inside the target
workspace. The generated inbox record is a request, not permission to edit
arbitrary files without local review.
