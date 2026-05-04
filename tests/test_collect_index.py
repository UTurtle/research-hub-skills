from __future__ import annotations

import json
from pathlib import Path

from research_hub.cli import main
from research_hub.collector import (
    collect_index,
    collect_index_ssh,
    load_collection_status,
)
from research_hub.registry import WorkspaceRecord, add_workspace


def write_context(path: Path, root_hash: str = "abc123") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "manifest.json").write_text(
        json.dumps({
            "type": "workspace_index_manifest",
            "workspace_id": "B",
            "host_id": "linux-b",
            "profile": "generic",
            "created_at": "2026-05-01T00:00:00+09:00",
            "documents": 2,
            "runs": 0,
            "claims": 0,
            "root_hash": root_hash,
        }),
        encoding="utf-8",
    )
    (path / "documents.jsonl").write_text('{"source_path":"README.md"}\n', encoding="utf-8")
    (path / "document_chunks.jsonl").write_text('{"chunk_id":"README.md::0"}\n', encoding="utf-8")


def test_collect_index_copies_once_then_skips_unchanged(tmp_path: Path) -> None:
    hub = tmp_path / "hub"
    context = tmp_path / "workspace" / "_research_context"
    write_context(context)

    first = collect_index(hub, "B", context)
    second = collect_index(hub, "B", context)

    assert first["changed"] is True
    assert second["changed"] is False
    assert (hub / "snapshots" / "B" / "latest" / "documents.jsonl").exists()
    status = load_collection_status(hub)
    assert status["workspaces"][0]["workspace_id"] == "B"
    assert status["workspaces"][0]["documents"] == 2


def test_collect_index_cli_status(tmp_path: Path, capsys) -> None:
    hub = tmp_path / "hub"
    context = tmp_path / "workspace" / "_research_context"
    write_context(context, root_hash="def456")

    main([
        "collect-index",
        "--hub",
        str(hub),
        "--workspace-id",
        "B",
        "--source-context",
        str(context),
    ])
    main(["index-status", "--hub", str(hub)])

    output = capsys.readouterr().out
    assert "copied\t3 files" in output
    assert "B\t2 docs" in output
    assert "def456" in output


def test_publish_records_large_files_without_chunking_body(
    tmp_path: Path,
    monkeypatch,
) -> None:
    hub = tmp_path / "hub"
    workspace = tmp_path / "workspace"
    logs = workspace / "logs"
    references = workspace / "references"
    logs.mkdir(parents=True)
    references.mkdir()
    (workspace / "note.md").write_text("small note", encoding="utf-8")
    (references / "paper.md").write_text("paper note", encoding="utf-8")
    (logs / "train.log").write_text("x" * 100, encoding="utf-8")
    monkeypatch.setenv("RESEARCH_HUB_MAX_FILE_BYTES", "20")

    main([
        "publish",
        "--hub",
        str(hub),
        "--workspace-root",
        str(workspace),
        "--workspace-id",
        "B",
    ])

    context = hub / "contexts" / "B"
    manifest = json.loads((context / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["documents"] == 2
    assert manifest["large_files_omitted"] == 1
    chunks = (context / "document_chunks.jsonl").read_text(encoding="utf-8")
    assert "note.md" in chunks
    assert "references/paper.md" in chunks
    assert "logs/train.log" not in chunks
    large_files = [
        json.loads(line)
        for line in (context / "large_files.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert large_files[0]["source_path"] == "logs/train.log"
    assert large_files[0]["omitted_reason"] == "file_exceeds_RESEARCH_HUB_MAX_FILE_BYTES"


def test_collect_index_ssh_dry_run_plans_scp_commands(tmp_path: Path) -> None:
    result = collect_index_ssh(
        hub_root=tmp_path / "hub",
        workspace_id="B",
        ssh_host="linux-b",
        ssh_user="research",
        remote_context="/mnt/ssd/B/_research_context",
    )

    assert result["dry_run"] is True
    assert result["transport"] == "ssh"
    assert result["commands"][0] == [
        "scp",
        "research@linux-b:/mnt/ssd/B/_research_context/manifest.json",
        "<temp-context>/manifest.json",
    ]
    assert any("document_chunks.jsonl" in command[1] for command in result["commands"])


def test_collect_index_ssh_cli_dry_run(tmp_path: Path, capsys) -> None:
    main([
        "collect-index-ssh",
        "--hub",
        str(tmp_path / "hub"),
        "--workspace-id",
        "B",
        "--ssh-host",
        "linux-b",
        "--ssh-user",
        "research",
        "--remote-context",
        "/mnt/ssd/B/_research_context",
    ])

    output = capsys.readouterr().out
    assert "dry-run" in output
    assert "research@linux-b:/mnt/ssd/B/_research_context/manifest.json" in output


def test_refresh_hub_collects_registered_local_workspace(
    tmp_path: Path,
    capsys,
) -> None:
    hub = tmp_path / "hub"
    workspace = tmp_path / "workspace"
    context = workspace / "_research_context"
    write_context(context)
    add_workspace(
        hub,
        WorkspaceRecord(
            workspace_id="B",
            machine_role="4080",
            storage_role="research_ssd",
            root_hint=str(workspace),
            tailnet_hint="",
            inbox_path=str(tmp_path / "inbox"),
            can_run_training=True,
            capabilities=["torch"],
        ),
    )

    main(["refresh-hub", "--hub", str(hub)])

    output = capsys.readouterr().out
    assert "copied\tB\t3 files" in output
    assert (hub / "snapshots" / "B" / "latest" / "manifest.json").exists()


def test_refresh_hub_plans_registered_ssh_workspace(
    tmp_path: Path,
    capsys,
) -> None:
    hub = tmp_path / "hub"
    add_workspace(
        hub,
        WorkspaceRecord(
            workspace_id="C",
            machine_role="4080",
            storage_role="research_ssd",
            root_hint="/mnt/ssd/C",
            tailnet_hint="",
            inbox_path="/home/research/.research_hub/inbox",
            can_run_training=True,
            capabilities=["cuda"],
            transport="ssh",
            ssh_host="linux-c",
            ssh_user="research",
        ),
    )

    main(["refresh-hub", "--hub", str(hub)])

    output = capsys.readouterr().out
    assert "dry-run\tC" in output
