import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const ACCENT_COLORS: Record<string, string> = {
  blue: '#2563eb',
  green: '#10b981',
  amber: '#f59e0b',
  purple: '#7c3aed',
  cyan: '#06b6d4',
  pink: '#ec4899',
  orange: '#f97316',
  red: '#ef4444',
};

interface DeltaKpiCardProps {
  label: string;
  value: string | number;
  delta?: string;
  color: string;
  trend?: 'up' | 'down' | 'neutral';
}

export default function DeltaKpiCard({ label, value, delta, color, trend = 'neutral' }: DeltaKpiCardProps) {
  const accentColor = ACCENT_COLORS[color] || color;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 relative overflow-hidden">
      <div
        className="absolute top-0 left-0 right-0 h-[3px] rounded-t-xl"
        style={{ background: accentColor }}
      />
      <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-2">{label}</p>
      <p className="text-[28px] font-extrabold text-slate-900 leading-none tracking-tight">{value}</p>
      {delta && (
        <p className="text-[11px] font-medium mt-1 flex items-center gap-0.5" style={{
          color: trend === 'up' ? '#10b981' : trend === 'down' ? '#ef4444' : '#64748b',
        }}>
          {trend === 'up' && <TrendingUp size={10} />}
          {trend === 'down' && <TrendingDown size={10} />}
          {trend === 'neutral' && <Minus size={10} />}
          {delta}
        </p>
      )}
    </div>
  );
}