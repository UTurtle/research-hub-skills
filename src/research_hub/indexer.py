"""Workspace indexing utilities."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

DEFAULT_INCLUDE_EXTENSIONS = {
    ".md", ".txt", ".csv", ".json", ".jsonl", ".yaml", ".yml",
    ".log", ".py", ".sh", ".toml", ".ini", ".cfg",
}
DEFAULT_EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "wandb", "node_modules",
    ".mypy_cache", ".pytest_cache", "_research_context",
    "artifacts", "outputs", "data", "datasets", "logs", "checkpoints", "ckpts",
}
DEFAULT_EXCLUDE_EXTENSIONS = {
    ".wav", ".flac", ".mp3", ".pt", ".pth", ".ckpt", ".pkl",
    ".npy", ".npz",
}
LARGE_FILE_METADATA_PRUNE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".mypy_cache", ".pytest_cache", "_research_context",
}


@dataclass(frozen=True)
class IndexConfig:
    workspace_root: Path
    workspace_id: str
    host_id: str
    out_dir: Path
    include_extensions: set[str]
    exclude_dirs: set[str]
    exclude_extensions: set[str]
    max_file_bytes: int | None = None
    profile: str = "generic"


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file_obj:
        for block in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_indexable_files(config: IndexConfig) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(config.workspace_root):
        dirnames[:] = [
            name for name in dirnames if name not in config.exclude_dirs
        ]
        current = Path(dirpath)
        for filename in filenames:
            path = current / filename
            suffix = path.suffix.lower()
            if suffix in config.exclude_extensions:
                continue
            if suffix not in config.include_extensions:
                continue
            if config.max_file_bytes is not None:
                try:
                    if path.stat().st_size > config.max_file_bytes:
                        continue
                except OSError:
                    continue
            yield path


def iter_large_file_records(config: IndexConfig) -> Iterable[dict[str, Any]]:
    if config.max_file_bytes is None:
        return
    for dirpath, dirnames, filenames in os.walk(config.workspace_root):
        dirnames[:] = [
            name for name in dirnames if name not in LARGE_FILE_METADATA_PRUNE_DIRS
        ]
        current = Path(dirpath)
        for filename in filenames:
            path = current / filename
            suffix = path.suffix.lower()
            if suffix in config.exclude_extensions:
                continue
            if suffix not in config.include_extensions:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size <= config.max_file_bytes:
                continue
            yield {
                "workspace_id": config.workspace_id,
                "host_id": config.host_id,
                "source_path": path.relative_to(config.workspace_root).as_posix(),
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "suffix": suffix,
                "omitted_reason": "file_exceeds_RESEARCH_HUB_MAX_FILE_BYTES",
                "max_file_bytes": config.max_file_bytes,
            }


def split_chunks(text: str, max_chars: int = 3000) -> list[str]:
    lines = text.splitlines()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        add_len = len(line) + 1
        if current and current_len + add_len > max_chars:
            chunks.append("\n".join(current).strip())
            current = []
            current_len = 0
        current.append(line)
        current_len += add_len
    if current:
        chunks.append("\n".join(current).strip())
    return [chunk for chunk in chunks if chunk]


def build_index(config: IndexConfig) -> None:
    config.out_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = config.out_dir / "document_chunks.jsonl"
    docs_path = config.out_dir / "documents.jsonl"
    large_files_path = config.out_dir / "large_files.jsonl"
    sqlite_path = config.out_dir / "search_index.sqlite"
    profile = load_profile(config.profile)
    document_records: list[dict[str, Any]] = []
    large_file_records = list(iter_large_file_records(config))
    with docs_path.open("w", encoding="utf-8") as docs_file, (
        chunks_path.open("w", encoding="utf-8")
    ) as chunks_file:
        for path in iter_indexable_files(config):
            rel_path = path.relative_to(config.workspace_root).as_posix()
            text = load_text(path)
            stat = path.stat()
            file_hash = sha1_file(path)
            record: dict[str, Any] = {
                "workspace_id": config.workspace_id,
                "host_id": config.host_id,
                "source_path": rel_path,
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "sha1": file_hash,
            }
            if profile:
                record.update(
                    profile.enrich_document(
                        path, config.workspace_root, rel_path, text, stat
                    )
                )
            document_records.append(record)
            docs_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            for idx, chunk in enumerate(split_chunks(text)):
                chunks_file.write(json.dumps({
                    "workspace_id": config.workspace_id,
                    "host_id": config.host_id,
                    "source_path": rel_path,
                    "chunk_id": f"{rel_path}::{idx}",
                    "chunk_index": idx,
                    "text": chunk,
                    "sha1": file_hash,
                }, ensure_ascii=False) + "\n")
    write_jsonl(large_files_path, large_file_records)
    build_sqlite_index(chunks_path, sqlite_path)
    runs: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    if profile:
        runs, claims = write_profile_outputs(config, profile, document_records)
    write_manifest(config, document_records, runs, claims, large_file_records)


def build_sqlite_index(chunks_path: Path, sqlite_path: Path) -> None:
    if sqlite_path.exists():
        sqlite_path.unlink()
    conn = sqlite3.connect(sqlite_path)
    try:
        conn.execute(
            "CREATE VIRTUAL TABLE chunks USING fts5("
            "chunk_id, source_path, text)"
        )
        with chunks_path.open("r", encoding="utf-8") as file_obj:
            for line in file_obj:
                record = json.loads(line)
                conn.execute(
                    "INSERT INTO chunks(chunk_id, source_path, text) "
                    "VALUES (?, ?, ?)",
                    (record["chunk_id"], record["source_path"], record["text"]),
                )
        conn.commit()
    finally:
        conn.close()


def load_profile(profile: str) -> Any | None:
    if profile == "generic":
        return None
    return importlib.import_module(f"research_hub.profiles.{profile}")


def write_profile_outputs(
    config: IndexConfig,
    profile: Any,
    document_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs = profile.build_runs(document_records)
    claims = profile.build_claims(document_records)
    write_jsonl(config.out_dir / "runs.jsonl", runs)
    write_jsonl(config.out_dir / "claims.jsonl", claims)
    return runs, claims


def write_manifest(
    config: IndexConfig,
    document_records: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    large_file_records: list[dict[str, Any]],
) -> None:
    root_hash = hashlib.sha1()
    for record in sorted(document_records, key=lambda item: item["source_path"]):
        root_hash.update(str(record["source_path"]).encode("utf-8"))
        root_hash.update(str(record["sha1"]).encode("utf-8"))
    for record in sorted(large_file_records, key=lambda item: item["source_path"]):
        root_hash.update(str(record["source_path"]).encode("utf-8"))
        root_hash.update(str(record["size"]).encode("utf-8"))
        root_hash.update(str(record["mtime"]).encode("utf-8"))
    manifest = {
        "type": "workspace_index_manifest",
        "workspace_id": config.workspace_id,
        "host_id": config.host_id,
        "profile": config.profile,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "documents": len(document_records),
        "large_files_omitted": len(large_file_records),
        "runs": len(runs),
        "claims": len(claims),
        "root_hash": root_hash.hexdigest(),
    }
    (config.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file_obj:
        for record in records:
            file_obj.write(json.dumps(record, ensure_ascii=False) + "\n")
