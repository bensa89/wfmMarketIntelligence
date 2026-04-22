import type { SignalFeedItem } from '../../types/intelligence';
import MovementBadge from './MovementBadge';
import ConfidenceBar from './ConfidenceBar';
import { getCapabilityLabel } from '../../constants/capabilities';
import { formatDistanceToNow } from '../../utils/dates';

interface Props {
  items: SignalFeedItem[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  onSelectItem: (item: SignalFeedItem) => void;
}

export default function SignalFeedTable({ items, total, page, pageSize, onPageChange, onSelectItem }: Props) {
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
              {['Signal', 'Competitor', 'Capability', 'Strength', 'Confidence', 'Date'].map((h) => (
                <th key={h} className="text-left text-[11px] font-medium text-slate-500 uppercase tracking-wide pb-2 pr-4">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-slate-600">No signals match the current filters</td>
              </tr>
            ) : (
              items.map((item) => (
                <tr
                  key={item.id}
                  className="cursor-pointer hover:bg-white/[0.03] transition-colors"
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                  onClick={() => onSelectItem(item)}
                >
                  <td className="py-3 pr-4 max-w-[300px]">
                    <div className="text-slate-200 font-medium line-clamp-2 leading-snug">{item.title}</div>
                    {item.topic && <div className="text-slate-600 text-[11px] mt-0.5 truncate">{item.topic}</div>}
                  </td>
                  <td className="py-3 pr-4 text-slate-400 whitespace-nowrap">{item.company_name ?? '—'}</td>
                  <td className="py-3 pr-4 text-slate-500 whitespace-nowrap">
                    {item.assessment?.capability_primary
                      ? getCapabilityLabel(item.assessment.capability_primary)
                      : '—'}
                  </td>
                  <td className="py-3 pr-4">
                    <MovementBadge strength={item.assessment?.movement_strength} />
                  </td>
                  <td className="py-3 pr-4">
                    <ConfidenceBar value={item.assessment?.confidence} />
                  </td>
                  <td className="py-3 text-slate-500 whitespace-nowrap">
                    {formatDistanceToNow(item.published_at || item.created_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <span className="text-[12px] text-slate-500">{total} total signals</span>
          <div className="flex gap-1">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="px-2.5 py-1 rounded-md text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-30 transition-colors"
              style={{ background: 'rgba(255,255,255,0.06)' }}
            >
              ←
            </button>
            <span className="px-3 py-1 text-[12px] text-slate-400 tabular-nums">{page} / {totalPages}</span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="px-2.5 py-1 rounded-md text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-30 transition-colors"
              style={{ background: 'rgba(255,255,255,0.06)' }}
            >
              →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
