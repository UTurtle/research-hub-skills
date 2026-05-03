#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-${HOME}/.codex}"
TARGET_DIR="${CODEX_HOME}/skills"

if [ -z "${CODEX_HOME}" ] || [ "${CODEX_HOME}" = "/" ]; then
  echo "Refusing unsafe CODEX_HOME: ${CODEX_HOME}" >&2
  exit 1
fi

mkdir -p "${TARGET_DIR}"

for skill_dir in "${REPO_ROOT}/skills"/*; do
  [ -d "${skill_dir}" ] || continue
  name="$(basename "${skill_dir}")"
  target="${TARGET_DIR}/${name}"
  case "${target}" in
    "${TARGET_DIR}/"*) ;;
    *) echo "Refusing unsafe skill target: ${target}" >&2; exit 1 ;;
  esac
  rm -rf "${target}"
  cp -R "${skill_dir}" "${target}"
  echo "Installed skill: ${name}"
done

echo "Installed Research Hub skills into ${TARGET_DIR}"
