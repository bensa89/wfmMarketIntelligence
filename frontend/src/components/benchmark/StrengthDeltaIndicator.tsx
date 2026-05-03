interface StrengthDeltaIndicatorProps {
  delta: number | null;
}

export function StrengthDeltaIndicator({ delta }: StrengthDeltaIndicatorProps) {
  if (delta === null) return <span className="text-slate-400 text-xs">—</span>;
  if (delta > 0) return <span className="text-emerald-600 text-xs font-medium">↑+{delta}</span>;
  if (delta < 0) return <span className="text-red-500 text-xs font-medium">↓{delta}</span>;
  return <span className="text-slate-400 text-xs">→0</span>;
}