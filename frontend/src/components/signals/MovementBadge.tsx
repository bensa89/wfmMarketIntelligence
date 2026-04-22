import type { MovementStrength } from '../../types/intelligence';

interface Props {
  strength: MovementStrength | null | undefined;
  size?: 'sm' | 'md';
}

const CONFIG: Record<MovementStrength, { label: string; bg: string; text: string; dot: string }> = {
  weak:           { label: 'Weak',           bg: 'rgba(100,116,139,0.15)', text: '#94a3b8', dot: '#64748b' },
  relevant:       { label: 'Relevant',       bg: 'rgba(59,130,246,0.15)',  text: '#60a5fa', dot: '#3b82f6' },
  strong:         { label: 'Strong',         bg: 'rgba(139,92,246,0.15)',  text: '#a78bfa', dot: '#8b5cf6' },
  market_shaping: { label: 'Market Shaping', bg: 'rgba(251,146,60,0.18)', text: '#fb923c', dot: '#f97316' },
};

export default function MovementBadge({ strength, size = 'sm' }: Props) {
  if (!strength) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-full font-medium ${size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'}`}
        style={{ background: 'rgba(71,85,105,0.2)', color: '#64748b' }}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-slate-600 inline-block" />
        Unassessed
      </span>
    );
  }

  const c = CONFIG[strength];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'}`}
      style={{ background: c.bg, color: c.text }}
    >
      <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: c.dot }} />
      {c.label}
    </span>
  );
}
