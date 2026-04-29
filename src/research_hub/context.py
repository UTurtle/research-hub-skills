"""Context projection utilities."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

DEFAULT_RESEARCH_STATE = """# Latest Research State

This file is generated from indexed workspace evidence.

Use evidence paths. Do not organize evidence only by branch number.
"""
DEFAULT_CLAIM_BOUNDARIES = """# Latest Claim Boundaries

This file is generated. Review important claims manually.

Diagnostic or oracle results must not be reported as deployable results.
"""


def write_default_context(context_dir: Path) -> None:
    context_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "START_HERE.md": (
            "# Research Context Start\n\n"
            "Read latest_research_state.md and latest_claim_boundaries.md "
            "before doing work.\n"
        ),
        "latest_research_state.md": DEFAULT_RESEARCH_STATE,
        "latest_claim_boundaries.md": DEFAULT_CLAIM_BOUNDARIES,
        "active_runs.md": "# Active Runs\n\nNo active runs indexed yet.\n",
        "related_workspaces.md": "# Related Workspaces\n\nGenerated.\n",
        "related_papers.md": "# Related Papers\n\nGenerated.\n",
        "related_discussions.md": "# Related Discussions\n\nGenerated.\n",
    }
    for filename, content in files.items():
        (context_dir / filename).write_text(content, encoding="utf-8")


def copy_index_to_context(index_dir: Path, context_dir: Path) -> None:
    context_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("document_chunks.jsonl", "search_index.sqlite"):
        src = index_dir / filename
        if src.exists():
            shutil.copy2(src, context_dir / filename)
    links_path = context_dir / "source_links.jsonl"
    docs_path = index_dir / "documents.jsonl"
    if not docs_path.exists():
        links_path.write_text("", encoding="utf-8")
        return
    with docs_path.open("r", encoding="utf-8") as docs_file, (
        links_path.open("w", encoding="utf-8")
    ) as links_file:
        for line in docs_file:
            record = json.loads(line)
            links_file.write(json.dumps({
                "source_path": record["source_path"],
                "workspace_id": record["workspace_id"],
                "host_id": record["host_id"],
                "sha1": record["sha1"],
            }, ensure_ascii=False) + "\n")


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
