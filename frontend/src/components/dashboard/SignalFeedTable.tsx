import type { Signal, CrawlRunList, Company } from '../../types';
import SignalTypeIcon from '../SignalTypeIcon';
import RelevanceBadge from '../RelevanceBadge';
import { getCompanyColor } from './CompanyColorMap';
import { formatPublishedAt } from '../../utils/dates';

interface SignalFeedTableProps {
  signals: Signal[];
  companies: Company[];
  lastCrawl: CrawlRunList | null;
  onSignalClick?: (signal: Signal) => void;
}

export default function SignalFeedTable({ signals, companies, lastCrawl, onSignalClick }: SignalFeedTableProps) {
  const lastCrawlTime = lastCrawl?.started_at ? new Date(lastCrawl.started_at) : null;

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div
        className="grid text-[10px] font-semibold uppercase tracking-wider text-slate-500 px-4 py-2.5 border-b border-slate-200 bg-slate-50"
        style={{ gridTemplateColumns: 'minmax(0,2.2fr) minmax(0,1fr) 140px 80px 70px' }}
      >
        <span>Signal</span>
        <span>Unternehmen</span>
        <span>Typ</span>
        <span>Datum</span>
        <span>Relevanz</span>
      </div>

      {signals.length === 0 && (
        <p className="text-slate-400 text-[13px] text-center py-8">Keine Signale gefunden.</p>
      )}

      {signals.map((signal) => {
        const company = companies.find((c) => c.id === signal.company_id);
        const { label: dateLabel, isUnknown: dateUnknown } = formatPublishedAt(signal.published_at);

        const isNew = lastCrawlTime && new Date(signal.created_at) >= lastCrawlTime;
        const isUpdated = lastCrawlTime && !isNew && signal.from_search;

        return (
          <div
            key={signal.id}
            onClick={() => onSignalClick?.(signal)}
            className={`grid items-center px-4 py-3 border-b border-slate-100 last:border-b-0 hover:bg-slate-50 cursor-pointer transition-colors ${
              isNew ? 'bg-blue-50/40' : ''
            }`}
            style={{ gridTemplateColumns: 'minmax(0,2.2fr) minmax(0,1fr) 140px 80px 70px' }}
          >
            <div className="min-w-0 pr-2">
              <div className="flex items-center gap-1.5">
                {isNew ? (
                  <span className="text-[9px] font-bold bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded shrink-0">NEW</span>
                ) : isUpdated ? (
                  <span className="text-[9px] font-bold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded shrink-0">UPD</span>
                ) : null}
                <p className="text-[12px] font-semibold text-slate-900 truncate">{signal.title}</p>
              </div>
              {signal.why_it_matters && (
                <p className="text-[10px] text-blue-600 truncate mt-0.5">
                  {signal.why_it_matters}
                </p>
              )}
            </div>
            <div className="flex items-center gap-1.5 min-w-0">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ background: company ? getCompanyColor(company.id) : '#a1a1aa' }}
              />
              <span className="text-[12px] font-medium text-slate-600 truncate">{company?.name ?? '—'}</span>
            </div>
            <div>
              <SignalTypeIcon type={signal.signal_type} variant="chip" />
            </div>
            <span className={`text-[11px] ${dateUnknown ? 'text-slate-300 italic' : 'text-slate-500'}`}>
              {dateLabel}
            </span>
            <RelevanceBadge score={signal.relevance_score} variant="bar" />
          </div>
        );
      })}
    </div>
  );
}