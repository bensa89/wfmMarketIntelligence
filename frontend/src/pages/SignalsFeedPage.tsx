import { useState } from 'react';
import { useSignalsFeed } from '../hooks/useSignalsFeed';
import { useCompanies } from '../hooks/useCompanies';
import SignalFeedFilters from '../components/signals/SignalFeedFilters';
import SignalFeedTable from '../components/signals/SignalFeedTable';
import SignalDetailDrawer from '../components/signals/SignalDetailDrawer';
import type { SignalsFeedFilters, SignalFeedItem } from '../types/intelligence';

const DEFAULT_FILTERS: SignalsFeedFilters = {
  sort_by: 'published_at',
  page: 1,
  page_size: 25,
};

export default function SignalsFeedPage() {
  const [filters, setFilters] = useState<SignalsFeedFilters>(DEFAULT_FILTERS);
  const [selectedItem, setSelectedItem] = useState<SignalFeedItem | null>(null);

  const { data, isLoading } = useSignalsFeed(filters);
  const { data: companies = [] } = useCompanies();

  function handleFilterChange(partial: Partial<SignalsFeedFilters>) {
    setFilters((prev) => ({ ...prev, ...partial }));
  }

  function handleReset() {
    setFilters(DEFAULT_FILTERS);
  }

  return (
    <div className="flex flex-col h-full">
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex-shrink-0">
        <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">Signals Feed</h1>
        <p className="text-[12px] text-slate-500 mt-0.5">Operative intelligence with assessment context</p>
      </div>
      <div className="flex-1 overflow-auto px-6 py-5">
      <SignalFeedFilters
        filters={filters}
        companies={companies.filter((c) => c.type === 'competitor')}
        onChange={handleFilterChange}
        onReset={handleReset}
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
        />
      )}

      {selectedItem && (
        <SignalDetailDrawer
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
        />
      )}
      </div>
    </div>
  );
}
