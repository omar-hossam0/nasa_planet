"""Prespecified pilot/fresh holdout inference comparisons; no NASA p-values."""
import sys,json,time,inspect
from pathlib import Path
import numpy as np
from scipy.stats import norm
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/science'))
from src.inference_candidates import adjusted_mk,ar1_regression,gls_fixed_rho
from src.inference import circular_block_indices,wilson_interval
from src.trend_estimation import sen_slopes
from review_sahel_ndvi import sha,write_json
from run_science_inference_study import preserved_inputs,ar1
REPORTS=ROOT/'packages/science/phase_reports'
OUT=ROOT/'data/derived/science_inference/followup'

def snapshot():
 d=preserved_inputs()
 for name in ['PHASE_4_REPORT.md','PHASE_4_STUDY.json','PHASE_4_VALIDATION.json','PHASE_4_DECISION.json']:
  path=REPORTS/name;d[path.relative_to(ROOT).as_posix()]=sha(path)
 for name in ['packages/science/src/inference.py','packages/science/config/inference_policy.json','packages/science/notebooks/04_inference_validation.ipynb']:
  d[name]=sha(ROOT/name)
 return d

def evaluate(config,stage):
 results=[]
 count=config[stage+'_replications'];seed=config[stage+'_seed']
 for n in config['lengths']:
  for phi in config['phis']:
   for seasonal in config['seasonal_profiles']:
    rng=np.random.default_rng(np.random.SeedSequence([seed,n,int(phi*100),int(seasonal!='none')]))
    errors=ar1(rng,count,n,phi)
    seasonal_means=np.zeros(n)
    if seasonal!='none':
     import calendar
     pattern=3*np.sin(2*np.pi*np.arange(12)/12)
     seasonal_means=np.array([np.average(pattern,weights=[calendar.monthrange(2001+y,m)[1] for m in range(1,13)]) for y in range(n)])
    for truth in config['slopes']:
     values=errors+truth*np.arange(n)+seasonal_means
     for name,method in [('adjusted_mk',adjusted_mk),('ar1_regression',ar1_regression)]:
      reject=cover=fail=0;bias=[];rho=[]
      for y in values:
       result=method(y,np.arange(2001,2001+n))
       if result['status']!='candidate':fail+=1;continue
       reject+=result['p']<=.05;cover+=result['interval'][0]<=truth<=result['interval'][1]
       bias.append(result['slope']-truth)
       if 'rho' in result:rho.append(result['rho'])
      valid=count-fail
      row={'stage':stage,'candidate':name,'n':n,'phi':phi,'season':seasonal,'truth':truth,'trials':count,'valid':valid,'failures':fail,
       'rejections':int(reject),'covered':int(cover),'rejection_rate':reject/valid if valid else None,'coverage':cover/valid if valid else None,
       'rejection_mc95':wilson_interval(int(reject),valid) if valid else None,'coverage_mc95':wilson_interval(int(cover),valid) if valid else None,
       'slope_bias':float(np.mean(bias)) if bias else None,'mean_estimated_rho':float(np.mean(rho)) if rho else None}
      a=config['acceptance']
      row['passes_screen']= bool(valid and fail==0 and row['coverage_mc95'][0]>=a['coverage_lower_wilson_min'] and
       (row['rejection_mc95'][1]<=a['null_upper_wilson_max'] if truth==0 else row['rejection_mc95'][0]>=a['power_lower_wilson_min']))
      results.append(row)
    print(stage,n,phi,seasonal,'finished',flush=True)
 return results

def diagnose():
 rng=np.random.default_rng(440158);n=24;rep=499
 population=ar1(np.random.default_rng(550198),5000,n,0)
 true_sd=float(np.std(sen_slopes(population.T,np.arange(n))['slope'],ddof=1))
 noise=rng.normal(size=(200,n));slopes=sen_slopes(noise.T,np.arange(n))['slope']
 modes={name:[] for name in ['fitted_iid','fitted_block4','oracle_noise_iid','oracle_noise_block4','known_gaussian_iid']}
 covered={name:0 for name in modes};variance_ratios=[];unique=[]
 for k,y in enumerate(noise):
  residual=y-slopes[k]*np.arange(n);variance_ratios.append(np.var(residual,ddof=1)/np.var(y,ddof=1))
  for name in modes:
   if name=='known_gaussian_iid': samples=rng.normal(size=(rep,n))
   else:
    values=residual if name.startswith('fitted') else y
    length=4 if name.endswith('block4') else 1
    idx=circular_block_indices(n,rep,length,rng);samples=values[idx]
    if name=='fitted_iid':unique.append(float(np.mean([len(np.unique(i)) for i in idx])))
   err=sen_slopes(samples.T,np.arange(n))['slope']
   modes[name].append(float(np.std(err,ddof=1)))
   lo,hi=np.quantile(err,[.025,.975]);covered[name]+=slopes[k]-hi<=0<=slopes[k]-lo
 return {'seed':440158,'oracle_population_seed':550198,'records':200,'bootstrap_replicates':rep,'n':n,
  'independent_population_records':5000,'true_sampling_slope_sd_mc':true_sd,
  'mean_detrended_to_raw_variance_ratio':float(np.mean(variance_ratios)),
  'mean_unique_positions_in_iid_resample':float(np.mean(unique)),
  'comparisons':{name:{'mean_bootstrap_slope_sd':float(np.mean(sd)),'ratio_to_true_sampling_sd':float(np.mean(sd)/true_sd),
   'coverage':float(covered[name]/200),'coverage_mc95':wilson_interval(int(covered[name]),200)} for name,sd in modes.items()},
  'interpretation':'oracle noise/known Gaussian draws diagnose mechanisms, not deployable methods or unique causal attribution'}

def checks():
 from scipy.linalg import toeplitz
 rng=np.random.default_rng(1)
 max_error=0
 for phi in [-.5,0,.4,.8]:
  y=rng.normal(size=24);x=np.arange(24);X=np.column_stack([np.ones(24),x])
  cov=toeplitz(phi**np.arange(24));inv=np.linalg.inv(cov)
  expected=np.linalg.solve(X.T@inv@X,X.T@inv@y)
  actual=gls_fixed_rho(y,x,phi)[0]
  max_error=max(max_error,float(np.max(abs(actual-expected))))
 assert max_error<1e-10
 for method in [adjusted_mk,ar1_regression]:
  y=rng.normal(size=24);before=y.copy();years=np.arange(2001,2025)
  a=method(y,years);b=method(y+273.15,years)
  assert abs(a['slope']-b['slope'])<1e-10
  np.testing.assert_array_equal(y,before)
  y[2]=np.nan;assert method(y,years)['status']=='insufficient_data';assert np.isnan(y[2])
  assert method(np.ones(24),years)['status']=='no_variation'
 return {'dense_covariance_gls_reference_max_error':max_error,'input_and_missing_preservation':True,'constant_and_short_admission_checked':True}

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 config_path=ROOT/'packages/science/config/inference_followup.json';config=json.loads(config_path.read_text())
 before=snapshot();identity={'config_sha256':sha(config_path),'candidate_code_sha256':sha(ROOT/'packages/science/src/inference_candidates.py'),'runner_sha256':sha(Path(__file__))}
 write_json(OUT/'protocol_before_evaluation.json',{'config':config,'identity':identity,'prior_hashes':before})
 tests=checks();start=time.perf_counter()
 pilot=evaluate(config,'pilot');write_json(OUT/'pilot.json',pilot)
 # No tuning or candidate selection between pilot and holdout. Different seed streams.
 final=evaluate(config,'final');diagnosis=diagnose()
 assert snapshot()==before
 decisions={name:{'passes_all_holdout_screens':all(r['passes_screen'] for r in final if r['candidate']==name),
  'failed_holdout_scenarios':sum(not r['passes_screen'] for r in final if r['candidate']==name),'release':False} for name in ['adjusted_mk','ar1_regression']}
 result={'config':config,'identity':identity,'pilot':pilot,'final':final,'decisions':decisions,'bootstrap_diagnosis':diagnosis,'checks':tests,
  'prior_hashes':before,'preserved_file_count':len(before),'application_release':False,'phase5_started':False,'elapsed_seconds':time.perf_counter()-start,
  'no_nasa_pvalues_used_for_selection':True,'seeds_independent_between_pilot_final_and_diagnosis':True,
  'paired_design':'candidates and trend signs reuse noise within stage; rates use independent trials within each scenario'}
 write_json(REPORTS/'PHASE_4_FOLLOWUP.json',result)
 print('FOLLOWUP COMPLETE',decisions,flush=True)
if __name__=='__main__':main()
