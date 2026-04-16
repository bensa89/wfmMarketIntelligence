interface RelevanceBadgeProps {
  score: number | null;
  size?: 'sm' | 'md';
}

export default function RelevanceBadge({ score, size = 'md' }: RelevanceBadgeProps) {
  if (score === null || score === undefined) {
    return <span className={`text-dark-muted ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>N/A</span>;
  }

  const pct = Math.round(score * 100);
  let colorClass: string;
  if (score >= 0.7) {
    colorClass = 'bg-signal-high/20 text-signal-high';
  } else if (score >= 0.4) {
    colorClass = 'bg-signal-medium/20 text-signal-medium';
  } else {
    colorClass = 'bg-signal-low/20 text-signal-low';
  }

  const sizeClass = size === 'sm' ? 'text-xs px-1.5 py-0.5' : 'text-sm px-2 py-1';

  return (
    <span className={`inline-flex items-center rounded font-medium ${colorClass} ${sizeClass}`}>
      {pct}%
    </span>
  );
}
