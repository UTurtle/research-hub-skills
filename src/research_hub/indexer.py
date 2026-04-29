"""Workspace indexing utilities."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_INCLUDE_EXTENSIONS = {
    ".md", ".txt", ".csv", ".json", ".jsonl", ".yaml", ".yml",
    ".log", ".py", ".sh",
}
DEFAULT_EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "wandb", "node_modules",
    ".mypy_cache", ".pytest_cache", "_research_context",
}
DEFAULT_EXCLUDE_EXTENSIONS = {
    ".wav", ".flac", ".mp3", ".pt", ".pth", ".ckpt", ".pkl",
    ".npy", ".npz",
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
            yield path


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
    sqlite_path = config.out_dir / "search_index.sqlite"
    with docs_path.open("w", encoding="utf-8") as docs_file, (
        chunks_path.open("w", encoding="utf-8")
    ) as chunks_file:
        for path in iter_indexable_files(config):
            rel_path = path.relative_to(config.workspace_root).as_posix()
            text = load_text(path)
            stat = path.stat()
            file_hash = sha1_file(path)
            docs_file.write(json.dumps({
                "workspace_id": config.workspace_id,
                "host_id": config.host_id,
                "source_path": rel_path,
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "sha1": file_hash,
            }, ensure_ascii=False) + "\n")
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
    build_sqlite_index(chunks_path, sqlite_path)


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
