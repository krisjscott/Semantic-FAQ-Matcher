import { ArrowRight, Code2, Cpu, Database, Fingerprint } from 'lucide-react';
import { PageHeading, Tag } from '../components/Shared';
import type { Metadata } from '../types';

export function AboutPage({ metadata }: { metadata: Metadata | null }) {
  return <><PageHeading eyebrow="UNDER THE HOOD" title="Built around meaning" description="Your notebook's matching approach, connected to a complete local application." />
    <section className="method-hero panel"><Tag>PS 47 · Semantic FAQ Matcher</Tag><h2>A small model.<br />A useful connection.</h2><p>Clarity retrieves answers from your FAQ dataset. The model embeds questions and compares their meaning. The answer always comes from the CSV.</p><div className="formula"><span>0.85 <small>× cosine similarity</small></span><b>+</b><span>0.15 <small>× keyword overlap</small></span><ArrowRight size={20} /><span>Combined score</span></div></section>
    <div className="about-grid">{[
      { Icon: Cpu, title: 'The same model', text: 'all-MiniLM-L6-v2 runs locally through Sentence Transformers and PyTorch. FAQ embeddings are normalized and computed once at startup.' },
      { Icon: Code2, title: 'The same ranking', text: 'Keyword overlap is the number of shared lowercase word tokens divided by the number of distinct query tokens. The top three combined scores are returned.' },
      { Icon: Database, title: 'Your source data', text: `${metadata?.faq_count ?? 'Your'} FAQs, loaded from semantic_faq_dataset.csv. The original and additional test labels are preserved. Unrelated queries measure rejection.` },
      { Icon: Fingerprint, title: 'Honest measurement', text: '0.45 is the initial threshold, not a proven optimum. Scores are not probabilities. The evaluation lab reports measured results and identifies invalid expected IDs.' },
    ].map(({ Icon, title, text }) => <section className="panel about-card" key={title}><span className="stat-icon"><Icon size={21} /></span><h3>{title}</h3><p>{text}</p></section>)}</div>
    <section className="panel source-details"><h3>Dataset fingerprint</h3><p>SHA-256 identifies the FAQ snapshot loaded by this backend process.</p><code>{metadata?.dataset_sha256 ?? 'Waiting for the backend…'}</code></section>
    <div className="docs-links"><a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">Explore API documentation <ArrowRight size={15} /></a><a href="https://sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html" target="_blank" rel="noreferrer">Sentence Transformers documentation <ArrowRight size={15} /></a></div>
  </>;
}
