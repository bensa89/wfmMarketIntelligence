import { Info } from 'lucide-react';

interface Props {
  text: string;
}

export default function InfoTooltip({ text }: Props) {
  return (
    <span className="relative group inline-flex items-center ml-1">
      <Info size={11} className="text-slate-300 group-hover:text-slate-400 transition-colors cursor-default" />
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-52 rounded-lg bg-slate-800 text-white text-[11px] leading-relaxed px-2.5 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-lg">
        {text}
        <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
      </span>
    </span>
  );
}
