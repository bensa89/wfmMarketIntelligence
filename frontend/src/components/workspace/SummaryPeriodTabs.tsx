import type { CompetitorSummary } from '../../types/intelligence';

interface Props {
  activePeriod: '30d' | '90d';
  onChangePeriod: (p: '30d' | '90d') => void;
  summary30d: CompetitorSummary | null;
  summary90d: CompetitorSummary | null;
}

export default function SummaryPeriodTabs({ activePeriod, onChangePeriod, summary30d, summary90d }: Props) {
  const tabs = [
    { key: '30d' as const, label: '30 Days', summary: summary30d },
    { key: '90d' as const, label: '90 Days', summary: summary90d },
  ];

  return (
    <div className="flex gap-2 mb-4">
      {tabs.map(({ key, label, summary }) => (
        <button
          key={key}
          onClick={() => onChangePeriod(key)}
          className={`px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors flex items-center gap-1.5 border ${
            activePeriod === key
              ? 'bg-blue-50 text-blue-700 border-blue-200'
              : 'text-slate-500 hover:text-slate-700 border-transparent'
          }`}
        >
          {label}
          {!summary && <span className="text-[10px] text-slate-400">(no data)</span>}
        </button>
      ))}
    </div>
  );
}
