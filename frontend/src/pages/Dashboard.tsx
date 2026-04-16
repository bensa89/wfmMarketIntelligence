import { useState } from 'react';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useCrawlAll } from '../hooks/useCrawl';
import SignalCard from '../components/SignalCard';
import FilterBar from '../components/FilterBar';
import type { SignalType } from '../types';
import { TrendingUp, AlertTriangle, FileText, Play } from 'lucide-react';

export default function Dashboard() {
  const { data: companies, isLoading: companiesLoading } = useCompanies();
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);
  const [companyId, setCompanyId] = useState('');
  const crawlAll = useCrawlAll();

  const { data: signals, isLoading: signalsLoading } = useSignals({
    company_id: companyId || undefined,
    signal_type: signalType || undefined,
    min_relevance: minRelevance || undefined,
  });

  const competitorCount = companies?.filter((c) => c.type === 'competitor').length ?? 0;
  const highRelevanceCount = signals?.filter((s) => (s.relevance_score ?? 0) >= 0.7).length ?? 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <button
          onClick={() => crawlAll.mutate()}
          disabled={crawlAll.isPending}
          className="btn-primary flex items-center gap-2"
        >
          <Play size={16} />
          {crawlAll.isPending ? 'Crawling...' : 'Run Crawl'}
        </button>
      </div>

      {crawlAll.isSuccess && (
        <div className="mb-4 p-3 rounded bg-signal-high/10 text-signal-high text-sm">
          Crawl complete: {crawlAll.data.sources_processed} sources processed
        </div>
      )}
      {crawlAll.isError && (
        <div className="mb-4 p-3 rounded bg-signal-low/10 text-signal-low text-sm">
          Crawl failed
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="card flex items-center gap-4">
          <TrendingUp className="text-dark-accent" size={24} />
          <div>
            <p className="text-2xl font-bold">{signals?.length ?? '-'}</p>
            <p className="text-sm text-dark-muted">Total Signals</p>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <AlertTriangle className="text-signal-high" size={24} />
          <div>
            <p className="text-2xl font-bold">{highRelevanceCount}</p>
            <p className="text-sm text-dark-muted">High Relevance</p>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <FileText className="text-indigo-400" size={24} />
          <div>
            <p className="text-2xl font-bold">{competitorCount}</p>
            <p className="text-sm text-dark-muted">Competitors</p>
          </div>
        </div>
      </div>

      <FilterBar
        signalType={signalType}
        onSignalTypeChange={setSignalType}
        minRelevance={minRelevance}
        onMinRelevanceChange={setMinRelevance}
        companyId={companyId}
        onCompanyChange={setCompanyId}
        companies={companies}
      />

      {signalsLoading || companiesLoading ? (
        <p className="text-dark-muted">Loading signals...</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {signals?.map((signal) => {
            const company = companies?.find((c) => c.id === signal.company_id);
            return (
              <SignalCard
                key={signal.id}
                signal={signal}
                showCompany
                companyName={company?.name}
                companySlug={company?.slug}
              />
            );
          })}
          {signals?.length === 0 && (
            <p className="text-dark-muted col-span-2">No signals found. Try running a crawl.</p>
          )}
        </div>
      )}
    </div>
  );
}
