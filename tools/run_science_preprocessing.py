"""Execute the Stage 2 notebook in the current virtual environment."""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sahel-only", action="store_true",
                        help="Execute only the new Sahel comparison; retain earlier notebook outputs and figures")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    path = root / "packages/science/notebooks/02_preprocessing.ipynb"
    nb = nbformat.read(path, as_version=4)
    if args.sahel_only:
        positions = [i for i, cell in enumerate(nb.cells)
                     if "sahel-comparison" in cell.metadata.get("tags", [])]
        if not positions:
            raise ValueError("No tagged Sahel comparison cells found")
        # The original import/setup cell supplies paths and canonical manifests.
        execution = nbformat.v4.new_notebook(cells=[copy.deepcopy(nb.cells[1]),
                                                   *[copy.deepcopy(nb.cells[i]) for i in positions]])
    else:
        execution = nb
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    try:
        NotebookClient(execution, km=manager, timeout=120, resources={"metadata": {"path": str(root)}}).execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    if args.sahel_only:
        for position, cell in zip(positions, execution.cells[1:]):
            nb.cells[position] = cell
    nbformat.write(nb, path)
    print(f"Executed {path.relative_to(root)}")
    print("Sahel figures: data/derived/science/sahel_ndvi_preprocessing_comparison/")
    if not args.sahel_only:
        print("Original diagnostics: data/derived/science/phase_2/")


if __name__ == "__main__":
    main()
