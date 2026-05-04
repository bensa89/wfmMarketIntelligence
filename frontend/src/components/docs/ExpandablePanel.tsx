import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface Props {
  title: string;
  children: React.ReactNode;
  variant?: 'data' | 'prompt';
}

export function ExpandablePanel({ title, children, variant = 'data' }: Props) {
  const [open, setOpen] = useState(false);

  const borderColor =
    variant === 'prompt'
      ? 'border-purple-700/40 bg-purple-950/20'
      : 'border-slate-700/40 bg-slate-800/30';

  return (
    <div className={`mt-3 rounded-lg border ${borderColor}`}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 w-full px-4 py-2.5 text-left text-[13px] font-medium text-slate-300 hover:text-slate-100 transition-colors"
      >
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        {title}
      </button>
      {open && (
        <div className="px-4 pb-4 text-[13px] text-slate-400 border-t border-white/5">
          {children}
        </div>
      )}
    </div>
  );
}
