#!/usr/bin/env bash
# Deploy a tested, immutable release to the host.
#
#   IMAGE_TAG=sha-abc1234 ./deploy.sh
#   ./deploy.sh --tag sha-abc1234
#
# Never builds on the server, never installs Docker, never re-runs bootstrap.
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/trend-detective}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.prod.yaml}"
STATE_DIR="${APP_DIR}/state"
CURRENT_TAG_FILE="${STATE_DIR}/current_tag"
PREVIOUS_TAG_FILE="${STATE_DIR}/previous_tag"
MARKER_FILE="${MARKER_FILE:-/var/lib/trend-detective/bootstrap.version}"
HEALTHCHECK="${APP_DIR}/scripts/deploy/healthcheck.sh"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"

IMAGE_PREFIX="${IMAGE_PREFIX:?IMAGE_PREFIX is required, e.g. ghcr.io/owner/repo}"

log()  { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[fail]\033[0m %s\n' "$*" >&2; exit 1; }

IMAGE_TAG="${IMAGE_TAG:-}"
if [[ "${1:-}" == "--tag" ]]; then
  IMAGE_TAG="${2:-}"
fi
[[ -n "${IMAGE_TAG}" ]] || fail "IMAGE_TAG is required (immutable sha tag)"

# --- 1. prerequisites --------------------------------------------------------
command -v docker >/dev/null 2>&1 || fail "docker is not installed; run bootstrap.sh once"
docker compose version >/dev/null 2>&1 || fail "docker compose plugin missing"
[[ -f "${MARKER_FILE}" ]] || fail "host not bootstrapped (${MARKER_FILE} missing)"
[[ -f "${APP_DIR}/${COMPOSE_FILE}" ]] || fail "${COMPOSE_FILE} missing in ${APP_DIR}"
[[ -x "${HEALTHCHECK}" ]] || fail "healthcheck.sh missing or not executable"

cd "${APP_DIR}"
mkdir -p "${STATE_DIR}" "${APP_DIR}/logs"

# Optional registry credentials written by the deploy workflow (mode 600).
if [[ -f "${APP_DIR}/.registry.env" ]]; then
  # shellcheck disable=SC1091
  set -a; . "${APP_DIR}/.registry.env"; set +a
fi

export BACKEND_IMAGE="${IMAGE_PREFIX}/backend:${IMAGE_TAG}"
export FRONTEND_IMAGE="${IMAGE_PREFIX}/frontend:${IMAGE_TAG}"
export IMAGE_TAG
log "target release: ${IMAGE_TAG}"
log "backend image:  ${BACKEND_IMAGE}"

# --- 2. registry authentication (optional) -----------------------------------
if [[ -n "${GHCR_USER:-}" && -n "${GHCR_TOKEN:-}" ]]; then
  log "authenticating to ghcr.io as ${GHCR_USER}"
  printf '%s' "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USER}" --password-stdin >/dev/null \
    || fail "ghcr login failed"
elif [[ -n "${GHCR_TOKEN:-}" ]]; then
  fail "GHCR_TOKEN provided without GHCR_USER"
else
  log "no registry credentials supplied; relying on public package visibility"
fi

# --- 3. validate configuration ----------------------------------------------
docker compose -f "${COMPOSE_FILE}" config --quiet || fail "compose configuration is invalid"

# --- 4. remember the current release for rollback ----------------------------
PREVIOUS_TAG=""
if [[ -f "${CURRENT_TAG_FILE}" ]]; then
  PREVIOUS_TAG="$(cat "${CURRENT_TAG_FILE}")"
  if [[ "${PREVIOUS_TAG}" == "${IMAGE_TAG}" ]]; then
    log "release ${IMAGE_TAG} is already recorded as current; redeploying anyway"
  fi
  printf '%s\n' "${PREVIOUS_TAG}" > "${PREVIOUS_TAG_FILE}"
  log "previous release: ${PREVIOUS_TAG}"
fi

# --- 5. bring up one release, verified ---------------------------------------
# Returns non-zero on ANY failure (pull, compose up, health check) so the caller
# can roll back. `compose up` itself can fail when depends_on: service_healthy
# never becomes true, which must also trigger a rollback.
bring_up() {
  local tag="$1"
  export BACKEND_IMAGE="${IMAGE_PREFIX}/backend:${tag}"
  export FRONTEND_IMAGE="${IMAGE_PREFIX}/frontend:${tag}"

  if [[ "${SKIP_PULL:-false}" == "true" ]]; then
    # First install from a local image tarball (no registry involved).
    log "SKIP_PULL=true; using locally loaded images for ${tag}"
    docker image inspect "${BACKEND_IMAGE}" >/dev/null 2>&1 \
      || { warn "backend image ${BACKEND_IMAGE} not present locally"; return 1; }
    docker image inspect "${FRONTEND_IMAGE}" >/dev/null 2>&1 \
      || { warn "frontend image ${FRONTEND_IMAGE} not present locally"; return 1; }
  else
    log "pulling ${tag}"
    docker compose -f "${COMPOSE_FILE}" pull || { warn "image pull failed for ${tag}"; return 1; }
  fi

  log "starting containers for ${tag}"
  docker compose -f "${COMPOSE_FILE}" up -d --no-build --remove-orphans \
    || { warn "compose up failed for ${tag}"; return 1; }

  log "running health checks (timeout ${HEALTH_TIMEOUT}s)"
  HEALTH_TIMEOUT="${HEALTH_TIMEOUT}" "${HEALTHCHECK}" || { warn "health checks failed for ${tag}"; return 1; }
  return 0
}

# --- 6. deploy the requested release ----------------------------------------
if bring_up "${IMAGE_TAG}"; then
  printf '%s\n' "${IMAGE_TAG}" > "${CURRENT_TAG_FILE}"
  log "deployment succeeded: ${IMAGE_TAG}"
  docker compose -f "${COMPOSE_FILE}" ps
  exit 0
fi

warn "release ${IMAGE_TAG} FAILED"
docker compose -f "${COMPOSE_FILE}" logs --no-color --tail 120 > "${APP_DIR}/logs/failed-${IMAGE_TAG}.log" 2>&1 || true
warn "logs written to ${APP_DIR}/logs/failed-${IMAGE_TAG}.log"

# --- 7. rollback -------------------------------------------------------------
if [[ -n "${PREVIOUS_TAG}" && "${PREVIOUS_TAG}" != "${IMAGE_TAG}" ]]; then
  log "rolling back to ${PREVIOUS_TAG}"
  if bring_up "${PREVIOUS_TAG}"; then
    printf '%s\n' "${PREVIOUS_TAG}" > "${CURRENT_TAG_FILE}"
    warn "rolled back to ${PREVIOUS_TAG}; deployment of ${IMAGE_TAG} FAILED"
    exit 1
  fi
  warn "rollback to ${PREVIOUS_TAG} also failed — manual intervention required"
  exit 2
fi

warn "no previous release to roll back to"
exit 1
