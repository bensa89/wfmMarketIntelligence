interface Props {
  id: string;
  title: string;
  type: 'rule' | 'ai';
  explanation: React.ReactNode;
  example: React.ReactNode;
  children?: React.ReactNode;
}

export function PipelineSection({ id, title, type, explanation, example, children }: Props) {
  return (
    <section id={id} className="scroll-mt-24 py-10 border-t border-white/5">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
        {type === 'rule' ? (
          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-900/40 text-blue-300 border border-blue-700/30">
            🔢 Regel
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-900/40 text-purple-300 border border-purple-700/30">
            🤖 KI
          </span>
        )}
      </div>

      <div className="text-[14px] text-slate-400 leading-relaxed space-y-2 mb-5">
        {explanation}
      </div>

      <div className="rounded-lg border border-amber-700/40 bg-amber-950/20 px-4 py-3 mb-4">
        <p className="text-[11px] font-semibold text-amber-500 uppercase tracking-wider mb-1">
          In unserem Beispiel
        </p>
        <div className="text-[13px] text-amber-200/80 leading-relaxed">{example}</div>
      </div>

      {children}
    </section>
  );
}
