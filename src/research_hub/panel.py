"""Static panel generation."""

from __future__ import annotations

import html
from pathlib import Path


def build_panel(context_dir: Path, panel_dir: Path) -> None:
    panel_dir.mkdir(parents=True, exist_ok=True)
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
