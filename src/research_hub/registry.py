"""Workspace registry for lazy distributed routing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from research_hub.jsonl import read_json, write_json

REGISTRY_PATH = Path("registry") / "workspaces.json"


@dataclass(frozen=True)
class WorkspaceRecord:
    workspace_id: str
    machine_role: str
    storage_role: str
    root_hint: str
    tailnet_hint: str
    inbox_path: str
    can_store_library_blobs: bool = False
    can_run_training: bool = False
    capabilities: list[str] = field(default_factory=list)
    transport: str = "local_path"
    ssh_host: str = ""
    ssh_user: str = ""
    remote_inbox: str = ""
    hub_ssh_host: str = ""
    hub_ssh_user: str = ""
    hub_ssh_root: str = ""


def registry_path(hub_root: Path) -> Path:
    return hub_root / REGISTRY_PATH


def default_registry() -> dict[str, list[dict[str, Any]]]:
    return {"workspaces": []}


def load_registry(hub_root: Path) -> dict[str, Any]:
    registry = read_json(registry_path(hub_root))
    if not registry:
        return default_registry()
    registry.setdefault("workspaces", [])
    return registry


def save_registry(hub_root: Path, registry: dict[str, Any]) -> None:
    write_json(registry_path(hub_root), registry)


def add_workspace(hub_root: Path, record: WorkspaceRecord) -> dict[str, Any]:
    registry = load_registry(hub_root)
    records = [
        item for item in registry["workspaces"]
        if item.get("workspace_id") != record.workspace_id
    ]
    payload = asdict(record)
    payload["capabilities"] = sorted(set(record.capabilities))
    records.append(payload)
    registry["workspaces"] = sorted(
        records,
        key=lambda item: str(item.get("workspace_id", "")),
    )
    save_registry(hub_root, registry)
    return registry


def select_archive_workspace(registry: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [
        item for item in registry.get("workspaces", [])
        if item.get("storage_role") == "archive_hdd"
        and item.get("can_store_library_blobs") is True
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: str(item.get("workspace_id", "")))[0]
