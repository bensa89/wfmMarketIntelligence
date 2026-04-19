import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import type { SignalOverTimePoint } from '../../types';
import { getCompanyColor } from './CompanyColorMap';

interface SignalsOverTimeChartProps {
  data: SignalOverTimePoint[];
}

const DAY_OPTIONS = [7, 14, 30] as const;

export default function SignalsOverTimeChart({ data }: SignalsOverTimeChartProps) {
  const [days, setDays] = useState<number>(14);

  const filtered = days === 7
    ? data.slice(-7)
    : days === 14
    ? data.slice(-14)
    : data;

  const companyIds = [...new Set(data.map((d) => d.company_id))];

  const chartData: Record<string, string | number>[] = [];
  const dates = [...new Set(filtered.map((d) => d.date))].sort();
  for (const date of dates) {
    const entry: Record<string, string | number> = { date };
    for (const cid of companyIds) {
      const point = filtered.find((d) => d.date === date && d.company_id === cid);
      entry[cid] = point ? point.count : 0;
    }
    chartData.push(entry);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Signale über Zeit</p>
        <div className="flex gap-1">
          {DAY_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                days === d
                  ? 'bg-blue-100 text-blue-700 border border-blue-300'
                  : 'bg-white text-slate-500 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>
      <div className="bg-white border border-slate-200 rounded-xl p-3">
        {companyIds.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {companyIds.map((cid) => {
              const name = filtered.find((d) => d.company_id === cid)?.company_name ?? cid;
              return (
                <span key={cid} className="flex items-center gap-1 text-[9px]">
                  <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: getCompanyColor(cid) }} />
                  <span className="text-slate-600">{name}</span>
                </span>
              );
            })}
          </div>
        )}
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={chartData} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 9, fill: '#94a3b8' }}
              tickFormatter={(v: string) => {
                const d = new Date(v);
                return `${d.getDate().toString().padStart(2, '0')}.${(d.getMonth() + 1).toString().padStart(2, '0')}`;
              }}
            />
            <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ fontSize: 11, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8 }}
            />
            {companyIds.map((cid) => (
              <Line
                key={cid}
                type="monotone"
                dataKey={cid}
                stroke={getCompanyColor(cid)}
                strokeWidth={1.5}
                dot={false}
                name={filtered.find((d) => d.company_id === cid)?.company_name ?? cid}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}