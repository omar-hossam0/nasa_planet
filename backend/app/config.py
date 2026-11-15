"""Backend configuration. No secrets are stored or exposed here."""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
REPO_DIR = BASE_DIR.parent                                  # repo root
DATA_DIR = Path(os.environ.get("TD_DATA_DIR", REPO_DIR / "data" / "nasa"))
VAR_DIR = Path(os.environ.get("TD_VAR_DIR", BASE_DIR / "var"))
DB_PATH = Path(os.environ.get("TD_DB_PATH", VAR_DIR / "app.db"))
ARTIFACT_DIR = Path(os.environ.get("TD_ARTIFACT_DIR", VAR_DIR / "artifacts"))

# compute limits, checked before a job is created
MAX_CELLS_PER_VARIABLE = int(os.environ.get("TD_MAX_CELLS", "40000"))
MIN_AOI_AREA_DEG2 = float(os.environ.get("TD_MIN_AOI_AREA", "0.05"))
MAX_AOI_AREA_DEG2 = float(os.environ.get("TD_MAX_AOI_AREA", "400.0"))
MAX_VARIABLES_PER_REQUEST = int(os.environ.get("TD_MAX_VARIABLES", "4"))
WORKER_POLL_SECONDS = float(os.environ.get("TD_WORKER_POLL", "0.2"))

# test hooks: allow overriding the resolved revisions without editing files
METHOD_REVISION_OVERRIDE = os.environ.get("TD_METHOD_REVISION_OVERRIDE")

SOFTWARE_REVISION = "m3-1.0.0"


def ensure_dirs() -> None:
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# the explanation layer (Member 4) lives at <repo>/ai
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))
