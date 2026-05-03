from __future__ import annotations

import json
import zipfile
from pathlib import Path

from research_hub.cli import main
from research_hub.dispatch import (
    approve_proposal,
    create_dispatch_proposal,
    load_proposals,
)
from research_hub.intake import create_intake_item, load_intake_items
from research_hub.jsonl import append_jsonl, read_jsonl, write_json
from research_hub.panel import build_hub_panel
from research_hub.registry import (
    WorkspaceRecord,
    add_workspace,
    default_registry,
    load_registry,
    select_archive_workspace,
)


def test_jsonl_helpers_create_parent_and_preserve_order(tmp_path: Path) -> None:
    path = tmp_path / "state" / "items.jsonl"

    append_jsonl(path, {"id": "a", "value": 1})
    append_jsonl(path, {"id": "b", "value": 2})

    assert read_jsonl(path) == [
        {"id": "a", "value": 1},
        {"id": "b", "value": 2},
    ]


def test_write_json_creates_parent_and_sorts_keys(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "record.json"

    write_json(path, {"z": 1, "a": 2})

    text = path.read_text(encoding="utf-8")
    assert text.startswith("{\n  \"a\": 2,")


def test_workspace_registry_selects_archive(tmp_path: Path) -> None:
    hub = tmp_path / "hub"
    assert default_registry() == {"workspaces": []}

    add_workspace(
        hub,
        WorkspaceRecord(
            workspace_id="B",
            machine_role="4080",
            storage_role="research_ssd",
            root_hint="/workspace/B",
            tailnet_hint="b-machine.tailnet",
            inbox_path=str(tmp_path / "inbox" / "B"),
            can_store_library_blobs=False,
            can_run_training=True,
            capabilities=["cuda", "torch"],
        ),
    )
    add_workspace(
        hub,
        WorkspaceRecord(
            workspace_id="A",
            machine_role="3090",
            storage_role="archive_hdd",
            root_hint="/workspace/A",
            tailnet_hint="a-machine.tailnet",
            inbox_path=str(tmp_path / "inbox" / "A"),
            can_store_library_blobs=True,
            can_run_training=True,
            capabilities=["cuda", "dcase2026"],
        ),
    )

    registry = load_registry(hub)
    assert len(registry["workspaces"]) == 2
    assert select_archive_workspace(registry)["workspace_id"] == "A"


def test_intake_copies_and_extracts_zip_without_touching_source(tmp_path: Path) -> None:
    hub = tmp_path / "hub"
    source_zip = tmp_path / "bundle.zip"
    with zipfile.ZipFile(source_zip, "w") as zip_file:
        zip_file.writestr("repo/README.md", "main26 torch branch")

    before = source_zip.read_bytes()
    item = create_intake_item(
        hub_root=hub,
        source_path=source_zip,
        title="Torch ZIP",
        kind="zip_bundle",
    )

    assert source_zip.read_bytes() == before
    assert len(item["item_id"]) <= 30
    assert Path(item["copied_path"]).exists()
    assert Path(item["extracted_path"], "repo", "README.md").exists()
    assert load_intake_items(hub)[0]["item_id"] == item["item_id"]


def test_dispatch_approval_creates_outbox_and_inbox(tmp_path: Path) -> None:
    hub = tmp_path / "hub"
    source = tmp_path / "bundle"
    source.mkdir()
    (source / "README.md").write_text(
        "main26 dual-path torch experiment",
        encoding="utf-8",
    )
    inbox_b = tmp_path / "workspace_inbox" / "B"

    add_workspace(
        hub,
        WorkspaceRecord(
            "A",
            "3090",
            "archive_hdd",
            "/A",
            "a.tailnet",
            str(tmp_path / "workspace_inbox" / "A"),
            True,
            True,
            ["cuda", "dcase2026"],
        ),
    )
    add_workspace(
        hub,
        WorkspaceRecord(
            "B",
            "4080",
            "research_ssd",
            "/B",
            "b.tailnet",
            str(inbox_b),
            False,
            True,
            ["cuda", "torch", "main26"],
        ),
    )
    item = create_intake_item(hub, source, "Torch branch bundle", "folder_bundle")

    proposal = create_dispatch_proposal(hub, item["item_id"])
    assert proposal["recommended_targets"][0]["workspace_id"] == "A"
    assert any(
        target["workspace_id"] == "B"
        for target in proposal["recommended_targets"]
    )
    assert load_proposals(hub)[0]["proposal_id"] == proposal["proposal_id"]

    requests = approve_proposal(hub, proposal["proposal_id"], ["B"])

    assert requests[0]["workspace_id"] == "B"
    assert requests[0]["source_refs"][0]["blob_root"]
    assert list((hub / "outbox" / "B").glob("*.json"))
    inbox_files = list((inbox_b / "pending").glob("*.json"))
    assert len(inbox_files) == 1
    assert "torch" in inbox_files[0].read_text(encoding="utf-8").lower()


def test_ssh_transport_approval_records_dry_run_commands(tmp_path: Path) -> None:
    hub = tmp_path / "hub"
    source = tmp_path / "note.md"
    source.write_text("main26 torch review", encoding="utf-8")
    add_workspace(
        hub,
        WorkspaceRecord(
            workspace_id="B",
            machine_role="4080",
            storage_role="research_ssd",
            root_hint="/mnt/ssd/B",
            tailnet_hint="",
            inbox_path="/home/research/.research_hub/inbox",
            can_store_library_blobs=False,
            can_run_training=True,
            capabilities=["torch", "main26"],
            transport="ssh",
            ssh_host="linux-b",
            ssh_user="research",
            remote_inbox="/home/research/.research_hub/inbox",
            hub_ssh_host="linux-a",
            hub_ssh_user="research",
            hub_ssh_root="/data/research_hub",
        ),
    )
    item = create_intake_item(hub, source, "Torch note", "related_work_note")
    proposal = create_dispatch_proposal(hub, item["item_id"])

    requests = approve_proposal(hub, proposal["proposal_id"], ["B"])

    delivery = requests[0]["delivery"]
    assert delivery["transport"] == "ssh"
    assert delivery["dry_run"] is True
    assert delivery["commands"][0][:3] == ["ssh", "research@linux-b", "mkdir"]
    assert requests[0]["source_refs"][0]["hub_access"]["host"] == "research@linux-a"


def test_hub_panel_includes_intake_and_proposals(tmp_path: Path) -> None:
    hub = tmp_path / "hub"
    source = tmp_path / "note.md"
    source.write_text("main26 torch note", encoding="utf-8")
    add_workspace(
        hub,
        WorkspaceRecord("B", "4080", "research_ssd", "/B", "", str(tmp_path / "inbox"), False, True, ["torch"]),
    )
    item = create_intake_item(hub, source, "Torch note", "related_work_note")
    create_dispatch_proposal(hub, item["item_id"])

    build_hub_panel(hub, hub / "panel")

    html = (hub / "panel" / "index.html").read_text(encoding="utf-8")
    assert "Torch note" in html
    assert "Dispatch Proposals" in html


def test_cli_minimal_loop(tmp_path: Path) -> None:
    hub = tmp_path / "hub"
    inbox = tmp_path / "inbox" / "B"
    source = tmp_path / "note.md"
    source.write_text("torch integration note", encoding="utf-8")

    main(["registry-init", "--hub", str(hub)])
    main([
        "registry-add",
        "--hub",
        str(hub),
        "--workspace-id",
        "B",
        "--machine-role",
        "4080",
        "--storage-role",
        "research_ssd",
        "--root-hint",
        "/B",
        "--inbox-path",
        str(inbox),
        "--can-run-training",
        "--capability",
        "torch",
    ])
    main([
        "intake-add",
        "--hub",
        str(hub),
        "--source-path",
        str(source),
        "--title",
        "Torch note",
        "--kind",
        "related_work_note",
    ])
    item_id = load_intake_items(hub)[0]["item_id"]
    main(["dispatch-propose", "--hub", str(hub), "--item-id", item_id])
    proposal_id = load_proposals(hub)[0]["proposal_id"]
    main([
        "dispatch-approve",
        "--hub",
        str(hub),
        "--proposal-id",
        proposal_id,
        "--workspace-id",
        "B",
    ])
    main(["hub-panel", "--hub", str(hub)])

    assert json.loads(next((inbox / "pending").glob("*.json")).read_text())[
        "workspace_id"
    ] == "B"
    assert (hub / "panel" / "index.html").exists()


def test_init_writes_research_hub_workspace_marker(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    hub = tmp_path / "hub"

    main([
        "init",
        "--workspace-root",
        str(workspace),
        "--hub",
        str(hub),
        "--workspace-id",
        "B",
    ])

    marker = workspace / "RESEARCH_HUB.md"
    assert marker.exists()
    marker_text = marker.read_text(encoding="utf-8")
    assert "Research Hub Workspace" in marker_text
    assert str(hub.resolve()) in marker_text
    assert "Detected workspace id: `B`" in marker_text
    assert (workspace / "AGENTS.md").exists()
    assert (workspace / "_research_context" / "START_HERE.md").exists()
