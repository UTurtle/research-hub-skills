"""Git-backed hub synchronization."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(hub: Path, args: list[str]) -> None:
    if not (hub / ".git").exists():
        raise RuntimeError(f"Hub is not a Git repository: {hub}")
    subprocess.run(["git", "-C", str(hub), *args], check=True)


def sync_push(hub: Path, message: str) -> None:
    run_git(hub, ["add", "."])
    result = subprocess.run(
        ["git", "-C", str(hub), "diff", "--cached", "--quiet"],
        check=False,
    )
    if result.returncode == 0:
        return
    run_git(hub, ["commit", "-m", message])
    run_git(hub, ["push"])


def sync_pull(hub: Path) -> None:
    run_git(hub, ["pull", "--ff-only"])
