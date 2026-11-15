import sys,json,time,calendar
from pathlib import Path
import numpy as np
from scipy.stats import t as student
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/science'))
from src.double_bootstrap_diagnostics import geometry,fit,build_cache,probabilities
from src.trend_estimation import sen_slopes
from src.inference import wilson_interval
from review_sahel_ndvi import sha,write_json
from research_reml_uncertainty import frozen
OUT=ROOT/'data/derived/science_inference/double_diagnosis';REPORTS=ROOT/'packages/science/phase_reports'

def preserve():
 d=frozen()
 for name in ['PHASE_4_REML_RESEARCH.json','PHASE_4_DOUBLE_BOOTSTRAP.json','PHASE_4_UNCERTAINTY_REPORT.md']:
  p=REPORTS/name;d[p.relative_to(ROOT).as_posix()]=sha(p)
 for name in ['src/reml_uncertainty.py','config/uncertainty_research.json','config/double_bootstrap_research.json']:
  p=ROOT/'packages/science'/name;d[p.relative_to(ROOT).as_posix()]=sha(p)
 return d

def panel(c,n,model,seed):
 rng=np.random.default_rng(np.random.SeedSequence([seed,n,c['models'].index(model)]));N=c['records_per_panel'];phi=c['boundary_phi'] if model=='boundary_ar1' else c['phi']
 z=rng.normal(size=(N,n+300)) if model!='student5_ar1' else rng.standard_t(5,size=(N,n+300))*np.sqrt(3/5)
 if model=='heteroskedastic_ar1':z[:,-n:]*=np.linspace(1,2,n)
 innovation=z.copy()
 for k in range(1,n+300):
  z[:,k]+=phi*z[:,k-1]
  if model=='arma11':z[:,k]+=.4*innovation[:,k-1]
 y=z[:,-n:]*np.sqrt(1-phi*phi)
 if model=='seasonal_annualized':
  pattern=3*np.sin(2*np.pi*np.arange(12)/12)
  y+=np.array([np.average(pattern,weights=[calendar.monthrange(2001+i,m)[1] for m in range(1,13)]) for i in range(n)])
 return y,phi

def metrics(y,cache,truth):
 geo,inner,outer,critical,inverted=cache;f=fit(y,geo);point=f['slope']+truth;stat=point/f['se']
 p=probabilities(stat,f['index'],inner,outer);crit=critical[f['index']];inv=inverted[f['index']]
 noncover=abs(f['slope']/f['se'])>crit;noncover_inv=abs(f['slope']/f['se'])>inv
 reject=p<=.05;N=len(y);covered=int((~noncover).sum());rejected=int(reject.sum())
 # Sen remains a separately computed descriptive statistic, never substituted.
 sen=sen_slopes((y+truth*np.arange(y.shape[1])).T,np.arange(y.shape[1]))['slope']
 return {'truth':truth,'records':N,'rejections':rejected,'covered':covered,'rejection_rate':rejected/N,'coverage':covered/N,
  'rejection_mc95_conditional_cache':wilson_interval(rejected,N),'coverage_mc95_conditional_cache':wilson_interval(covered,N),
  'inverted_interval_coverage':float((~noncover_inv).mean()),'p_interval_disagreement':float((reject!=noncover).mean()),
  'inverted_p_interval_disagreement':float((reject!=noncover_inv).mean()),'mean_fitted_rho':float(f['rho'].mean()),
  'fit_boundary_rate':float(f['boundary'].mean()),'sen_minus_regression_mean':float((sen-point).mean()),
  'sen_minus_regression_mean_absolute':float(abs(sen-point).mean()),'sen_minus_regression_max_absolute':float(abs(sen-point).max()),
  'regression_slope_bias':float((point-truth).mean()),'sen_slope_bias':float((sen-truth).mean())}

def main():
 start=time.perf_counter();OUT.mkdir(parents=True,exist_ok=True);path=ROOT/'packages/science/config/double_bootstrap_diagnostics.json';c=json.loads(path.read_text())
 before=preserve();accept=json.loads((ROOT/'packages/science/config/double_bootstrap_research.json').read_text())['acceptance']
 identity={'config':sha(path),'code':sha(ROOT/'packages/science/src/double_bootstrap_diagnostics.py'),'runner':sha(Path(__file__))}
 write_json(OUT/'protocol_before_evaluation.json',{'config':c,'identity':identity,'acceptance':accept,'prior_hashes':before})
 rows=[]
 for n in c['lengths']:
  fixed={model:panel(c,n,model,c['fixed_panel_seed'])[0] for model in c['models']}
  for grid,spec in c['grids'].items():
   for k in range(c['cache_realizations']):
    cache=build_cache(n,spec,c['cache_seed']+k,c['inner_replicates'],c['outer_replicates'])
    for model in c['models']:
     for kind,y in [('fixed',fixed[model]),('fresh',panel(c,n,model,c['fresh_panel_seed']+k)[0])]:
      for truth in c['truths']:
       m=metrics(y,cache,truth);m.update(n=n,grid=grid,cache=k,model=model,panel=kind)
       a=accept;rate=m['rejection_rate'];cov=m['coverage']
       m['passes_original_screen']=bool(a['coverage_target_band'][0]<=cov<=a['coverage_target_band'][1] and m['coverage_mc95_conditional_cache'][0]>=a['coverage_lower_wilson_min'] and
        (a['null_rate_target_band'][0]<=rate<=a['null_rate_target_band'][1] and m['rejection_mc95_conditional_cache'][1]<=a['null_upper_wilson_max'] if truth==0 else m['rejection_mc95_conditional_cache'][0]>=a['power_lower_wilson_min']))
       rows.append(m)
    print(n,grid,'cache',k,'complete',flush=True)
    write_json(OUT/'progress.json',{'rows':rows,'identity':identity})
 aggregate=[]
 for n in c['lengths']:
  for grid in c['grids']:
   for model in c['models']:
    for kind in ['fixed','fresh']:
     for truth in c['truths']:
      group=[r for r in rows if (r['n'],r['grid'],r['model'],r['panel'],r['truth'])==(n,grid,model,kind,truth)]
      item={'n':n,'grid':grid,'model':model,'panel':kind,'truth':truth,'cache_realizations':len(group),'failed_cache_screens':sum(not r['passes_original_screen'] for r in group)}
      for field in ['rejection_rate','coverage','fit_boundary_rate','mean_fitted_rho','p_interval_disagreement','inverted_interval_coverage','inverted_p_interval_disagreement','sen_minus_regression_mean_absolute']:
       a=np.array([r[field] for r in group]);se=a.std(ddof=1)/np.sqrt(len(a));radius=student.ppf(.975,len(a)-1)*se
       item[field]={'mean':float(a.mean()),'min':float(a.min()),'max':float(a.max()),'sd_across_caches':float(a.std(ddof=1)),
        'mc95_cluster_mean':[float(a.mean()-radius),float(a.mean()+radius)] if kind=='fresh' else None}
      aggregate.append(item)
 for p,h in before.items():assert sha(ROOT/p)==h,p
 write_json(REPORTS/'PHASE_4_DOUBLE_DIAGNOSIS.json',{'config':c,'acceptance_unchanged':accept,'identity':identity,'rows':rows,'aggregate':aggregate,'prior_hashes':before,
  'release':False,'phase5_started':False,'elapsed_seconds':time.perf_counter()-start,
  'accounting':'Within a panel scenarios and grids/caches are paired; fixed-panel cache variation is conditional on records. Fresh panel/cache pairs are independent across cache IDs; cluster-t intervals use eight units, not pooled Bernoulli trials.'})
 print('COMPLETE',len(rows),flush=True)
if __name__=='__main__':main()
