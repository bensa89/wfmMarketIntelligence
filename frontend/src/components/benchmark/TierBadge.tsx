import type { BenchmarkTier } from '../../types/benchmark';

const TIER_CONFIG: Record<BenchmarkTier, { label: string; className: string }> = {
  leader: { label: 'Leader', className: 'bg-emerald-600 text-white' },
  strong: { label: 'Strong', className: 'bg-blue-600 text-white' },
  emerging: { label: 'Emerging', className: 'bg-amber-500 text-slate-900' },
  weakly_evidenced: { label: 'Weakly Evidenced', className: 'bg-slate-200 text-slate-500' },
};

interface TierBadgeProps {
  tier: BenchmarkTier;
  size?: 'sm' | 'md';
}

export function TierBadge({ tier, size = 'md' }: TierBadgeProps) {
  const config = TIER_CONFIG[tier] ?? TIER_CONFIG.weakly_evidenced;
  const sizeClass = size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-xs';
  return (
    <span className={`inline-flex items-center rounded font-medium ${sizeClass} ${config.className}`}>
      {config.label}
    </span>
  );
}