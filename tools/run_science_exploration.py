"""Execute the committed Phase 1 notebook using the active Python environment."""
from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "packages/science/notebooks/01_exploration.ipynb"
    notebook = nbformat.read(path, as_version=4)
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    try:
        NotebookClient(notebook, km=manager, timeout=120,
                       resources={"metadata": {"path": str(root)}}).execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    if any(output.output_type == "error" for cell in notebook.cells if cell.cell_type == "code"
           for output in cell.get("outputs", [])):
        raise RuntimeError("Exploration notebook contains errors")
    nbformat.write(notebook, path)
    print(f"Executed notebook: {path.relative_to(root)}")
    print("Plot: data/derived/science/phase_1/precipitation_exploration.png")


if __name__ == "__main__":
    main()
