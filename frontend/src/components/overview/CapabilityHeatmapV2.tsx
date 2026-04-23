import React from 'react';
import type { HeatmapRow } from '../../types/intelligence';
import { CAPABILITIES } from '../../constants/capabilities';

interface Props {
  rows: HeatmapRow[];
}

const VISIBLE_CAPABILITIES = Object.values(CAPABILITIES)
  .filter((c) => c.visibilityToUser)
  .sort((a, b) => b.strategicWeight - a.strategicWeight)
  .slice(0, 8);

function scoreToColor(score: number): string {
  if (score === 0) return 'rgba(203,213,225,0.4)';
  if (score < 30) return 'rgba(59,130,246,0.12)';
  if (score < 60) return 'rgba(59,130,246,0.35)';
  if (score < 80) return 'rgba(139,92,246,0.45)';
  return 'rgba(249,115,22,0.55)';
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
                style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', height: 64, verticalAlign: 'bottom' } as React.CSSProperties}
                title={c.label}
              >
                {c.label}
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
                    <div
                      className="w-7 h-5 rounded mx-auto"
                      style={{ background: scoreToColor(score) }}
                      title={score > 0 ? `${c.label}: ${score}` : `${c.label}: no data`}
                    />
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
