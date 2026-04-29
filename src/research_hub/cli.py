"""Command line interface for research-hub."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path
from typing import Sequence

from research_hub.context import (
    copy_index_to_context,
    copy_tree,
    write_default_context,
)
from research_hub.git_sync import sync_pull, sync_push
from research_hub.indexer import (
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_EXCLUDE_EXTENSIONS,
    DEFAULT_INCLUDE_EXTENSIONS,
    IndexConfig,
    build_index,
)
from research_hub.panel import build_panel


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="research-hub")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (
        "init", "publish", "pull-context", "open", "sync-push",
        "sync-pull",
    ):
        sub_parser = subparsers.add_parser(command)
        add_common_args(sub_parser)
    args = parser.parse_args(argv)
    workspace_root = Path(args.workspace_root).resolve()
    hub_root = Path(args.hub).resolve()
    index_dir = hub_root / "index" / args.workspace_id
    context_dir = workspace_root / "_research_context"
    hub_context_dir = hub_root / "contexts" / args.workspace_id
    panel_dir = hub_root / "panel"
    if args.command == "init":
        run_init(workspace_root, context_dir)
        return
    if args.command == "publish":
        config = make_index_config(
            workspace_root, args.workspace_id, args.host_id, index_dir,
            args.profile
        )
        build_index(config)
        write_default_context(hub_context_dir)
        copy_index_to_context(index_dir, hub_context_dir)
        copy_tree(hub_context_dir, context_dir)
        build_panel(hub_context_dir, panel_dir)
        return
    if args.command == "pull-context":
        if hub_context_dir.exists():
            copy_tree(hub_context_dir, context_dir)
        else:
            write_default_context(context_dir)
        return
    if args.command == "open":
        print(panel_dir / "index.html")
        return
    if args.command == "sync-push":
        sync_push(hub_root, "Update research hub state")
        return
    if args.command == "sync-pull":
        sync_pull(hub_root)
        return


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument(
        "--workspace-id",
        default=os.environ.get("RESEARCH_WORKSPACE_ID", Path.cwd().name),
    )
    parser.add_argument(
        "--host-id",
        default=os.environ.get("RESEARCH_HOST_ID", "local"),
    )
    parser.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )
    parser.add_argument(
        "--profile",
        choices=("generic", "dcase2026"),
        default=os.environ.get("RESEARCH_PROFILE", "generic"),
    )


def make_index_config(
    workspace_root: Path,
    workspace_id: str,
    host_id: str,
    index_dir: Path,
    profile: str,
) -> IndexConfig:
    return IndexConfig(
        workspace_root=workspace_root,
        workspace_id=workspace_id,
        host_id=host_id,
        out_dir=index_dir,
        include_extensions=set(DEFAULT_INCLUDE_EXTENSIONS),
        exclude_dirs=set(DEFAULT_EXCLUDE_DIRS),
        exclude_extensions=set(DEFAULT_EXCLUDE_EXTENSIONS),
        profile=profile,
    )


def run_init(workspace_root: Path, context_dir: Path) -> None:
    workspace_root.mkdir(parents=True, exist_ok=True)
    write_default_context(context_dir)
    agents_path = workspace_root / "AGENTS.md"
    if agents_path.exists():
        return
    template = Path(__file__).parents[2] / "templates" / "AGENTS.md"
    if template.exists():
        shutil.copy2(template, agents_path)
    else:
        agents_path.write_text(
            "# Agent Protocol\n\nRead `_research_context/START_HERE.md`.\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
