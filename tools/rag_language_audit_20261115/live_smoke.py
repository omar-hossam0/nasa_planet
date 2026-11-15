"""Four bounded live documentation checks; server-side configuration, no secrets logged."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.api.v1.questions import get_pipeline
OUT=Path(__file__).resolve().parent
cases=json.loads((OUT/'cases.json').read_text(encoding='utf-8'))
queries=[next(c['query'] for c in cases if c['language']==lang and c['variables']==[variable])
         for lang,variable in [('en','air_temperature'),('ar','precipitation'),('en','vegetation_greenness'),('ar','soil_moisture')]]
pipeline=get_pipeline()
rows=[]
for query in queries:
    result=pipeline.explain(query)
    rows.append({'query':query,'mode':result.get('mode'),'status':result.get('status'),
                 'fallback_reason':result.get('fallback_reason'),'answer':result.get('answer'),
                 'citation_count':len(result.get('citations',[]))})
(OUT/'live_smoke.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in row.items() if k not in ('query','answer')} for row in rows]))
