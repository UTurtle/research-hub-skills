#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${1:-https://github.com/UTurtle/research-hub-skills.git}"
TARGET_DIR="${2:-.research-hub-skills}"

if [ -d "${TARGET_DIR}/.git" ]; then
  git -C "${TARGET_DIR}" fetch --all --prune
  git -C "${TARGET_DIR}" pull --ff-only
else
  git clone "${REPO_URL}" "${TARGET_DIR}"
fi

echo "Fetched research hub skills into ${TARGET_DIR}"
