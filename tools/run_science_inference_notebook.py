"""Execute only the Phase 4 calibration notebook; earlier notebooks unchanged."""
from pathlib import Path
import sys

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / "packages/science/notebooks/04_inference_validation.ipynb"
    notebook = nbformat.read(path, as_version=4)
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    try:
        NotebookClient(notebook, km=manager, timeout=120,
                       resources={"metadata": {"path": str(root)}}).execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    nbformat.write(notebook, path)
    print(f"Executed {path.relative_to(root)}")


if __name__ == "__main__":
    main()
