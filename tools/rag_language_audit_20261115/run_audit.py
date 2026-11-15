"""Retained bilingual generated-composition audit, no live provider calls."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'backend')]
from packages.rag.retriever import Retriever
OUT=Path(__file__).resolve().parent
TERMS={
 'air_temperature':{'en':['air temperature','warmer','hotter','cooling','air temp','temprature','heating up','temperature'],'ar':['حرارة الهواء','بتسخن','بيسخن','الاحترار','حراره الجو','حرارة الهوا','بتبرد','درجة الحرارة']},
 'soil_moisture':{'en':['soil moisture','soil water','soil wetness','dry soil','soil humidity','soil drying','water in soil','topsoil moisture'],'ar':['رطوبة التربة','رطوبه التربه','مياه التربة','التربة ناشفة','جفاف التربه','بلل التربة','رطوبة الارض','مية التربة']},
 'precipitation':{'en':['rain','rainfall','precipitation','raining','rainier','rain totals','rain fall','preciptation'],'ar':['المطر','الأمطار','امطار','بتمطر','الهطول','المطر بيقل','هطول','مطر']},
 'vegetation_greenness':{'en':['NDVI','vegetation','greener','plant cover','vegetation health','plant greenness','vegetation cover','greenness'],'ar':['NDVI','الخضرة','الغطاء النباتي','اخضرار النبات','النباتات','غطاء نباتي','الخضره','النبات بيقل']}}
WRAPPERS={'en':['What is {}?','Explain {}.','Show changes in {}.','What are the limitations of {}?','I want to study {} in the Nile Delta.','Tell me about {} in Morocco.','Can I compare {} across years?','What does NASA say about {}?'],
 'ar':['يعني إيه {}؟','اشرح {} لو سمحت','عايز أشوف التغير في {}','إيه قيود بيانات {}؟','عايز أعرف {} في دلتا النيل','وريني {} في المغرب','ينفع أشوف {} عبر السنين؟','وضحلي {} من بيانات ناسا']}
HOLDOUT={'air_temperature':{'en':['air temperatures','temperature changes','getting warmer'],'ar':['الحرارة بتزيد','درجة حرارة الجو','حرارة الهواء بتقل']},
 'soil_moisture':{'en':['soil moisture changes','soil getting wetter','soil getting drier'],'ar':['التربة بتجف','محتوى التربة من المياه','رطوبة التربة بتقل']},
 'precipitation':{'en':['annual rainfall','monthly precipitation','rainfall decreasing'],'ar':['مجموع المطر السنوي','كمية الأمطار الشهرية','الأمطار بتزيد']},
 'vegetation_greenness':{'en':['vegetation greeness','NDVI changes','plants getting greener'],'ar':['مؤشر اخضرار النباتات','تغير الغطاء النباتي','قيمة NDVI']}}

def main():
    started=time.perf_counter();cases=[]
    for split,words in [('development',TERMS),('heldout_compositions',HOLDOUT)]:
        for variable,langs in words.items():
            for language,terms in langs.items():
                for term in terms:
                    for wrapper in WRAPPERS[language]:
                        cases.append({'split':split,'language':language,'query':wrapper.format(term),'variables':[variable],'status':None})
    safeguards=[('drought','ambiguous'),('الجفاف','ambiguous'),('رطوبة','ambiguous'),('humidity','ambiguous'),('sea surface temperature','unsupported'),('حرارة البحر','unsupported'),('predict air temperature','unsupported'),('توقع الأمطار','unsupported'),('temperature in 1990','unavailable'),('rainfall in 2030','unavailable'),('earthquake prediction','unsupported'),('football scores','unsupported')]
    for query,status in safeguards:
        for wrapper in ['{}','{}?','Please explain {}','عايز أفهم {}','{} لو سمحت']:
            cases.append({'split':'scope_safety','language':'mixed','query':wrapper.format(query),'variables':None,'status':status})
    (OUT/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf-8')
    retriever=Retriever();corpus={c['chunk_id']:c for c in retriever.chunks};rows=[]
    for c in cases:
        answer=retriever.answer_query(c['query'])
        correct=(set(answer['variable_ids'])==set(c['variables']) and bool(answer['citations'])) if c['variables'] is not None else answer['status']==c['status']
        errors=[x['chunk_id'] for x in answer['citations'] if x['chunk_id'] not in corpus or any(x[k]!=corpus[x['chunk_id']][k] for k in ['text','source_url','raw_source_hash'])]
        rows.append({**c,'passed':correct and not errors,'actual_variables':answer['variable_ids'],'actual_status':answer['status'],'reason':answer.get('reason_code'),'citation_errors':errors})
    summary={'cases':len(rows),'passed':sum(r['passed'] for r in rows),'failed':sum(not r['passed'] for r in rows),'by_split':{s:{'total':sum(r['split']==s for r in rows),'failed':sum(r['split']==s and not r['passed'] for r in rows)} for s in ['development','heldout_compositions','scope_safety']},'elapsed_seconds':round(time.perf_counter()-started,2),'limitations':'Generated compositions, not independent real-user accuracy; heldout phrases reuse wrappers; no live LLM evaluation.'}
    for name,value in [('results.json',rows),('summary.json',summary)]: (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary));print(json.dumps([r for r in rows if not r['passed']][:12],ensure_ascii=True))

if __name__=='__main__':main()
