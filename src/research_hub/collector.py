"""Manifest-first workspace index collection."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from research_hub.jsonl import read_json, write_json

COLLECTED_FILES = (
    "manifest.json",
    "documents.jsonl",
    "document_chunks.jsonl",
    "claims.jsonl",
    "runs.jsonl",
    "source_links.jsonl",
)


def collect_index(
    hub_root: Path,
    workspace_id: str,
    source_context: Path,
    force: bool = False,
) -> dict[str, Any]:
    manifest_path = source_context / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing manifest: {manifest_path}")
    manifest = read_json(manifest_path)
    target_dir = hub_root / "snapshots" / workspace_id / "latest"
    previous = read_json(target_dir / "manifest.json")
    unchanged = (
        not force
        and previous.get("root_hash")
        and previous.get("root_hash") == manifest.get("root_hash")
    )
    if unchanged:
        return {
            "workspace_id": workspace_id,
            "changed": False,
            "copied_files": [],
            "target_dir": str(target_dir),
            "root_hash": manifest.get("root_hash", ""),
        }
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for filename in COLLECTED_FILES:
        source = source_context / filename
        if not source.exists():
            continue
        shutil.copy2(source, target_dir / filename)
        copied.append(filename)
    collection_record = {
        "workspace_id": workspace_id,
        "changed": True,
        "copied_files": copied,
        "target_dir": str(target_dir),
        "root_hash": manifest.get("root_hash", ""),
        "collected_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    write_json(target_dir / "collection.json", collection_record)
    write_collection_status(hub_root)
    return collection_record


def collect_index_ssh(
    hub_root: Path,
    workspace_id: str,
    ssh_host: str,
    remote_context: str,
    ssh_user: str = "",
    force: bool = False,
    execute: bool = False,
) -> dict[str, Any]:
    remote = f"{ssh_user}@{ssh_host}" if ssh_user else ssh_host
    target_dir = hub_root / "snapshots" / workspace_id / "latest"
    previous = read_json(target_dir / "manifest.json")
    commands = build_scp_commands(remote, remote_context)
    if not execute:
        return {
            "workspace_id": workspace_id,
            "changed": None,
            "copied_files": [],
            "target_dir": str(target_dir),
            "transport": "ssh",
            "dry_run": True,
            "commands": commands,
        }
    with tempfile.TemporaryDirectory() as tmp:
        temp_context = Path(tmp) / "context"
        temp_context.mkdir(parents=True, exist_ok=True)
        manifest_target = temp_context / "manifest.json"
        subprocess.run([
            "scp",
            f"{remote}:{remote_context.rstrip('/')}/manifest.json",
            str(manifest_target),
        ], check=True)
        manifest = read_json(manifest_target)
        unchanged = (
            not force
            and previous.get("root_hash")
            and previous.get("root_hash") == manifest.get("root_hash")
        )
        if unchanged:
            return {
                "workspace_id": workspace_id,
                "changed": False,
                "copied_files": [],
                "target_dir": str(target_dir),
                "root_hash": manifest.get("root_hash", ""),
                "transport": "ssh",
                "dry_run": False,
            }
        for filename in COLLECTED_FILES:
            if filename == "manifest.json":
                continue
            subprocess.run([
                "scp",
                f"{remote}:{remote_context.rstrip('/')}/{filename}",
                str(temp_context / filename),
            ], check=False)
        result = collect_index(hub_root, workspace_id, temp_context, force=True)
        result["transport"] = "ssh"
        result["dry_run"] = False
        return result


def build_scp_commands(remote: str, remote_context: str) -> list[list[str]]:
    remote_context = remote_context.rstrip("/")
    commands = [[
        "scp",
        f"{remote}:{remote_context}/manifest.json",
        "<temp-context>/manifest.json",
    ]]
    for filename in COLLECTED_FILES:
        if filename == "manifest.json":
            continue
        commands.append([
            "scp",
            f"{remote}:{remote_context}/{filename}",
            f"<temp-context>/{filename}",
        ])
    return commands


def write_collection_status(hub_root: Path) -> dict[str, Any]:
    snapshots_root = hub_root / "snapshots"
    workspaces = []
    if snapshots_root.exists():
        for workspace_dir in sorted(path for path in snapshots_root.iterdir() if path.is_dir()):
            latest = workspace_dir / "latest"
            manifest = read_json(latest / "manifest.json")
            collection = read_json(latest / "collection.json")
            if not manifest:
                continue
            workspaces.append({
                "workspace_id": workspace_dir.name,
                "created_at": manifest.get("created_at", ""),
                "documents": manifest.get("documents", 0),
                "root_hash": manifest.get("root_hash", ""),
                "collected_at": collection.get("collected_at", ""),
                "target_dir": str(latest),
            })
    status = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "workspaces": workspaces,
    }
    write_json(hub_root / "snapshots" / "STATUS.json", status)
    return status


def load_collection_status(hub_root: Path) -> dict[str, Any]:
    status = read_json(hub_root / "snapshots" / "STATUS.json")
    if status:
        return status
    return write_collection_status(hub_root)
