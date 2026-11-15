"""Create and execute the Phase 5 real-data demonstration only."""
import sys
from pathlib import Path
import nbformat as nb
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'packages/science/notebooks/05_descriptive_spatial.ipynb'
book=nb.v4.new_notebook(cells=[
 nb.v4.new_markdown_cell('# Phase 5: descriptive spatial trends\nEstimated change only. Inference is disabled after failed Phase 4 validation. Positive/negative/zero are numerical descriptions, never significance or stability labels. All prior data and preparation policies are preserved.'),
 nb.v4.new_code_cell("from pathlib import Path\nimport json\nimport xarray as xr\nfrom IPython.display import display, Image\nroot=Path.cwd()\nr=json.loads((root/'data/derived/science_spatial/phase_5/results.json').read_text())\nprint('Cases:',len(r['cases']), 'Inference:',r['inference_status'])\nfor c in r['cases']:\n print(c['key'], c['periods']['annual'][0]['slope_per_year'],c['periods']['annual'][0]['slope_units'])"),
 nb.v4.new_markdown_cell('## Sahel NDVI: three preparation policies\nStrict 100% remains default. Standard 100% is a fixed-support comparison. Standard 95% remains experimental: monthly geography changes and incomplete annual cell records remain missing. Gray in the slope map denotes unavailable slopes; consult the separate support map to distinguish exclusion. Shares use preparation-eligible cells including unavailable cells.'),
 nb.v4.new_code_cell("sahel=[c for c in r['cases'] if c['variable_id']=='vegetation_greenness' and c['region_id']=='sahel_comparison']\nfor c in sahel:\n print(c['policy'],'eligible selected-area fraction:',c['eligible_area_fraction_selected'])\n display(c['periods']['annual'][0]['cell_shares'])\n print('Missing eligible cell-years:',c['annual_missing_eligible_cell_years'])\n display(Image(filename=str(root/c['map_artifact'])))\ndisplay(r['policy_comparisons'])"),
 nb.v4.new_markdown_cell('## Period sensitivity\nEvery period is compared to its own actual 2001–2024 reference. Eligibility remains fixed. These windows are descriptive; short records and raw monthly seasonality limit interpretation. Regional slopes are computed from the regional series, not the average cell slope.'),
 nb.v4.new_code_cell("for c in sahel:\n print(c['policy'])\n for p in c['periods']['annual']:\n  display({k:p[k] for k in ['start_year','end_year','n_valid','valid_span_years','slope_per_year','regional_direction_agrees_full_period']})\nwith xr.open_dataset(root/sahel[-1]['grid_artifact']) as grid:\n display(grid)\n print('Unavailable comparison code:',-1)"),
 nb.v4.new_markdown_cell('## Boundary\nNo p-values, confidence intervals, FDR, causal claims or statistically demonstrated changes are published. Policy/location differences are not interchangeable estimates or uncertainty intervals. Stop at Phase 5 for owner review before Phase 6.'),
])
book.metadata['kernelspec']={'display_name':'NASA science Python','language':'python','name':'python3'}
manager=KernelManager(kernel_name='python3')
manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
try:
 NotebookClient(book,km=manager,timeout=120,resources={'metadata':{'path':str(ROOT)}}).execute()
finally:
 if manager.has_kernel:manager.shutdown_kernel(now=True)
nb.write(book,path)
print('Executed',path)
