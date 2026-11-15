import sys,json,time,calendar
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/science'))
from src.reml_uncertainty import fit_reml,simulate_ar,geometry
from src.inference import wilson_interval
from run_science_inference_study import ar1
from research_reml_uncertainty import frozen
from review_sahel_ndvi import sha,write_json
OUT=ROOT/'data/derived/science_inference/double_bootstrap'
REPORTS=ROOT/'packages/science/phase_reports'

def caches(n,seed,c):
 inner=[];outer=[];critical=[];rho=geometry(n)[0]
 for j,r in enumerate(rho):
  noise=simulate_ar(np.random.default_rng(np.random.SeedSequence([seed,301,n,j])).normal(size=(c['inner_replicates'],n)),r)
  f=fit_reml(noise);inner.append(np.sort(abs(f['slope']/f['se'])))
 for j,r in enumerate(rho):
  noise=simulate_ar(np.random.default_rng(np.random.SeedSequence([seed,902,n,j])).normal(size=(c['outer_replicates'],n)),r)
  f=fit_reml(noise);stat=abs(f['slope']/f['se']);ri=np.rint((f['rho']+.5)/.025).astype(int)
  p=np.empty(len(stat))
  for k in np.unique(ri):
   mask=ri==k;p[mask]=(1+len(inner[k])-np.searchsorted(inner[k],stat[mask],side='left'))/(len(inner[k])+1)
  outer.append(np.sort(p))
  # Outer calibration changes the test construction, not its .05 threshold.
  rawcut=outer[-1][int(np.floor(.05*(len(p)+1)))-1]
  critical.append(float(np.quantile(inner[j],1-rawcut,method='higher')))
 return inner,outer,np.array(critical)

def stage(c,name):
 seed=c[name+'_seed'];N=c['pilot_records'] if name=='pilot' else c['validation_records'];rows=[]
 for n in c['lengths']:
  inner,outer,critical=caches(n,seed,c)
  for phi in c['phis']:
   for season in c['seasonal_profiles']:
    code=int(season!='none');rng=np.random.default_rng(np.random.SeedSequence([seed,n,int(phi*100),code]))
    y=ar1(rng,N,n,phi)
    if code:
     pattern=3*np.sin(2*np.pi*np.arange(12)/12)
     y+=np.array([np.average(pattern,weights=[calendar.monthrange(2001+i,m)[1] for m in range(1,13)]) for i in range(n)])
    f=fit_reml(y);ri=np.rint((f['rho']+.5)/.025).astype(int)
    for truth in c['slopes']:
     point=f['slope']+truth;stat=abs(point/f['se']);p=np.empty(N)
     for j in np.unique(ri):
      mask=ri==j;raw=(1+len(inner[j])-np.searchsorted(inner[j],stat[mask],side='left'))/(len(inner[j])+1)
      p[mask]=(1+np.searchsorted(outer[j],raw,side='right'))/(len(outer[j])+1)
     lo=point-critical[ri]*f['se'];hi=point+critical[ri]*f['se']
     rej=int((p<=.05).sum());cover=int(((lo<=truth)&(hi>=truth)).sum());rate=rej/N;cov=cover/N
     a=c['acceptance'];row={'stage':name,'n':n,'phi':phi,'season':season,'truth':truth,'trials':N,'rejected':rej,'covered':cover,'rejection_rate':rate,'coverage':cov,'rejection_mc95':wilson_interval(rej,N),'coverage_mc95':wilson_interval(cover,N),'mean_width':float(np.mean(hi-lo)),'failures':0}
     row['passes_screen']=bool(a['coverage_target_band'][0]<=cov<=a['coverage_target_band'][1] and row['coverage_mc95'][0]>=a['coverage_lower_wilson_min'] and (a['null_rate_target_band'][0]<=rate<=a['null_rate_target_band'][1] and row['rejection_mc95'][1]<=a['null_upper_wilson_max'] if truth==0 else row['rejection_mc95'][0]>=a['power_lower_wilson_min']))
     rows.append(row)
    print(name,n,phi,season,flush=True)
 return rows

def main():
 OUT.mkdir(parents=True,exist_ok=True);start=time.perf_counter();path=ROOT/'packages/science/config/double_bootstrap_research.json';c=json.loads(path.read_text());before=frozen()
 extra=REPORTS/'PHASE_4_REML_RESEARCH.json';before[extra.relative_to(ROOT).as_posix()]=sha(extra)
 identity={'config':sha(path),'script':sha(Path(__file__))}
 write_json(OUT/'protocol_before_evaluation.json',{'config':c,'identity':identity,'prior_hashes':before})
 pilot=stage(c,'pilot');final=stage(c,'validation')
 for p,h in before.items():assert sha(ROOT/p)==h,p
 write_json(REPORTS/'PHASE_4_DOUBLE_BOOTSTRAP.json',{'config':c,'identity':identity,'pilot':pilot,'validation':final,'failed_scenarios':sum(not r['passes_screen'] for r in final),'prior_hashes':before,'application_release':False,'phase5_started':False,'elapsed_seconds':time.perf_counter()-start,'limitations':['finite rho grid','inner/outer calibration caches shared across trials; Wilson intervals conditional on caches','Gaussian AR1 model required','grid and simulation error need sensitivity before release']})
 print('FAILED SCENARIOS',sum(not r['passes_screen'] for r in final),flush=True)
if __name__=='__main__':main()
