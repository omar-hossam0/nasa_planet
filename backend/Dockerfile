# Trend Detective backend image.
# Runtime only: test tooling is filtered out so the image stays small.
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Unprivileged runtime user (no shell needed).
RUN adduser --disabled-password --gecos "" --uid 10001 appuser

# Build context is the REPOSITORY ROOT (see compose.yaml and .dockerignore),
# because the backend imports packages/rag, ai/ and reads the RAG corpus.

# Dependencies first so the layer is cached across source-only changes.
COPY backend/requirements.txt ./
RUN sed -E '/^[[:space:]]*pytest/d' requirements.txt > /tmp/runtime-requirements.txt \
    && pip install --no-cache-dir -r /tmp/runtime-requirements.txt \
    && rm -f /tmp/runtime-requirements.txt

# Application code only. Tests, caches and .env are excluded via .dockerignore.
COPY backend/app ./app
# Runtime configuration read by app/core/regions.py (DEFAULT_REGIONS = <root>/config/regions.json)
COPY backend/config ./config
COPY backend/run.py ./

# In-process libraries: RAG (retrieval + explanation) and the science package.
# They are NOT separate services, so they ship inside this image.
COPY packages ./packages
COPY ai ./ai
# Registry + corpus. Heavy trees (measurements/, regional/) are pruned by the
# root .dockerignore; what remains is a few MB of JSON/JSONL.
COPY data/nasa ./data/nasa
# Scope registry read by packages/rag/id_mapping.py (ROOT/docs/architecture/...)
COPY docs/architecture/scope.v2.json ./docs/architecture/scope.v2.json

# Scientific runtime for packages/science (Theil-Sen, Mann-Kendall, bootstrap).
# numpy/xarray/netCDF4 come from the package's own audit pins; scipy is the
# only extra. Notebook tooling (matplotlib/ipykernel) is intentionally excluded.
RUN pip install --no-cache-dir -r packages/science/requirements-audit.txt "scipy>=1.14,<2"

USER appuser

EXPOSE 8000

# Liveness probe against the real health endpoint (no curl in the image).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

# No --reload in a container. Bind to 0.0.0.0 so the port is reachable.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
