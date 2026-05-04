"""Command line interface for research-hub."""

from __future__ import annotations

import argparse
import os
import shutil
import time
from pathlib import Path
from typing import Sequence

from research_hub.context import (
    copy_index_to_context,
    copy_tree,
    write_default_context,
)
from research_hub.collector import (
    collect_index,
    collect_index_ssh,
    load_collection_status,
    write_collection_status,
)
from research_hub.dispatch import approve_proposal, create_dispatch_proposal
from research_hub.git_sync import sync_pull, sync_push
from research_hub.indexer import (
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_EXCLUDE_EXTENSIONS,
    DEFAULT_INCLUDE_EXTENSIONS,
    IndexConfig,
    build_index,
    iter_indexable_files,
)
from research_hub.intake import create_intake_item
from research_hub.panel import build_hub_panel, build_panel
from research_hub.registry import (
    WorkspaceRecord,
    add_workspace,
    default_registry,
    load_registry,
    registry_path,
    save_registry,
)
from research_hub.web import run_web


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="research-hub")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (
        "init", "publish", "pull-context", "open", "sync-push",
        "sync-pull", "watch",
    ):
        sub_parser = subparsers.add_parser(command)
        add_common_args(sub_parser)
        if command == "watch":
            sub_parser.add_argument("--interval", type=float, default=30.0)
            sub_parser.add_argument("--once", action="store_true")
            sub_parser.add_argument("--max-cycles", type=int, default=0)
    add_registry_parsers(subparsers)
    add_intake_parsers(subparsers)
    add_dispatch_parsers(subparsers)
    add_hub_panel_parser(subparsers)
    add_web_parser(subparsers)
    add_collect_parsers(subparsers)
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
                transport=args.transport,
                ssh_host=args.ssh_host,
                ssh_user=args.ssh_user,
                remote_inbox=args.remote_inbox,
                hub_ssh_host=args.hub_ssh_host,
                hub_ssh_user=args.hub_ssh_user,
                hub_ssh_root=args.hub_ssh_root,
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
            execute_transport=args.execute_transport,
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
    if args.command == "web":
        run_web(
            hub_root=Path(args.hub).resolve(),
            host=args.host,
            port=args.port,
            token=args.token,
        )
        return
    if args.command == "collect-index":
        result = collect_index(
            hub_root=Path(args.hub).resolve(),
            workspace_id=args.workspace_id,
            source_context=Path(args.source_context).resolve(),
            force=args.force,
        )
        state = "copied" if result.get("changed") else "skipped"
        copied_count = len(result.get("copied_files", []))
        print(f"{state}\t{copied_count} files\t{result['target_dir']}")
        return
    if args.command == "collect-index-ssh":
        result = collect_index_ssh(
            hub_root=Path(args.hub).resolve(),
            workspace_id=args.workspace_id,
            ssh_host=args.ssh_host,
            ssh_user=args.ssh_user,
            remote_context=args.remote_context,
            force=args.force,
            execute=args.execute_transport,
        )
        if result.get("dry_run"):
            print(f"dry-run\t{result['target_dir']}")
            for command in result.get("commands", []):
                print(" ".join(command))
        else:
            state = "copied" if result.get("changed") else "skipped"
            copied_count = len(result.get("copied_files", []))
            print(f"{state}\t{copied_count} files\t{result['target_dir']}")
        return
    if args.command == "refresh-hub":
        results = refresh_hub_from_registry(
            hub_root=Path(args.hub).resolve(),
            force=args.force,
            execute_transport=args.execute_transport,
        )
        for result in results:
            workspace_id = result.get("workspace_id", "unknown")
            if result.get("error"):
                print(f"error\t{workspace_id}\t{result['error']}")
                continue
            if result.get("dry_run"):
                print(f"dry-run\t{workspace_id}\t{result['target_dir']}")
                continue
            state = "copied" if result.get("changed") else "skipped"
            copied_count = len(result.get("copied_files", []))
            print(f"{state}\t{workspace_id}\t{copied_count} files")
        return
    if args.command == "index-status":
        status = load_collection_status(Path(args.hub).resolve())
        for workspace in status.get("workspaces", []):
            print(
                f"{workspace['workspace_id']}\t"
                f"{workspace.get('documents', 0)} docs\t"
                f"{workspace.get('created_at', '')}\t"
                f"{workspace.get('root_hash', '')[:12]}"
            )
        return
    workspace_root = Path(args.workspace_root).resolve()
    hub_root = Path(args.hub).resolve()
    index_dir = hub_root / "index" / args.workspace_id
    context_dir = workspace_root / "_research_context"
    hub_context_dir = hub_root / "contexts" / args.workspace_id
    panel_dir = hub_root / "panel"
    if args.command == "init":
        run_init(
            workspace_root,
            context_dir,
            hub_root=hub_root,
            workspace_id=args.workspace_id,
        )
        return
    if args.command == "publish":
        run_publish(
            workspace_root=workspace_root,
            workspace_id=args.workspace_id,
            host_id=args.host_id,
            profile=args.profile,
            index_dir=index_dir,
            hub_context_dir=hub_context_dir,
            context_dir=context_dir,
            panel_dir=panel_dir,
        )
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
    if args.command == "watch":
        run_watch(
            workspace_root=workspace_root,
            workspace_id=args.workspace_id,
            host_id=args.host_id,
            profile=args.profile,
            index_dir=index_dir,
            hub_context_dir=hub_context_dir,
            context_dir=context_dir,
            panel_dir=panel_dir,
            interval=args.interval,
            once=args.once,
            max_cycles=args.max_cycles,
        )
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
    registry_add.add_argument(
        "--transport",
        choices=("local_path", "ssh"),
        default="local_path",
    )
    registry_add.add_argument("--ssh-host", default="")
    registry_add.add_argument("--ssh-user", default="")
    registry_add.add_argument("--remote-inbox", default="")
    registry_add.add_argument("--hub-ssh-host", default="")
    registry_add.add_argument("--hub-ssh-user", default="")
    registry_add.add_argument("--hub-ssh-root", default="")


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
    dispatch_approve.add_argument("--execute-transport", action="store_true")


def add_hub_panel_parser(subparsers: argparse._SubParsersAction) -> None:
    hub_panel = subparsers.add_parser("hub-panel")
    hub_panel.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )


def add_web_parser(subparsers: argparse._SubParsersAction) -> None:
    web = subparsers.add_parser("web")
    web.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8787)
    web.add_argument("--token", default=os.environ.get("RESEARCH_HUB_TOKEN", ""))


def add_collect_parsers(subparsers: argparse._SubParsersAction) -> None:
    collect = subparsers.add_parser("collect-index")
    collect.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )
    collect.add_argument("--workspace-id", required=True)
    collect.add_argument("--source-context", required=True)
    collect.add_argument("--force", action="store_true")
    collect_ssh = subparsers.add_parser("collect-index-ssh")
    collect_ssh.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )
    collect_ssh.add_argument("--workspace-id", required=True)
    collect_ssh.add_argument("--ssh-host", required=True)
    collect_ssh.add_argument("--ssh-user", default="")
    collect_ssh.add_argument("--remote-context", required=True)
    collect_ssh.add_argument("--force", action="store_true")
    collect_ssh.add_argument("--execute-transport", action="store_true")
    status = subparsers.add_parser("index-status")
    status.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )
    refresh = subparsers.add_parser("refresh-hub")
    refresh.add_argument(
        "--hub",
        default=os.environ.get("RESEARCH_HUB", ".research_hub_local"),
    )
    refresh.add_argument("--force", action="store_true")
    refresh.add_argument("--execute-transport", action="store_true")


def make_index_config(
    workspace_root: Path,
    workspace_id: str,
    host_id: str,
    index_dir: Path,
    profile: str,
) -> IndexConfig:
    max_file_bytes_env = os.environ.get("RESEARCH_HUB_MAX_FILE_BYTES", "200000")
    max_file_bytes = (
        None
        if max_file_bytes_env.lower() in {"", "none", "0"}
        else int(max_file_bytes_env)
    )
    return IndexConfig(
        workspace_root=workspace_root,
        workspace_id=workspace_id,
        host_id=host_id,
        out_dir=index_dir,
        include_extensions=set(DEFAULT_INCLUDE_EXTENSIONS),
        exclude_dirs=set(DEFAULT_EXCLUDE_DIRS),
        exclude_extensions=set(DEFAULT_EXCLUDE_EXTENSIONS),
        max_file_bytes=max_file_bytes,
        profile=profile,
    )


def run_init(
    workspace_root: Path,
    context_dir: Path,
    hub_root: Path | None = None,
    workspace_id: str | None = None,
) -> None:
    workspace_root.mkdir(parents=True, exist_ok=True)
    write_default_context(context_dir)
    write_research_hub_marker(workspace_root, hub_root, workspace_id)
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


def write_research_hub_marker(
    workspace_root: Path,
    hub_root: Path | None,
    workspace_id: str | None,
) -> None:
    marker_path = workspace_root / "RESEARCH_HUB.md"
    if marker_path.exists():
        return
    template = Path(__file__).parents[2] / "templates" / "RESEARCH_HUB.md"
    if template.exists():
        content = template.read_text(encoding="utf-8")
    else:
        content = "# Research Hub Workspace\n"
    if hub_root is not None:
        content += f"\nDetected hub path: `{hub_root}`\n"
    if workspace_id is not None:
        content += f"\nDetected workspace id: `{workspace_id}`\n"
    marker_path.write_text(content, encoding="utf-8")


def run_publish(
    workspace_root: Path,
    workspace_id: str,
    host_id: str,
    profile: str,
    index_dir: Path,
    hub_context_dir: Path,
    context_dir: Path,
    panel_dir: Path,
) -> None:
    config = make_index_config(
        workspace_root, workspace_id, host_id, index_dir, profile
    )
    build_index(config)
    write_default_context(hub_context_dir)
    copy_index_to_context(index_dir, hub_context_dir)
    copy_tree(hub_context_dir, context_dir)
    build_panel(hub_context_dir, panel_dir)


def workspace_signature(
    workspace_root: Path,
    workspace_id: str,
    host_id: str,
    profile: str,
) -> tuple[tuple[str, int, int], ...]:
    config = make_index_config(
        workspace_root,
        workspace_id,
        host_id,
        workspace_root / "_research_context" / ".watch_tmp",
        profile,
    )
    signature: list[tuple[str, int, int]] = []
    for path in iter_indexable_files(config):
        stat = path.stat()
        signature.append((
            path.relative_to(workspace_root).as_posix(),
            stat.st_size,
            stat.st_mtime_ns,
        ))
    return tuple(sorted(signature))


def run_watch(
    workspace_root: Path,
    workspace_id: str,
    host_id: str,
    profile: str,
    index_dir: Path,
    hub_context_dir: Path,
    context_dir: Path,
    panel_dir: Path,
    interval: float,
    once: bool,
    max_cycles: int,
) -> None:
    previous: tuple[tuple[str, int, int], ...] | None = None
    cycles = 0
    while True:
        current = workspace_signature(workspace_root, workspace_id, host_id, profile)
        if current != previous:
            run_publish(
                workspace_root=workspace_root,
                workspace_id=workspace_id,
                host_id=host_id,
                profile=profile,
                index_dir=index_dir,
                hub_context_dir=hub_context_dir,
                context_dir=context_dir,
                panel_dir=panel_dir,
            )
            print(f"published\t{workspace_id}\t{len(current)} files")
            previous = current
        else:
            print(f"unchanged\t{workspace_id}\t{len(current)} files")
        cycles += 1
        if once or (max_cycles and cycles >= max_cycles):
            return
        time.sleep(interval)


def refresh_hub_from_registry(
    hub_root: Path,
    force: bool = False,
    execute_transport: bool = False,
) -> list[dict[str, object]]:
    registry = load_registry(hub_root)
    results: list[dict[str, object]] = []
    for record in registry.get("workspaces", []):
        workspace_id = str(record.get("workspace_id", ""))
        if not workspace_id:
            continue
        transport = str(record.get("transport") or "local_path")
        root_hint = str(record.get("root_hint") or "")
        try:
            if transport == "local_path":
                if not root_hint:
                    raise ValueError("missing root_hint")
                result = collect_index(
                    hub_root,
                    workspace_id,
                    Path(root_hint) / "_research_context",
                    force=force,
                )
            elif transport == "ssh":
                ssh_host = str(record.get("ssh_host") or "")
                if not ssh_host:
                    raise ValueError("missing ssh_host")
                remote_context = str(
                    record.get("remote_context")
                    or f"{root_hint.rstrip('/')}/_research_context"
                )
                result = collect_index_ssh(
                    hub_root=hub_root,
                    workspace_id=workspace_id,
                    ssh_host=ssh_host,
                    ssh_user=str(record.get("ssh_user") or ""),
                    remote_context=remote_context,
                    force=force,
                    execute=execute_transport,
                )
            else:
                raise ValueError(f"unsupported transport: {transport}")
            results.append(result)
        except Exception as exc:  # keep refreshing other registered workspaces
            results.append({
                "workspace_id": workspace_id,
                "error": str(exc),
                "transport": transport,
            })
    write_collection_status(hub_root)
    return results


if __name__ == "__main__":
    main()
