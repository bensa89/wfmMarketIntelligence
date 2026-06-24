import type { OverviewResponse } from '../../types/intelligence';
import type { LastCrawlSummary } from '../../types';
import KPICard from './KPICard';

interface Props {
  overview: OverviewResponse;
  lastCrawl: LastCrawlSummary;
}

export default function DashboardKPIRow({ overview, lastCrawl }: Props) {
  const totalSignals = overview.top_movers_30d.reduce((sum, m) => sum + m.signal_count, 0);
  const avgScore = overview.top_movers_30d.length > 0
    ? Math.round(overview.top_movers_30d.reduce((sum, m) => sum + m.avg_movement_score, 0) / overview.top_movers_30d.length)
    : 0;
  const importantSignalCount = overview.recent_market_shaping_30d.length;

  const { crawl_run } = lastCrawl;

  return (
    <div className={`grid grid-cols-2 sm:grid-cols-4 gap-3 md:gap-4 mb-6 ${crawl_run ? 'lg:grid-cols-8' : ''}`}>
      <KPICard label="Signals (30d)" value={totalSignals} accent="bg-blue-500" />
      <KPICard label="Avg Movement Score" value={avgScore} accent="bg-purple-500" />
      <KPICard label="Wichtige neue Signale" value={importantSignalCount} accent="bg-orange-500" />
      {crawl_run && (
        <>
          <KPICard label="Neue Signals" value={lastCrawl.new_signals} accent="bg-blue-500" />
          <KPICard label="Neue Dokumente" value={lastCrawl.new_documents} accent="bg-green-500" />
          <KPICard
            label="Fehler"
            value={crawl_run.total_errors}
            accent={crawl_run.total_errors > 0 ? 'bg-red-500' : 'bg-slate-300'}
            valueClassName={crawl_run.total_errors > 0 ? 'text-red-600' : undefined}
          />
          <KPICard label="Hochrelevante Signals" value={lastCrawl.high_relevance_signals} accent="bg-purple-500" />
        </>
      )}
      <KPICard label="Unanalysiert (Backlog)" value={lastCrawl.unanalysed_backlog} accent="bg-orange-500" />
    </div>
  );
}
