import type { RiskItem } from '../../types/intelligence';
import CompanyLogo from '../CompanyLogo';

interface Props {
  risks: RiskItem[];
  opportunities: RiskItem[];
  watchpoints?: RiskItem[];
  onSelectSignal?: (signalId: string) => void;
}

interface ColumnProps {
  title: string;
  items: RiskItem[];
  bulletClass: string;
  hoverClass: string;
  newBadgeClass: string;
  max?: number;
  onSelectSignal?: (signalId: string) => void;
}

function RiskColumn({ title, items = [], bulletClass, hoverClass, newBadgeClass, max = 5, onSelectSignal }: ColumnProps) {
  const visible = items.slice(0, max);
  return (
    <div>
      <h4 className="text-[12px] font-semibold mb-2" style={{ color: 'inherit' }}>{title}</h4>
      {visible.length === 0 ? (
        <p className="text-slate-500 text-[11px]">None identified</p>
      ) : (
        <ul className="space-y-2">
          {visible.map((item, i) => {
            const firstSignalId = item.signal_ids?.[0];
            const clickable = !!firstSignalId && !!onSelectSignal;
            return (
              <li
                key={i}
                onClick={clickable ? () => onSelectSignal!(firstSignalId) : undefined}
                className={`flex flex-col gap-0.5 p-1 -mx-1 rounded ${clickable ? `cursor-pointer ${hoverClass} group` : ''}`}
              >
                <div className="flex gap-2">
                  <span className={`${bulletClass} flex-shrink-0 mt-0.5`}>▸</span>
                  <span className="text-[12px] text-slate-700 leading-snug">
                    {item.text}
                    {item.signal_ids && item.signal_ids.length > 1 && (
                      <span className="ml-1 text-[10px] text-slate-400">+{item.signal_ids.length - 1}</span>
                    )}
                    {item.is_new === true && (
                      <span className={`ml-1.5 text-[9px] font-semibold px-1.5 py-0.5 rounded-full uppercase tracking-wide ${newBadgeClass}`}>
                        NEW
                      </span>
                    )}
                  </span>
                </div>
                {item.company_name && item.company_slug && (
                  <div className="flex items-center gap-1 ml-4">
                    <CompanyLogo
                      name={item.company_name}
                      slug={item.company_slug}
                      companyId={item.company_id}
                      size="sm"
                    />
                    <span className="text-[10px] text-slate-400">{item.company_name}</span>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default function RisksOpportunitiesPanel({ risks, opportunities, watchpoints, onSelectSignal }: Props) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="bg-red-50 border border-red-100 rounded-xl p-4 text-red-700">
        <RiskColumn
          title="Emerging Risks"
          items={risks}
          bulletClass="text-red-500"
          hoverClass="hover:bg-red-100"
          newBadgeClass="bg-red-100 text-red-700"
          onSelectSignal={onSelectSignal}
        />
      </div>

      <div className="bg-green-50 border border-green-100 rounded-xl p-4 text-green-700">
        <RiskColumn
          title="Emerging Opportunities"
          items={opportunities}
          bulletClass="text-green-500"
          hoverClass="hover:bg-green-100"
          newBadgeClass="bg-green-100 text-green-700"
          onSelectSignal={onSelectSignal}
        />
      </div>

      <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 text-amber-700">
        <RiskColumn
          title="Watchpoints"
          items={watchpoints ?? []}
          bulletClass="text-amber-500"
          hoverClass="hover:bg-amber-100"
          newBadgeClass="bg-amber-100 text-amber-700"
          onSelectSignal={onSelectSignal}
        />
      </div>
    </div>
  );
}
