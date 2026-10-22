import { ArrowDown, ArrowRight, Check, CheckCheck, ChevronDown, Clock3, Copy, CornerDownLeft, MessageSquareText, Search as SearchIcon, SlidersHorizontal, Sparkles, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, errorMessage } from '../services/api';
import type { FAQ, Match, Metadata, Remote } from '../types';
import { ErrorNotice, Spinner, Tag } from '../components/Shared';

export function SearchPage({ metadata, faqs, threshold, setThreshold }: {
  metadata: Metadata | null; faqs: FAQ[]; threshold: number; setThreshold: (value: number) => void;
}) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<Remote<Match>>({ kind: 'idle' });
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [settings, setSettings] = useState(false);
  const [copied, setCopied] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function submit(event?: FormEvent, example?: string) {
    event?.preventDefault();
    const text = (example ?? query).trim();
    if (!text) return;
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setQuery(text); setSubmittedQuery(text); setCopied(false); setResult({ kind: 'loading' });
    try {
      const data = await api.match(text, threshold, current.signal);
      setResult({ kind: 'success', data });
      setHistory(previous => [text, ...previous.filter(q => q !== text)].slice(0, 5));
    } catch (error) {
      if (!current.signal.aborted) setResult({ kind: 'error', message: errorMessage(error) });
    }
  }
  const examples = ['Order Tracking', 'Refunds', 'Account'].map(category => faqs.find(faq => faq.category === category)).filter(faq => faq !== undefined);
  return <>
    <div className="search-intro"><div className="eyebrow"><span className="small-dot" /> A LITTLE CLARITY GOES A LONG WAY</div>
      <h1>Your questions.<br /><span>The right answers.</span></h1>
      <p>Ask in your own words. Find the answer that understands what you mean.</p>
    </div>
    <div className="stats-strip">
      <div><span className="stat-icon"><MessageSquareText size={19} /></span><div><strong>{metadata?.faq_count ?? '—'}</strong><span>FAQs in your knowledge base</span></div></div>
      <div><span className="stat-icon"><Sparkles size={19} /></span><div><strong>{metadata?.categories.length ?? '—'}</strong><span>Categories covered</span></div></div>
      <div><span className="stat-icon"><SlidersHorizontal size={19} /></span><div><strong>{threshold.toFixed(2)} <small>threshold</small></strong><span>Adjustable matching sensitivity</span></div></div>
    </div>
    <div className="search-layout"><div className="search-main">
      <section className="panel query-panel"><div className="panel-header"><h2><SearchIcon size={18} /> Find an answer</h2><Tag tone="gray">Semantic search</Tag></div>
        <form onSubmit={event => void submit(event)}><label htmlFor="question">What would you like to know?</label>
          <div className="textarea-wrap"><textarea id="question" placeholder="e.g. How do I find out where my order is?" value={query} maxLength={2000} onChange={event => setQuery(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) void submit(event); }} />
            {query && <button type="button" className="clear-query" onClick={() => setQuery('')} aria-label="Clear question"><X size={16} /></button>}
            <span className="character-count">{query.length}/2000</span></div>
          <div className="query-actions"><span><CornerDownLeft size={13} /> Ctrl + Enter to search</span><button className="primary" disabled={!query.trim() || result.kind === 'loading'}>{result.kind === 'loading' ? <Spinner /> : <Sparkles size={16} />}{result.kind === 'loading' ? 'Finding your answer…' : 'Find answer'}<ArrowRight size={16} /></button></div>
        </form>
        <div className="try-examples"><span>NEED A STARTING POINT?</span><div>{examples.map(faq => <button key={faq.faq_id} onClick={() => void submit(undefined, faq.question)}>{faq.category}<ArrowUpIcon /></button>)}</div></div>
      </section>
      <div aria-live="polite" aria-busy={result.kind === 'loading'}>
        {result.kind === 'idle' && <div className="empty-answer"><div className="empty-icon"><MessageSquareText size={25} /><Sparkles size={12} /></div><h3>A good answer starts with a question</h3><p>Your best match and related FAQs will appear here.</p><div className="empty-dots"><span /><span /><span /></div></div>}
        {result.kind === 'loading' && <div className="empty-answer"><Spinner /><h3>Looking for the closest meaning…</h3><p>Comparing your question with the FAQ knowledge base.</p></div>}
        {result.kind === 'error' && <ErrorNotice message={result.message} retry={() => void submit()} />}
        {result.kind === 'success' && <div className="result-stack">
          <div className="result-caption"><span>RESULT FOR “{submittedQuery}”</span><span><Clock3 size={12} />{result.data.elapsed_ms.toFixed(0)} ms</span></div>
          <section className={`panel answer-panel ${result.data.status === 'Match found' ? 'accepted' : ''}`}>
            <div className="answer-top"><Tag tone={result.data.status === 'Match found' ? 'green' : 'amber'}>{result.data.status === 'Match found' && <Check size={12} />}{result.data.status}</Tag><span className="mono">Score {result.data.similarity.toFixed(4)}</span></div>
            {result.data.matched_question && <h2>{result.data.matched_question}</h2>}<p className="answer-text">{result.data.answer}</p>
            <div className="answer-footer"><span>{result.data.faq_id && <code>{result.data.faq_id}</code>} {result.data.category ?? `Below the ${result.data.threshold.toFixed(2)} threshold`}</span>
              <button className="icon-text" onClick={() => { void navigator.clipboard.writeText(result.data.answer).then(() => setCopied(true)).catch(() => setCopied(false)); }} aria-label="Copy answer">{copied ? <CheckCheck size={15} /> : <Copy size={15} />}{copied ? 'Copied' : 'Copy'}</button></div>
          </section>
          <div className="section-title"><h3>Top candidates</h3><span>Ranked by combined score</span></div>
          {result.data.top_matches.map((match, i) => <details className="panel candidate" key={match.faq_id}><summary><span className="rank">0{i + 1}</span><div><strong>{match.question}</strong><span>{match.category} <span className="separator">/</span> {match.faq_id}</span></div><span className="candidate-score">{match.score.toFixed(4)}</span><ChevronDown size={15} /></summary><div className="candidate-detail"><p>{match.answer}</p><div><span>Cosine similarity <b>{match.semantic_similarity.toFixed(4)}</b></span><span>Keyword overlap <b>{match.keyword_overlap.toFixed(4)}</b></span></div></div></details>)}
          <p className="caption">Scores measure similarity, not the probability that an answer is correct.</p>
        </div>}
      </div>
    </div>
    <aside className="search-aside"><section className="how-card"><span className="aside-icon"><Sparkles size={20} /></span><h3>Meaning over keywords.</h3><p>You don't need the exact words. Clarity connects your question to the most relevant FAQ.</p><div className="how-steps"><div><span>01</span><div><strong>Understand the question</strong><p>Encode its meaning with MiniLM.</p></div></div><ArrowDown size={14} /><div><span>02</span><div><strong>Compare & rank</strong><p>85% semantic + 15% keywords.</p></div></div><ArrowDown size={14} /><div><span>03</span><div><strong>Find a useful answer</strong><p>Return a match above your threshold.</p></div></div></div><div className="local-badge"><span className="small-dot" /> Local model. No API key needed.</div></section>
      <section className="panel tuning-card"><button className="settings-toggle" onClick={() => setSettings(!settings)} aria-expanded={settings}><span><SlidersHorizontal size={16} /> Search settings</span><ChevronDown size={16} /></button>{settings && <div className="settings-content"><label htmlFor="search-threshold">Match threshold <b>{threshold.toFixed(2)}</b></label><input id="search-threshold" type="range" min="0" max="1" step="0.01" value={threshold} onChange={event => setThreshold(Number(event.target.value))} /><p>Higher values reject more questions. The initial 0.45 setting has not been established as optimal.</p><button className="text-button" onClick={() => setThreshold(0.45)}>Reset to 0.45</button></div>}</section>
      {history.length > 0 && <section className="recent"><div className="section-title"><h3>Recent questions</h3><button className="text-button" onClick={() => setHistory([])}>Clear</button></div>{history.map(text => <button key={text} onClick={() => void submit(undefined, text)}><Clock3 size={14} /><span>{text}</span><ArrowRight size={13} /></button>)}</section>}
    </aside></div>
    <div className="page-footnote"><span className="small-dot" /> Built on your knowledge. Powered by sentence transformers.</div>
  </>;
}
function ArrowUpIcon() { return <ArrowRight size={12} className="example-arrow" />; }
