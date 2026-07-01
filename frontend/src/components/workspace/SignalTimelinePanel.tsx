import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useCompetitorSignalStats } from '../../hooks/useCompetitorSignalStats';
import type { SignalStatsTimelinePoint } from '../../types/intelligence';

interface Props {
  slug: string;
  days: 30 | 90;
}

function formatBucketLabel(bucket: string, granularity: 'day' | 'week'): string {
  const d = new Date(`${bucket}T00:00:00Z`);
  if (granularity === 'week') {
    const onejan = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    const week = Math.ceil(((d.getTime() - onejan.getTime()) / 86400000 + onejan.getUTCDay() + 1) / 7);
    return `KW ${week}`;
  }
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
}

export default function SignalTimelinePanel({ slug, days }: Props) {
  const { data, isLoading, error } = useCompetitorSignalStats(slug, days);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-[13px] font-semibold text-slate-800">Signal-Aktivität</h2>
        {data && (
          <span className="text-[11px] text-slate-400">
            {data.total} Signal{data.total === 1 ? '' : 's'} in den letzten {days} Tagen
          </span>
        )}
      </div>

      {isLoading && <p className="text-slate-400 text-[12px]">Lädt…</p>}
      {error && <p className="text-red-500 text-[12px]">Fehler: Daten konnten nicht geladen werden (failed).</p>}
      {data && data.total === 0 && (
        <p className="text-slate-400 text-[12px]">No signals in this period.</p>
      )}
      {data && data.total > 0 && (
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data.timeline as SignalStatsTimelinePoint[]}>
            <XAxis
              dataKey="bucket"
              tickFormatter={(v: string) => formatBucketLabel(v, data.granularity)}
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              axisLine={{ stroke: '#e2e8f0' }}
              tickLine={false}
            />
            <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={24} />
            <Tooltip
              labelFormatter={(v) => formatBucketLabel(String(v ?? ''), data.granularity)}
              formatter={(value) => [Number(value ?? 0), 'Signals']}
            />
            <Bar dataKey="count" fill="#3b82f6" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
