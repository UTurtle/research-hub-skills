from __future__ import annotations

from pathlib import Path

from research_hub.intake import create_intake_item, load_intake_items
from research_hub.registry import WorkspaceRecord, add_workspace, load_registry
from research_hub.web import handle_post, render_home


def test_render_home_shows_core_forms(tmp_path: Path) -> None:
    hub = tmp_path / "hub"
    add_workspace(
        hub,
        WorkspaceRecord("B", "4080", "research_ssd", "/B", "", str(tmp_path / "inbox"), False, True, ["torch"]),
    )
    source = tmp_path / "note.md"
    source.write_text("main26 torch note", encoding="utf-8")
    create_intake_item(hub, source, "Torch note", "related_work_note")

    html = render_home(hub)

    assert "Research Hub" in html
    assert "/registry-add" in html
    assert "/intake-add" in html
    assert "/dispatch-propose" in html
    assert "Torch note" in html


def test_handle_post_adds_workspace_and_intake(tmp_path: Path) -> None:
    hub = tmp_path / "hub"
    source = tmp_path / "note.md"
    source.write_text("torch note", encoding="utf-8")

    message = handle_post(
        hub,
        "/registry-add",
        {
            "workspace_id": "B",
            "machine_role": "4080",
            "storage_role": "research_ssd",
            "root_hint": "/B",
            "inbox_path": str(tmp_path / "inbox" / "B"),
            "can_run_training": "on",
            "capabilities": "torch cuda",
            "transport": "ssh",
            "ssh_host": "linux-b",
            "ssh_user": "research",
            "remote_inbox": "/home/research/.research_hub/inbox",
        },
    )
    assert message == "workspace-added"
    workspace = load_registry(hub)["workspaces"][0]
    assert workspace["workspace_id"] == "B"
    assert workspace["transport"] == "ssh"
    assert workspace["ssh_host"] == "linux-b"

    message = handle_post(
        hub,
        "/intake-add",
        {
            "source_path": str(source),
            "title": "Torch note",
            "kind": "related_work_note",
        },
    )
    assert message.startswith("intake-added-")
    assert load_intake_items(hub)[0]["title"] == "Torch note"
