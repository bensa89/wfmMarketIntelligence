interface Props {
  value: number | null | undefined;
  showLabel?: boolean;
}

export default function ConfidenceBar({ value, showLabel = true }: Props) {
  if (value == null) return <span className="text-slate-600 text-[11px]">—</span>;

  const pct = Math.round(value * 100);
  const color = pct >= 80 ? '#22c55e' : pct >= 60 ? '#3b82f6' : pct >= 40 ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-slate-700 overflow-hidden flex-shrink-0">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      {showLabel && (
        <span className="text-[11px] tabular-nums" style={{ color }}>
          {pct}%
        </span>
      )}
    </div>
  );
}
