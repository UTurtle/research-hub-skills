#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_ROOT="${1:-$(pwd)}"
HUB_ROOT="${RESEARCH_HUB:-${WORKSPACE_ROOT}/.research_hub_local}"
WORKSPACE_ID="${RESEARCH_WORKSPACE_ID:-$(basename "${WORKSPACE_ROOT}")}"
HOST_ID="${RESEARCH_HOST_ID:-local}"

export PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}"

python -m research_hub.cli init \
  --workspace-root "${WORKSPACE_ROOT}" \
  --hub "${HUB_ROOT}" \
  --workspace-id "${WORKSPACE_ID}" \
  --host-id "${HOST_ID}"

python -m research_hub.cli publish \
  --workspace-root "${WORKSPACE_ROOT}" \
  --hub "${HUB_ROOT}" \
  --workspace-id "${WORKSPACE_ID}" \
  --host-id "${HOST_ID}"

python -m research_hub.cli pull-context \
  --workspace-root "${WORKSPACE_ROOT}" \
  --hub "${HUB_ROOT}" \
  --workspace-id "${WORKSPACE_ID}" \
  --host-id "${HOST_ID}"

echo "Research context installed at: ${WORKSPACE_ROOT}/_research_context"
echo "To refresh once:"
echo "  RESEARCH_HUB=\"${HUB_ROOT}\" RESEARCH_WORKSPACE_ID=\"${WORKSPACE_ID}\" bash ${REPO_ROOT}/scripts/install_workspace.sh \"${WORKSPACE_ROOT}\""
echo "To keep it updated in the foreground:"
echo "  PYTHONPATH=\"${REPO_ROOT}/src\" python -m research_hub.cli watch --workspace-root \"${WORKSPACE_ROOT}\" --hub \"${HUB_ROOT}\" --workspace-id \"${WORKSPACE_ID}\""
