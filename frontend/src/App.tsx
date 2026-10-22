import { ArrowUpRight, BookOpen, ChevronRight, CircleHelp, Code2, FlaskConical, Layers, Menu, MessageSquareText, Search, X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { ErrorNotice, Spinner } from './components/Shared';
import { AboutPage } from './pages/About';
import { EvaluationPage } from './pages/Evaluation';
import { LibraryPage } from './pages/Library';
import { SearchPage } from './pages/Search';
import { api, errorMessage } from './services/api';
import type { FAQ, Metadata, Remote } from './types';

const pages = [
  { id: 'search', label: 'Find an answer', Icon: Search },
  { id: 'knowledge', label: 'Knowledge base', Icon: BookOpen },
  { id: 'evaluation', label: 'Evaluation lab', Icon: FlaskConical },
  { id: 'about', label: 'How it works', Icon: CircleHelp },
];
function pageFromHash() { const hash = window.location.hash.slice(1); return pages.some(p => p.id === hash) ? hash : 'search'; }

export default function App() {
  const [page, setPage] = useState(pageFromHash);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [threshold, setThreshold] = useState(0.45);
  const [remote, setRemote] = useState<Remote<{ metadata: Metadata; faqs: FAQ[] }>>({ kind: 'loading' });
  const load = useCallback(async (signal?: AbortSignal) => {
    setRemote({ kind: 'loading' });
    try {
      const [metadata, faqs] = await Promise.all([api.metadata(signal), api.faqs(signal)]);
      setRemote({ kind: 'success', data: { metadata, faqs } });
    } catch (error) { if (!signal?.aborted) setRemote({ kind: 'error', message: errorMessage(error) }); }
  }, []);
  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => controller.abort(); }, [load]);
  useEffect(() => { const change = () => { setPage(pageFromHash()); setMobileMenu(false); }; window.addEventListener('hashchange', change); return () => window.removeEventListener('hashchange', change); }, []);
  const metadata = remote.kind === 'success' ? remote.data.metadata : null;
  const faqs = remote.kind === 'success' ? remote.data.faqs : [];
  return <div className="app-shell min-h-screen selection:bg-emerald-100">
    {mobileMenu && <button className="mobile-overlay" aria-label="Close navigation" onClick={() => setMobileMenu(false)} />}
    <aside className={`sidebar ${mobileMenu ? 'is-open' : ''}`}><a className="brand" href="#search"><span className="brand-mark"><MessageSquareText size={24} /></span><span>clarity<span className="brand-period">.</span></span></a>
      <div className="workspace-label">YOUR WORKSPACE</div><nav aria-label="Main navigation">{pages.map(({ id, label, Icon }) => <a key={id} href={`#${id}`} className={page === id ? 'active' : ''} aria-current={page === id ? 'page' : undefined}><Icon size={18} /><span>{label}</span>{page === id && <span className="nav-dot" />}{id === 'knowledge' && metadata && <small>{metadata.faq_count}</small>}</a>)}</nav>
      <div className="sidebar-project"><span className="project-glyph"><Layers size={17} /></span><div><strong>Semantic FAQ Matcher</strong><span>Problem statement 47</span></div></div>
      <div className="sidebar-bottom"><div className="model-status"><span className={`status-dot ${remote.kind === 'success' ? 'online' : ''}`} /><div><strong>{remote.kind === 'success' ? 'Model connected' : remote.kind === 'loading' ? 'Connecting to model…' : 'Backend unavailable'}</strong><span>all-MiniLM-L6-v2</span></div>{remote.kind === 'loading' && <Spinner />}</div><div className="sidebar-footer"><span>LOCAL WORKSPACE</span><span>v1.0</span></div></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div><button className="menu-button" aria-label={mobileMenu ? 'Close navigation' : 'Open navigation'} onClick={() => setMobileMenu(!mobileMenu)}>{mobileMenu ? <X size={20} /> : <Menu size={20} />}</button><span className="breadcrumb-root">Workspace</span><ChevronRight size={13} /><strong>{pages.find(p => p.id === page)?.label}</strong></div><a className="topbar-link" href="#about"><span className="small-dot" /> Semantic FAQ Matcher <ArrowUpRight size={13} /></a></header>
      <main className={page === 'search' ? 'main-content search-content' : 'main-content'}>
        {remote.kind === 'error' && <ErrorNotice message={remote.message} retry={() => void load()} />}
        {page === 'search' && <SearchPage metadata={metadata} faqs={faqs} threshold={threshold} setThreshold={setThreshold} />}
        {page === 'knowledge' && (remote.kind === 'loading' ? <div className="empty-answer"><Spinner /><h3>Loading your knowledge base…</h3></div> : <LibraryPage metadata={metadata} faqs={faqs} />)}
        {page === 'evaluation' && <EvaluationPage metadata={metadata} threshold={threshold} setThreshold={setThreshold} />}
        {page === 'about' && <AboutPage metadata={metadata} />}
      </main><footer className="app-footer"><span>Clarity turns questions into answers.</span><span><Code2 size={13} /> React + FastAPI <span className="footer-dot">·</span> Runs locally</span></footer>
    </div>
  </div>;
}
