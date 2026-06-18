import { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import * as LucideIcons from 'lucide-react';
import type { HeatmapRow } from '../../types/intelligence';
import { CAPABILITIES, type CapabilityMeta } from '../../constants/capabilities';

interface Props {
  rows: HeatmapRow[];
}

const VISIBLE_CAPABILITIES = Object.values(CAPABILITIES)
  .filter((c) => c.visibilityToUser)
  .sort((a, b) => b.strategicWeight - a.strategicWeight)
  .slice(0, 8);

function renderIcon(iconName: string) {
  const IconComponent = (LucideIcons as Record<string, any>)[iconName];
  if (!IconComponent) return null;
  return <IconComponent className="w-4 h-4" />;
}

function scoreToColor(score: number): string {
  if (score === 0) return 'rgba(203,213,225,0.4)';
  if (score < 30) return 'rgba(59,130,246,0.12)';
  if (score < 60) return 'rgba(59,130,246,0.35)';
  if (score < 80) return 'rgba(139,92,246,0.45)';
  return 'rgba(249,115,22,0.55)';
}

interface HeatmapCellProps {
  capability: CapabilityMeta;
  companyName: string;
  score: number;
}

function HeatmapCell({ capability, companyName, score }: HeatmapCellProps) {
  const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number } | null>(null);
  const cellRef = useRef<HTMLDivElement>(null);

  function handleMouseEnter() {
    if (!cellRef.current) return;
    const r = cellRef.current.getBoundingClientRect();
    setTooltipPos({ top: r.bottom + 6, left: r.left + r.width / 2 });
  }

  return (
    <div className="relative">
      <div
        ref={cellRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={() => setTooltipPos(null)}
        className="w-7 h-5 rounded mx-auto"
        style={{ background: scoreToColor(score) }}
      />
      {tooltipPos && createPortal(
        <div
          style={{ position: 'fixed', top: tooltipPos.top, left: tooltipPos.left, transform: 'translateX(-50%)' }}
          className="z-[9999] w-56 bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-left pointer-events-none"
        >
          <div className="flex items-center gap-1.5 mb-1.5 text-slate-700">
            {renderIcon(capability.icon)}
            <span className="text-xs font-semibold">{capability.label}</span>
          </div>
          <p className="text-[11px] text-slate-500 mb-2">{capability.description}</p>
          <div className="text-xs text-slate-600 mb-1">Company: <span className="font-medium text-slate-900">{companyName}</span></div>
          <div className="text-xs text-slate-600">
            Avg. Movement Score (30d): <span className="font-medium text-slate-900">{score > 0 ? score : '–'}</span>
          </div>
          {score === 0 && (
            <p className="mt-2 text-xs text-slate-400 italic">Keine Signale in den letzten 30 Tagen</p>
          )}
        </div>,
        document.body,
      )}
    </div>
  );
}

export default function CapabilityHeatmapV2({ rows }: Props) {
  if (rows.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex items-center justify-center h-48">
        <p className="text-slate-400 text-[12px]">No assessment data yet</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 overflow-x-auto">
      <h3 className="text-[13px] font-semibold text-slate-700 mb-4">Capability Activity (30d)</h3>
      <table className="w-full text-[11px]">
        <thead>
          <tr>
            <th className="text-left text-slate-500 pb-2 pr-3 font-medium w-32">Company</th>
            {VISIBLE_CAPABILITIES.map((c) => (
              <th
                key={c.key}
                className="text-slate-500 pb-2 px-1 font-medium text-center"
                title={c.label}
              >
                <div className="flex items-center justify-center text-slate-500">
                  {renderIcon(c.icon)}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.company_id}>
              <td className="pr-3 py-1 text-slate-700 truncate max-w-[8rem]" title={row.company_name}>
                {row.company_name}
              </td>
              {VISIBLE_CAPABILITIES.map((c) => {
                const score = row.capabilities[c.key] ?? 0;
                return (
                  <td key={c.key} className="px-0.5 py-0.5 text-center">
                    <HeatmapCell capability={c} companyName={row.company_name} score={score} />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
