interface RelevanceBadgeProps {
  score: number | null;
  /** 'badge' = colored pill; 'bar' = progress bar + number (for tables) */
  variant?: 'badge' | 'bar';
  size?: 'sm' | 'md';
}

export default function RelevanceBadge({ score, variant = 'badge', size = 'md' }: RelevanceBadgeProps) {
  if (score === null || score === undefined) {
    return <span className="text-ink-muted text-xs">N/A</span>;
  }

  const pct = Math.round(score * 100);
  const isHigh   = score >= 0.7;
  const isMedium = score >= 0.4;

  const badgeStyle = isHigh
    ? { background: '#dcfce7', color: '#15803d' }
    : isMedium
    ? { background: '#fef3c7', color: '#92400e' }
    : { background: '#fee2e2', color: '#b91c1c' };

  const barColor = isHigh ? '#10b981' : isMedium ? '#f59e0b' : '#ef4444';

  if (variant === 'bar') {
    return (
      <div className="flex items-center gap-2 w-full">
        <div className="flex-1 h-1 bg-app-border rounded-full overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{ width: `${pct}%`, background: barColor }}
          />
        </div>
        <span className="text-[11px] font-bold text-ink min-w-[28px] text-right">{pct}%</span>
      </div>
    );
  }

  const sizeClass = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-1';

  return (
    <span
      className={`inline-flex items-center rounded-md font-semibold ${sizeClass}`}
      style={badgeStyle}
    >
      {pct}%
    </span>
  );
}
