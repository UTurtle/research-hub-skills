"""Workspace inbox request writer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_hub.jsonl import write_json


def write_inbox_request(inbox_path: Path, request: dict[str, Any]) -> Path:
    target = inbox_path / "pending" / f"{request['request_id']}.json"
    write_json(target, request)
    return target
