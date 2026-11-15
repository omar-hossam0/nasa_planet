# Docker — how to run the stack

A short, practical guide. No prior Docker experience assumed.

---

## What Docker is used for

Docker packages the app and its dependencies into images, so the same thing runs on a
teammate's laptop, in CI, and later on the Azure VM. The project runs as **two
containers**: the React frontend (served by Nginx) and the FastAPI backend.

RAG and ML are **not** containers today. They ship as Python libraries imported inside the
backend process (`packages/rag`, `ai/`, `packages/science`). Wrapping a library in a
container that only talks to itself would add moving parts without adding a service.

---

## Requirements

- Docker Engine or Docker Desktop (with the daemon running)
- Docker Compose V2 (`docker compose version`)
- Free host ports: **8000** (backend) and **8080** (frontend) — change them in `.env` if busy

Check:

```bash
docker --version
docker compose version
```

---

## How to build

```bash
docker compose build
```

## How to start

```bash
docker compose up -d
```

Then open:

- Frontend — <http://localhost:8080>
- API docs — <http://localhost:8000/docs>
- Health — <http://localhost:8000/health>

The frontend container also proxies `/v1`, `/health`, `/docs`, `/redoc` and
`/openapi.json` to the backend, so <http://localhost:8080/docs> works too.

## How to stop

```bash
docker compose down --remove-orphans
```

## How to view logs

```bash
docker compose logs -f              # all services
docker compose logs -f backend      # one service
docker compose logs --tail 200      # last 200 lines
```

---

## Available services

| Service | Host port | Status | Description |
|---|---|---|---|
| `backend` | 8000 | Running | FastAPI. Mock mode by default; no database required. |
| `frontend` | 8080 | Running | React 19 + Vite build served by Nginx, proxies API to `backend:8000`. |
| `rag` | — | Bundled in `backend` | `packages/rag` + the corpus are copied **into the backend image** and imported in-process. |
| `ml` | — | Not deployed | No trained model artifact exists in the repository. |

> **Build context is the repository root** (`context: .`, `dockerfile: backend/Dockerfile`),
> because the image needs `packages/`, `ai/`, `data/nasa/**` and
> `docs/architecture/scope.v2.json`. The root `.dockerignore` prunes the heavy trees
> (`measurements/`, `regional/`, `frontend/`, `dist/`).

Inside the Compose network, containers reach each other by **service name**:
`http://backend:8000`, never `localhost`.

---

## Mock mode

`MOCK_MODE=true` is the default. In this mode:

- no database is required (`JOB_BACKEND=inline`),
- no NASA download happens at request time,
- no LLM provider key is required; retrieval falls back to the deterministic path,
- every analysis response is labelled `data_mode: "mock"`.

To switch to durable storage later, set `JOB_BACKEND=database` and provide `DATABASE_URL`.
The baseline stack does not start a database.

---

## Optional services (RAG and ML)

`compose.optional.example.yaml` is a **template**, not a working configuration: the build
contexts it references (`services/rag`, `services/ml`) do not exist yet.

When a team delivers a real HTTP service:

1. Put its `Dockerfile` in `services/rag` or `services/ml`.
2. Add the corresponding `Dockerfile` and `.dockerignore`.
3. Start it explicitly:

```bash
docker compose -f compose.yaml -f compose.optional.example.yaml --profile rag up -d
```

Do not enable a profile before its build context exists — Compose will fail, by design.

Model weights and NASA datasets stay **outside** the images and are mounted read-only
(`MODEL_DIR`), so images stay small and reproducible.

---

## Troubleshooting

**Port already in use**
Change the host port in `.env` (`BACKEND_PORT`, `FRONTEND_PORT`) and restart. The container
port stays the same.

Port **8080 is commonly taken** by other local tools. If `up` fails with
`bind: Only one usage of each socket address`, run:

```bash
FRONTEND_PORT=8090 docker compose up -d
```

and open <http://localhost:8090>. The CI variant (`compose.ci.yaml`) publishes no host
ports, so it is not affected by this.

**`compose config` complains about a missing variable**
Copy `.env.example` to `.env` and fill only what you need. Every variable has a safe default;
none are required to boot.

**Build fails on `npm ci`**
The lockfile is authoritative. Do not delete `package-lock.json`; run `npm install` locally
and commit the updated lockfile instead.

**Container is `unhealthy`**
```bash
docker compose ps
docker compose logs backend
docker inspect --format '{{json .State.Health}}' $(docker compose ps -q backend)
```
The backend healthcheck calls `GET /health` from inside the container. If it fails, the app
did not start — read the logs, not the healthcheck.

**Frontend loads but API calls fail**
The Nginx config proxies to `http://backend:8000`. If you renamed the service, update
`frontend/nginx.conf`.

**"RAG/ML service not found"**
Expected: they are not services yet. See the optional services section.

**Container-to-container `localhost` confusion**
Inside a container, `localhost` is that container only. Use the Compose service name.

---

## CI behaviour

`.github/workflows/ci.yml` runs on every push to any branch, on every pull request, and on
manual dispatch. Jobs: **backend**, **rag**, **ai-ml**, **statistics**, **frontend**, and
**docker**.

The `docker` job (after backend and frontend pass):

1. validates `compose.yaml` and `compose.ci.yaml`,
2. builds both images,
3. starts the stack with `--wait` (healthcheck-gated, no sleeps),
4. checks `/health` and `/openapi.json`,
5. runs a full mock analysis: create → poll → result, asserting `data_mode: "mock"`,
6. checks the frontend serves its index and can reach `backend:8000`,
7. prints logs on failure and always tears the stack down.

`compose.ci.yaml` publishes no host ports, so parallel jobs cannot collide.

---

## Future Azure deployment

The same images and Compose file are intended to run on the Azure Linux VM. That deployment
is **not configured or tested yet**; it comes after the container setup is reviewed. Expect
to add: a reverse proxy or public port mapping, resource limits, and a read-only mount for
data and model weights.
