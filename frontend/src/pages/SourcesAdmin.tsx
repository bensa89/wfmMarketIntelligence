import { useState } from 'react';
import { useCompanies, useCreateCompany } from '../hooks/useCompanies';
import { useSources, useCreateSource, useUpdateSource, useDeleteSource } from '../hooks/useSources';
import { useCrawlAll, useCrawlSource } from '../hooks/useCrawl';
import type { CompanyType, SourceType } from '../types';
import { Plus, Play, Trash2 } from 'lucide-react';

const sourceTypes: SourceType[] = ['news', 'blog', 'product', 'press', 'jobs'];

export default function SourcesAdmin() {
  const { data: companies, isLoading: companiesLoading } = useCompanies();
  const { data: sources, isLoading: sourcesLoading } = useSources();
  const createCompany = useCreateCompany();
  const createSource = useCreateSource();
  const updateSource = useUpdateSource();
  const deleteSource = useDeleteSource();
  const crawlAll = useCrawlAll();
  const crawlSingle = useCrawlSource();

  const [newCompanyOpen, setNewCompanyOpen] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newCompanySlug, setNewCompanySlug] = useState('');
  const [newCompanyType, setNewCompanyType] = useState<CompanyType>('competitor');
  const [newCompanyWebsite, setNewCompanyWebsite] = useState('');

  const [newSourceCompanyId, setNewSourceCompanyId] = useState('');
  const [newSourceUrl, setNewSourceUrl] = useState('');
  const [newSourceLabel, setNewSourceLabel] = useState('');
  const [newSourceType, setNewSourceType] = useState<SourceType>('news');

  function handleCreateCompany(e: React.FormEvent) {
    e.preventDefault();
    if (!newCompanyName || !newCompanySlug) return;
    createCompany.mutate(
      { name: newCompanyName, slug: newCompanySlug, type: newCompanyType, website: newCompanyWebsite || null },
      { onSuccess: () => {
        setNewCompanyOpen(false);
        setNewCompanyName('');
        setNewCompanySlug('');
        setNewCompanyWebsite('');
      }},
    );
  }

  function handleCreateSource(e: React.FormEvent) {
    e.preventDefault();
    if (!newSourceCompanyId || !newSourceUrl) return;
    createSource.mutate(
      { company_id: newSourceCompanyId, url: newSourceUrl, label: newSourceLabel || null, source_type: newSourceType },
      { onSuccess: () => {
        setNewSourceUrl('');
        setNewSourceLabel('');
        setNewSourceType('news');
      }},
    );
  }

  function handleToggleSource(sourceId: string, currentActive: boolean) {
    updateSource.mutate({ sourceId, data: { is_active: !currentActive } });
  }

  function handleDeleteSource(sourceId: string) {
    if (window.confirm('Delete this source?')) {
      deleteSource.mutate(sourceId);
    }
  }

  function handleCrawlSource(sourceId: string) {
    crawlSingle.mutate(sourceId);
  }

  const isLoading = companiesLoading || sourcesLoading;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Sources Admin</h1>
        <div className="flex gap-2">
          <button onClick={() => crawlAll.mutate()} disabled={crawlAll.isPending} className="btn-primary flex items-center gap-2">
            <Play size={16} /> {crawlAll.isPending ? 'Crawling...' : 'Run Full Crawl'}
          </button>
          <button onClick={() => setNewCompanyOpen(true)} className="btn-secondary flex items-center gap-2">
            <Plus size={16} /> Add Company
          </button>
        </div>
      </div>

      {crawlAll.isSuccess && (
        <div className="mb-4 p-3 rounded bg-signal-high/10 text-signal-high text-sm">
          Crawl complete: {crawlAll.data.sources_processed} sources processed
        </div>
      )}

      {isLoading ? (
        <p className="text-dark-muted">Loading...</p>
      ) : (
        <div className="space-y-6">
          {companies?.map((company) => {
            const companySources = sources?.filter((s) => s.company_id === company.id) ?? [];
            return (
              <div key={company.id} className="card">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-semibold">{company.name}</h2>
                  <span className={`text-xs px-2 py-0.5 rounded ${company.type === 'competitor' ? 'bg-type-product_update/20 text-type-product_update' : 'bg-type-ai_announcement/20 text-type-ai_announcement'}`}>
                    {company.type === 'competitor' ? 'Competitor' : 'Market Source'}
                  </span>
                </div>
                {company.website && <p className="text-xs text-dark-muted mb-3">{company.website}</p>}
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-dark-border">
                      <th className="text-left py-2 text-dark-muted font-medium">URL</th>
                      <th className="text-left py-2 text-dark-muted font-medium">Label</th>
                      <th className="text-left py-2 text-dark-muted font-medium">Type</th>
                      <th className="text-left py-2 text-dark-muted font-medium">Active</th>
                      <th className="text-left py-2 text-dark-muted font-medium">Last Crawled</th>
                      <th className="text-right py-2 text-dark-muted font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {companySources.map((source) => (
                      <tr key={source.id} className="border-b border-dark-border/50">
                        <td className="py-2 max-w-xs truncate" title={source.url}>{source.url}</td>
                        <td className="py-2">{source.label || '-'}</td>
                        <td className="py-2">
                          <span className="text-xs px-1.5 py-0.5 rounded bg-dark-bg">{source.source_type}</span>
                        </td>
                        <td className="py-2">
                          <button
                            onClick={() => handleToggleSource(source.id, source.is_active)}
                            className={`text-xs px-2 py-0.5 rounded ${source.is_active ? 'bg-signal-high/20 text-signal-high' : 'bg-dark-bg text-dark-muted'}`}
                          >
                            {source.is_active ? 'Active' : 'Inactive'}
                          </button>
                        </td>
                        <td className="py-2 text-dark-muted text-xs">
                          {source.last_crawled_at ? new Date(source.last_crawled_at).toLocaleDateString('de-DE') : 'Never'}
                        </td>
                        <td className="py-2 text-right">
                          <button onClick={() => handleCrawlSource(source.id)} className="text-dark-accent hover:text-indigo-300 mr-2" title="Crawl this source">
                            <Play size={14} />
                          </button>
                          <button onClick={() => handleDeleteSource(source.id)} className="text-signal-low hover:text-red-400" title="Delete source">
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                    {companySources.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-2 text-dark-muted text-center">No sources configured</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            );
          })}
        </div>
      )}

      {newCompanyOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-8 z-50" onClick={() => setNewCompanyOpen(false)}>
          <div className="card w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">Add Company</h2>
            <form onSubmit={handleCreateCompany} className="space-y-3">
              <div>
                <label className="block text-sm text-dark-muted mb-1">Name</label>
                <input value={newCompanyName} onChange={(e) => setNewCompanyName(e.target.value)} className="input-field w-full" required />
              </div>
              <div>
                <label className="block text-sm text-dark-muted mb-1">Slug</label>
                <input value={newCompanySlug} onChange={(e) => setNewCompanySlug(e.target.value)} className="input-field w-full" required placeholder="e.g. company-name" />
              </div>
              <div>
                <label className="block text-sm text-dark-muted mb-1">Type</label>
                <select value={newCompanyType} onChange={(e) => setNewCompanyType(e.target.value as CompanyType)} className="input-field w-full">
                  <option value="competitor">Competitor</option>
                  <option value="market_source">Market Source</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-dark-muted mb-1">Website (optional)</label>
                <input value={newCompanyWebsite} onChange={(e) => setNewCompanyWebsite(e.target.value)} className="input-field w-full" />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="submit" disabled={createCompany.isPending} className="btn-primary flex-1">
                  {createCompany.isPending ? 'Creating...' : 'Create'}
                </button>
                <button type="button" onClick={() => setNewCompanyOpen(false)} className="btn-secondary flex-1">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card mt-6">
        <h2 className="text-lg font-semibold mb-4">Add Source</h2>
        <form onSubmit={handleCreateSource} className="flex items-end gap-3">
          <div className="flex-1">
            <label className="block text-sm text-dark-muted mb-1">Company</label>
            <select value={newSourceCompanyId} onChange={(e) => setNewSourceCompanyId(e.target.value)} className="input-field w-full" required>
              <option value="">Select...</option>
              {companies?.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="flex-[2]">
            <label className="block text-sm text-dark-muted mb-1">URL</label>
            <input value={newSourceUrl} onChange={(e) => setNewSourceUrl(e.target.value)} className="input-field w-full" required placeholder="https://..." />
          </div>
          <div>
            <label className="block text-sm text-dark-muted mb-1">Label</label>
            <input value={newSourceLabel} onChange={(e) => setNewSourceLabel(e.target.value)} className="input-field w-full" placeholder="News" />
          </div>
          <div>
            <label className="block text-sm text-dark-muted mb-1">Type</label>
            <select value={newSourceType} onChange={(e) => setNewSourceType(e.target.value as SourceType)} className="input-field w-full">
              {sourceTypes.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <button type="submit" disabled={createSource.isPending} className="btn-primary">
            {createSource.isPending ? 'Adding...' : 'Add Source'}
          </button>
        </form>
      </div>
    </div>
  );
}
