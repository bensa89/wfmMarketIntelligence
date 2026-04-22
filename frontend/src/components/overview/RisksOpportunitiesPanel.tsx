interface Props {
  risks: string[];
  opportunities: string[];
}

export default function RisksOpportunitiesPanel({ risks, opportunities }: Props) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}
      >
        <h4 className="text-[12px] font-semibold text-red-400 mb-3">Emerging Risks</h4>
        {risks.length === 0 ? (
          <p className="text-slate-600 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {risks.slice(0, 5).map((r, i) => (
              <li key={i} className="flex gap-2 text-[12px] text-slate-300">
                <span className="text-red-500 mt-0.5 flex-shrink-0">▸</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.15)' }}
      >
        <h4 className="text-[12px] font-semibold text-green-400 mb-3">Emerging Opportunities</h4>
        {opportunities.length === 0 ? (
          <p className="text-slate-600 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {opportunities.slice(0, 5).map((o, i) => (
              <li key={i} className="flex gap-2 text-[12px] text-slate-300">
                <span className="text-green-500 mt-0.5 flex-shrink-0">▸</span>
                <span>{o}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
