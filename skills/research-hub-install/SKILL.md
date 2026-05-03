---
name: research-hub-install
description: Use when installing or refreshing research-hub-skills in a workspace, especially when the user needs to choose a NAS/shared hub path and workspace id before running the installer.
---

# research-hub-install

Purpose: install Research Hub into the current workspace with a lightweight
hub path, usually a NAS mount or local archive path.

Workflow:

1. Identify the workspace root. Use the current directory unless the user names
   another path.
2. Ensure this repo exists as `.research-hub-skills`. If missing, run
   `git clone https://github.com/UTurtle/research-hub-skills.git .research-hub-skills`
   or the repo's `install.sh` bootstrap.
3. Ask for `RESEARCH_HUB` when it is not already set. Prefer a mounted NAS or
   archive path, for example `/mnt/nas/research_hub`. If the user wants a local
   trial, use `<workspace>/.research_hub_local`.
4. Ask for `RESEARCH_WORKSPACE_ID` when it is not already set. Default to the
   workspace directory name.
5. Optionally ask for `RESEARCH_HOST_ID` only when the host name matters.
   Default to `local`.
6. Run:
   `RESEARCH_HUB=<hub> RESEARCH_WORKSPACE_ID=<id> bash .research-hub-skills/scripts/install_workspace.sh <workspace>`
7. Verify `<workspace>/_research_context/manifest.json` exists.
8. If this is a remote Linux workspace, tell the user the hub can later run
   `collect-index-ssh` against `<workspace>/_research_context`.

Do not copy raw research files into the hub. Generated index/context files are
projections; original workspace files remain authoritative.
