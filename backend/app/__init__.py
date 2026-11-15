"""Trend Detective backend package."""

__version__ = "m3-1.0.0"
from pathlib import Path
import sys

# Shared science/RAG contracts are repository packages in this monorepo.
_repository_root = str(Path(__file__).resolve().parents[2])
if _repository_root not in sys.path:
    sys.path.insert(0, _repository_root)
