"""Dispatch proposals, approvals, and outbox requests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from research_hub.inbox import write_inbox_request
from research_hub.intake import load_intake_items
from research_hub.jsonl import append_jsonl, read_jsonl, write_json
from research_hub.registry import load_registry

PROPOSALS_PATH = Path("dispatch") / "proposals.jsonl"
APPROVED_PATH = Path("dispatch") / "approved.jsonl"
TEXT_EXTENSIONS = {".md", ".txt", ".py", ".json", ".toml", ".yaml", ".yml"}


def load_proposals(hub_root: Path) -> list[dict[str, Any]]:
    return read_jsonl(hub_root / PROPOSALS_PATH)


def find_intake_item(hub_root: Path, item_id: str) -> dict[str, Any]:
    for item in load_intake_items(hub_root):
        if item.get("item_id") == item_id:
            return item
    raise ValueError(f"unknown intake item: {item_id}")


def find_proposal(hub_root: Path, proposal_id: str) -> dict[str, Any]:
    for proposal in load_proposals(hub_root):
        if proposal.get("proposal_id") == proposal_id:
            return proposal
    raise ValueError(f"unknown proposal: {proposal_id}")


def read_blob_text(item: dict[str, Any], max_chars: int = 24000) -> str:
    roots = [Path(item["blob_root"])]
    if item.get("extracted_path"):
        roots.insert(0, Path(str(item["extracted_path"])))
    parts: list[str] = []
    total = 0
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            parts.append(text)
            total += len(text)
            if total >= max_chars:
                return "\n".join(parts)[:max_chars].lower()
    return "\n".join(parts)[:max_chars].lower()


def score_workspace(
    workspace: dict[str, Any],
    item: dict[str, Any],
    text: str,
) -> tuple[float, list[str]]:
    score = 0.05
    reasons = ["registered workspace"]
    capabilities = {str(value).lower() for value in workspace.get("capabilities", [])}
    is_archive = (
        workspace.get("storage_role") == "archive_hdd"
        and workspace.get("can_store_library_blobs") is True
    )
    if is_archive:
        score += 0.45
        reasons.append("archive_hdd can store central blobs")
        if item.get("kind") in {"folder_bundle", "zip_bundle"}:
            score += 0.2
            reasons.append("bundle uploads should be archived centrally")
    if "torch" in text and "torch" in capabilities:
        score += 0.35
        reasons.append("intake mentions torch and workspace advertises torch")
    if "cuda" in capabilities and workspace.get("can_run_training"):
        score += 0.1
        reasons.append("workspace can run GPU training")
    for token in ("main25", "main26", "main27", "main28", "dcase2026"):
        if token in text and token in capabilities:
            score += 0.1
            reasons.append(f"capability overlaps intake token {token}")
    return min(score, 1.0), reasons


def create_dispatch_proposal(hub_root: Path, item_id: str) -> dict[str, Any]:
    item = find_intake_item(hub_root, item_id)
    registry = load_registry(hub_root)
    text = read_blob_text(item)
    targets = []
    for workspace in registry.get("workspaces", []):
        score, reasons = score_workspace(workspace, item, text)
        action = (
            "archive_and_index"
            if workspace.get("can_store_library_blobs")
            else "review_and_integrate"
        )
        targets.append({
            "workspace_id": workspace["workspace_id"],
            "action": action,
            "confidence": round(score, 2),
            "reason": "; ".join(reasons),
        })
    targets.sort(key=lambda row: (-row["confidence"], row["workspace_id"]))
    proposal_id = (
        "proposal-"
        f"{datetime.now().astimezone().strftime('%Y%m%d%H%M%S')}-"
        f"{item_id[-8:]}"
    )
    proposal = {
        "proposal_id": proposal_id,
        "item_id": item_id,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "recommended_targets": targets,
        "requires_approval": True,
        "status": "pending",
    }
    append_jsonl(hub_root / PROPOSALS_PATH, proposal)
    write_json(hub_root / "dispatch" / "pending" / f"{proposal_id}.json", proposal)
    return proposal


def approve_proposal(
    hub_root: Path,
    proposal_id: str,
    workspace_ids: list[str],
) -> list[dict[str, Any]]:
    proposal = find_proposal(hub_root, proposal_id)
    item = find_intake_item(hub_root, str(proposal["item_id"]))
    registry = load_registry(hub_root)
    workspaces = {
        item["workspace_id"]: item
        for item in registry.get("workspaces", [])
    }
    requests: list[dict[str, Any]] = []
    for target in proposal.get("recommended_targets", []):
        workspace_id = str(target.get("workspace_id"))
        if workspace_id not in workspace_ids:
            continue
        if workspace_id not in workspaces:
            raise ValueError(f"unknown workspace in proposal: {workspace_id}")
        workspace = workspaces[workspace_id]
        request_id = f"request-{proposal_id}-{workspace_id}"
        request = {
            "request_id": request_id,
            "proposal_id": proposal_id,
            "item_id": proposal["item_id"],
            "workspace_id": workspace_id,
            "action": target["action"],
            "source_refs": [{
                "item_id": proposal["item_id"],
                "blob_root": item.get("blob_root", ""),
                "extracted_path": item.get("extracted_path", ""),
            }],
            "instructions": target["reason"],
            "status": "pending",
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        write_json(hub_root / "outbox" / workspace_id / f"{request_id}.json", request)
        write_inbox_request(Path(str(workspace["inbox_path"])), request)
        append_jsonl(hub_root / APPROVED_PATH, request)
        requests.append(request)
    return requests
