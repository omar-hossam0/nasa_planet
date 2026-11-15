import { useState } from 'react';
import type { Analysis, Lang } from './api';
import './analysis-insights.css';

const number=(value:number,digits=4)=>value.toLocaleString('en-US',{maximumFractionDigits:digits});

export function InferenceNotice({lang}:{lang:Lang}) {
  const en=lang==='en';
  return <details className="inference-notice">
    <summary>{en?'Why are p-value and confidence interval unavailable?':'لماذا قيمة p وفترة الثقة غير متاحتين؟'}</summary>
    <div className="inference-steps">
      <div><b>✓</b><span>{en?'Measurements + QA':'البيانات وفحص الجودة'}</span><small>{en?'Processed':'تمت المعالجة'}</small></div>
      <div><b>✓</b><span>{en?'Descriptive slope':'الميل الوصفي'}</span><small>{en?'Computed':'محسوب'}</small></div>
      <div><b>—</b><span>{en?'Statistical inference':'الاستدلال الإحصائي'}</span><small>{en?'Not released':'غير معتمد حاليًا'}</small></div>
    </div>
    <p>{en?'The slope describes estimated annual change in the observed record. It does not establish a statistically confirmed trend. The current inference method has not passed its validation gate, so this app withholds p-values and confidence intervals.':'الميل يصف التغيّر السنوي التقديري في البيانات المرصودة، ولا يثبت اتجاهًا مؤكدًا إحصائيًا. طريقة الاستدلال الحالية لم تجتز بوابة التحقق، لذلك لا يعرض التطبيق قيمة p أو فترة ثقة.'}</p>
    <p><strong>p-value:</strong> {en?'the probability, under a specified null model, of a test result at least as extreme as the observed one. It is not the probability that the trend is real.':'احتمال نتيجة اختبار مساوية أو أكثر تطرفًا من المرصودة تحت فرضية العدم والنموذج المحدد. ليست احتمال أن الاتجاه حقيقي.'}</p>
    <p><strong>{en?'95% confidence interval:':'فترة الثقة 95%:'}</strong> {en?'an interval from a validated uncertainty procedure around the slope. No interval is being estimated here. Missing is not zero.':'مجال ناتج من طريقة معتمدة لقياس عدم اليقين حول الميل. لا يتم تقدير هذا المجال هنا، وعدم توفره لا يعني صفرًا.'}</p>
  </details>;
}

export function AnalysisInsights({analysis,lang,variableId}:{analysis:Analysis;lang:Lang;variableId:string}) {
  const [selected,setSelected]=useState<number|null>(null);
  const en=lang==='en';
  const variable=analysis.result.variables.find(v=>v.variable_id===variableId);
  if (!variable?.annual) return null;
  const annual=variable.annual;
  const unitLabel=variable.units==='1'?(en?'unitless':'بدون وحدة'):variable.units;
  const finite=annual.values.filter((v):v is number=>v!=null&&Number.isFinite(v));
  const low=finite.length?Math.min(...finite):0, high=finite.length?Math.max(...finite):1;
  const span=high-low||1;
  const x=(year:number)=>60+(year-annual.years[0])/Math.max(1,annual.years.at(-1)!-annual.years[0])*510;
  const y=(value:number)=>high===low?114:190-(value-low)/span*150;
  const path=annual.values.map((v,index)=>v==null?'':`${index===0||annual.values[index-1]==null?'M':'L'}${x(annual.years[index])},${y(v)}`).join(' ');
  const selectedIndex=Math.min(selected??annual.years.length-1,annual.years.length-1);
  const slopes=(analysis.spatial?.slope.flat()||[]).filter((v):v is number=>v!=null&&Number.isFinite(v));
  const minimum=slopes.length?Math.min(...slopes):0, maximum=slopes.length?Math.max(...slopes):1;
  const bins=Array.from({length:12},()=>0);
  slopes.forEach(value=>bins[Math.min(11,Math.floor((value-minimum)/(maximum-minimum||1)*12))]++);
  const peak=Math.max(1,...bins);
  const counts=variable.cell_counts;
  const support=variable.support;
  const retained=support?.eligible_area_fraction??0;
  return <section className="analysis-insights" dir={en?'ltr':'rtl'} aria-labelledby="insights-heading">
    <header><span className="insight-eyebrow">UNDERSTAND THE RESULT</span>
      <h2 id="insights-heading">{en?'From observations to estimated change':'من البيانات إلى التغيّر التقديري'}</h2>
      <p>{en?'These views use the stored science output. They do not add a significance test or predict future values.':'الرسوم مبنية على مخرجات التحليل المحفوظة. لا تضيف اختبار دلالة ولا تتنبأ بقيم مستقبلية.'}</p></header>
    <div className="insights-grid">
      <article className="insight-card annual-card">
        <h3>{en?'Annual observations':'القيم السنوية'}</h3>
        <p>{variable.variable_id==='precipitation' ? (en?'Complete annual accumulated precipitation, mm.':'الهطول السنوي المتراكم للسنوات المكتملة، بوحدة مم.') : (en?`Calendar-day-weighted annual mean, ${unitLabel}.`:`المتوسط السنوي الموزون بأيام الشهور، ${unitLabel}.`)}</p>
        {finite.length>0?<svg viewBox="0 0 600 235" role="img" aria-label={en?'Annual observed values. No forecast or confidence band.':'القيم السنوية المرصودة، بدون توقع أو نطاق ثقة.'} className="annual-observations">
          <path d="M60 40H570 M60 115H570 M60 190H570" stroke="#d4e0da" strokeDasharray="4 5" fill="none"/>
          <text x="8" y="45">{number(high,3)}</text><text x="8" y="195">{number(low,3)}</text>
          <text x="60" y="219">{annual.years[0]}</text><text x="540" y="219">{annual.years.at(-1)}</text>
          <path d={path} className="annual-path"/>
          {annual.values.map((value,index)=>value==null?null:<circle key={annual.years[index]} cx={x(annual.years[index])} cy={y(value)} r={selectedIndex===index?6:3.5}
            className="annual-point" onMouseEnter={()=>setSelected(index)} onFocus={()=>setSelected(index)} tabIndex={0}
            aria-label={`${annual.years[index]}: ${number(value,6)} ${variable.units}`}><title>{annual.years[index]}: {number(value,6)} {variable.units}</title></circle>)}
        </svg>:<p>{en?'No complete annual observations are available for this selection.':'لا تتوفر قيم سنوية مكتملة لهذا الاختيار.'}</p>}
        <div className="annual-readout"><b>{annual.years[selectedIndex]}</b><span>{annual.values[selectedIndex]==null?(en?'Missing':'غير متاح'):number(annual.values[selectedIndex]!,6)} {unitLabel}</span></div>
        <label htmlFor="annual-year">{en?'Inspect a year':'استكشف سنة'}</label>
        <input id="annual-year" type="range" min={0} max={Math.max(0,annual.years.length-1)} value={selectedIndex} onChange={event=>setSelected(Number(event.target.value))}/>
        <small>{en?'Vertical scale follows the observed range. The annual slope summarizes change; the line connects observations, not a fitted forecast.':'المقياس الرأسي يتبع نطاق القيم المرصودة. الميل يلخص التغيّر، والخط يربط القيم ولا يمثل توقعًا.'}</small>
        <details><summary>{en?'View annual values':'اعرض القيم السنوية'}</summary><div className="annual-table"><table><thead><tr><th>{en?'Year':'السنة'}</th><th>{variable.units}</th></tr></thead><tbody>{annual.years.map((year,index)=><tr key={year}><td>{year}</td><td>{annual.values[index]==null?'—':number(annual.values[index]!,6)}</td></tr>)}</tbody></table></div></details>
      </article>
      <article className="insight-card">
        <h3>{en?'Local cells can differ':'الخلايا قد تختلف محليًا'}</h3>
        <p>{en?'Distribution of computed annual cell slopes. This is spatial variation, not a confidence interval.':'توزيع ميول الخلايا السنوية المحسوبة. يصف الاختلاف المكاني، وليس فترة ثقة.'}</p>
        {slopes.length ? <svg viewBox="0 0 360 185" role="img" aria-label={en?'Histogram of observed cell slopes':'توزيع تكراري لميول الخلايا'} className="slope-histogram">
          <text x="18" y="15">{en?'Cells per bin':'خلايا لكل نطاق'} · {peak} {en?'max':'كحد أقصى'}</text>
          {bins.map((count,index)=>{const start=minimum+index*(maximum-minimum)/12,end=minimum+(index+1)*(maximum-minimum)/12;return <rect key={index} x={18+index*27} y={135-count/peak*110} width={23} height={count/peak*110}
            fill={start<=0&&end>=0?'#899ca2':start>0?'#398b64':'#bb784c'}><title>{number(start,6)} – {number(end,6)}: {count} {en?'cells':'خلية'}</title></rect>;})}
          <path d="M18 136H342" stroke="#849c96"/><text x="18" y="158">{number(minimum,5)}</text><text x="270" y="158">{number(maximum,5)}</text><text x="18" y="178">{variable.trend?.slope_units}</text>
        </svg>:<p>{en?'No cell estimates available.':'لا تتوفر تقديرات للخلايا.'}</p>}
        <small>{en?'Green: positive range. Orange: negative range. Grey: a bin touching zero.':'الأخضر نطاق موجب، والبرتقالي نطاق سالب، والرمادي نطاق يلامس الصفر.'}</small>
        {counts&&<dl className="cell-direction-counts"><div><dt>{en?'Positive':'موجب'}</dt><dd>{counts.positive}</dd></div><div><dt>{en?'Negative':'سالب'}</dt><dd>{counts.negative}</dd></div><div><dt>{en?'Exactly zero':'صفر تمامًا'}</dt><dd>{counts.zero}</dd></div><div><dt>{en?'Eligible, unavailable':'مؤهل، غير متاح'}</dt><dd>{counts.unavailable}</dd></div></dl>}
        <small>{en?'Counts refer to QA-eligible cells. A positive or negative sign does not mean statistical significance.':'العدّ يخص الخلايا المقبولة بالجودة. الإشارة الموجبة أو السالبة لا تعني دلالة إحصائية.'}</small>
      </article>
      <article className="insight-card">
        <h3>{en?'What area supports this result?':'ما المساحة التي تمثلها النتيجة؟'}</h3>
        {support&&<><svg viewBox="0 0 200 165" role="img" aria-label={`${number(retained*100,1)}% ${en?'of selected native-cell area retained':'من مساحة الخلايا الأصلية المختارة تم الاحتفاظ بها'}`} className="coverage-donut">
          <circle cx="100" cy="78" r="55" className="donut-track"/>
          <circle cx="100" cy="78" r="55" className="donut-retained" pathLength="100" strokeDasharray={`${retained*100} 100`} transform="rotate(-90 100 78)"/>
          <text x="100" y="79" textAnchor="middle" className="donut-value">{number(retained*100,1)}%</text><text x="100" y="100" textAnchor="middle">{en?'retained area':'المساحة المقبولة'}</text>
        </svg><p className="coverage-count">{support.eligible_cells.toLocaleString()} / {support.selected_cells.toLocaleString()} {en?'cells retained':'خلية تم الاحتفاظ بها'}</p></>}
        <div className="coverage-meter"><span>{en?'Valid monthly regional values':'القيم الشهرية الإقليمية الصالحة'}</span><strong>{number(variable.counts.valid_fraction*100,1)}%</strong><div><i style={{width:`${variable.counts.valid_fraction*100}%`}}/></div></div>
        <small>{en?'A complete monthly series may describe only the retained footprint. Temporal completeness and spatial coverage answer different questions.':'قد تكون السلسلة الشهرية مكتملة لكنها تصف المساحة المقبولة فقط. اكتمال الزمن والتغطية المكانية مقياسان مختلفان.'}</small>
      </article>
    </div>
    <InferenceNotice lang={lang}/>
  </section>;
}
