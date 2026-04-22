import { useState, useEffect, useRef } from 'react';
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
  lastMonth?: boolean;
  onLastMonthChange?: (v: boolean) => void;
  searchQuery?: string;
  onSearchQueryChange?: (v: string) => void;
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
  lastMonth,
  onLastMonthChange,
  searchQuery = '',
  onSearchQueryChange,
}: FilterBarProps) {
  const [localSearch, setLocalSearch] = useState(searchQuery);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    setLocalSearch(searchQuery);
  }, [searchQuery]);

  const handleSearchInput = (value: string) => {
    setLocalSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onSearchQueryChange?.(value);
    }, 300);
  };

  const clearSearch = () => {
    setLocalSearch('');
    if (debounceRef.current) clearTimeout(debounceRef.current);
    onSearchQueryChange?.('');
  };

  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      {onSearchQueryChange && (
        <div className="relative">
          <svg
            className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            value={localSearch}
            onChange={(e) => handleSearchInput(e.target.value)}
            placeholder="Signale durchsuchen..."
            className="text-[12px] py-1.5 h-8 pl-8 pr-7 bg-white border border-slate-200 rounded-lg text-slate-600 w-56 focus:outline-none focus:border-blue-300"
          />
          {localSearch && (
            <button
              onClick={clearSearch}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      )}

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

      {onLastMonthChange && (
        <button
          onClick={() => onLastMonthChange(!lastMonth)}
          className={`px-3 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
            lastMonth
              ? 'bg-amber-100 border-amber-300 text-amber-700'
              : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
          }`}
        >
          Letzter Monat
        </button>
      )}
    </div>
  );
}