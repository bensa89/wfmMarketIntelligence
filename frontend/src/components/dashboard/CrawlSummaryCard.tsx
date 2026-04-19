import type { CrawlRunList } from '../../types';

interface CrawlSummaryCardProps {
  lastCrawl: CrawlRunList | null;
  newSignalsCount: number;
  updatedSignalsCount: number;
  newDocumentsCount: number;
  candidatesCount: number;
}

export default function CrawlSummaryCard({
  lastCrawl,
  newSignalsCount,
  updatedSignalsCount,
  newDocumentsCount,
  candidatesCount,
}: CrawlSummaryCardProps) {
  const crawlTime = lastCrawl?.finished_at
    ? new Date(lastCrawl.finished_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : '—';

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 border-l-[3px] border-l-emerald-500">
      <div className="flex items-center justify-between mb-3">
        <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Seit letztem Crawl</p>
        <span className="text-[10px] text-slate-400">{crawlTime}</span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[12px]">
        <div>
          <span className="text-slate-500">Neue Signale: </span>
          <span className="font-bold text-slate-900">{newSignalsCount}</span>
        </div>
        <div>
          <span className="text-slate-500">Geändert: </span>
          <span className="font-bold text-slate-900">{updatedSignalsCount}</span>
        </div>
        <div>
          <span className="text-slate-500">Neue Dokumente: </span>
          <span className="font-bold text-slate-900">{newDocumentsCount}</span>
        </div>
        <div>
          <span className="text-slate-500">Candidates: </span>
          <span className="font-bold text-slate-900">{candidatesCount}</span>
        </div>
      </div>
    </div>
  );
}