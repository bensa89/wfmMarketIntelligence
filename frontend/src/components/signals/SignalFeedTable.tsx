import type { SignalFeedItem } from '../../types/intelligence';
import MovementBadge from './MovementBadge';
import ConfidenceBar from './ConfidenceBar';
import { getCapabilityLabel } from '../../constants/capabilities';
import DateWithTooltip from '../DateWithTooltip';

interface Props {
  items: SignalFeedItem[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  onSelectItem: (item: SignalFeedItem) => void;
}

function Pagination({ page, total, pageSize, onPageChange }: Pick<Props, 'page' | 'total' | 'pageSize' | 'onPageChange'>) {
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-200">
      <span className="text-[12px] text-slate-500">{total} total signals</span>
      <div className="flex gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="px-2.5 py-1 rounded-md text-[12px] bg-white border border-slate-200 text-slate-600 hover:text-slate-900 disabled:opacity-30 transition-colors"
        >
          ←
        </button>
        <span className="px-3 py-1 text-[12px] text-slate-600 tabular-nums">{page} / {totalPages}</span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="px-2.5 py-1 rounded-md text-[12px] bg-white border border-slate-200 text-slate-600 hover:text-slate-900 disabled:opacity-30 transition-colors"
        >
          →
        </button>
      </div>
    </div>
  );
}

export default function SignalFeedTable({ items, total, page, pageSize, onPageChange, onSelectItem }: Props) {
  if (items.length === 0) {
    return (
      <div className="py-12 text-center text-slate-500 text-sm">
        No signals match the current filters
      </div>
    );
  }

  return (
    <div>
      {/* ── Mobile card list (hidden on md+) ── */}
      <div className="md:hidden space-y-2">
        {items.map((item) => (
          <div
            key={item.id}
            className="bg-white rounded-lg border border-slate-200 p-3 cursor-pointer hover:bg-slate-50 transition-colors"
            onClick={() => onSelectItem(item)}
          >
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <span className="text-[11px] font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded whitespace-nowrap">
                {item.company_name ?? '—'}
              </span>
              <MovementBadge strength={item.assessment?.movement_strength} />
            </div>
            <div className="text-[13px] font-medium text-slate-900 line-clamp-2 leading-snug mb-1.5">
              {item.title}
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              {item.assessment?.capability_primary && (
                <span className="text-[11px] text-slate-500 truncate">
                  {getCapabilityLabel(item.assessment.capability_primary)}
                </span>
              )}
              <ConfidenceBar value={item.assessment?.confidence} />
              {item.published_at && (
                <span className="text-[11px] text-slate-400 ml-auto whitespace-nowrap">
                  <DateWithTooltip date={item.published_at} />
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* ── Desktop table (hidden below md) ── */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              {['Signal', 'Competitor', 'Capability', 'Strength', 'Confidence', 'Datum'].map((h) => (
                <th key={h} className="text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500 pb-2 pr-4 pt-2">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                onClick={() => onSelectItem(item)}
              >
                <td className="py-3 pr-4 max-w-[300px]">
                  <div className="text-slate-900 font-medium line-clamp-2 leading-snug">{item.title}</div>
                  {item.topic && <div className="text-slate-500 text-[11px] mt-0.5 truncate">{item.topic}</div>}
                </td>
                <td className="py-3 pr-4 text-slate-600 whitespace-nowrap">{item.company_name ?? '—'}</td>
                <td className="py-3 pr-4 text-slate-600 whitespace-nowrap">
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
                <td className="py-3 text-slate-600">
                  {item.published_at && (
                    <div>
                      <DateWithTooltip date={item.published_at} />
                    </div>
                  )}
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    analysiert: <DateWithTooltip date={item.created_at} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} total={total} pageSize={pageSize} onPageChange={onPageChange} />
    </div>
  );
}
