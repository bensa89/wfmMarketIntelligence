interface Props {
  risks: string[];
  opportunities: string[];
}

export default function RisksOpportunitiesPanel({ risks, opportunities }: Props) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-red-50 border border-red-100 rounded-xl p-4">
        <h4 className="text-[12px] font-semibold text-red-700 mb-3">Emerging Risks</h4>
        {risks.length === 0 ? (
          <p className="text-slate-500 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {risks.slice(0, 5).map((r, i) => (
              <li key={i} className="flex gap-2 text-[12px] text-slate-700">
                <span className="text-red-500 mt-0.5 flex-shrink-0">▸</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="bg-green-50 border border-green-100 rounded-xl p-4">
        <h4 className="text-[12px] font-semibold text-green-700 mb-3">Emerging Opportunities</h4>
        {opportunities.length === 0 ? (
          <p className="text-slate-500 text-[11px]">None identified</p>
        ) : (
          <ul className="space-y-1.5">
            {opportunities.slice(0, 5).map((o, i) => (
              <li key={i} className="flex gap-2 text-[12px] text-slate-700">
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
