import type { SignalsFeedFilters, MovementStrength } from '../../types/intelligence';
import type { SignalType } from '../../types';
import { CAPABILITIES } from '../../constants/capabilities';

interface Props {
  filters: SignalsFeedFilters;
  companies: Array<{ id: string; name: string }>;
  onChange: (f: Partial<SignalsFeedFilters>) => void;
  onReset: () => void;
}

const SIGNAL_TYPES: SignalType[] = [
  'product_update', 'ai_announcement', 'partnership', 'positioning_change',
  'target_market_change', 'event_or_thought_leadership', 'hiring_signal', 'other',
];

const MOVEMENT_STRENGTHS: MovementStrength[] = ['weak', 'relevant', 'strong', 'market_shaping'];

const SORT_OPTIONS = [
  { value: 'published_at', label: 'Date' },
  { value: 'movement_score', label: 'Movement Score' },
  { value: 'confidence', label: 'Confidence' },
] as const;

export default function SignalFeedFilters({ filters, companies, onChange, onReset }: Props) {
  const hasActiveFilters = !!(
    filters.company_id || filters.capability || filters.signal_type ||
    filters.movement_strength || filters.min_confidence
  );

  return (
    <div
      className="sticky top-0 z-10 flex flex-wrap items-center gap-2 px-6 py-3 -mx-6 mb-4"
      style={{ background: '#0a0f1e', borderBottom: '1px solid rgba(255,255,255,0.06)' }}
    >
      {/* Company */}
      <select
        value={filters.company_id ?? ''}
        onChange={(e) => onChange({ company_id: e.target.value || undefined, page: 1 })}
        className="rounded-lg text-[12px] px-2.5 py-1.5 text-slate-300 focus:outline-none"
        style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        <option value="">All Competitors</option>
        {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>

      {/* Capability */}
      <select
        value={filters.capability ?? ''}
        onChange={(e) => onChange({ capability: e.target.value || undefined, page: 1 })}
        className="rounded-lg text-[12px] px-2.5 py-1.5 text-slate-300 focus:outline-none"
        style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        <option value="">All Capabilities</option>
        {Object.values(CAPABILITIES).filter((c) => c.visibilityToUser).map((c) => (
          <option key={c.key} value={c.key}>{c.label}</option>
        ))}
      </select>

      {/* Signal Type */}
      <select
        value={filters.signal_type ?? ''}
        onChange={(e) => onChange({ signal_type: e.target.value || undefined, page: 1 })}
        className="rounded-lg text-[12px] px-2.5 py-1.5 text-slate-300 focus:outline-none"
        style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        <option value="">All Types</option>
        {SIGNAL_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
      </select>

      {/* Movement Strength */}
      <select
        value={filters.movement_strength ?? ''}
        onChange={(e) => onChange({ movement_strength: (e.target.value as MovementStrength) || undefined, page: 1 })}
        className="rounded-lg text-[12px] px-2.5 py-1.5 text-slate-300 focus:outline-none"
        style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        <option value="">All Strengths</option>
        {MOVEMENT_STRENGTHS.map((s) => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
      </select>

      {/* Sort */}
      <select
        value={filters.sort_by ?? 'published_at'}
        onChange={(e) => onChange({ sort_by: e.target.value as 'published_at' | 'movement_score' | 'confidence' })}
        className="rounded-lg text-[12px] px-2.5 py-1.5 text-slate-300 focus:outline-none"
        style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>Sort: {o.label}</option>)}
      </select>

      {hasActiveFilters && (
        <button
          onClick={onReset}
          className="text-[12px] text-slate-500 hover:text-slate-300 transition-colors px-2 py-1"
        >
          Reset
        </button>
      )}
    </div>
  );
}
