interface Props {
  label: string;
  value: number;
  accent: string;
  valueClassName?: string;
}

export default function KPICard({ label, value, accent, valueClassName }: Props) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className={`h-[3px] ${accent}`} />
      <div className="px-4 py-3">
        <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-1">{label}</div>
        <div className={`text-[28px] font-extrabold leading-none tabular-nums ${valueClassName ?? 'text-slate-900'}`}>
          {value}
        </div>
      </div>
    </div>
  );
}
