import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useSignalsFeed } from '../hooks/useSignalsFeed';
import { useCompanies } from '../hooks/useCompanies';
import { useLastCompletedCrawl } from '../hooks/useCrawlRuns';
import SignalFeedFilters from '../components/signals/SignalFeedFilters';
import SignalFeedTable from '../components/signals/SignalFeedTable';
import SignalDetailModal from '../components/signals/SignalDetailModal';
import type { SignalsFeedFilters, SignalFeedItem } from '../types/intelligence';

const DEFAULT_FILTERS: SignalsFeedFilters = {
  sort_by: 'published_at',
  page: 1,
  page_size: 25,
};

export default function SignalsFeedPage() {
  const [searchParams] = useSearchParams();
  const [filters, setFilters] = useState<SignalsFeedFilters>(() => ({
    ...DEFAULT_FILTERS,
    ...(searchParams.get('created_from') ? { created_from: searchParams.get('created_from')! } : {}),
    ...(searchParams.get('created_to') ? { created_to: searchParams.get('created_to')! } : {}),
  }));
  const [selectedItem, setSelectedItem] = useState<SignalFeedItem | null>(null);

  const { data, isLoading } = useSignalsFeed(filters);
  const { data: companies = [] } = useCompanies();
  const { lastCrawl } = useLastCompletedCrawl();

  function handleFilterChange(partial: Partial<SignalsFeedFilters>) {
    setFilters((prev) => ({ ...prev, ...partial }));
  }

  function handleReset() {
    setFilters(DEFAULT_FILTERS);
  }

  return (
    <div className="h-full overflow-auto">
      <div className="bg-white border-b border-slate-200 px-4 md:px-6 py-4">
        <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">Signals Feed</h1>
        <p className="text-[12px] text-slate-500 mt-0.5">Operative intelligence with assessment context</p>
      </div>
      <div className="px-4 md:px-6 py-5">
      <SignalFeedFilters
        filters={filters}
        companies={companies.filter((c) => c.type === 'competitor')}
        onChange={handleFilterChange}
        onReset={handleReset}
        lastCrawlStartedAt={lastCrawl?.started_at ?? null}
      />

      {isLoading ? (
        <div className="flex items-center justify-center h-48">
          <span className="text-slate-500 text-sm">Loading signals…</span>
        </div>
      ) : (
        <SignalFeedTable
          items={data?.items ?? []}
          total={data?.total ?? 0}
          page={filters.page ?? 1}
          pageSize={filters.page_size ?? 25}
          onPageChange={(p) => handleFilterChange({ page: p })}
          onSelectItem={setSelectedItem}
          newSinceTimestamp={lastCrawl?.started_at ?? null}
        />
      )}

      {selectedItem && (
        <SignalDetailModal
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
        />
      )}
      </div>
    </div>
  );
}
