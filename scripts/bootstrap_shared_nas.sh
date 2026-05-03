#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
REPO_URL="${RESEARCH_HUB_SKILLS_REPO:-https://github.com/UTurtle/research-hub-skills.git}"
TARGET_DIR="${RESEARCH_HUB_SKILLS_DIR:-.research-hub-skills}"
EXECUTE=0
INSTALL_TIMERS=1

for arg in "$@"; do
  case "${arg}" in
    --execute) EXECUTE=1 ;;
    --no-timers) INSTALL_TIMERS=0 ;;
    *) echo "Unknown argument: ${arg}" >&2; exit 2 ;;
  esac
done

prompt() {
  label="$1"
  default="$2"
  printf "%s [%s]: " "${label}" "${default}" > /dev/tty
  IFS= read -r answer < /dev/tty || answer=""
  if [ -n "${answer}" ]; then
    printf "%s" "${answer}"
  else
    printf "%s" "${default}"
  fi
}

confirm() {
  label="$1"
  default="$2"
  answer="$(prompt "${label} y/n" "${default}")"
  case "${answer}" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

run_or_print() {
  if [ "${EXECUTE}" = "1" ]; then
    "$@"
  else
    printf "DRY-RUN:"
    printf " %q" "$@"
    printf "\n"
  fi
}

run_shell_or_print() {
  command="$1"
  if [ "${EXECUTE}" = "1" ]; then
    bash -lc "${command}"
  else
    printf "DRY-RUN: bash -lc %q\n" "${command}"
  fi
}

ssh_shell_or_print() {
  remote="$1"
  command="$2"
  if [ "${EXECUTE}" = "1" ]; then
    ssh "${remote}" "bash -lc $(printf "%q" "${command}")"
  else
    printf "DRY-RUN: ssh %q bash -lc %q\n" "${remote}" "${command}"
  fi
}

if [ ! -r /dev/tty ]; then
  echo "Interactive terminal required. Re-run from A with a TTY." >&2
  exit 2
fi

echo "Research Hub shared NAS bootstrap"
echo "Default mode is dry-run. Re-run with --execute after reviewing commands."

HUB_ROOT="$(prompt "Shared NAS hub path visible from A/B/C" "${RESEARCH_HUB:-/mnt/nas/research_hub}")"
USE_TAILSCALE=0
if confirm "Use Tailscale hostnames/IPs for SSH" "y"; then
  USE_TAILSCALE=1
fi
LOCAL_ID="$(prompt "Local workspace id" "${RESEARCH_WORKSPACE_ID:-A}")"
LOCAL_ROOT="$(prompt "Local workspace root on A" "$(pwd)")"
LOCAL_MACHINE_ROLE="$(prompt "Local machine role" "3090")"
LOCAL_STORAGE_ROLE="$(prompt "Local storage role archive_hdd/research_ssd/scratch" "archive_hdd")"
LOCAL_INBOX="$(prompt "Local inbox path" "${HUB_ROOT}/inbox/${LOCAL_ID}")"

run_or_print mkdir -p "${HUB_ROOT}"
run_shell_or_print "if [ ! -f '${HUB_ROOT}/registry/workspaces.json' ]; then PYTHONPATH='${REPO_ROOT}/src' python -m research_hub.cli registry-init --hub '${HUB_ROOT}'; fi"
run_shell_or_print "PYTHONPATH='${REPO_ROOT}/src' python -m research_hub.cli registry-add --hub '${HUB_ROOT}' --workspace-id '${LOCAL_ID}' --machine-role '${LOCAL_MACHINE_ROLE}' --storage-role '${LOCAL_STORAGE_ROLE}' --root-hint '${LOCAL_ROOT}' --tailnet-hint 'local' --inbox-path '${LOCAL_INBOX}' --can-store-library-blobs --can-run-training --capability local --capability shared_nas"
run_shell_or_print "RESEARCH_HUB='${HUB_ROOT}' RESEARCH_WORKSPACE_ID='${LOCAL_ID}' bash '${REPO_ROOT}/scripts/install_workspace.sh' '${LOCAL_ROOT}'"
if [ "${INSTALL_TIMERS}" = "1" ]; then
  run_shell_or_print "RESEARCH_HUB='${HUB_ROOT}' RESEARCH_WORKSPACE_ID='${LOCAL_ID}' bash '${REPO_ROOT}/scripts/install_user_timer.sh' '${LOCAL_ROOT}'"
fi

while confirm "Add a remote workspace" "y"; do
  REMOTE_ID="$(prompt "Remote workspace id" "B")"
  if [ "${USE_TAILSCALE}" = "1" ]; then
    REMOTE_SSH="$(prompt "Remote SSH target, Tailscale DNS/IP is fine" "research@${REMOTE_ID}")"
    TAILNET_HINT="${REMOTE_SSH}"
  else
    REMOTE_SSH="$(prompt "Remote SSH target" "research@192.168.0.22")"
    TAILNET_HINT=""
  fi
  REMOTE_ROOT="$(prompt "Remote workspace root" "/mnt/ssd/${REMOTE_ID}")"
  REMOTE_MACHINE_ROLE="$(prompt "Remote machine role" "4080")"
  REMOTE_STORAGE_ROLE="$(prompt "Remote storage role archive_hdd/research_ssd/scratch" "research_ssd")"
  REMOTE_INBOX="$(prompt "Remote inbox path" "${HUB_ROOT}/inbox/${REMOTE_ID}")"
  REMOTE_CAPS="$(prompt "Remote capabilities comma-separated" "cuda,torch,shared_nas")"

remote_script="
set -euo pipefail
mkdir -p '${REMOTE_ROOT}'
cd '${REMOTE_ROOT}'
if [ -d '${TARGET_DIR}/.git' ]; then
  git -C '${TARGET_DIR}' fetch --all --prune
  git -C '${TARGET_DIR}' pull --ff-only
else
  git clone '${REPO_URL}' '${TARGET_DIR}'
fi
RESEARCH_HUB='${HUB_ROOT}' RESEARCH_WORKSPACE_ID='${REMOTE_ID}' bash '${TARGET_DIR}/scripts/install_workspace.sh' '${REMOTE_ROOT}'
"
  if [ "${INSTALL_TIMERS}" = "1" ]; then
    remote_script="${remote_script}
RESEARCH_HUB='${HUB_ROOT}' RESEARCH_WORKSPACE_ID='${REMOTE_ID}' bash '${TARGET_DIR}/scripts/install_user_timer.sh' '${REMOTE_ROOT}'
"
  fi
  ssh_shell_or_print "${REMOTE_SSH}" "${remote_script}"

  IFS=',' read -r -a cap_array <<< "${REMOTE_CAPS}"
  cap_args=""
  for cap in "${cap_array[@]}"; do
    cap="$(printf "%s" "${cap}" | xargs)"
    [ -n "${cap}" ] || continue
    cap_args="${cap_args} --capability '${cap}'"
  done
  ssh_user="${REMOTE_SSH%@*}"
  ssh_host="${REMOTE_SSH#*@}"
  if [ "${ssh_user}" = "${REMOTE_SSH}" ]; then
    ssh_user=""
    ssh_host="${REMOTE_SSH}"
  fi
  run_shell_or_print "PYTHONPATH='${REPO_ROOT}/src' python -m research_hub.cli registry-add --hub '${HUB_ROOT}' --workspace-id '${REMOTE_ID}' --machine-role '${REMOTE_MACHINE_ROLE}' --storage-role '${REMOTE_STORAGE_ROLE}' --root-hint '${REMOTE_ROOT}' --tailnet-hint '${TAILNET_HINT}' --inbox-path '${REMOTE_INBOX}' --transport local_path --ssh-host '${ssh_host}' --ssh-user '${ssh_user}' --can-run-training${cap_args}"
done

run_shell_or_print "PYTHONPATH='${REPO_ROOT}/src' python -m research_hub.cli refresh-hub --hub '${HUB_ROOT}'"
run_shell_or_print "PYTHONPATH='${REPO_ROOT}/src' python -m research_hub.cli index-status --hub '${HUB_ROOT}'"

echo "Bootstrap plan complete."
if [ "${EXECUTE}" != "1" ]; then
  echo "Review the dry-run, then re-run with --execute."
fi
