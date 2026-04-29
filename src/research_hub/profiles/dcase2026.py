"""DCASE2026 profile enrichment for research-hub."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

IMPORTANT_BASENAMES = {
    "current_state.md": 100,
    "status.md": 92,
    "contract.md": 95,
    "summary.md": 90,
}
ROLE_PATTERNS = [
    ("current_state", re.compile(r"(^|/)current_state\.md$", re.I), 100),
    ("status", re.compile(r"(^|/)status\.md$", re.I), 92),
    ("contract", re.compile(r"(^|/)contract\.md$", re.I), 95),
    ("summary", re.compile(r"(^|/)summary\.md$", re.I), 90),
    ("result", re.compile(r"result|rollup|reading|read", re.I), 88),
    ("diagram", re.compile(r"diagram|mermaid|architecture", re.I), 80),
    ("script", re.compile(r"\.py$|\.sh$", re.I), 35),
    ("manifest", re.compile(r"manifest|input_manifest|queue", re.I), 45),
]
BRANCH_RE = re.compile(r"(?:^|/)(?:workspace|workspaces)?/?(main\d+[^/]*)", re.I)
FLOAT_RE = re.compile(r"(?<![\w.])(?:0\.\d{3,}|1\.0+)(?![\w.])")
METRIC_WORD_RE = re.compile(
    r"official|hmean|harmonic|AUC|pAUC|score|mean-machine|mean_machine",
    re.I,
)
TAG_RULES = {
    "noiseaware": ["noise-aware", "noiseaware", "near", "far", "residual"],
    "renderer": ["renderer", "formula", "source law", "source_law"],
    "e2e_generator": ["Woosh", "MeanAudio", "Resonate", "TangoFlux", "generator"],
    "learnable": ["LoRA", "LayerDistill", "distill", "learnable", "BEATs", "LDN"],
    "backend": ["kNN", "Mahalanobis", "LDN", "score fusion", "rank"],
    "ops": ["gpubook", "rsync", "NAS", "control-plane", "workspace", "queue"],
}
CLAIM_HINTS = [
    ("oracle", re.compile(r"oracle|label-aware|selector.*diagnostic", re.I)),
    ("diagnostic", re.compile(r"diagnostic|ceiling|upper|not final|not deployable", re.I)),
    ("deployable", re.compile(r"deployable|single global|practical|claim ledger", re.I)),
    ("negative", re.compile(r"fail|failed|blocker|damage|demote|weak|not useful", re.I)),
    ("ops", re.compile(r"rsync|NAS|control-plane|heartbeat|recovery|resume", re.I)),
]
STATUS_HINTS = [
    ("blocked", re.compile(r"blocked|missing|failed|failure|stopped|누락|실패", re.I)),
    ("active", re.compile(r"active|running|queued|in progress|진행|대기", re.I)),
    ("complete", re.compile(r"complete|completed|done|finished|끝|완료", re.I)),
    ("stale", re.compile(r"stale|deprecated|old|obsolete|not current", re.I)),
]


def enrich_document(
    path: Path,
    workspace_root: Path,
    relpath: str,
    text: str,
    stat: Any,
) -> dict[str, Any]:
    role, priority = infer_role(relpath)
    branch = infer_branch(relpath)
    run_id = infer_run_id(relpath)
    metrics = extract_metrics(text)
    claim_hint = infer_hint(text, CLAIM_HINTS)
    status_hint = infer_hint(text, STATUS_HINTS)
    if branch in {"main6", "main22", "main23", "main24"}:
        priority += 8
    if metrics:
        priority += 8
    if claim_hint in {"deployable", "oracle", "diagnostic"}:
        priority += 5
    return {
        "type": "document",
        "workspace_root": str(workspace_root),
        "path": str(path),
        "relpath": relpath,
        "size_bytes": stat.st_size,
        "branch": branch,
        "run_id": run_id,
        "doc_role": role,
        "priority": priority,
        "tags": infer_tags(text, relpath),
        "claim_type_hint": claim_hint,
        "status_hint": status_hint,
        "metrics": metrics,
        "excerpt": make_excerpt(text),
    }


def infer_branch(relpath: str) -> str | None:
    match = BRANCH_RE.search(relpath)
    if not match:
        return None
    normalized = re.match(r"(main\d+)", match.group(1), re.I)
    return normalized.group(1).lower() if normalized else match.group(1).lower()


def infer_run_id(relpath: str) -> str | None:
    for part in relpath.split("/"):
        if re.match(r"20\d{2}[-_]", part) or re.match(r"\d{4}[-_][A-Za-z]", part):
            return part
    return None


def infer_role(relpath: str) -> tuple[str, int]:
    lower = relpath.lower()
    basename = Path(relpath).name.lower()
    if basename in IMPORTANT_BASENAMES:
        return basename.replace(".md", ""), IMPORTANT_BASENAMES[basename]
    for role, pattern, priority in ROLE_PATTERNS:
        if pattern.search(lower):
            return role, priority
    suffix = Path(relpath).suffix.lower()
    return "document", 40 if suffix in {".md", ".txt"} else 20


def infer_tags(text: str, relpath: str) -> list[str]:
    haystack = f"{relpath}\n{text[:20000]}".lower()
    tags = [
        tag
        for tag, words in TAG_RULES.items()
        if any(word.lower() in haystack for word in words)
    ]
    return sorted(set(tags))


def infer_hint(
    text: str,
    rules: list[tuple[str, re.Pattern[str]]],
    default: str = "unknown",
) -> str:
    sample = text[:50000]
    for label, pattern in rules:
        if pattern.search(sample):
            return label
    return default


def extract_metrics(text: str, limit: int = 12) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not METRIC_WORD_RE.search(line):
            continue
        for raw in FLOAT_RE.findall(line)[:4]:
            value = float(raw)
            label = "metric"
            for candidate in (
                "DCASE-like",
                "harmonic",
                "hmean",
                "official",
                "mean-machine",
                "AUC",
                "pAUC",
                "score",
            ):
                if candidate.lower() in line.lower():
                    label = candidate
                    break
            metrics.append({
                "label": label,
                "value": value,
                "context": re.sub(r"\s+", " ", line.strip())[:300],
            })
            if len(metrics) >= limit:
                return metrics
    return metrics


def make_excerpt(text: str, max_len: int = 900) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    selected: list[str] = []
    for line in lines:
        if re.search(
            r"claim|결론|현재|official|DCASE|best|status|boundary|next|blocked|완료|실패",
            line,
            re.I,
        ):
            selected.append(line)
        if len("\n".join(selected)) > max_len:
            break
    if not selected:
        selected = lines[:8]
    return "\n".join(selected)[:max_len]


def build_runs(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str | None, str], list[dict[str, Any]]] = {}
    for document in documents:
        run_id = document.get("run_id")
        if run_id:
            grouped.setdefault((document.get("branch"), str(run_id)), []).append(document)
    runs: list[dict[str, Any]] = []
    for (branch, run_id), docs in sorted(grouped.items(), key=lambda item: str(item[0])):
        status = "unknown"
        for preferred in ("blocked", "active", "complete"):
            if any(doc.get("status_hint") == preferred for doc in docs):
                status = preferred
                break
        metrics = [
            metric
            for doc in docs
            for metric in doc.get("metrics", [])
        ]
        runs.append({
            "type": "run",
            "workspace_id": docs[0]["workspace_id"],
            "branch": branch,
            "run_id": run_id,
            "status": status,
            "documents": [
                doc["source_path"]
                for doc in sorted(docs, key=lambda row: -int(row.get("priority", 0)))[:12]
            ],
            "best_metric": max(metrics, key=lambda item: item.get("value", -1)) if metrics else None,
            "claim_type_hint": next(
                (doc.get("claim_type_hint") for doc in docs if doc.get("claim_type_hint") != "unknown"),
                "unknown",
            ),
            "top_excerpt": sorted(docs, key=lambda row: -int(row.get("priority", 0)))[0].get("excerpt", ""),
        })
    return runs


def build_claims(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for document in documents:
        hint = document.get("claim_type_hint", "unknown")
        role = document.get("doc_role", "document")
        if hint not in {"deployable", "oracle", "diagnostic", "negative"} and role not in {
            "current_state",
            "result",
            "summary",
        }:
            continue
        lines = [
            line.strip()
            for line in str(document.get("excerpt", "")).splitlines()
            if re.search(
                r"claim|결론|deployable|diagnostic|oracle|official|DCASE|best|현재|boundary",
                line,
                re.I,
            )
        ]
        if not lines and document.get("metrics"):
            lines.append(str(document.get("excerpt") or document.get("source_path")))
        if not lines:
            continue
        claims.append({
            "type": "claim",
            "workspace_id": document["workspace_id"],
            "branch": document.get("branch"),
            "claim": " / ".join(lines)[:600],
            "claim_type": hint,
            "metrics": document.get("metrics", [])[:6],
            "scope": "unknown; inspect source",
            "evidence_paths": [document["source_path"]],
            "doc_role": role,
            "priority": document.get("priority", 0),
        })
    claims.sort(key=lambda item: (-int(item.get("priority", 0)), str(item.get("branch"))))
    return claims[:500]
