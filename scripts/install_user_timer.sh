#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_ROOT="${1:-$(pwd)}"
HUB_ROOT="${RESEARCH_HUB:-${WORKSPACE_ROOT}/.research_hub_local}"
WORKSPACE_ID="${RESEARCH_WORKSPACE_ID:-$(basename "${WORKSPACE_ROOT}")}"
HOST_ID="${RESEARCH_HOST_ID:-local}"
PROFILE="${RESEARCH_PROFILE:-generic}"
INTERVAL="${RESEARCH_HUB_TIMER_INTERVAL:-daily}"
UNIT_SAFE="$(printf "%s" "${WORKSPACE_ID}" | tr -c 'A-Za-z0-9_' '-')"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
SERVICE_NAME="research-hub-${UNIT_SAFE}.service"
TIMER_NAME="research-hub-${UNIT_SAFE}.timer"

mkdir -p "${SYSTEMD_USER_DIR}"

cat > "${SYSTEMD_USER_DIR}/${SERVICE_NAME}" <<EOF
[Unit]
Description=Research Hub publish for ${WORKSPACE_ID}

[Service]
Type=oneshot
WorkingDirectory=${WORKSPACE_ROOT}
Environment=PYTHONPATH=${REPO_ROOT}/src
Environment=RESEARCH_HUB=${HUB_ROOT}
Environment=RESEARCH_WORKSPACE_ID=${WORKSPACE_ID}
Environment=RESEARCH_HOST_ID=${HOST_ID}
Environment=RESEARCH_PROFILE=${PROFILE}
ExecStart=python -m research_hub.cli publish --workspace-root ${WORKSPACE_ROOT} --hub ${HUB_ROOT} --workspace-id ${WORKSPACE_ID} --host-id ${HOST_ID} --profile ${PROFILE}
EOF

cat > "${SYSTEMD_USER_DIR}/${TIMER_NAME}" <<EOF
[Unit]
Description=Run Research Hub publish for ${WORKSPACE_ID} on schedule

[Timer]
OnCalendar=${INTERVAL}
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now "${TIMER_NAME}"

echo "Installed user timer: ${TIMER_NAME}"
echo "Check status with: systemctl --user status ${TIMER_NAME}"
