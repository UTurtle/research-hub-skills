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
