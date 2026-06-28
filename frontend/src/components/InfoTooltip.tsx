import { Info } from 'lucide-react';

interface Props {
  text: string;
  placement?: 'top' | 'bottom';
  side?: 'center' | 'right';
}

export default function InfoTooltip({ text, placement = 'top', side = 'center' }: Props) {
  const isBottom = placement === 'bottom';
  const hPos = side === 'right' ? 'right-0' : 'left-1/2 -translate-x-1/2';
  const arrowPos = side === 'right' ? 'right-2' : 'left-1/2 -translate-x-1/2';
  return (
    <span className={`relative group inline-flex items-center ${isBottom ? '' : 'ml-1'}`}>
      <Info size={11} className="text-slate-300 group-hover:text-slate-400 transition-colors cursor-default" />
      <span
        className={`absolute ${hPos} ${isBottom ? 'top-full mt-1.5 w-60' : 'bottom-full mb-1.5 w-52'} rounded-lg bg-slate-800 text-white text-[11px] leading-relaxed px-2.5 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-lg`}
      >
        {text}
        {!isBottom && (
          <span className={`absolute top-full ${arrowPos} border-4 border-transparent border-t-slate-800`} />
        )}
      </span>
    </span>
  );
}
