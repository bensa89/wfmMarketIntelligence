import { Link } from 'react-router-dom';
import type { Signal } from '../types';
import RelevanceBadge from './RelevanceBadge';
import SignalTypeIcon from './SignalTypeIcon';

interface SignalCardProps {
  signal: Signal;
  showCompany?: boolean;
  companyName?: string;
  companySlug?: string;
}

export default function SignalCard({ signal, showCompany = false, companyName, companySlug }: SignalCardProps) {
  const dateStr = signal.published_at
    ? new Date(signal.published_at).toLocaleDateString('de-DE')
    : new Date(signal.created_at).toLocaleDateString('de-DE');

  const linkTarget = companySlug
    ? `/competitors/${companySlug}`
    : `/competitors/${signal.company_id}`;

  return (
    <Link
      to={linkTarget}
      className="card block hover:border-dark-accent/50 transition-colors"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-dark-text truncate">{signal.title}</h3>
          <div className="flex items-center gap-2 mt-1">
            <SignalTypeIcon type={signal.signal_type} size={14} />
            {signal.topic && (
              <span className="text-xs text-dark-muted px-1.5 py-0.5 bg-dark-bg rounded">
                {signal.topic}
              </span>
            )}
          </div>
        </div>
        <RelevanceBadge score={signal.relevance_score} size="sm" />
      </div>
      {signal.summary && (
        <p className="text-sm text-dark-muted line-clamp-2 mb-2">{signal.summary}</p>
      )}
      {signal.why_it_matters && (
        <p className="text-xs text-indigo-300 line-clamp-2 mb-2">
          <span className="font-medium">Why it matters:</span> {signal.why_it_matters}
        </p>
      )}
      <div className="flex items-center justify-between mt-2 text-xs text-dark-muted">
        <span>{dateStr}</span>
        {showCompany && companyName && (
          <span className="text-dark-accent">{companyName}</span>
        )}
      </div>
    </Link>
  );
}
