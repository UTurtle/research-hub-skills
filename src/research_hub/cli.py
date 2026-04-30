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
from research_hub.dispatch import approve_proposal, create_dispatch_proposal
from research_hub.git_sync import sync_pull, sync_push
from research_hub.indexer import (
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_EXCLUDE_EXTENSIONS,
    DEFAULT_INCLUDE_EXTENSIONS,
    IndexConfig,
    build_index,
)
from research_hub.intake import create_intake_item
from research_hub.panel import build_hub_panel, build_panel
from research_hub.registry import (
    WorkspaceRecord,
    add_workspace,
    default_registry,
    registry_path,
    save_registry,
)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="research-hub")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (
        "init", "publish", "pull-context", "open", "sync-push",
        "sync-pull",
    ):
        sub_parser = subparsers.add_parser(command)
        add_common_args(sub_parser)
    add_registry_parsers(subparsers)
    add_intake_parsers(subparsers)
    add_dispatch_parsers(subparsers)
    add_hub_panel_parser(subparsers)
    args = parser.parse_args(argv)
    if args.command == "registry-init":
        hub_root = Path(args.hub).resolve()
        save_registry(hub_root, default_registry())
        print(registry_path(hub_root))
        return
    if args.command == "registry-add":
        hub_root = Path(args.hub).resolve()
        add_workspace(
            hub_root,
            WorkspaceRecord(
                workspace_id=args.workspace_id,
                machine_role=args.machine_role,
                storage_role=args.storage_role,
                root_hint=args.root_hint,
                tailnet_hint=args.tailnet_hint,
                inbox_path=args.inbox_path,
                can_store_library_blobs=args.can_store_library_blobs,
                can_run_training=args.can_run_training,
                capabilities=args.capability,
            ),
        )
        print(registry_path(hub_root))
        return
    if args.command == "intake-add":
        item = create_intake_item(
            hub_root=Path(args.hub).resolve(),
            source_path=Path(args.source_path).resolve(),
            title=args.title,
            kind=args.kind,
            source_label=args.source_label,
        )
        print(item["item_id"])
        return
    if args.command == "dispatch-propose":
        proposal = create_dispatch_proposal(
            Path(args.hub).resolve(),
            args.item_id,
        )
        print(proposal["proposal_id"])
        return
    if args.command == "dispatch-approve":
        requests = approve_proposal(
            Path(args.hub).resolve(),
            args.proposal_id,
            args.workspace_id,
        )
        for request in requests:
            print(request["request_id"])
        return
    if args.command == "hub-panel":
        hub_root = Path(args.hub).resolve()
        panel_dir = hub_root / "panel"
        build_hub_panel(hub_root, panel_dir)
        print(panel_dir / "index.html")
        return
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


def add_registry_parsers(subparsers: argparse._SubParsersAction) -> None:
    registry_init = subparsers.add_parser("registry-init")
    registry_init.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )
    registry_add = subparsers.add_parser("registry-add")
    registry_add.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )
    registry_add.add_argument("--workspace-id", required=True)
    registry_add.add_argument("--machine-role", required=True)
    registry_add.add_argument(
        "--storage-role",
        choices=("archive_hdd", "research_ssd", "scratch"),
        required=True,
    )
    registry_add.add_argument("--root-hint", required=True)
    registry_add.add_argument("--tailnet-hint", default="")
    registry_add.add_argument("--inbox-path", required=True)
    registry_add.add_argument("--can-store-library-blobs", action="store_true")
    registry_add.add_argument("--can-run-training", action="store_true")
    registry_add.add_argument("--capability", action="append", default=[])


def add_intake_parsers(subparsers: argparse._SubParsersAction) -> None:
    intake_add = subparsers.add_parser("intake-add")
    intake_add.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )
    intake_add.add_argument("--source-path", required=True)
    intake_add.add_argument("--title", required=True)
    intake_add.add_argument("--kind", default="user_upload")
    intake_add.add_argument("--source-label", default="user_upload")


def add_dispatch_parsers(subparsers: argparse._SubParsersAction) -> None:
    dispatch_propose = subparsers.add_parser("dispatch-propose")
    dispatch_propose.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )
    dispatch_propose.add_argument("--item-id", required=True)
    dispatch_approve = subparsers.add_parser("dispatch-approve")
    dispatch_approve.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )
    dispatch_approve.add_argument("--proposal-id", required=True)
    dispatch_approve.add_argument("--workspace-id", action="append", required=True)


def add_hub_panel_parser(subparsers: argparse._SubParsersAction) -> None:
    hub_panel = subparsers.add_parser("hub-panel")
    hub_panel.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
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
