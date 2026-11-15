#!/usr/bin/env bash
# Verify a running production stack. Read-only. Exit 0 = healthy.
#
#   ./healthcheck.sh
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/trend-detective}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.prod.yaml}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"
PUBLIC_HTTP_PORT="${PUBLIC_HTTP_PORT:-80}"
PUBLIC_HTTPS_PORT="${PUBLIC_HTTPS_PORT:-443}"
PUBLIC_HOSTNAME="${PUBLIC_HOSTNAME:-astraverd.duckdns.org}"
CURRENT_TAG_FILE="${APP_DIR}/state/current_tag"

log()  { printf '  \033[1;32mok\033[0m   %s\n' "$*"; }
bad()  { printf '  \033[1;31mFAIL\033[0m %s\n' "$*" >&2; }
info() { printf '  \033[1;34minfo\033[0m %s\n' "$*"; }

failures=0

http_ok() {
  local url="$1" label="$2"
  if curl -fsS --max-time 10 -o /dev/null "${url}"; then
    log "${label} (${url})"
  else
    bad "${label} (${url})"
    failures=$((failures + 1))
  fi
}

cd "${APP_DIR}" || { bad "cannot cd to ${APP_DIR}"; exit 1; }

# --- 1. compose configuration ------------------------------------------------
if docker compose -f "${COMPOSE_FILE}" config --quiet; then
  log "compose configuration valid"
else
  bad "compose configuration invalid"
  failures=$((failures + 1))
fi

# --- 2. containers running and healthy (retryable while starting) ------------
container_ids="$(docker compose -f "${COMPOSE_FILE}" ps -q)"
if [[ -z "${container_ids}" ]]; then
  bad "no containers are running"
  exit 1
fi

check_containers() {
  local problems=0
  for id in ${container_ids}; do
    local name state health
    name="$(docker inspect -f '{{.Name}}' "${id}" 2>/dev/null | sed 's#^/##')"
    state="$(docker inspect -f '{{.State.Status}}' "${id}" 2>/dev/null)"
    health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${id}" 2>/dev/null)"

    if [[ "${state}" != "running" ]]; then
      bad "${name}: state=${state}"
      problems=$((problems + 1))
    elif [[ "${health}" == "unhealthy" ]]; then
      bad "${name}: unhealthy"
      problems=$((problems + 1))
    elif [[ "${health}" == "starting" ]]; then
      info "${name}: still starting"
      problems=$((problems + 1))
    else
      log "${name}: running (health=${health})"
    fi
  done
  return "${problems}"
}

# --- 3. HTTP endpoints, with bounded retries ---------------------------------
# `failures` is reset on every attempt: only the final attempt decides the
# verdict, otherwise a slow first start would poison a healthy deployment.
deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
attempt=1
while :; do
  failures=0

  check_containers || failures=$((failures + $?))

  http_ok "https://${PUBLIC_HOSTNAME}:${PUBLIC_HTTPS_PORT}/health" "public /health"
  http_ok "https://${PUBLIC_HOSTNAME}:${PUBLIC_HTTPS_PORT}/ready"  "public /ready"
  http_ok "https://${PUBLIC_HOSTNAME}:${PUBLIC_HTTPS_PORT}/"       "public frontend /"

  if [[ ${failures} -eq 0 ]]; then
    break
  fi

  if [[ $(date +%s) -ge ${deadline} ]]; then
    warn "still failing after ${HEALTH_TIMEOUT}s"
    break
  fi

  info "attempt ${attempt} incomplete; retrying in 5s"
  attempt=$((attempt + 1))
  sleep 5
done

# --- 4. API contract smoke ---------------------------------------------------
if curl -fsS --max-time 10 "https://${PUBLIC_HOSTNAME}:${PUBLIC_HTTPS_PORT}/openapi.json" \
     | grep -q '"/v1/analyses"'; then
  log "openapi exposes /v1/analyses"
else
  bad "openapi missing /v1/analyses"
  failures=$((failures + 1))
fi

redirect_code="$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' \
  "http://${PUBLIC_HOSTNAME}:${PUBLIC_HTTP_PORT}/")"
if [[ "${redirect_code}" =~ ^30[1278]$ ]]; then
  log "HTTP redirects to HTTPS (status ${redirect_code})"
else
  bad "HTTP did not redirect to HTTPS (status ${redirect_code})"
  failures=$((failures + 1))
fi

# --- 5. deployed version -----------------------------------------------------
if [[ -f "${CURRENT_TAG_FILE}" ]]; then
  log "recorded release: $(cat "${CURRENT_TAG_FILE}")"
else
  info "no release tag recorded yet"
fi

echo
if [[ ${failures} -eq 0 ]]; then
  echo "HEALTHY"
  exit 0
fi
echo "UNHEALTHY: ${failures} failure(s)"
exit 1
