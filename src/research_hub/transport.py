"""Inbox transport adapters for local paths and SSH."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from research_hub.inbox import write_inbox_request
from research_hub.jsonl import write_json


def deliver_request(
    workspace: dict[str, Any],
    request: dict[str, Any],
    execute_remote: bool = False,
) -> dict[str, Any]:
    transport = str(workspace.get("transport") or "local_path")
    if transport == "local_path":
        inbox_path = Path(str(workspace["inbox_path"]))
        written = write_inbox_request(inbox_path, request)
        return {
            "transport": "local_path",
            "delivered": True,
            "path": str(written),
        }
    if transport == "ssh":
        return deliver_request_ssh(workspace, request, execute_remote)
    raise ValueError(f"unsupported transport: {transport}")


def deliver_request_ssh(
    workspace: dict[str, Any],
    request: dict[str, Any],
    execute_remote: bool = False,
) -> dict[str, Any]:
    remote = remote_target(workspace)
    remote_inbox = str(workspace.get("remote_inbox") or workspace.get("inbox_path"))
    mkdir_command = ["ssh", remote, "mkdir", "-p", f"{remote_inbox}/pending"]
    remote_target_path = f"{remote}:{remote_inbox}/pending/{request['request_id']}.json"
    scp_command: list[str]
    if execute_remote:
        with tempfile.TemporaryDirectory() as tmp:
            local_request = Path(tmp) / f"{request['request_id']}.json"
            write_json(local_request, request)
            scp_command = ["scp", str(local_request), remote_target_path]
            subprocess.run(mkdir_command, check=True)
            subprocess.run(scp_command, check=True)
    else:
        scp_command = ["scp", "<request-json>", remote_target_path]
    return {
        "transport": "ssh",
        "delivered": bool(execute_remote),
        "dry_run": not execute_remote,
        "commands": [mkdir_command, scp_command],
        "remote_target": remote_target_path,
    }


def remote_target(workspace: dict[str, Any]) -> str:
    host = str(workspace.get("ssh_host") or workspace.get("tailnet_hint") or "")
    if not host:
        raise ValueError("ssh transport requires ssh_host or tailnet_hint")
    user = str(workspace.get("ssh_user") or "")
    return f"{user}@{host}" if user else host


def add_hub_access_refs(
    request: dict[str, Any],
    workspace: dict[str, Any],
) -> dict[str, Any]:
    hub_host = str(workspace.get("hub_ssh_host") or "")
    hub_root = str(workspace.get("hub_ssh_root") or "")
    if not hub_host or not hub_root:
        return request
    hub_user = str(workspace.get("hub_ssh_user") or "")
    hub_target = f"{hub_user}@{hub_host}" if hub_user else hub_host
    updated_refs = []
    for ref in request.get("source_refs", []):
        updated = dict(ref)
        updated["hub_access"] = {
            "method": "ssh",
            "host": hub_target,
            "base_path": hub_root,
        }
        updated_refs.append(updated)
    request["source_refs"] = updated_refs
    return request
