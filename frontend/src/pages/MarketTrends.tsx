import { useState } from 'react';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import SignalCard from '../components/SignalCard';
import FilterBar from '../components/FilterBar';
import type { SignalType } from '../types';
import { TrendingUp } from 'lucide-react';

export default function MarketTrends() {
  const { data: companies } = useCompanies();
  const marketSources = companies?.filter((c) => c.type === 'market_source') ?? [];
  const marketCompanyIds = marketSources.map((c) => c.id);

  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);
  const [selectedCompanyId, setSelectedCompanyId] = useState('');

  const { data: allSignals, isLoading } = useSignals({
    signal_type: signalType || undefined,
    min_relevance: minRelevance || undefined,
  });

  const marketSignals = allSignals?.filter((s) => {
    const isMarket = selectedCompanyId ? s.company_id === selectedCompanyId : marketCompanyIds.includes(s.company_id);
    return isMarket;
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2 flex items-center gap-2">
        <TrendingUp size={24} /> Market Trends
      </h1>
      <p className="text-sm text-dark-muted mb-4">
        Signals from market and industry sources
      </p>

      <FilterBar
        signalType={signalType}
        onSignalTypeChange={setSignalType}
        minRelevance={minRelevance}
        onMinRelevanceChange={setMinRelevance}
        companyId={selectedCompanyId}
        onCompanyChange={setSelectedCompanyId}
        companies={marketSources}
      />

      {isLoading ? (
        <p className="text-dark-muted">Loading signals...</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {(marketSignals ?? []).map((signal) => {
            const company = marketSources.find((c) => c.id === signal.company_id);
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
          {marketSignals?.length === 0 && (
            <p className="text-dark-muted col-span-2">
              No market trend signals found. Add market sources and run a crawl.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
