"""Render the retained annual observations; does not fit or select a new model."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent
cases = json.loads((OUT/'case_results.json').read_text(encoding='utf-8'))
variables = ['air_temperature', 'soil_moisture', 'precipitation', 'vegetation_greenness']
regions = ['nile_corridor', 'morocco_comparison', 'sahel_comparison']
labels = ['Air temperature (K)', 'Soil moisture (kg m-2)', 'Annual precipitation (mm)', 'NDVI (unitless)']
fig, axes = plt.subplots(4, 3, figsize=(15, 13), constrained_layout=True)
for row, variable in enumerate(variables):
    for col, region in enumerate(regions):
        c = next(c for c in cases if c['variable_id']==variable and c['region_id']==region)
        ax = axes[row, col]
        year = np.array(c['years'])
        flagged = bool(c['AR1']['raw_review_flags'])
        ax.plot(year, c['annual_values'], 'o-', color='#b16838' if flagged else '#236d81', markersize=3)
        ax.plot(year, c['AR1']['intercept']+c['AR1']['slope']*(year-year[0]), '--', color='#555555', lw=1)
        ax.set_title(region.replace('_', ' ')+'\n'+('Review signals' if flagged else 'No raw review signal')+
                     f"; retained area {100*c['retained_area_fraction']:.1f}%", fontsize=9)
        ax.set_xticks([2001, 2012, 2024])
        ax.grid(alpha=.2)
        if col == 0:
            ax.set_ylabel(labels[row])
fig.suptitle('Actual project source cubes: annual regional series, 2001-2024\n'
             'Dashed: diagnostic linear mean. Review signals are exploratory; no inference approval.', fontsize=13)
fig.savefig(OUT/'annual_series_overview.png', dpi=130)
plt.close(fig)
