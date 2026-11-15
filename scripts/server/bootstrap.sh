#!/usr/bin/env bash
# Trend Detective — one-time Azure VM bootstrap.
#
# Prepares an Ubuntu host to run the application with Docker Compose.
# Safe to re-run: every step checks state before changing anything.
#
#   sudo ./bootstrap.sh
#
# It does NOT deploy the application, does NOT touch SSH configuration and does
# NOT modify firewall or Azure NSG rules.
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/trend-detective}"
APP_USER="${APP_USER:-azureuser}"
MARKER_DIR="/var/lib/trend-detective"
MARKER_FILE="${MARKER_DIR}/bootstrap.version"
BOOTSTRAP_VERSION="1"

log()  { printf '\033[1;34m[bootstrap]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[fail]\033[0m %s\n' "$*" >&2; exit 1; }

FAILED_TASKS=()
COMPLETED_TASKS=()

run_step() {
  local name="$1"; shift
  if "$@"; then
    COMPLETED_TASKS+=("$name")
  else
    FAILED_TASKS+=("$name")
    warn "step failed: $name"
  fi
}

# ---------------------------------------------------------------- A. system ---
require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    fail "run as root (sudo ./bootstrap.sh)"
  fi
}

detect_system() {
  [[ -r /etc/os-release ]] || fail "/etc/os-release not found; unsupported host"
  # shellcheck disable=SC1091
  . /etc/os-release
  OS_ID="${ID:-unknown}"
  OS_VERSION="${VERSION_ID:-unknown}"
  OS_PRETTY="${PRETTY_NAME:-unknown}"
  ARCH="$(uname -m)"

  log "OS: ${OS_PRETTY} (id=${OS_ID} version=${OS_VERSION} arch=${ARCH})"

  if [[ "${OS_ID}" != "ubuntu" ]]; then
    warn "this script targets Ubuntu; detected '${OS_ID}'. Docker install will be skipped."
    return 1
  fi
  case "${OS_VERSION}" in
    22.04|24.04) : ;;
    *) warn "untested Ubuntu version '${OS_VERSION}'; continuing carefully" ;;
  esac

  log "CPU cores: $(nproc)"
  log "Memory: $(free -h | awk '/^Mem:/{print $2}') total, $(free -h | awk '/^Mem:/{print $7}') available"
  log "Disk (/): $(df -h / | awk 'NR==2{print $2" total, "$4" free"}')"
  log "Inodes (/): $(df -i / | awk 'NR==2{print $2" total, "$4" free"}')"
  return 0
}

# ------------------------------------------------------------ B. packages ----
install_base_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends \
    ca-certificates curl gnupg lsb-release tar gzip jq
}

# -------------------------------------------------------------- C. docker ----
install_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "docker and compose already installed; skipping installation"
    return 0
  fi

  install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.asc ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
  fi

  local codename
  codename="$(. /etc/os-release && echo "${VERSION_CODENAME}")"
  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
    "$(dpkg --print-architecture)" "${codename}" > /etc/apt/sources.list.d/docker.list

  apt-get update -qq
  apt-get install -y -qq --no-install-recommends \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

configure_docker_service() {
  systemctl enable --now docker
  systemctl is-active --quiet docker || return 1
  docker info >/dev/null 2>&1 || return 1
  return 0
}

# ------------------------------------------------------------- E. dirs -------
prepare_directories() {
  install -d -m 0755 "${APP_DIR}"
  install -d -m 0755 "${APP_DIR}/state" "${APP_DIR}/logs"
  install -d -m 0755 "${MARKER_DIR}"

  if id "${APP_USER}" >/dev/null 2>&1; then
    chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
  else
    warn "user '${APP_USER}' not found; leaving ownership as root"
  fi
}

# ------------------------------------------------------------- F. account ----
configure_deploy_user() {
  if ! id "${APP_USER}" >/dev/null 2>&1; then
    warn "user '${APP_USER}' does not exist; skipping group membership"
    return 1
  fi
  # Docker group membership is equivalent to root. Documented, not hidden.
  if id -nG "${APP_USER}" | tr ' ' '\n' | grep -qx docker; then
    log "${APP_USER} is already in the docker group"
  else
    usermod -aG docker "${APP_USER}"
    log "added ${APP_USER} to the docker group (re-login required to take effect)"
  fi
  return 0
}

# -------------------------------------------------------------- G. network ---
report_ports() {
  log "expected inbound ports: 22 (ssh), ${FRONTEND_PORT:-80} (frontend)"
  log "backend stays on 127.0.0.1:8000 and is never published publicly"
  if command -v ss >/dev/null 2>&1; then
    local busy
    busy="$(ss -ltnp 2>/dev/null | awk 'NR>1{print $4}' | grep -E ':(80|8000)$' || true)"
    [[ -n "${busy}" ]] && warn "ports already in use: ${busy}" || log "ports 80/8000 are free"
  fi
}

# -------------------------------------------------------------- I. verify -----
verify_installation() {
  local ok=0
  command -v docker >/dev/null 2>&1 && log "docker: $(docker --version)" || { warn "docker missing"; ok=1; }
  docker compose version >/dev/null 2>&1 && log "compose: $(docker compose version --short 2>/dev/null || echo present)" || { warn "compose plugin missing"; ok=1; }
  systemctl is-active --quiet docker && log "docker service: active" || { warn "docker service inactive"; ok=1; }
  [[ -d "${APP_DIR}" ]] || { warn "${APP_DIR} missing"; ok=1; }
  return "${ok}"
}

write_marker() {
  printf '%s\n' "${BOOTSTRAP_VERSION}" > "${MARKER_FILE}.tmp"
  mv "${MARKER_FILE}.tmp" "${MARKER_FILE}"
  chmod 0644 "${MARKER_FILE}"
  log "wrote ${MARKER_FILE} (version ${BOOTSTRAP_VERSION})"
}

# ------------------------------------------------------------------ main -----
main() {
  log "starting bootstrap (version ${BOOTSTRAP_VERSION})"
  require_root

  if [[ -f "${MARKER_FILE}" ]]; then
    log "existing bootstrap marker: $(cat "${MARKER_FILE}") — repairing as needed"
  fi

  run_step "detect-system" detect_system
  run_step "base-packages" install_base_packages
  run_step "install-docker" install_docker
  run_step "docker-service" configure_docker_service
  run_step "directories" prepare_directories
  run_step "deploy-user" configure_deploy_user
  run_step "ports" report_ports

  if verify_installation; then
    COMPLETED_TASKS+=("verify")
    write_marker
  else
    FAILED_TASKS+=("verify")
    warn "verification failed; marker NOT written"
  fi

  echo
  echo "==================== bootstrap summary ===================="
  echo "OS:            ${OS_PRETTY:-unknown}"
  echo "Docker:        $(docker --version 2>/dev/null || echo 'not installed')"
  echo "Compose:       $(docker compose version --short 2>/dev/null || echo 'not available')"
  echo "App directory: ${APP_DIR}"
  echo "Deploy user:   ${APP_USER}"
  echo "Disk free:     $(df -h / | awk 'NR==2{print $4}')"
  echo "Completed:     ${COMPLETED_TASKS[*]:-none}"
  echo "Failed:        ${FAILED_TASKS[*]:-none}"
  echo "==========================================================="

  if [[ ${#FAILED_TASKS[@]} -gt 0 ]]; then
    echo
    echo "Manual follow-up required for: ${FAILED_TASKS[*]}"
    echo "Re-run this script after fixing; it is idempotent."
    exit 1
  fi

  log "bootstrap complete; run verify.sh to confirm readiness"
}

main "$@"
