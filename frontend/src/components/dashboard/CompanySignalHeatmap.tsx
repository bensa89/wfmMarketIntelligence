import type { CompanySignalTypeCount } from '../../types';
import { labelMap } from '../SignalTypeIcon';
import { getCompanyColor } from './CompanyColorMap';

const TYPE_KEYS = ['ai_announcement', 'product_update', 'partnership', 'hiring_signal', 'other'] as const;

interface CompanySignalHeatmapProps {
  data: CompanySignalTypeCount[];
  companies: { id: string; name: string }[];
}

function getCellBg(count: number, maxCount: number): React.CSSProperties {
  if (count === 0) return { background: '#f1f5f9', color: '#94a3b8' };
  const intensity = count / Math.max(maxCount, 1);
  if (intensity > 0.6) return { background: '#1e3a8a', color: '#dbeafe' };
  if (intensity > 0.3) return { background: '#3b82f6', color: '#dbeafe' };
  return { background: '#dbeafe', color: '#1e3a8a' };
}

export default function CompanySignalHeatmap({ data, companies }: CompanySignalHeatmapProps) {
  const companyIds = companies.map((c) => c.id);
  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div>
      <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider mb-2">Unternehmen × Typ</p>
      <div className="bg-white border border-slate-200 rounded-xl p-2 text-[9px]">
        <div className="grid grid-cols-[56px_repeat(5,1fr)] gap-px text-center">
          <div />
          {TYPE_KEYS.map((key) => (
            <div key={key} className="text-slate-400 text-[7px]">
              {labelMap[key as keyof typeof labelMap]?.split(' ')[0] ?? key.slice(0, 4)}
            </div>
          ))}
        </div>
        {companyIds.map((cid) => {
          const company = companies.find((c) => c.id === cid);
          return (
            <div key={cid} className="grid grid-cols-[56px_repeat(5,1fr)] gap-px text-center mt-px">
              <div className="text-left text-slate-500 text-[8px] truncate flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: getCompanyColor(cid) }} />
                {company?.name ?? '—'}
              </div>
              {TYPE_KEYS.map((typeKey) => {
                const entry = data.find((d) => d.company_id === cid && d.signal_type === typeKey);
                const count = entry?.count ?? 0;
                return (
                  <div key={typeKey} className="rounded px-1 py-0.5 font-semibold text-[8px]" style={getCellBg(count, maxCount)}>
                    {count > 0 ? count : ''}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}