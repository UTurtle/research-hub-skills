#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${RESEARCH_HUB_SKILLS_REPO:-https://github.com/UTurtle/research-hub-skills.git}"
TARGET_DIR="${RESEARCH_HUB_SKILLS_DIR:-.research-hub-skills}"
BRANCH="${RESEARCH_HUB_SKILLS_BRANCH:-}"
WORKSPACE_ROOT="${1:-$(pwd)}"

prompt_tty() {
  prompt="$1"
  default="$2"
  if [ -r /dev/tty ]; then
    printf "%s [%s]: " "${prompt}" "${default}" > /dev/tty
    IFS= read -r answer < /dev/tty || answer=""
    if [ -n "${answer}" ]; then
      printf "%s" "${answer}"
    else
      printf "%s" "${default}"
    fi
  else
    printf "%s" "${default}"
  fi
}

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

if [ -z "${INSTALL_RESEARCH_HUB_WORKSPACE:-}" ] && [ -r /dev/tty ]; then
  connect_now="$(prompt_tty "Connect this workspace to Research Hub now? y/n" "y")"
  case "${connect_now}" in
    y|Y|yes|YES) INSTALL_RESEARCH_HUB_WORKSPACE=1 ;;
    *) INSTALL_RESEARCH_HUB_WORKSPACE=0 ;;
  esac
fi

if [ "${INSTALL_RESEARCH_HUB_WORKSPACE:-0}" = "1" ]; then
  export RESEARCH_HUB="${RESEARCH_HUB:-$(prompt_tty "RESEARCH_HUB NAS/archive path" "${WORKSPACE_ROOT}/.research_hub_local")}"
  export RESEARCH_WORKSPACE_ID="${RESEARCH_WORKSPACE_ID:-$(prompt_tty "RESEARCH_WORKSPACE_ID" "$(basename "${WORKSPACE_ROOT}")")}"
  bash "${TARGET_DIR}/scripts/install_workspace.sh" "${WORKSPACE_ROOT}"
else
  cat <<EOF
Codex skills installed.

Next, tell Codex: "install this repo and connect this workspace".
The installed research-hub-install skill should ask for:
- RESEARCH_HUB, for example /mnt/nas/research_hub
- RESEARCH_WORKSPACE_ID, for example B or dcase2026

To install this workspace without Codex prompts:
  RESEARCH_HUB=/mnt/nas/research_hub RESEARCH_WORKSPACE_ID=$(basename "${WORKSPACE_ROOT}") bash ${TARGET_DIR}/scripts/install_workspace.sh "${WORKSPACE_ROOT}"
EOF
fi
