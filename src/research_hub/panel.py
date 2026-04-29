"""Static panel generation."""

from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def build_panel(context_dir: Path, panel_dir: Path) -> None:
    panel_dir.mkdir(parents=True, exist_ok=True)
    docs = read_jsonl(context_dir / "documents.jsonl")
    runs = read_jsonl(context_dir / "runs.jsonl")
    claims = read_jsonl(context_dir / "claims.jsonl")
    if docs or runs or claims:
        build_index_panel(docs, runs, claims, panel_dir)
        return
    state = read_or_default(context_dir / "latest_research_state.md")
    claims = read_or_default(context_dir / "latest_claim_boundaries.md")
    active = read_or_default(context_dir / "active_runs.md")
    body = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Research Hub Panel</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.5; }}
    pre {{ background: #f6f6f6; padding: 1rem; overflow-x: auto; }}
    section {{ margin-bottom: 2rem; }}
  </style>
</head>
<body>
  <h1>Research Hub Panel</h1>
  <section><h2>Latest Research State</h2><pre>{html.escape(state)}</pre></section>
  <section><h2>Claim Boundaries</h2><pre>{html.escape(claims)}</pre></section>
  <section><h2>Active Runs</h2><pre>{html.escape(active)}</pre></section>
</body>
</html>
"""
    (panel_dir / "index.html").write_text(body, encoding="utf-8")
    (panel_dir / "research_state.md").write_text(state, encoding="utf-8")


def read_or_default(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return "Not generated yet."


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def build_index_panel(
    docs: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    panel_dir: Path,
) -> None:
    by_branch_docs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_branch_runs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_branch_claims: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for doc in docs:
        by_branch_docs[str(doc.get("branch") or "other")].append(doc)
    for run in runs:
        by_branch_runs[str(run.get("branch") or "other")].append(run)
    for claim in claims:
        by_branch_claims[str(claim.get("branch") or "other")].append(claim)

    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Research Hub Panel</title>",
        "<style>body{font-family:system-ui,sans-serif;margin:24px;line-height:1.45}"
        "table{border-collapse:collapse;width:100%;font-size:13px}"
        "td,th{border:1px solid #ddd;padding:6px;vertical-align:top}"
        ".card{border:1px solid #ddd;border-left:5px solid #555;padding:12px;margin:10px 0}"
        "code{background:#f4f4f4;padding:1px 4px}</style></head><body>",
        "<h1>Research Hub Panel</h1>",
        "<p>Generated projection. Original workspace files remain authoritative.</p>",
    ]
    for branch in sorted(set(by_branch_docs) | set(by_branch_runs) | set(by_branch_claims)):
        parts.append(f"<h2>{html.escape(branch)}</h2>")
        for claim in sorted(
            by_branch_claims.get(branch, []),
            key=lambda item: -int(item.get("priority", 0)),
        )[:8]:
            paths = ", ".join(claim.get("evidence_paths", []))
            parts.append(
                "<section class='card'>"
                f"<strong>{html.escape(str(claim.get('claim_type', 'unknown')))}</strong>"
                f"<p>{html.escape(str(claim.get('claim', '')))}</p>"
                f"<p><code>{html.escape(paths)}</code></p>"
                "</section>"
            )
        branch_runs = by_branch_runs.get(branch, [])
        if branch_runs:
            parts.append("<h3>Runs</h3><table><tr><th>run</th><th>status</th><th>metric</th></tr>")
            for run in branch_runs[:12]:
                metric = run.get("best_metric") or {}
                parts.append(
                    "<tr>"
                    f"<td>{html.escape(str(run.get('run_id', '')))}</td>"
                    f"<td>{html.escape(str(run.get('status', 'unknown')))}</td>"
                    f"<td>{html.escape(str(metric.get('value', '')))}</td>"
                    "</tr>"
                )
            parts.append("</table>")
        branch_docs = sorted(
            by_branch_docs.get(branch, []),
            key=lambda item: -int(item.get("priority", 0)),
        )
        if branch_docs:
            parts.append("<h3>Documents</h3><table><tr><th>role</th><th>priority</th><th>path</th><th>excerpt</th></tr>")
            for doc in branch_docs[:20]:
                parts.append(
                    "<tr>"
                    f"<td>{html.escape(str(doc.get('doc_role', 'document')))}</td>"
                    f"<td>{html.escape(str(doc.get('priority', '')))}</td>"
                    f"<td><code>{html.escape(str(doc.get('source_path', '')))}</code></td>"
                    f"<td>{html.escape(str(doc.get('excerpt', '')))}</td>"
                    "</tr>"
                )
            parts.append("</table>")
    parts.append("</body></html>")
    (panel_dir / "index.html").write_text("\n".join(parts), encoding="utf-8")
    build_markdown(docs, runs, claims, panel_dir)
    build_agent_contexts(docs, runs, claims, panel_dir)


def build_markdown(
    docs: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    panel_dir: Path,
) -> None:
    lines = ["# Research Hub Panel", "", "Original workspace files remain authoritative.", ""]
    for claim in sorted(claims, key=lambda item: -int(item.get("priority", 0)))[:30]:
        lines.append(f"- **{claim.get('claim_type', 'unknown')}** {claim.get('claim', '')}")
        for path in claim.get("evidence_paths", []):
            lines.append(f"  - evidence: `{path}`")
    if runs:
        lines.extend(["", "## Runs", ""])
        for run in runs[:50]:
            metric = run.get("best_metric") or {}
            lines.append(
                f"- `{run.get('run_id')}` ({run.get('status', 'unknown')}): "
                f"{metric.get('label', '')} {metric.get('value', '')}"
            )
    if not claims and docs:
        lines.extend(["", "## Top Documents", ""])
        for doc in sorted(docs, key=lambda item: -int(item.get("priority", 0)))[:30]:
            lines.append(f"- `{doc.get('source_path')}`")
    (panel_dir / "research_state.md").write_text("\n".join(lines), encoding="utf-8")


def build_agent_contexts(
    docs: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    panel_dir: Path,
) -> None:
    context_dir = panel_dir / "agent_context"
    context_dir.mkdir(parents=True, exist_ok=True)
    branches = sorted({str(item.get("branch")) for item in docs + runs + claims if item.get("branch")})
    for branch in branches:
        payload = {
            "branch": branch,
            "current_claims": [item for item in claims if item.get("branch") == branch][:20],
            "active_runs": [
                item for item in runs
                if item.get("branch") == branch and item.get("status") == "active"
            ],
            "blocked_runs": [
                item for item in runs
                if item.get("branch") == branch and item.get("status") == "blocked"
            ],
            "top_documents": [
                item for item in sorted(
                    docs,
                    key=lambda row: -int(row.get("priority", 0)),
                )
                if item.get("branch") == branch
            ][:40],
        }
        (context_dir / f"{branch}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
