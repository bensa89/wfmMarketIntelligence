interface ConfidenceIndicatorProps {
  confidence: number;
  showLabel?: boolean;
}

export function ConfidenceIndicator({ confidence, showLabel = false }: ConfidenceIndicatorProps) {
  const filled = Math.round(confidence * 5);
  const label = confidence >= 0.8 ? 'High' : confidence >= 0.5 ? 'Med' : 'Low';
  return (
    <span className="inline-flex items-center gap-1" title={`Confidence: ${Math.round(confidence * 100)}%`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <span
          key={i}
          className={`h-1.5 w-1.5 rounded-full ${i < filled ? 'bg-slate-600' : 'bg-slate-200'}`}
        />
      ))}
      {showLabel && <span className="ml-1 text-xs text-slate-500">{label}</span>}
    </span>
  );
}