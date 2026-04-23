import { formatDistanceToNow, formatAbsolute } from '../utils/dates';

interface Props {
  date: string | null | undefined;
}

export default function DateWithTooltip({ date }: Props) {
  if (!date) return <span className="text-slate-400">–</span>;

  return (
    <span className="relative group/dt inline-block">
      <span className="cursor-default">{formatDistanceToNow(date)}</span>
      <span className="
        absolute bottom-full left-0 mb-1 z-50
        whitespace-nowrap
        px-2 py-1 rounded
        bg-slate-800 text-white text-[11px]
        opacity-0 group-hover/dt:opacity-100
        pointer-events-none
        transition-opacity duration-150
      ">
        {formatAbsolute(date)}
      </span>
    </span>
  );
}
