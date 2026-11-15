import sys,json,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/science'))
from review_sahel_ndvi import sha,write_json
r=json.loads((ROOT/'packages/science/phase_reports/PHASE_4_SEN_RESEARCH.json').read_text())
for p,h in r['prior_hashes'].items():assert sha(ROOT/p)==h,p
for k,p in [('config','packages/science/config/sen_uncertainty_research.json'),('code','packages/science/src/sen_uncertainty.py'),('script','tools/research_sen_uncertainty.py')]:assert sha(ROOT/p)==r['identity'][k]
assert len(r['rows'])==1080
for a in r['aggregate']:
 g=[x for x in r['rows'] if (x['n'],x['method'],x['model'],x['truth'])==(a['n'],a['method'],a['model'],a['truth'])]
 assert len(g)==4
 for field in ['coverage','rejection_rate','mean_interval_width']:np.testing.assert_allclose(a[field]['mean'],np.mean([x[field] for x in g]))
for x in r['rows']:
 assert x['covered']/x['trials']==x['coverage']
 assert x['rejected']/x['trials']==x['rejection_rate']
assert not r['application_release'] and not r['phase5_started']
suite=unittest.defaultTestLoader.discover(str(ROOT/'packages/science/tests'));run=unittest.TextTestRunner(verbosity=1).run(suite)
write_json(ROOT/'packages/science/phase_reports/PHASE_4_SEN_TESTS.json',{'tests_run':run.testsRun,'passed':run.wasSuccessful(),'errors':len(run.errors),'failures':len(run.failures),'skipped':len(run.skipped),'prior_hashes_unchanged':True,'protected_file_count':len(r['prior_hashes']),'accounting_verified':True,'release':False,'phase5_started':False})
if not run.wasSuccessful():raise SystemExit(1)
