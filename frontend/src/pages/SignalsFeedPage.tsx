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
    <div style={{ background: '#0a0f1e', minHeight: '100%' }}>
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="mb-4">
        <h1 className="text-xl font-semibold text-slate-100">Signals Feed</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">Operative intelligence with assessment context</p>
      </div>

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
