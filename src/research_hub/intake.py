"""Central intake ledger and blob store."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from research_hub.jsonl import append_jsonl, read_jsonl

ITEMS_PATH = Path("intake") / "items.jsonl"


def load_intake_items(hub_root: Path) -> list[dict[str, Any]]:
    return read_jsonl(hub_root / ITEMS_PATH)


def sha1_path(path: Path) -> str:
    digest = hashlib.sha1()
    if path.is_file():
        with path.open("rb") as file_obj:
            for block in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        with child.open("rb") as file_obj:
            for block in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def make_item_id(title: str, source_hash: str) -> str:
    stamp = datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
    return f"intake-{stamp}-{source_hash[:8]}"


def create_intake_item(
    hub_root: Path,
    source_path: Path,
    title: str,
    kind: str,
    source_label: str = "user_upload",
) -> dict[str, Any]:
    source_path = source_path.resolve()
    source_hash = sha1_path(source_path)
    item_id = make_item_id(title, source_hash)
    blob_root = (hub_root / "intake" / "blobs" / item_id).resolve()
    blob_root.mkdir(parents=True, exist_ok=True)
    copied_path = copy_into_blob(source_path, blob_root)
    extracted_path = extract_zip_if_needed(copied_path, blob_root)
    item = {
        "item_id": item_id,
        "kind": kind,
        "title": title,
        "blob_root": str(blob_root),
        "copied_path": str(copied_path),
        "extracted_path": str(extracted_path) if extracted_path else "",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sha1": source_hash,
        "source_label": source_label,
        "source_name": source_path.name,
        "status": "indexed",
    }
    append_jsonl(hub_root / ITEMS_PATH, item)
    return item


def copy_into_blob(source_path: Path, blob_root: Path) -> Path:
    destination = blob_root / source_path.name
    if source_path.is_dir():
        shutil.copytree(source_path, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(source_path, destination)
    return destination


def extract_zip_if_needed(copied_path: Path, blob_root: Path) -> Path | None:
    if copied_path.suffix.lower() != ".zip":
        return None
    extract_root = blob_root / "extracted"
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(copied_path) as zip_file:
        zip_file.extractall(extract_root)
    return extract_root
