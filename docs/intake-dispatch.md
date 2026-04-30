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
