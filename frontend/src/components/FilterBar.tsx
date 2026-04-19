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
  { value: 'product_update',              label: 'Product' },
  { value: 'ai_announcement',             label: 'AI' },
  { value: 'partnership',                 label: 'Partnership' },
  { value: 'positioning_change',          label: 'Positioning' },
  { value: 'target_market_change',        label: 'Market Shift' },
  { value: 'event_or_thought_leadership', label: 'Events' },
  { value: 'hiring_signal',               label: 'Hiring' },
];

const relevanceLevels: { value: number; label: string }[] = [
  { value: 0,   label: 'Alle' },
  { value: 0.4, label: '≥ 40%' },
  { value: 0.7, label: '≥ 70%' },
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
    <div className="flex flex-wrap items-center gap-2 mb-4">
      {/* Company picker */}
      {companies && onCompanyChange && (
        <select
          value={companyId || ''}
          onChange={(e) => onCompanyChange(e.target.value)}
          className="input-field text-[12px] py-1.5 h-8"
        >
          <option value="">Alle Unternehmen</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      )}

      {/* Divider */}
      {companies && <div className="w-px h-5 bg-app-border" />}

      {/* Signal type pills */}
      <button
        onClick={() => onSignalTypeChange('')}
        className={`px-3 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
          signalType === ''
            ? 'bg-accent-blue/10 border-accent-blue/30 text-accent-blue'
            : 'bg-app-card border-app-border text-ink-secondary hover:bg-app-bg'
        }`}
      >
        Alle
      </button>
      {signalTypes.map((t) => (
        <button
          key={t.value}
          onClick={() => onSignalTypeChange(signalType === t.value ? '' : t.value)}
          className={`px-3 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
            signalType === t.value
              ? 'bg-accent-blue/10 border-accent-blue/30 text-accent-blue'
              : 'bg-app-card border-app-border text-ink-secondary hover:bg-app-bg'
          }`}
        >
          {t.label}
        </button>
      ))}

      {/* Divider */}
      <div className="w-px h-5 bg-app-border" />

      {/* Relevance level pills */}
      {relevanceLevels.map((r) => (
        <button
          key={r.value}
          onClick={() => onMinRelevanceChange(r.value)}
          className={`px-3 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
            minRelevance === r.value
              ? 'bg-signal-high/10 border-signal-high/30 text-signal-high'
              : 'bg-app-card border-app-border text-ink-secondary hover:bg-app-bg'
          }`}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}
