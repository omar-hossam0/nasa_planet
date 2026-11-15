import sys,json,time,calendar
from pathlib import Path
import numpy as np
from scipy.stats import t
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/science'))
from src.sen_uncertainty import sen_pivot,calibrated_sen,subsampling_sen
from src.reml_uncertainty import fit_reml,simulate_ar
from src.inference import wilson_interval
from run_science_inference_study import ar1
from review_sahel_ndvi import sha,write_json
from diagnose_double_bootstrap import preserve
OUT=ROOT/'data/derived/science_inference/sen_research';REPORTS=ROOT/'packages/science/phase_reports'
MODELS=[('gaussian0',0.),('gaussian4',.4),('gaussian7',.7),('offgrid55',.55),('seasonal',.7),('student5',.7),('arma11',.7),('heteroskedastic',.7),('boundary95',.95)]

def panel(seed,n,model,phi,N):
 rng=np.random.default_rng(np.random.SeedSequence([seed,n,[a[0] for a in MODELS].index(model)]))
 z=rng.standard_t(5,size=(N,n+300))*np.sqrt(3/5) if model=='student5' else rng.normal(size=(N,n+300))
 if model=='heteroskedastic':z[:,-n:]*=np.linspace(1,2,n)
 innovations=z.copy()
 for i in range(1,n+300):
  z[:,i]+=phi*z[:,i-1]
  if model=='arma11':z[:,i]+=.4*innovations[:,i-1]
 y=z[:,-n:]*np.sqrt(1-phi*phi)
 if model=='seasonal':
  cycle=3*np.sin(2*np.pi*np.arange(12)/12)
  y+=np.array([np.average(cycle,weights=[calendar.monthrange(2001+i,m)[1] for m in range(1,13)]) for i in range(n)])
 return y

def summary(out,truth):
 N=len(out['slope']);point=out['slope']+truth
 # Affine equivariance lets all linear trend signs reuse the same error draws.
 reject=out['p'] if truth==0 else None
 return point

def main():
 start=time.perf_counter();OUT.mkdir(parents=True,exist_ok=True)
 path=ROOT/'packages/science/config/sen_uncertainty_research.json';c=json.loads(path.read_text());accept=json.loads((ROOT/'packages/science/config/double_bootstrap_research.json').read_text())['acceptance']
 before=preserve()
 for p in REPORTS.glob('PHASE_4*'):
  if not p.name.startswith('PHASE_4_SEN'):before[p.relative_to(ROOT).as_posix()]=sha(p)
 identity={'config':sha(path),'code':sha(ROOT/'packages/science/src/sen_uncertainty.py'),'script':sha(Path(__file__))}
 write_json(OUT/'protocol_before_evaluation.json',{'config':c,'acceptance':accept,'identity':identity,'prior_hashes':before})
 rows=[]
 for n in c['lengths']:
  for cache in range(c['cache_realizations']):
   distributions=[]
   for j,rho in enumerate(c['rho_grid']):
    rng=np.random.default_rng(np.random.SeedSequence([c['cache_seed'],n,cache,j]))
    draws=simulate_ar(rng.normal(size=(c['calibration_replicates'],n)),rho)
    slope,scale=sen_pivot(draws);distributions.append(np.sort(abs(slope/scale)))
   for model,phi in MODELS:
    y=panel(c['validation_seed']+cache,n,model,phi,c['records_per_panel']);rho_hat=fit_reml(y)['rho']
    for truth in c['truths']:
     values=y+truth*np.arange(n)
     outputs={'sen_parametric_plugin':calibrated_sen(values,c['rho_grid'],distributions,rho_hat),
              'sen_nuisance_grid_envelope':calibrated_sen(values,c['rho_grid'],distributions)}
     for fraction in c['subsample_fractions']:outputs['sen_subsampling_'+str(fraction)]=subsampling_sen(values,fraction)
     for method,out in outputs.items():
      rejected=int((out['p']<=.05).sum());covered=int((abs(out['slope']-truth)<=out['radius']).sum());N=len(y)
      row={'method':method,'n':n,'cache':cache,'model':model,'phi':phi,'truth':truth,'trials':N,'rejected':rejected,'covered':covered,
       'rejection_rate':rejected/N,'coverage':covered/N,'rejection_mc95':wilson_interval(rejected,N),'coverage_mc95':wilson_interval(covered,N),
       'mean_interval_width':float(np.mean(2*out['radius'])),'sen_bias':float(np.mean(out['slope']-truth))}
      a=accept;row['passes_screen']=bool(a['coverage_target_band'][0]<=row['coverage']<=a['coverage_target_band'][1] and row['coverage_mc95'][0]>=a['coverage_lower_wilson_min'] and
       (a['null_rate_target_band'][0]<=row['rejection_rate']<=a['null_rate_target_band'][1] and row['rejection_mc95'][1]<=a['null_upper_wilson_max'] if truth==0 else row['rejection_mc95'][0]>=a['power_lower_wilson_min']))
      rows.append(row)
   print(n,'cache',cache,'complete',flush=True)
 aggregate=[]
 for n in c['lengths']:
  for method in sorted(set(r['method'] for r in rows)):
   for model,phi in MODELS:
    for truth in c['truths']:
     group=[r for r in rows if (r['n'],r['method'],r['model'],r['truth'])==(n,method,model,truth)]
     item={'n':n,'method':method,'model':model,'phi':phi,'truth':truth,'failed_cache_screens':sum(not r['passes_screen'] for r in group)}
     for field in ['coverage','rejection_rate','mean_interval_width']:
      x=np.array([r[field] for r in group]);radius=t.ppf(.975,len(x)-1)*x.std(ddof=1)/np.sqrt(len(x))
      item[field]={'mean':float(x.mean()),'min':float(x.min()),'max':float(x.max()),'mc95_cluster_mean':[float(x.mean()-radius),float(x.mean()+radius)]}
     aggregate.append(item)
 for p,h in before.items():assert sha(ROOT/p)==h,p
 write_json(REPORTS/'PHASE_4_SEN_RESEARCH.json',{'config':c,'acceptance_unchanged':accept,'identity':identity,'rows':rows,'aggregate':aggregate,'prior_hashes':before,
  'application_release':False,'phase5_started':False,'elapsed_seconds':time.perf_counter()-start,
  'assumptions':'Sen point estimates and intervals target beta only under the stated additive symmetric linear-trend model. Grid maximum is not a continuous nuisance supremum.',
  'accounting':'Four independent cache/panel pairs; candidates, trends and blocks paired within each condition. Cluster-t ranges use four units, not 4000 independent Bernoulli trials.'})
 print('COMPLETE',len(rows),flush=True)
if __name__=='__main__':main()
