from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research_hub.cli import main


class DcaseProfileTests(unittest.TestCase):
    def test_publish_without_profile_keeps_generic_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            hub = Path(tmp) / "hub"
            root.mkdir()
            (root / "note.md").write_text("# Note\nscore 0.500000\n", encoding="utf-8")

            main([
                "publish",
                "--workspace-root",
                str(root),
                "--hub",
                str(hub),
                "--workspace-id",
                "generic",
            ])

            index_dir = hub / "index" / "generic"
            docs = read_jsonl(index_dir / "documents.jsonl")
            self.assertEqual(docs[0]["source_path"], "note.md")
            self.assertNotIn("branch", docs[0])
            self.assertFalse((index_dir / "runs.jsonl").exists())
            self.assertFalse((index_dir / "claims.jsonl").exists())

    def test_publish_with_dcase_profile_writes_enriched_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            hub = Path(tmp) / "hub"
            run_dir = root / "workspaces" / "main6_noiseaware" / "2026-04-28-main6-run"
            run_dir.mkdir(parents=True)
            (run_dir / "contract.md").write_text(
                "\n".join(
                    [
                        "# main6 contract",
                        "single global noise-aware residual is deployable.",
                        "official DCASE-like harmonic score 0.608921",
                        "status complete",
                    ]
                ),
                encoding="utf-8",
            )

            main(
                [
                    "publish",
                    "--workspace-root",
                    str(root),
                    "--hub",
                    str(hub),
                    "--workspace-id",
                    "smoke",
                    "--host-id",
                    "local",
                    "--profile",
                    "dcase2026",
                ]
            )

            index_dir = hub / "index" / "smoke"
            docs = read_jsonl(index_dir / "documents.jsonl")
            self.assertEqual(docs[0]["branch"], "main6")
            self.assertEqual(docs[0]["workspace_root"], str(root))
            self.assertEqual(docs[0]["doc_role"], "contract")
            self.assertEqual(docs[0]["claim_type_hint"], "deployable")
            self.assertEqual(docs[0]["status_hint"], "complete")
            self.assertEqual(docs[0]["metrics"][0]["value"], 0.608921)

            runs = read_jsonl(index_dir / "runs.jsonl")
            self.assertEqual(runs[0]["branch"], "main6")
            self.assertEqual(runs[0]["status"], "complete")

            claims = read_jsonl(index_dir / "claims.jsonl")
            self.assertEqual(claims[0]["claim_type"], "deployable")
            self.assertEqual(claims[0]["evidence_paths"], [docs[0]["source_path"]])

            self.assertTrue((hub / "contexts" / "smoke" / "manifest.json").exists())
            self.assertTrue((hub / "panel" / "agent_context" / "main6.json").exists())


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


if __name__ == "__main__":
    unittest.main()
