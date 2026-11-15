import type { Explanation, Lang } from './api';
import './result-explanation.css';

export function ResultExplanation({ explanation, lang }: { explanation: Explanation; lang: Lang }) {
  const en = lang === 'en';
  const assessments = explanation.assessments || [];
  // Reason sections are presented once, next to their associated assessment.
  const reasonIds = new Set(assessments.flatMap(a => a.reasons.map(r => `${a.variable_id}_${r.code}`)));
  const judgmentIds = new Set(assessments.map(a => `${a.variable_id}_judgment`));
  const sections = (explanation.sections || []).filter(s => !reasonIds.has(s.section_id) && !judgmentIds.has(s.section_id));
  return <div className="result-explanation" dir={en ? 'ltr' : 'rtl'}>
    <p className="result-explanation-label">{en ? 'Result interpretation · Scientific rules and templates' : 'تفسير النتيجة · قواعد وقوالب علمية'}</p>
    {assessments.map(assessment => <section className="result-assessment" key={assessment.variable_id}
      data-assessment-status={assessment.descriptive_status}>
      <h3>{assessment.headline}</h3>
      <p className="assessment-scope">{en ? 'This assessment applies to the selected area and time window.' : 'هذا التقييم يخص المساحة والفترة المختارتين.'}</p>
      <ul>{assessment.reasons.map(reason => <li key={reason.code} data-reason-code={reason.code}
        className={`assessment-reason assessment-${reason.severity}`}>{reason.message}</li>)}</ul>
    </section>)}
    {sections.length ? sections.map(section => <section className="result-explanation-section" key={section.section_id}>
      <h4>{section.title}</h4><p>{section.body}</p>
    </section>) : !explanation.sections && <p>{explanation.explanation.answer}</p>}
    {explanation.citations.length > 0 && <details className="result-explanation-sources">
      <summary>{en ? 'Source documentation' : 'وثائق المصادر'}</summary>
      <ul>{explanation.citations.map((citation, index) => <li key={`${citation.source_url}-${index}`}>
        <a href={citation.source_url} target="_blank" rel="noreferrer">{en ? `Source ${index+1}` : `المصدر ${index+1}`}</a>
      </li>)}</ul>
    </details>}
  </div>;
}
