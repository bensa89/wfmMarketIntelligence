import type { SignalType, CompanyType } from '../types';

interface FilterBarProps {
  signalType: SignalType | '';
  onSignalTypeChange: (v: SignalType | '') => void;
  minRelevance: number;
  onMinRelevanceChange: (v: number) => void;
  companyId?: string;
  onCompanyChange?: (v: string) => void;
  companies?: { id: string; name: string; type: CompanyType }[];
}

const signalTypes: { value: SignalType; label: string }[] = [
  { value: 'product_update', label: 'Product Update' },
  { value: 'ai_announcement', label: 'AI Announcement' },
  { value: 'partnership', label: 'Partnership' },
  { value: 'positioning_change', label: 'Positioning Change' },
  { value: 'target_market_change', label: 'Market Shift' },
  { value: 'event_or_thought_leadership', label: 'Thought Leadership' },
  { value: 'hiring_signal', label: 'Hiring Signal' },
  { value: 'other', label: 'Other' },
];

export default function FilterBar({
  signalType,
  onSignalTypeChange,
  minRelevance,
  onMinRelevanceChange,
  companyId,
  onCompanyChange,
  companies,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-4">
      {companies && onCompanyChange && (
        <select
          value={companyId || ''}
          onChange={(e) => onCompanyChange(e.target.value)}
          className="input-field"
        >
          <option value="">All Companies</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      )}
      <select
        value={signalType}
        onChange={(e) => onSignalTypeChange(e.target.value as SignalType | '')}
        className="input-field"
      >
        <option value="">All Types</option>
        {signalTypes.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>
      <div className="flex items-center gap-2">
        <label className="text-sm text-dark-muted">Min Relevance:</label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={minRelevance}
          onChange={(e) => onMinRelevanceChange(parseFloat(e.target.value))}
          className="w-24 accent-dark-accent"
        />
        <span className="text-sm text-dark-text w-8">
          {Math.round(minRelevance * 100)}%
        </span>
      </div>
    </div>
  );
}
