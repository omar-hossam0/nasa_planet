import { useEffect, useRef, useState } from 'react';
import type { Lang, RegionId, VariableId } from './api';
import './rag-chat.css';

type Citation = { chunk_id: string; title: string; source_url: string; text: string; section_locator?: string };
export type AnalysisProposal = { region_id: RegionId; variable_ids: VariableId[]; start_month: string; end_month: string };
type Reply = { mode: string; status: string; answer: string | null; citations: Citation[];
  provider_http_status?: number; fallback_reason?: string;
  workflow?: { state: string; message: string; analysis_request: AnalysisProposal | null };
  excerpts?: Citation[]; context?: { definition_chunks?: Citation[] }; limitations?: string[];
  message?: string; clarification?: string; capability_note: string };
type Turn = { question: string; reply: Reply };

function sourceLink(value: string) {
  try { const url = new URL(value); return url.protocol === 'https:' ? url.href : undefined; }
  catch { return undefined; }
}

export function RagChat({ lang, region, start, end, onProposal }: { lang: Lang; region: RegionId; start?: string; end?: string; onProposal?: (proposal: AnalysisProposal) => void }) {
  const en = lang === 'en';
  const [question, setQuestion] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const active = useRef<AbortController | null>(null);
  useEffect(() => {
    active.current?.abort(); active.current = null; setTurns([]); setError(''); setBusy(false);
    return () => active.current?.abort();
  }, [region]);

  async function send() {
    const query = question.trim();
    if (!query || busy) return;
    const controller = new AbortController(); active.current = controller;
    const timeout = setTimeout(() => controller.abort(), 30000);
    setBusy(true); setError('');
    try {
      const response = await fetch('/v1/explanations/ask', { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ query, language: lang, region_id: region || null, start_month: start, end_month: end }) });
      const reply = await response.json();
      if (!response.ok) throw new Error(reply?.error?.message || `Request failed (${response.status})`);
      if (controller.signal.aborted) return;
      setTurns(previous => [...previous.slice(-9), { question: query, reply }]);
      setQuestion('');
    } catch (failure) {
      if (active.current !== controller) return;
      setError(controller.signal.aborted
        ? (en ? 'The request was cancelled or timed out. Try again.' : 'الطلب اتلغى أو تجاوز وقت الانتظار. جرّب تاني.')
        : failure instanceof Error ? failure.message : String(failure));
    } finally {
      clearTimeout(timeout);
      if (active.current === controller) { active.current = null; setBusy(false); }
    }
  }

  return <section className="rag-chat" aria-labelledby="rag-heading" dir={en ? 'ltr' : 'rtl'}>
    <header><div><span className="eyebrow">DOCUMENTATION ASSISTANT</span>
      <h2 id="rag-heading">{en ? 'Ask the RAG assistant' : 'اسأل مساعد المعرفة'}</h2></div>
      <button type="button" disabled={busy || !turns.length} onClick={() => setTurns([])}>{en ? 'Clear' : 'مسح'}</button></header>
    <p>{en ? 'Ask about climate variables and NASA documentation. Each question is independent; this assistant does not read your analysis results or calculate statistics.' : 'اسأل عن متغيرات المناخ ووثائق ناسا. كل سؤال مستقل؛ المساعد لا يقرأ نتيجة تحليلك ولا يحسب إحصائيات.'}</p>
    <div className="rag-examples">{(en ? ['What is precipitation?', 'What is NDVI?', 'What is soil moisture?'] : ['ما هو الهطول؟', 'ما هو NDVI؟', 'ما هي رطوبة التربة؟']).map(example =>
      <button type="button" disabled={busy} key={example} onClick={() => setQuestion(example)}>{example}</button>)}</div>
    <div className="rag-turns" aria-live="polite" aria-busy={busy}>
      {turns.map((turn, index) => {
        const reply = turn.reply;
        const evidence = [...new Map([...reply.citations, ...(reply.context?.definition_chunks || []), ...(reply.excerpts || [])].map(c => [c.chunk_id, c])).values()];
        return <article key={index} className="rag-turn">
          <h3>{turn.question}</h3>
          {reply.provider_http_status === 429 && <p role="status">{en ? 'Gemini is currently rate-limited or out of quota. A source-based explanation is shown when available.' : 'Gemini رفض الطلب بسبب حد الطلبات أو الحصة. يُعرض شرح موثّق من القوالب عند توفره.'}</p>}
          {reply.workflow && <div className="rag-workflow">
            <p>{reply.workflow.message}</p>
            {reply.workflow.analysis_request && onProposal && <>
              <p>{reply.workflow.analysis_request.region_id} · {reply.workflow.analysis_request.variable_ids.join(', ')} · {reply.workflow.analysis_request.start_month} — {reply.workflow.analysis_request.end_month}</p>
              <button type="button" onClick={() => onProposal(reply.workflow!.analysis_request!)}>{en ? 'Run this analysis' : 'شغّل التحليل ده'}</button>
            </>}
          </div>}
          <span className="rag-mode">{reply.mode === 'grounded_template' ? (en ? 'Source-based explanation (template; no LLM)' : '\u0634\u0631\u062d \u0645\u0648\u062b\u0642 \u0628\u0627\u0644\u0642\u0648\u0627\u0644\u0628') : reply.mode === 'llm' ? (en ? 'Generated answer · validated citations' : 'إجابة مولدة بمراجع متحقق منها') : (en ? 'Retrieved excerpts · no generated answer' : 'مقاطع مسترجعة · بدون إجابة مولدة')}</span>
          <p>{reply.answer || reply.clarification || reply.message || (evidence.length ? (en ? 'Relevant documentation is shown below.' : 'الوثائق المرتبطة بسؤالك موجودة بالأسفل.') : (en ? 'No supporting documentation was found. Try a question about the project variables.' : 'لم نجد وثائق تدعم السؤال. جرّب سؤال عن متغيرات المشروع.'))}</p>
          {evidence.map(citation => <details key={citation.chunk_id} className="rag-citation">
            <summary>{citation.title} · {citation.section_locator || citation.chunk_id}</summary>
            <p dir="auto">{citation.text}</p>
            {sourceLink(citation.source_url) && <a href={sourceLink(citation.source_url)} target="_blank" rel="noopener noreferrer">{en ? 'Open source' : 'افتح المصدر'}</a>}
            <code>{citation.chunk_id}</code>
          </details>)}
          {!!reply.limitations?.length && <ul>{reply.limitations.map((limitation,i) => <li key={i}>{limitation}</li>)}</ul>}
        </article>;
      })}
      {busy && <p role="status">{en ? 'Searching documentation…' : 'جاري البحث في الوثائق…'}</p>}
    </div>
    <form onSubmit={event => { event.preventDefault(); void send(); }}>
      <label htmlFor="rag-question">{en ? 'Your question' : 'سؤالك'}</label>
      <textarea id="rag-question" maxLength={500} rows={3} value={question} disabled={busy}
        onChange={event => setQuestion(event.target.value)} placeholder={en ? 'Ask about precipitation, temperature, soil moisture or NDVI…' : 'اسأل عن الهطول أو الحرارة أو رطوبة التربة أو NDVI…'} />
      <footer><small>{question.length}/500</small><button type="submit" disabled={busy || !question.trim()}>{en ? 'Ask' : 'اسأل'}</button></footer>
      {error && <p role="alert">{error}</p>}
    </form>
  </section>;
}
