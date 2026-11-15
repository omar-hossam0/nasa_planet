"""Fixed protocol, independent pilot/holdout, no NASA selection."""
import sys,json,time,calendar
from pathlib import Path
import numpy as np
from scipy.stats import t
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/science'))
from src.reml_uncertainty import fit_reml,refitted_t_errors,geometry
from src.inference import wilson_interval
from review_sahel_ndvi import sha,write_json
from research_inference_followup import snapshot
from run_science_inference_study import ar1
OUT=ROOT/'data/derived/science_inference/reml_research';REPORTS=ROOT/'packages/science/phase_reports'

def frozen():
 d=snapshot()
 for p in [ROOT/'packages/science/config/inference_followup.json',ROOT/'packages/science/src/inference_candidates.py',REPORTS/'PHASE_4_FOLLOWUP.json',REPORTS/'PHASE_4_FOLLOWUP_REPORT.md']:
  d[p.relative_to(ROOT).as_posix()]=sha(p)
 return d

def stage(config,name):
 seed=config[name+'_seed'];count=config['pilot_records'] if name=='pilot' else config['validation_records']
 rows=[];cache={}
 # For each trial, bootstrap samples are generated at its own fitted rho and
 # all nuisance parameters are re-fitted. Affine equivariance allows the same
 # errors for the three slopes; this does not use holdout data for calibration.
 for n in config['lengths']:
  for phi in config['phis']:
   for season in config['seasonal_profiles']:
    code=int(season!='none')
    rng=np.random.default_rng(np.random.SeedSequence([seed,n,int(phi*100),code]))
    y=ar1(rng,count,n,phi)
    if code:
     cycle=3*np.sin(2*np.pi*np.arange(12)/12)
     y+=np.array([np.average(cycle,weights=[calendar.monthrange(2001+i,m)[1] for m in range(1,13)]) for i in range(n)])
    fit=fit_reml(y)
    quantiles=[];errors=[];boot_boundaries=[]
    for i,rho in enumerate(fit['rho']):
     # Same simulated pivotal distribution at a fixed fitted rho can be shared
     # within a stage. Independent seed per rho/n and separate stage streams.
     key=(n,round(float(rho),8))
     if key not in cache:
      drawseed=np.random.SeedSequence([seed,807,n,int(round((rho+.5)*10000))])
      cache[key]=refitted_t_errors(rho,n,config['bootstrap_replicates'],drawseed)
     err,bound=cache[key];errors.append(err);quantiles.append(np.quantile(err,[.025,.975]));boot_boundaries.append(bound)
    quantiles=np.array(quantiles)
    for truth in config['slopes']:
     point=fit['slope']+truth
     for candidate in config['candidates']:
      if candidate=='reml_small_sample_t':
       critical=t.ppf(.975,n-2);lo=point-critical*fit['se'];hi=point+critical*fit['se']
       p=2*t.sf(abs(point/fit['se']),n-2)
      else:
       lo=point-quantiles[:,1]*fit['se'];hi=point-quantiles[:,0]*fit['se']
       p=np.array([(1+(abs(err)>=abs(stat)).sum())/(len(err)+1) for err,stat in zip(errors,point/fit['se'])])
      rejects=int((p<=.05).sum());covered=int(((lo<=truth)&(hi>=truth)).sum())
      row={'stage':name,'candidate':candidate,'n':n,'phi':phi,'season':season,'truth':truth,'trials':count,
       'rejected':rejects,'covered':covered,'rejection_rate':rejects/count,'coverage':covered/count,
       'rejection_mc95':wilson_interval(rejects,count),'coverage_mc95':wilson_interval(covered,count),
       'mean_rho':float(fit['rho'].mean()),'rho_boundary_rate':float(fit['boundary'].mean()),
       'bootstrap_fit_boundary_rate':float(np.mean(boot_boundaries)),'mean_interval_width':float(np.mean(hi-lo)),
       'slope_bias':float(np.mean(point-truth)),'failures':0}
      a=config['acceptance'];rate=row['rejection_rate'];cov=row['coverage']
      row['passes_screen']=bool(a['coverage_target_band'][0]<=cov<=a['coverage_target_band'][1] and row['coverage_mc95'][0]>=a['coverage_lower_wilson_min'] and
       (a['null_rate_target_band'][0]<=rate<=a['null_rate_target_band'][1] and row['rejection_mc95'][1]<=a['null_upper_wilson_max'] if truth==0 else row['rejection_mc95'][0]>=a['power_lower_wilson_min']))
      rows.append(row)
    print(name,n,phi,season,'complete',flush=True)
 return rows

def main():
 start=time.perf_counter();OUT.mkdir(parents=True,exist_ok=True)
 path=ROOT/'packages/science/config/uncertainty_research.json';config=json.loads(path.read_text());before=frozen()
 identity={'policy_sha256':sha(path),'code_sha256':sha(ROOT/'packages/science/src/reml_uncertainty.py'),'script_sha256':sha(Path(__file__))}
 write_json(OUT/'protocol_before_evaluation.json',{'config':config,'identity':identity,'prior_hashes':before})
 pilot=stage(config,'pilot');write_json(OUT/'pilot.json',pilot)
 # No adaptation after pilot. Entirely different records and simulation caches.
 final=stage(config,'validation')
 assert before==frozen()
 decisions={k:{'failed_scenarios':sum(not r['passes_screen'] for r in final if r['candidate']==k),'release':False} for k in config['candidates']}
 write_json(REPORTS/'PHASE_4_REML_RESEARCH.json',{'config':config,'identity':identity,'pilot':pilot,'validation':final,'decisions':decisions,
  'prior_hashes':before,'preserved_count':len(before),'elapsed_seconds':time.perf_counter()-start,'application_release':False,'phase5_started':False,
  'bootstrap_cache':'per-stage independent simulation by n/rho; common Monte Carlo errors shared at same fitted rho; not 1000 independent bootstrap calibrations',
  'limitations':['Gaussian stationary AR1 model','finite rho grid and boundaries','plug-in generating rho still estimated','parameter refits do not guarantee calibration','Monte Carlo cache uncertainty is shared across trials']})
 print(decisions,flush=True)
if __name__=='__main__':main()
