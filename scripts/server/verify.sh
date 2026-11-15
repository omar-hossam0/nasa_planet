#!/usr/bin/env bash
# Read-only readiness check for the Trend Detective host.
# Makes no changes. Exit 0 = ready to deploy.
#
#   ./verify.sh
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/trend-detective}"
APP_USER="${APP_USER:-azureuser}"
MARKER_FILE="${MARKER_FILE:-/var/lib/trend-detective/bootstrap.version}"
FRONTEND_PORT="${FRONTEND_PORT:-80}"

FAILURES=0
pass() { printf '  \033[1;32mok\033[0m   %s\n' "$*"; }
bad()  { printf '  \033[1;31mFAIL\033[0m %s\n' "$*"; FAILURES=$((FAILURES + 1)); }
info() { printf '  \033[1;34minfo\033[0m %s\n' "$*"; }

echo "Trend Detective — server readiness"
echo

echo "bootstrap"
if [[ -f "${MARKER_FILE}" ]]; then
  pass "marker present (version $(cat "${MARKER_FILE}"))"
else
  bad "marker missing at ${MARKER_FILE} — run bootstrap.sh"
fi

echo "docker"
if command -v docker >/dev/null 2>&1; then
  pass "docker $(docker --version | awk '{print $3}' | tr -d ',')"
else
  bad "docker not installed"
fi

if docker compose version >/dev/null 2>&1; then
  pass "compose $(docker compose version --short 2>/dev/null || echo present)"
else
  bad "docker compose plugin missing"
fi

if systemctl is-active --quiet docker 2>/dev/null; then
  pass "docker service active"
else
  bad "docker service not active"
fi

if docker info >/dev/null 2>&1; then
  pass "docker daemon reachable"
else
  bad "docker daemon not reachable by the current user"
fi

echo "directories"
for path in "${APP_DIR}" "${APP_DIR}/state" "${APP_DIR}/logs"; do
  if [[ -d "${path}" ]]; then
    pass "${path}"
  else
    bad "${path} missing"
  fi
done

echo "deploy user"
if id "${APP_USER}" >/dev/null 2>&1; then
  pass "user ${APP_USER} exists"
  if id -nG "${APP_USER}" | tr ' ' '\n' | grep -qx docker; then
    pass "${APP_USER} is in the docker group"
  else
    bad "${APP_USER} is not in the docker group"
  fi
else
  info "user ${APP_USER} not found (deployment must run as another docker-enabled user)"
fi

echo "network"
if command -v ss >/dev/null 2>&1; then
  if ss -ltn 2>/dev/null | awk 'NR>1{print $4}' | grep -qE ":${FRONTEND_PORT}\$"; then
    info "port ${FRONTEND_PORT} already bound (a release may be running)"
  else
    pass "port ${FRONTEND_PORT} free"
  fi
else
  info "ss not available; skipped port check"
fi

echo "resources"
info "memory available: $(free -h 2>/dev/null | awk '/^Mem:/{print $7}' || echo unknown)"
info "disk free: $(df -h "${APP_DIR}" 2>/dev/null | awk 'NR==2{print $4}' || echo unknown)"

echo
if [[ ${FAILURES} -eq 0 ]]; then
  echo "READY: host is prepared for deployment."
  exit 0
fi
echo "NOT READY: ${FAILURES} check(s) failed."
exit 1
