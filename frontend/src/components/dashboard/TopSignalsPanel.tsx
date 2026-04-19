import type { Signal, CrawlRunList } from '../../types';
import SignalTypeIcon from '../SignalTypeIcon';
import RelevanceBadge from '../RelevanceBadge';

interface TopSignalsPanelProps {
  signals: Signal[];
  lastCrawl: CrawlRunList | null;
  maxItems?: number;
  onSignalClick?: (signal: Signal) => void;
}

export default function TopSignalsPanel({ signals, lastCrawl, maxItems = 5, onSignalClick }: TopSignalsPanelProps) {
  const lastCrawlTime = lastCrawl?.started_at ? new Date(lastCrawl.started_at) : null;

  let displaySignals = signals;
  if (lastCrawlTime) {
    displaySignals = signals.filter(
      (s) => new Date(s.created_at) >= lastCrawlTime!
    );
  }
  displaySignals = displaySignals
    .sort((a, b) => (b.relevance_score ?? 0) - (a.relevance_score ?? 0))
    .slice(0, maxItems);

  if (displaySignals.length === 0) {
    return (
      <div>
        <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider mb-2">Top neue Signale</p>
        <p className="text-[12px] text-slate-400">Keine neuen Signale seit letztem Crawl.</p>
      </div>
    );
  }

  return (
    <div>
      <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider mb-2">Top neue Signale</p>
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        {displaySignals.map((signal) => {
          const isNew = lastCrawlTime && new Date(signal.created_at) >= lastCrawlTime;
          const isUpdated = lastCrawlTime && !isNew && signal.from_search;
          return (
            <div
              key={signal.id}
              onClick={() => onSignalClick?.(signal)}
              className="flex items-center gap-2 px-3 py-2 border-b border-slate-100 last:border-b-0 hover:bg-slate-50 cursor-pointer transition-colors"
            >
              {isNew ? (
                <span className="text-[9px] font-bold bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded shrink-0">NEW</span>
              ) : isUpdated ? (
                <span className="text-[9px] font-bold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded shrink-0">UPD</span>
              ) : (
                <span className="w-[30px] shrink-0" />
              )}
              <SignalTypeIcon type={signal.signal_type} variant="chip" />
              <span className="flex-1 text-[11px] font-semibold text-slate-900 truncate">{signal.title}</span>
              <RelevanceBadge score={signal.relevance_score} variant="badge" size="sm" />
            </div>
          );
        })}
      </div>
    </div>
  );
}