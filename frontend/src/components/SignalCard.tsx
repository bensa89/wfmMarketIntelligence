import { Link } from 'react-router-dom';
import type { Signal } from '../types';
import RelevanceBadge from './RelevanceBadge';
import SignalTypeIcon from './SignalTypeIcon';
import { formatPublishedAt } from '../utils/dates';

interface SignalCardProps {
  signal: Signal;
  showCompany?: boolean;
  companyName?: string;
  companySlug?: string;
  onClick?: () => void;
}

export default function SignalCard({ signal, showCompany = false, companyName, companySlug, onClick }: SignalCardProps) {
  const { label: dateLabel, isUnknown: dateUnknown } = formatPublishedAt(signal.published_at);

  const cardContent = (
    <>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-[13px] font-semibold text-ink leading-snug mb-1.5">
            {signal.title}
          </h3>
          <div className="flex items-center gap-1.5 flex-wrap">
            <SignalTypeIcon type={signal.signal_type} variant="chip" />
            {signal.topic && (
              <span className="text-[10px] text-ink-muted bg-app-bg px-1.5 py-0.5 rounded-md border border-app-border">
                {signal.topic}
              </span>
            )}
            {signal.from_search && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-md font-semibold"
                style={{ background: '#f5f3ff', color: '#6d28d9' }}>
                Search
              </span>
            )}
          </div>
        </div>
        <RelevanceBadge score={signal.relevance_score} size="sm" />
      </div>

      {signal.summary && (
        <p className="text-[12px] text-ink-secondary line-clamp-2 mb-2 leading-relaxed">
          {signal.summary}
        </p>
      )}
      {signal.why_it_matters && (
        <p className="text-[11px] line-clamp-2 mb-2 leading-relaxed"
          style={{ color: '#2563eb' }}>
          <span className="font-semibold">Why it matters:</span> {signal.why_it_matters}
        </p>
      )}

      <div className="flex items-center justify-between mt-3 text-[11px] text-ink-muted border-t border-app-border pt-2">
        <span className={dateUnknown ? 'italic text-ink-muted/60' : ''}>
          {dateLabel}
        </span>
        {showCompany && companyName && (
          <span className="font-medium text-accent-blue">{companyName}</span>
        )}
      </div>
    </>
  );

  const baseClass = "block w-full text-left bg-app-card border border-app-border rounded-xl p-4 transition-colors hover:border-accent-blue/40 hover:shadow-sm";

  if (onClick) {
    return <button onClick={onClick} className={baseClass}>{cardContent}</button>;
  }
  if (companySlug) {
    return <Link to={`/competitors/${companySlug}`} className={baseClass}>{cardContent}</Link>;
  }
  return <div className={baseClass}>{cardContent}</div>;
}
