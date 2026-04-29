# Research Library Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first dependency-free Research Library Substrate slice: agent startup index, vector-ready records, graph records, and a human `library.md` view generated from the existing Research Hub evidence.

**Architecture:** Add a focused `research_hub.library` module that reads generated JSONL evidence and writes library-facing outputs into the hub context directory. Keep `research_hub.indexer` responsible for base indexing and manifests, and keep `research_hub.context` responsible for copying generated files into `_research_context/`.

**Tech Stack:** Python standard library, JSONL, Markdown, SQLite FTS already present, `unittest`.

---

### Task 1: Generic Library Outputs

**Files:**
- Create: `tests/test_library_outputs.py`
- Create: `src/research_hub/library.py`
- Modify: `src/research_hub/indexer.py`
- Modify: `src/research_hub/cli.py`
- Modify: `src/research_hub/context.py`

- [ ] **Step 1: Write the failing generic output test**

Create `tests/test_library_outputs.py`:

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research_hub.cli import main


class LibraryOutputTests(unittest.TestCase):
    def test_generic_publish_writes_agent_index_retrieval_exports_and_library(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            hub = Path(tmp) / "hub"
            root.mkdir()
            (root / "note.md").write_text(
                "# Note\nThis workspace studies bearing faults and baseline metrics.\n",
                encoding="utf-8",
            )

            main([
                "publish",
                "--workspace-root",
                str(root),
                "--hub",
                str(hub),
                "--workspace-id",
                "generic",
                "--host-id",
                "local",
            ])

            context_dir = hub / "contexts" / "generic"
            workspace_context = root / "_research_context"

            agent_index = json.loads(
                (context_dir / "agent_context" / "INDEX.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(agent_index["workspace_id"], "generic")
            self.assertEqual(agent_index["profile"], "generic")
            self.assertIn("manifest.json", agent_index["recommended_read_order"])
            self.assertIn("source_links.jsonl", agent_index["source_policy"]["required_files"])

            vector_records = read_jsonl(context_dir / "retrieval" / "vector_records.jsonl")
            self.assertEqual(vector_records[0]["metadata"]["source_path"], "note.md")
            self.assertEqual(vector_records[0]["metadata"]["record_type"], "chunk")
            self.assertIn("bearing faults", vector_records[0]["text"])

            graph_nodes = read_jsonl(context_dir / "retrieval" / "graph_nodes.jsonl")
            graph_edges = read_jsonl(context_dir / "retrieval" / "graph_edges.jsonl")
            self.assertTrue(any(node["type"] == "document" for node in graph_nodes))
            self.assertTrue(any(edge["type"] == "contains_chunk" for edge in graph_edges))

            library = (context_dir / "library.md").read_text(encoding="utf-8")
            self.assertIn("note.md", library)
            self.assertIn("Original workspace files remain authoritative", library)

            self.assertTrue((workspace_context / "agent_context" / "INDEX.json").exists())
            self.assertTrue((workspace_context / "retrieval" / "vector_records.jsonl").exists())
            self.assertTrue((workspace_context / "library.md").exists())


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
$env:PYTHONPATH="C:\Users\zenbook\repos\dcase2026\_inspection\research-hub-skills-remote-check\src"; python -m unittest tests.test_library_outputs.LibraryOutputTests.test_generic_publish_writes_agent_index_retrieval_exports_and_library -v
```

Expected: FAIL because `agent_context/INDEX.json`, `retrieval/vector_records.jsonl`, `graph_nodes.jsonl`, `graph_edges.jsonl`, and `library.md` are not generated yet.

- [ ] **Step 3: Add `research_hub.library` helpers**

Create `src/research_hub/library.py`:

```python
"""Library substrate generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for record in records:
            file_obj.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_library_outputs(context_dir: Path) -> None:
    documents = read_jsonl(context_dir / "documents.jsonl")
    chunks = read_jsonl(context_dir / "document_chunks.jsonl")
    claims = read_jsonl(context_dir / "claims.jsonl")
    runs = read_jsonl(context_dir / "runs.jsonl")
    manifest = read_manifest(context_dir / "manifest.json", documents)
    write_agent_index(context_dir, manifest, claims, runs)
    write_vector_records(context_dir, chunks, documents, manifest)
    write_graph_records(context_dir, documents, chunks, claims, runs, manifest)
    write_library_markdown(context_dir, documents, claims, runs, manifest)


def read_manifest(path: Path, documents: list[dict[str, Any]]) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    workspace_id = documents[0].get("workspace_id", "unknown") if documents else "unknown"
    return {
        "type": "workspace_index_manifest",
        "workspace_id": workspace_id,
        "profile": "generic",
        "documents": len(documents),
        "runs": 0,
        "claims": 0,
    }


def write_agent_index(
    context_dir: Path,
    manifest: dict[str, Any],
    claims: list[dict[str, Any]],
    runs: list[dict[str, Any]],
) -> None:
    payload = {
        "type": "agent_context_index",
        "workspace_id": manifest.get("workspace_id", "unknown"),
        "profile": manifest.get("profile", "generic"),
        "recommended_read_order": [
            "START_HERE.md",
            "manifest.json",
            "library.md",
            "claims.jsonl" if claims else "",
            "runs.jsonl" if runs else "",
            "documents.jsonl",
            "document_chunks.jsonl",
            "source_links.jsonl",
            "retrieval/vector_records.jsonl",
            "retrieval/graph_nodes.jsonl",
            "retrieval/graph_edges.jsonl",
        ],
        "context_packs": discover_context_packs(context_dir),
        "source_policy": {
            "original_files_are_authoritative": True,
            "required_files": ["source_links.jsonl", "documents.jsonl"],
            "deep_read_rule": "Use generated context to choose source files, then inspect original paths before final claims.",
        },
        "profile_sections": {},
    }
    payload["recommended_read_order"] = [
        item for item in payload["recommended_read_order"] if item
    ]
    out = context_dir / "agent_context" / "INDEX.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def discover_context_packs(context_dir: Path) -> list[str]:
    pack_dir = context_dir / "agent_context"
    if not pack_dir.exists():
        return []
    return sorted(
        path.name
        for path in pack_dir.glob("*.json")
        if path.name != "INDEX.json"
    )


def write_vector_records(
    context_dir: Path,
    chunks: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    docs_by_path = {doc.get("source_path"): doc for doc in documents}
    records: list[dict[str, Any]] = []
    for chunk in chunks:
        source_path = chunk.get("source_path")
        doc = docs_by_path.get(source_path, {})
        records.append({
            "id": chunk.get("chunk_id"),
            "text": chunk.get("text", ""),
            "metadata": {
                "workspace_id": chunk.get("workspace_id"),
                "source_path": source_path,
                "sha1": chunk.get("sha1"),
                "record_type": "chunk",
                "profile": manifest.get("profile", "generic"),
                "tags": doc.get("tags", []),
                "claim_type_hint": doc.get("claim_type_hint", "unknown"),
                "status_hint": doc.get("status_hint", "unknown"),
            },
        })
    write_jsonl(context_dir / "retrieval" / "vector_records.jsonl", records)


def write_graph_records(
    context_dir: Path,
    documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    nodes: list[dict[str, Any]] = [{
        "id": f"workspace:{manifest.get('workspace_id', 'unknown')}",
        "type": "workspace",
        "label": manifest.get("workspace_id", "unknown"),
        "metadata": {"profile": manifest.get("profile", "generic")},
    }]
    edges: list[dict[str, Any]] = []
    for doc in documents:
        doc_id = f"document:{doc['source_path']}"
        nodes.append({
            "id": doc_id,
            "type": "document",
            "label": doc["source_path"],
            "metadata": doc,
        })
        edges.append({
            "source": nodes[0]["id"],
            "target": doc_id,
            "type": "has_document",
            "evidence_paths": [doc["source_path"]],
        })
    for chunk in chunks:
        chunk_id = f"chunk:{chunk['chunk_id']}"
        doc_id = f"document:{chunk['source_path']}"
        nodes.append({
            "id": chunk_id,
            "type": "chunk",
            "label": chunk["chunk_id"],
            "metadata": {
                "source_path": chunk["source_path"],
                "chunk_index": chunk["chunk_index"],
                "sha1": chunk["sha1"],
            },
        })
        edges.append({
            "source": doc_id,
            "target": chunk_id,
            "type": "contains_chunk",
            "evidence_paths": [chunk["source_path"]],
        })
    for idx, claim in enumerate(claims):
        claim_id = f"claim:{idx}"
        paths = claim.get("evidence_paths", [])
        nodes.append({
            "id": claim_id,
            "type": "claim",
            "label": claim.get("claim", ""),
            "metadata": claim,
        })
        for path in paths:
            edges.append({
                "source": claim_id,
                "target": f"document:{path}",
                "type": "supported_by",
                "evidence_paths": [path],
            })
    for run in runs:
        run_id = f"run:{run.get('run_id')}"
        nodes.append({
            "id": run_id,
            "type": "run",
            "label": run.get("run_id", ""),
            "metadata": run,
        })
        for path in run.get("documents", []):
            edges.append({
                "source": run_id,
                "target": f"document:{path}",
                "type": "uses_document",
                "evidence_paths": [path],
            })
    write_jsonl(context_dir / "retrieval" / "graph_nodes.jsonl", nodes)
    write_jsonl(context_dir / "retrieval" / "graph_edges.jsonl", edges)


def write_library_markdown(
    context_dir: Path,
    documents: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    lines = [
        "# Research Library",
        "",
        "Original workspace files remain authoritative. Use this generated library as a map back to source evidence.",
        "",
        f"- Workspace: `{manifest.get('workspace_id', 'unknown')}`",
        f"- Profile: `{manifest.get('profile', 'generic')}`",
        f"- Documents: {len(documents)}",
        f"- Claims: {len(claims)}",
        f"- Runs: {len(runs)}",
        "",
        "## Documents",
        "",
    ]
    for doc in documents[:100]:
        lines.append(f"- `{doc.get('source_path')}`")
    if claims:
        lines.extend(["", "## Claims", ""])
        for claim in claims[:50]:
            lines.append(f"- **{claim.get('claim_type', 'unknown')}** {claim.get('claim', '')}")
            for path in claim.get("evidence_paths", []):
                lines.append(f"  - evidence: `{path}`")
    if runs:
        lines.extend(["", "## Runs", ""])
        for run in runs[:50]:
            lines.append(f"- `{run.get('run_id')}` ({run.get('status', 'unknown')})")
            for path in run.get("documents", [])[:5]:
                lines.append(f"  - document: `{path}`")
    (context_dir / "library.md").write_text("\n".join(lines), encoding="utf-8")
```

- [ ] **Step 4: Wire library generation into publish**

Modify `src/research_hub/cli.py`:

```python
from research_hub.library import build_library_outputs
```

Then in the `publish` branch, use this order:

```python
        copy_index_to_context(index_dir, hub_context_dir)
        build_panel(hub_context_dir, panel_dir)
        panel_agent_context = panel_dir / "agent_context"
        if panel_agent_context.exists():
            copy_tree(panel_agent_context, hub_context_dir / "agent_context")
        build_library_outputs(hub_context_dir)
        copy_tree(hub_context_dir, context_dir)
```

Remove the older `copy_tree(hub_context_dir, context_dir)` call before
`build_panel`, and remove the older final `build_panel(hub_context_dir,
panel_dir)` call. The panel should be generated before library outputs so
profile-specific `agent_context/*.json` packs can be discovered by
`agent_context/INDEX.json`.

- [ ] **Step 5: Ensure generic manifests exist**

Modify `src/research_hub/indexer.py` so `manifest.json` is written for both generic and profiled indexes. Replace:

```python
    if profile:
        write_profile_outputs(config, profile, document_records)
```

with:

```python
    profile_counts = {"runs": 0, "claims": 0}
    if profile:
        profile_counts = write_profile_outputs(config, profile, document_records)
    write_manifest(config, document_records, profile_counts)
```

Then add:

```python
def write_manifest(
    config: IndexConfig,
    document_records: list[dict[str, Any]],
    profile_counts: dict[str, int],
) -> None:
    manifest = {
        "type": "workspace_index_manifest",
        "workspace_id": config.workspace_id,
        "host_id": config.host_id,
        "profile": config.profile,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "documents": len(document_records),
        "runs": profile_counts["runs"],
        "claims": profile_counts["claims"],
    }
    (config.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

And change `write_profile_outputs` to return counts and stop writing the manifest itself:

```python
def write_profile_outputs(
    config: IndexConfig,
    profile: Any,
    document_records: list[dict[str, Any]],
) -> dict[str, int]:
    runs = profile.build_runs(document_records)
    claims = profile.build_claims(document_records)
    write_jsonl(config.out_dir / "runs.jsonl", runs)
    write_jsonl(config.out_dir / "claims.jsonl", claims)
    return {"runs": len(runs), "claims": len(claims)}
```

- [ ] **Step 6: Ensure generated files are projected to the workspace**

No extra copy code is needed for `agent_context/`, `retrieval/`, or
`library.md` if Task 1 Step 4 writes them into `hub_context_dir` before:

```python
copy_tree(hub_context_dir, context_dir)
```

Confirm the publish branch copies the whole `hub_context_dir` after
`build_library_outputs(hub_context_dir)`.

- [ ] **Step 7: Run the generic test to verify it passes**

Run:

```bash
$env:PYTHONPATH="C:\Users\zenbook\repos\dcase2026\_inspection\research-hub-skills-remote-check\src"; python -m unittest tests.test_library_outputs.LibraryOutputTests.test_generic_publish_writes_agent_index_retrieval_exports_and_library -v
```

Expected: PASS.

- [ ] **Step 8: Commit Task 1**

```bash
git add tests/test_library_outputs.py src/research_hub/library.py src/research_hub/indexer.py src/research_hub/cli.py src/research_hub/context.py
git commit -m "Add generic research library outputs"
```

### Task 2: DCASE Profile Library Enrichment

**Files:**
- Modify: `tests/test_library_outputs.py`
- Modify: `src/research_hub/library.py`
- Modify: `src/research_hub/panel.py` if `agent_context` placement needs alignment

- [ ] **Step 1: Write the failing DCASE enrichment test**

Append this test to `LibraryOutputTests` in `tests/test_library_outputs.py`:

```python
    def test_dcase_publish_adds_claim_and_run_graph_nodes_and_profile_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            hub = Path(tmp) / "hub"
            run_dir = root / "workspaces" / "main6_noiseaware" / "2026-04-28-main6-run"
            run_dir.mkdir(parents=True)
            (run_dir / "contract.md").write_text(
                "\n".join([
                    "# main6 contract",
                    "single global noise-aware residual is deployable.",
                    "official DCASE-like harmonic score 0.608921",
                    "status complete",
                ]),
                encoding="utf-8",
            )

            main([
                "publish",
                "--workspace-root",
                str(root),
                "--hub",
                str(hub),
                "--workspace-id",
                "dcase",
                "--host-id",
                "local",
                "--profile",
                "dcase2026",
            ])

            context_dir = hub / "contexts" / "dcase"
            vector_records = read_jsonl(context_dir / "retrieval" / "vector_records.jsonl")
            self.assertEqual(vector_records[0]["metadata"]["profile"], "dcase2026")
            self.assertEqual(vector_records[0]["metadata"]["claim_type_hint"], "deployable")

            graph_nodes = read_jsonl(context_dir / "retrieval" / "graph_nodes.jsonl")
            self.assertTrue(any(node["type"] == "claim" for node in graph_nodes))
            self.assertTrue(any(node["type"] == "run" for node in graph_nodes))

            agent_index = json.loads(
                (context_dir / "agent_context" / "INDEX.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(agent_index["profile"], "dcase2026")
            self.assertIn("main6.json", agent_index["context_packs"])

            library = (context_dir / "library.md").read_text(encoding="utf-8")
            self.assertIn("deployable", library)
            self.assertIn("2026-04-28-main6-run", library)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
$env:PYTHONPATH="C:\Users\zenbook\repos\dcase2026\_inspection\research-hub-skills-remote-check\src"; python -m unittest tests.test_library_outputs.LibraryOutputTests.test_dcase_publish_adds_claim_and_run_graph_nodes_and_profile_metadata -v
```

Expected: FAIL if `agent_context/INDEX.json` is built before branch-specific packs or if claim/run graph nodes are missing.

- [ ] **Step 3: Keep profile packs available in context**

If the test fails because `main6.json` is absent from `context_packs`, verify
that Task 1 Step 4 was applied exactly. The publish order must copy
`panel/agent_context/*.json` into `hub_context_dir/agent_context/` before
calling `build_library_outputs(hub_context_dir)`.

- [ ] **Step 4: Run the DCASE test to verify it passes**

Run:

```bash
$env:PYTHONPATH="C:\Users\zenbook\repos\dcase2026\_inspection\research-hub-skills-remote-check\src"; python -m unittest tests.test_library_outputs.LibraryOutputTests.test_dcase_publish_adds_claim_and_run_graph_nodes_and_profile_metadata -v
```

Expected: PASS.

- [ ] **Step 5: Run existing DCASE tests**

Run:

```bash
$env:PYTHONPATH="C:\Users\zenbook\repos\dcase2026\_inspection\research-hub-skills-remote-check\src"; python -m unittest tests.test_dcase_profile -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add tests/test_library_outputs.py src/research_hub/library.py src/research_hub/cli.py src/research_hub/panel.py
git commit -m "Enrich research library outputs for profiles"
```

### Task 3: Documentation And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/integrations.md`
- Modify: `docs/skill-map.md`

- [ ] **Step 1: Update README output list**

In `README.md`, add a short subsection under Architecture:

```markdown
Generated library outputs include:

- `_research_context/agent_context/INDEX.json`
- `_research_context/retrieval/vector_records.jsonl`
- `_research_context/retrieval/graph_nodes.jsonl`
- `_research_context/retrieval/graph_edges.jsonl`
- `_research_context/library.md`
```

- [ ] **Step 2: Update integrations doc from future tense to first-slice wording**

In `docs/integrations.md`, replace the future adapter wording with:

```markdown
The first library substrate slice exports vector-ready records and provenance
graph records as JSONL. Downstream vector stores and graph databases can ingest
those files without becoming core dependencies.
```

- [ ] **Step 3: Update skill map**

In `docs/skill-map.md`, add `retrieval/*.jsonl` and `library.md` to the main
diagram outputs.

- [ ] **Step 4: Run full verification**

Run:

```bash
$env:PYTHONPATH="C:\Users\zenbook\repos\dcase2026\_inspection\research-hub-skills-remote-check\src"; python -m unittest discover -v
python -m compileall C:\Users\zenbook\repos\dcase2026\_inspection\research-hub-skills-remote-check\src
git diff --check
```

Expected:

- all unittests pass
- compileall exits 0
- diff check exits 0

- [ ] **Step 5: Commit Task 3**

```bash
git add README.md docs/integrations.md docs/skill-map.md
git commit -m "Document research library substrate outputs"
```

- [ ] **Step 6: Push branch**

```bash
git push
```

- [ ] **Step 7: Confirm clean branch**

```bash
git status --short --branch
```

Expected: branch tracks `origin/codex/add-research-hub-skills-v0.1` with no
local changes.
