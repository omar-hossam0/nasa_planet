# Deployment — CI/CD pipeline

How code reaches the Azure VM, and how to recover when it does not.

---

## 1. Pipeline at a glance

```text
push to any branch ──► CI (tests + docker smoke)          ──► done
PR targeting main  ──► CI (validates the merge)           ──► done, no deploy
push to main       ──► CI ──► publish images to GHCR ──► deploy to Azure VM ──► health checks
                                  │                              │
                              any job fails                  checks fail
                                  └────► NO DEPLOY         └────► rollback to previous tag
```

Everything lives in one workflow (`.github/workflows/ci.yml`) so the deploy job can use
explicit `needs:` dependencies instead of cross-workflow triggers.

---

## 2. Jobs

| Job | Runs on | Blocks deployment? |
|---|---|---|
| `backend` | every push / PR | yes |
| `rag` | every push / PR | yes |
| `ai-ml` | every push / PR | yes |
| `statistics` | every push / PR | yes |
| `frontend` | every push / PR | yes |
| `docker` | every push / PR (after backend + frontend) | yes |
| `publish-images` | **push to main only** | — |
| `deploy-production` | **push to main only** | — |

`deploy-production` has `needs: publish-images`, which itself needs all six CI jobs. A single
failing test therefore makes deployment impossible — the rule is enforced by the dependency
graph, not by documentation.

---

## 3. Triggers

```yaml
on:
  push:        { branches: ['**'] }   # every branch, including main
  pull_request:{ branches: ['**'] }   # PR validation, never deploys
  workflow_dispatch:
```

Deployment condition:

```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

Pull requests and feature branches can never reach the deploy job, even if they pass CI.

---

## 4. Required GitHub configuration

### Variables (Settings → Variables)

| Name | Example | Purpose |
|---|---|---|
| `AZURE_VM_HOST` | `172.174.114.48` | target host |
| `AZURE_VM_USER` | `azureuser` | SSH user |
| `AZURE_VM_PORT` | `22` | SSH port |
| `AZURE_VM_HOST_FINGERPRINT` | `SHA256:QhjP9cfOYuojeQfUbvngqCvP2lB83yzPZHX5sEVqIo4` | pinned host identity |

The fingerprint is **required**. The workflow scans the host key, compares it to this value
and refuses to continue on a mismatch. `StrictHostKeyChecking=no` is never used.

Verify the fingerprint against the VM before trusting it:

```bash
ssh-keyscan -t ed25519 172.174.114.48 | ssh-keygen -lf -
```

### Secrets

| Name | Required | Purpose |
|---|---|---|
| `AZURE_VM_SSH_KEY` | yes | private key for the deploy user |
| `GHCR_READ_TOKEN` | only if packages are private | read-only package token |
| `GHCR_USER` | with the token above | account owning that token |

`GITHUB_TOKEN` publishes images; it is **not** usable from the VM, which is why a separate
read token may be needed.

---

## 5. Image versioning

```text
ghcr.io/<owner>/<repo>/backend:sha-<full-commit-sha>
ghcr.io/<owner>/<repo>/frontend:sha-<full-commit-sha>
```

The SHA tag is immutable and identifies exactly the commit that passed CI. `latest` is also
published for convenience but **never** used by the deployment, which always pins the SHA.

`compose.prod.yaml` refuses to start without explicit image references:

```yaml
image: ${BACKEND_IMAGE:?BACKEND_IMAGE is required (immutable ghcr reference)}
```

---

## 6. What happens during a deploy

1. The workflow ships `compose.prod.yaml` and `scripts/deploy/` to
   `/opt/trend-detective` (tar over SSH — no rebuild on the server).
2. `deploy.sh` checks docker, compose, the bootstrap marker and the compose file.
3. It records the current tag as `state/previous_tag`.
4. `docker compose pull` → `up -d --no-build --remove-orphans`.
5. `healthcheck.sh` verifies containers, `/health`, `/ready`, the frontend and
   `/v1/analyses` in OpenAPI, with bounded retries (default 120 s).
6. On success the new tag is written to `state/current_tag`.
7. On failure: logs are saved to `logs/failed-<tag>.log`, and the previous tag is redeployed
   and re-checked.

Concurrency:

```yaml
concurrency:
  group: production-deploy
  cancel-in-progress: false
```

Only one deployment runs at a time, and a running deployment is never cancelled mid-flight.

---

## 7. Ports

| Service | Host binding | Public? |
|---|---|---|
| frontend | `0.0.0.0:80 → 8080` | yes |
| backend | `127.0.0.1:8000 → 8000` | **no** — loopback only |

Nginx proxies `/v1`, `/health`, `/docs`, `/redoc` and `/openapi.json` to `backend:8000` over
the internal `prod-net` network.

---

## 8. Rollback

Automatic: `deploy.sh` redeploys `state/previous_tag` and re-runs health checks.

Manual:

```bash
ssh azureuser@<host>
cd /opt/trend-detective
cat state/previous_tag
IMAGE_PREFIX=ghcr.io/<owner>/<repo> IMAGE_TAG=<previous-tag> ./scripts/deploy/deploy.sh
```

---

## 9. Verifying a deployment

```bash
curl -s http://<host>/health          # {"status":"ok", ...}
curl -s http://<host>/openapi.json    # OpenAPI document
ssh azureuser@<host> 'cd /opt/trend-detective && cat state/current_tag'
ssh azureuser@<host> 'cd /opt/trend-detective && ./scripts/deploy/healthcheck.sh'
```

---

## 10. Common errors

| Symptom | Cause | Fix |
|---|---|---|
| `host not bootstrapped` | bootstrap never ran | run `scripts/server/bootstrap.sh` once |
| `AZURE_VM_HOST_FINGERPRINT is not set` | variable missing | add it, verified against the host |
| `SSH host key fingerprint mismatch` | host reinstalled or MITM | re-verify the fingerprint before changing it |
| `image pull failed` | private package without token | add `GHCR_READ_TOKEN` or make the package public |
| `health checks failed` | app crash or wrong port | read `logs/failed-<tag>.log` |
| backend crash-loops with `Production release is not enabled` | `APP_ENV=production` | use `staging` (see above) |
| `deploy-production` skipped | not a push to main | expected behaviour |
| `statistics` job fails | missing scientific deps in CI image | check `packages/science/requirements.txt` |

---

## 11. Status of this pipeline

| Piece | State |
|---|---|
| CI jobs | implemented; backend/frontend/rag/ai-ml verified locally |
| Docker build + compose smoke | verified locally (images built, stack healthy) |
| `bootstrap.sh` / `verify.sh` | **executed on the Azure VM** (2026-11-15) — `verify.sh` reports READY |
| `compose.prod.yaml` | **deployed on the Azure VM** — both services healthy |
| `deploy.sh` / `healthcheck.sh` | **verified on the Azure VM** and locally (success, pull failure, rollback) |
| GHCR publishing | implemented; **blocked** — the local `gh` token lacks `write:packages` |
| Automatic deployment | implemented, **not yet exercised** (needs a push to `main`) |

### First install without a registry

When GHCR is not available yet, images can be transferred once and deployed with
`SKIP_PULL=true` (the script verifies the images exist locally instead of pulling):

```bash
docker save "$BACKEND_IMAGE" "$FRONTEND_IMAGE" | gzip -1 \
  | ssh azureuser@<host> 'gunzip | docker load'
ssh azureuser@<host> "cd /opt/trend-detective && \
  IMAGE_PREFIX=ghcr.io/<owner>/<repo> IMAGE_TAG=<tag> SKIP_PULL=true ./scripts/deploy/deploy.sh"
```

### Line endings

Shell scripts **must stay LF**. CRLF from Windows breaks the shebang inside Linux
(`/usr/bin/env: 'bash\r': No such file or directory`). `.gitattributes` now enforces
`*.sh text eol=lf`; if a script is edited on Windows, re-normalise before shipping.

### `APP_ENV` is capped at `staging`

`backend/app/core/config.py` raises on `APP_ENV=production`:

> Production release is not enabled: real science and authorization integration remain required

So `compose.prod.yaml` defaults to `staging`. Changing that default to `production` makes the
container crash-loop. Remove the guard only when the science and auth integration is real.
