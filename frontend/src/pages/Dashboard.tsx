import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useCrawlStream } from '../hooks/useCrawlStream';
import { useLastCompletedCrawl } from '../hooks/useCrawlRuns';
import { useActiveCrawlRun } from '../hooks/useActiveCrawlRun';
import { useSignalsOverTime, useSignalDistribution } from '../hooks/useSignalStats';
import { useSourceCandidates } from '../hooks/useSourceCandidates';
import { useDiscoveredPagesStats } from '../hooks/useDiscoveredPages';
import { useDocument } from '../hooks/useDocuments';
import DeltaKpiCard from '../components/dashboard/DeltaKpiCard';
import CrawlSummaryCard from '../components/dashboard/CrawlSummaryCard';
import TopSignalsPanel from '../components/dashboard/TopSignalsPanel';
import SignalsOverTimeChart from '../components/dashboard/SignalsOverTimeChart';
import SignalTypeDistribution from '../components/dashboard/SignalTypeDistribution';
import CompanySignalHeatmap from '../components/dashboard/CompanySignalHeatmap';
import SignalFeedTable from '../components/dashboard/SignalFeedTable';
import FilterBar from '../components/FilterBar';
import MarkdownViewer from '../components/MarkdownViewer';
import { Play, Loader2 } from 'lucide-react';
import type { SignalType, Signal } from '../types';

export default function Dashboard() {
  const { data: companies, isLoading: companiesLoading } = useCompanies();
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);
  const [companyId, setCompanyId] = useState('');
  const [onlyNew, setOnlyNew] = useState(false);
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const { start: startCrawl, isRunning: isCrawlRunning, summary: crawlSummary } = useCrawlStream();
  const { activeRun } = useActiveCrawlRun();
  const { lastCrawl } = useLastCompletedCrawl();
  const { data: allSignals } = useSignals({});
  const { data: signals, isLoading: signalsLoading } = useSignals({
    company_id: companyId || undefined,
    signal_type: signalType || undefined,
    min_relevance: minRelevance || undefined,
  });
  const { data: overTimeData } = useSignalsOverTime(14);
  const { data: distribution } = useSignalDistribution(companyId || undefined);
  const { data: candidates } = useSourceCandidates('candidate');
  const { data: discoveredStats } = useDiscoveredPagesStats();

  const competitorCount = companies?.filter((c) => c.type === 'competitor').length ?? 0;
  const lastCrawlTime = lastCrawl?.started_at ? new Date(lastCrawl.started_at) : null;

  const newSignalsCount = lastCrawlTime
    ? allSignals?.filter((s) => new Date(s.created_at) >= lastCrawlTime!).length ?? 0
    : 0;
  const highRelevanceCount = allSignals?.filter((s) => (s.relevance_score ?? 0) >= 0.7).length ?? 0;
  const newHighRelevanceCount = lastCrawlTime
    ? allSignals?.filter((s) => new Date(s.created_at) >= lastCrawlTime! && (s.relevance_score ?? 0) >= 0.7).length ?? 0
    : 0;
  const candidateCount = candidates?.length ?? 0;
  const unreviewedCount = candidates?.filter((c) => c.status === 'candidate').length ?? 0;
  const discoveredNew = discoveredStats?.new ?? 0;
  const discoveredTotal = discoveredStats?.total ?? 0;

  const filteredSignals = onlyNew && lastCrawlTime
    ? signals?.filter((s) => new Date(s.created_at) >= lastCrawlTime!) ?? []
    : signals ?? [];

  const lastCrawlTimeStr = lastCrawl?.finished_at
    ? new Date(lastCrawl.finished_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : null;

  const showCrawlRunning = isCrawlRunning || activeRun !== null;

  return (
    <div className="flex flex-col h-full bg-slate-50">
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-[12px] text-slate-500 mt-0.5">
            {allSignals?.length ?? '–'} Signale gesamt
            {lastCrawlTimeStr && ` · Letzter Crawl: ${lastCrawlTimeStr}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isCrawlRunning && (
            <span className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
              <Loader2 size={12} className="animate-spin" />
              Crawling...
            </span>
          )}
          <button
            onClick={() => startCrawl()}
            disabled={isCrawlRunning}
            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-colors flex items-center gap-1.5"
          >
            <Play size={12} />
            Crawl starten
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-6 py-5">
        {showCrawlRunning && (
          <div className="mb-4 px-4 py-2.5 rounded-xl text-[12px] font-medium border bg-blue-50 text-blue-700 border-blue-200">
            <Link to="/admin/sources" className="underline hover:no-underline">Crawl läuft</Link>
            {' — '}{activeRun?.total_sources ?? '...'} Quellen werden verarbeitet
            {activeRun?.total_new != null && activeRun.total_new > 0 && ` · ${activeRun.total_new} neue Dokumente`}
          </div>
        )}
        {crawlSummary && !isCrawlRunning && (
          <div className="mb-4 px-4 py-2.5 rounded-xl text-[12px] font-medium border bg-emerald-50 text-emerald-700 border-emerald-200">
            Crawl abgeschlossen: {crawlSummary.sources_processed} Quellen verarbeitet
            {crawlSummary.total_new > 0 && ` · ${crawlSummary.total_new} neue Dokumente`}
          </div>
        )}

        <div className="grid grid-cols-4 lg:grid-cols-8 gap-3 mb-6">
          <DeltaKpiCard label="Signale gesamt" value={allSignals?.length ?? '–'} delta={newSignalsCount > 0 ? `↑ +${newSignalsCount} seit letztem Crawl` : undefined} color="blue" trend={newSignalsCount > 0 ? 'up' : 'neutral'} />
          <DeltaKpiCard label="Hohe Relevanz" value={highRelevanceCount} delta={newHighRelevanceCount > 0 ? `↑ +${newHighRelevanceCount} neu` : undefined} color="green" trend={newHighRelevanceCount > 0 ? 'up' : 'neutral'} />
          <DeltaKpiCard label="Wettbewerber" value={competitorCount} color="amber" trend="neutral" />
          <DeltaKpiCard label="Neue Signale" value={newSignalsCount} delta={lastCrawlTime ? 'seit letztem Crawl' : undefined} color="purple" trend={newSignalsCount > 0 ? 'up' : 'neutral'} />
          <DeltaKpiCard label="Neue Dokumente" value={lastCrawl?.total_new ?? '–'} delta={lastCrawlTime ? 'seit letztem Crawl' : undefined} color="cyan" trend="neutral" />
          <DeltaKpiCard label="Source Candidates" value={candidateCount} delta={unreviewedCount > 0 ? `${unreviewedCount} ungeprüft` : undefined} color="pink" trend="neutral" />
          <DeltaKpiCard label="Discovered Pages" value={discoveredTotal} delta={discoveredNew > 0 ? `${discoveredNew} neu` : undefined} color="orange" trend={discoveredNew > 0 ? 'up' : 'neutral'} />
          <DeltaKpiCard label="Fehler letzter Crawl" value={lastCrawl?.total_errors ?? '–'} delta={(!lastCrawl?.total_errors || lastCrawl.total_errors === 0) ? '✓ Alle erfolgreich' : `${lastCrawl?.total_errors} Fehler`} color="red" trend={lastCrawl?.total_errors ? 'down' : 'neutral'} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <CrawlSummaryCard
              lastCrawl={lastCrawl ?? null}
              newSignalsCount={newSignalsCount}
              updatedSignalsCount={0}
              newDocumentsCount={lastCrawl?.total_new ?? 0}
              candidatesCount={candidateCount}
            />
            <TopSignalsPanel
              signals={allSignals ?? []}
              lastCrawl={lastCrawl ?? null}
              maxItems={5}
              onSignalClick={setSelectedSignal}
            />
            {overTimeData && overTimeData.length > 0 && (
              <SignalsOverTimeChart data={overTimeData} />
            )}
            <div className="grid grid-cols-2 gap-3">
              {distribution && <SignalTypeDistribution byType={distribution.by_type} />}
              {distribution && companies && (
                <CompanySignalHeatmap data={distribution.by_company_and_type} companies={companies} />
              )}
            </div>
          </div>

          <div className="lg:col-span-3">
            <FilterBar
              signalType={signalType}
              onSignalTypeChange={setSignalType}
              minRelevance={minRelevance}
              onMinRelevanceChange={setMinRelevance}
              companyId={companyId}
              onCompanyChange={setCompanyId}
              companies={companies?.map((c) => ({ id: c.id, name: c.name, type: c.type }))}
              onlyNew={onlyNew}
              onOnlyNewChange={setOnlyNew}
            />
            {signalsLoading || companiesLoading ? (
              <div className="flex items-center gap-2 text-slate-400 text-[13px]">
                <Loader2 size={14} className="animate-spin" />
                Lade Signale...
              </div>
            ) : (
              <SignalFeedTable
                signals={filteredSignals}
                companies={companies ?? []}
                lastCrawl={lastCrawl ?? null}
                onSignalClick={setSelectedSignal}
              />
            )}
          </div>
        </div>

        {selectedSignal && (
          <SignalDocumentModal signal={selectedSignal} onClose={() => setSelectedSignal(null)} />
        )}
      </div>
    </div>
  );
}

function SignalDocumentModal({ signal, onClose }: { signal: Signal; onClose: () => void }) {
  const { data: doc, isLoading } = useDocument(signal.document_id);

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-8 z-50" onClick={onClose}>
      <div className="bg-white rounded-xl max-w-3xl w-full max-h-[80vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div className="min-w-0 flex-1 mr-4">
            <h3 className="font-semibold text-slate-900 truncate">{signal.title}</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {signal.published_at
                ? new Date(signal.published_at).toLocaleDateString('de-DE')
                : new Date(signal.created_at).toLocaleDateString('de-DE')}
              {signal.source_url && (
                <> · <a href={signal.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Quelle</a></>
              )}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-sm font-medium shrink-0">Schließen</button>
        </div>
        <div className="px-6 py-4">
          {isLoading ? (
            <p className="text-slate-400 text-sm">Dokument wird geladen...</p>
          ) : doc?.content_markdown ? (
            <MarkdownViewer content={doc.content_markdown} />
          ) : (
            <p className="text-slate-400 text-sm">Kein Dokumentinhalt verfügbar.</p>
          )}
        </div>
      </div>
    </div>
  );
}