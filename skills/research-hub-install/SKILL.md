---
name: research-hub-install
description: Install, set up, bootstrap, connect, or refresh the UTurtle/research-hub-skills repo in a workspace. Use when the user says to install this repo/skill, connect the current workspace to Research Hub, set up a NAS/shared hub path, or run the Research Hub installer, even if they do not name this skill explicitly.
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
6. If the user only said "install this repo/skill", still ask the missing
   `RESEARCH_HUB` and `RESEARCH_WORKSPACE_ID` questions before connecting the
   workspace.
7. Run:
   `RESEARCH_HUB=<hub> RESEARCH_WORKSPACE_ID=<id> bash .research-hub-skills/scripts/install_workspace.sh <workspace>`
8. Verify `<workspace>/_research_context/manifest.json` exists.
9. If this is a remote Linux workspace, tell the user the hub can later run
   `collect-index-ssh` against `<workspace>/_research_context`.

Do not copy raw research files into the hub. Generated index/context files are
projections; original workspace files remain authoritative.
