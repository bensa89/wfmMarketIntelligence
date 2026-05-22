import { useState } from 'react';
import { Info } from 'lucide-react';

interface Props {
  text: string;
  placement?: 'top' | 'bottom';
}

export function InfoTooltip({ text, placement = 'top' }: Props) {
  const [visible, setVisible] = useState(false);
  const positionClass = placement === 'bottom'
    ? 'top-full mt-1.5'
    : 'bottom-full mb-1.5';
  return (
    <span className="relative inline-flex items-center">
      <Info
        className="w-3 h-3 text-slate-400 cursor-help flex-shrink-0"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
      />
      {visible && (
        <span className={`absolute z-50 ${positionClass} left-1/2 -translate-x-1/2 w-60 bg-slate-900 text-white text-[11px] rounded-lg px-3 py-2 shadow-xl pointer-events-none leading-snug whitespace-normal`}>
          {text}
        </span>
      )}
    </span>
  );
}
