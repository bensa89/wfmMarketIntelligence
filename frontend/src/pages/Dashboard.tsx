import { useState } from 'react';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useCrawlAll } from '../hooks/useCrawl';
import SignalCard from '../components/SignalCard';
import FilterBar from '../components/FilterBar';
import RelevanceBadge from '../components/RelevanceBadge';
import SignalTypeIcon from '../components/SignalTypeIcon';
import type { SignalType } from '../types';
import { Play, Loader2 } from 'lucide-react';

const KPI_BORDER: Record<string, string> = {
  blue:   'linear-gradient(90deg, #2563eb, #7c3aed)',
  green:  '#10b981',
  amber:  '#f59e0b',
  purple: '#7c3aed',
};

function KpiCard({ label, value, delta, color }: { label: string; value: string | number; delta?: string; color: keyof typeof KPI_BORDER }) {
  return (
    <div className="bg-app-card border border-app-border rounded-xl p-4 relative overflow-hidden">
      <div
        className="absolute top-0 left-0 right-0 h-[3px] rounded-t-xl"
        style={{ background: KPI_BORDER[color] }}
      />
      <p className="text-[11px] font-medium text-ink-muted uppercase tracking-wide mb-2">{label}</p>
      <p className="text-[28px] font-extrabold text-ink leading-none tracking-tight">{value}</p>
      {delta && <p className="text-[11px] text-signal-high font-medium mt-1">{delta}</p>}
    </div>
  );
}

export default function Dashboard() {
  const { data: companies, isLoading: companiesLoading } = useCompanies();
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);
  const [companyId, setCompanyId] = useState('');
  const crawlAll = useCrawlAll();

  const { data: signals, isLoading: signalsLoading } = useSignals({
    company_id:    companyId || undefined,
    signal_type:   signalType || undefined,
    min_relevance: minRelevance || undefined,
  });

  const { data: allSignals } = useSignals({});
  const competitorCount    = companies?.filter((c) => c.type === 'competitor').length ?? 0;
  const highRelevanceCount = allSignals?.filter((s) => (s.relevance_score ?? 0) >= 0.7).length ?? 0;
  const activeSourceCount  = companies?.length ?? 0;

  return (
    <div className="flex flex-col h-full">
      {/* Topbar */}
      <div className="bg-app-card border-b border-app-border px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-[15px] font-bold text-ink tracking-tight">Dashboard</h1>
          <p className="text-[12px] text-ink-muted mt-0.5">
            {allSignals?.length ?? '–'} Signale gesamt
          </p>
        </div>
        <div className="flex items-center gap-3">
          {crawlAll.isPending && (
            <span className="flex items-center gap-1.5 text-[11px] text-signal-high font-medium">
              <Loader2 size={12} className="animate-spin" />
              Crawling...
            </span>
          )}
          <button
            onClick={() => crawlAll.mutate()}
            disabled={crawlAll.isPending}
            className="btn-primary flex items-center gap-1.5 text-[12px] py-1.5 px-3"
          >
            <Play size={12} />
            Crawl starten
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-6 py-5">
        {/* Status banners */}
        {crawlAll.isSuccess && (
          <div className="mb-4 px-4 py-2.5 rounded-xl text-[12px] font-medium border"
            style={{ background: '#f0fdf4', color: '#15803d', borderColor: '#bbf7d0' }}>
            Crawl abgeschlossen: {crawlAll.data.sources_processed} Quellen verarbeitet
          </div>
        )}
        {crawlAll.isError && (
          <div className="mb-4 px-4 py-2.5 rounded-xl text-[12px] font-medium border"
            style={{ background: '#fef2f2', color: '#b91c1c', borderColor: '#fecaca' }}>
            Crawl fehlgeschlagen
          </div>
        )}

        {/* KPI grid */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          <KpiCard label="Signale gesamt"  value={allSignals?.length ?? '–'}  color="blue" />
          <KpiCard label="Hohe Relevanz"   value={highRelevanceCount}          color="green" />
          <KpiCard label="Wettbewerber"    value={competitorCount}             color="amber" />
          <KpiCard label="Unternehmen"     value={activeSourceCount}           color="purple" />
        </div>

        {/* Filters */}
        <FilterBar
          signalType={signalType}
          onSignalTypeChange={setSignalType}
          minRelevance={minRelevance}
          onMinRelevanceChange={setMinRelevance}
          companyId={companyId}
          onCompanyChange={setCompanyId}
          companies={companies}
        />

        {/* Signal table */}
        {signalsLoading || companiesLoading ? (
          <div className="flex items-center gap-2 text-ink-muted text-[13px]">
            <Loader2 size={14} className="animate-spin" />
            Lade Signale...
          </div>
        ) : (
          <div className="bg-app-card border border-app-border rounded-xl overflow-hidden">
            {/* Table head */}
            <div
              className="grid text-[10px] font-semibold uppercase tracking-wider text-ink-muted px-4 py-2.5 border-b border-app-border-sub"
              style={{ gridTemplateColumns: 'minmax(0,2.2fr) minmax(0,1fr) 140px 90px 90px' }}
            >
              <span>Signal</span>
              <span>Unternehmen</span>
              <span>Typ</span>
              <span>Datum</span>
              <span>Relevanz</span>
            </div>

            {signals?.length === 0 && (
              <p className="text-ink-muted text-[13px] text-center py-8">
                Keine Signale gefunden. Crawl starten?
              </p>
            )}

            {signals?.map((signal) => {
              const company = companies?.find((c) => c.id === signal.company_id);
              const dateStr = signal.published_at
                ? new Date(signal.published_at).toLocaleDateString('de-DE')
                : new Date(signal.created_at).toLocaleDateString('de-DE');

              return (
                <div
                  key={signal.id}
                  className="grid items-center px-4 py-3 border-b border-app-border-sub last:border-b-0 hover:bg-app-bg cursor-pointer transition-colors"
                  style={{ gridTemplateColumns: 'minmax(0,2.2fr) minmax(0,1fr) 140px 90px 90px' }}
                >
                  {/* Signal */}
                  <div className="min-w-0 pr-4">
                    <p className="text-[12px] font-semibold text-ink truncate">{signal.title}</p>
                    {signal.summary && (
                      <p className="text-[11px] text-ink-muted truncate mt-0.5">{signal.summary}</p>
                    )}
                  </div>

                  {/* Company */}
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ background: company ? '#2563eb' : '#a1a1aa' }}
                    />
                    <span className="text-[12px] font-medium text-ink-secondary truncate">
                      {company?.name ?? '—'}
                    </span>
                  </div>

                  {/* Type */}
                  <div>
                    <SignalTypeIcon type={signal.signal_type} variant="chip" />
                  </div>

                  {/* Date */}
                  <span className="text-[11px] text-ink-muted">{dateStr}</span>

                  {/* Relevance */}
                  <RelevanceBadge score={signal.relevance_score} variant="bar" />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
