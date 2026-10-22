import { AlertCircle, ArrowUpRight, LoaderCircle } from 'lucide-react';
import type { ReactNode } from 'react';

export function Spinner() { return <LoaderCircle size={17} className="spin" aria-label="Loading" />; }
export function ErrorNotice({ message, retry }: { message: string; retry?: () => void }) {
  return <div role="alert" className="error-notice"><AlertCircle size={18} /><span>{message}</span>{retry && <button onClick={retry}>Try again <ArrowUpRight size={14} /></button>}</div>;
}
export function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
export function Tag({ children, tone = 'green' }: { children: ReactNode; tone?: 'green' | 'gray' | 'amber' }) {
  return <span className={`tag ${tone}`}>{children}</span>;
}
export function percent(value: number | null) { return value === null ? 'Not available' : `${(value * 100).toFixed(1)}%`; }
