import sys,json,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/science'))
from review_sahel_ndvi import sha,write_json
r=json.loads((ROOT/'packages/science/phase_reports/PHASE_4_DOUBLE_DIAGNOSIS.json').read_text())
for p,h in r['prior_hashes'].items():assert sha(ROOT/p)==h,p
for key,path in [('config','packages/science/config/double_bootstrap_diagnostics.json'),('code','packages/science/src/double_bootstrap_diagnostics.py'),('runner','tools/diagnose_double_bootstrap.py')]:assert sha(ROOT/path)==r['identity'][key]
assert len(r['rows'])==1728
for row in r['rows']:
 assert row['records']==1000
 assert row['rejections']/1000==row['rejection_rate']
 assert row['covered']/1000==row['coverage']
for a in r['aggregate']:
 group=[v for v in r['rows'] if (v['n'],v['grid'],v['model'],v['panel'],v['truth'])==(a['n'],a['grid'],a['model'],a['panel'],a['truth'])]
 assert len(group)==8
 for field in ['rejection_rate','coverage','fit_boundary_rate']:
  np.testing.assert_allclose(a[field]['mean'],np.mean([v[field] for v in group]))
suite=unittest.defaultTestLoader.discover(str(ROOT/'packages/science/tests'));run=unittest.TextTestRunner(verbosity=1).run(suite)
write_json(ROOT/'packages/science/phase_reports/PHASE_4_DOUBLE_DIAGNOSIS_TESTS.json',{'tests_run':run.testsRun,'passed':run.wasSuccessful(),'errors':len(run.errors),'failures':len(run.failures),'skips':len(run.skipped),'preserved_count':len(r['prior_hashes']),'all_prior_hashes_unchanged':True,'scenario_accounting_verified':True,'application_release':False,'phase5_started':False})
if not run.wasSuccessful():raise SystemExit(1)
