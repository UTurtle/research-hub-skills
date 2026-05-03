#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${RESEARCH_HUB_SKILLS_REPO:-https://github.com/UTurtle/research-hub-skills.git}"
TARGET_DIR="${RESEARCH_HUB_SKILLS_DIR:-.research-hub-skills}"
BRANCH="${RESEARCH_HUB_SKILLS_BRANCH:-}"
WORKSPACE_ROOT="${1:-$(pwd)}"

if [ -d "${TARGET_DIR}/.git" ]; then
  git -C "${TARGET_DIR}" fetch --all --prune
  if [ -n "${BRANCH}" ]; then
    git -C "${TARGET_DIR}" checkout "${BRANCH}"
  fi
  git -C "${TARGET_DIR}" pull --ff-only
else
  if [ -n "${BRANCH}" ]; then
    git clone --branch "${BRANCH}" "${REPO_URL}" "${TARGET_DIR}"
  else
    git clone "${REPO_URL}" "${TARGET_DIR}"
  fi
fi

bash "${TARGET_DIR}/scripts/install_codex_skills.sh"

if [ "${INSTALL_RESEARCH_HUB_WORKSPACE:-0}" = "1" ]; then
  bash "${TARGET_DIR}/scripts/install_workspace.sh" "${WORKSPACE_ROOT}"
else
  cat <<EOF
Codex skills installed.

Next, ask Codex to use the research-hub-install skill in this workspace.
It should ask for:
- RESEARCH_HUB, for example /mnt/nas/research_hub
- RESEARCH_WORKSPACE_ID, for example B or dcase2026

To install this workspace without Codex prompts:
  RESEARCH_HUB=/mnt/nas/research_hub RESEARCH_WORKSPACE_ID=$(basename "${WORKSPACE_ROOT}") bash ${TARGET_DIR}/scripts/install_workspace.sh "${WORKSPACE_ROOT}"
EOF
fi
