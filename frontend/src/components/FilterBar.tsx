import type { SignalType, CompanyType } from '../types';

interface FilterBarProps {
  signalType: SignalType | '';
  onSignalTypeChange: (v: SignalType | '') => void;
  minRelevance: number;
  onMinRelevanceChange: (v: number) => void;
  companyId?: string;
  onCompanyChange?: (v: string) => void;
  companies?: { id: string; name: string; type: CompanyType }[];
  onlyNew?: boolean;
  onOnlyNewChange?: (v: boolean) => void;
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
  onlyNew,
  onOnlyNewChange,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      {companies && onCompanyChange && (
        <select
          value={companyId || ''}
          onChange={(e) => onCompanyChange(e.target.value)}
          className="text-[12px] py-1.5 h-8 bg-white border border-slate-200 rounded-lg px-2 text-slate-600"
        >
          <option value="">Alle Unternehmen</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      )}

      {companies && <div className="w-px h-5 bg-slate-200" />}

      <button
        onClick={() => onSignalTypeChange('')}
        className={`px-3 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
          signalType === ''
            ? 'bg-blue-100 border-blue-300 text-blue-700'
            : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
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
              ? 'bg-blue-100 border-blue-300 text-blue-700'
              : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
          }`}
        >
          {t.label}
        </button>
      ))}

      <div className="w-px h-5 bg-slate-200" />

      {relevanceLevels.map((r) => (
        <button
          key={r.value}
          onClick={() => onMinRelevanceChange(r.value)}
          className={`px-3 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
            minRelevance === r.value
              ? 'bg-emerald-100 border-emerald-300 text-emerald-700'
              : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
          }`}
        >
          {r.label}
        </button>
      ))}

      {onOnlyNewChange && (
        <>
          <div className="w-px h-5 bg-slate-200" />
          <button
            onClick={() => onOnlyNewChange(!onlyNew)}
            className={`px-3 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
              onlyNew
                ? 'bg-emerald-100 border-emerald-300 text-emerald-700'
                : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
            }`}
          >
            Nur Neue
          </button>
        </>
      )}
    </div>
  );
}