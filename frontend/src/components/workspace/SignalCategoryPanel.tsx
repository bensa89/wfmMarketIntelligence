import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useCompetitorSignalStats } from '../../hooks/useCompetitorSignalStats';
import { labelMap } from '../SignalTypeIcon';

interface Props {
  slug: string;
  days: 30 | 90;
}

export default function SignalCategoryPanel({ slug, days }: Props) {
  const { data, isLoading, error } = useCompetitorSignalStats(slug, days);
  const nonZero = data?.by_category.filter((c) => c.count > 0) ?? [];
  const chartData = nonZero.map((c) => ({ label: labelMap[c.signal_type], count: c.count }));

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <h2 className="text-[13px] font-semibold text-slate-800 mb-3">Signals nach Kategorie</h2>

      {isLoading && <p className="text-slate-400 text-[12px]">Lädt…</p>}
      {error && <p className="text-red-500 text-[12px]">Fehler: Daten konnten nicht geladen werden (failed).</p>}
      {data && nonZero.length === 0 && (
        <p className="text-slate-400 text-[12px]">No signals in this period.</p>
      )}
      {data && nonZero.length > 0 && (
        <ResponsiveContainer width="100%" height={Math.max(120, nonZero.length * 32)}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey="label"
              tick={{ fontSize: 11, fill: '#475569' }}
              axisLine={false}
              tickLine={false}
              width={140}
            />
            <Tooltip formatter={(value) => [Number(value ?? 0), 'Signals']} />
            <Bar dataKey="count" fill="#3b82f6" radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
