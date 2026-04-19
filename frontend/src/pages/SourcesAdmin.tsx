import React, { useState } from 'react';
import { useCompanies, useCreateCompany, useUpdateCompanyDynamic, useDeleteCompany } from '../hooks/useCompanies';
import { useSources, useCreateSource, useUpdateSource, useDeleteSource } from '../hooks/useSources';
import { useCrawlStream } from '../hooks/useCrawlStream';
import { CrawlProgressPanel } from '../components/CrawlProgressPanel';
import { useDiscoveredPages, useToggleDiscoveredPage, useDeleteDiscoveredPage } from '../hooks/useDiscoveredPages';
import type { CompanyType, SourceType, Source, DiscoveredPage, Company } from '../types';
import { Plus, Play, Trash2, Edit2, X, ChevronDown, ChevronRight } from 'lucide-react';
import { ApiError } from '../api/client';

const sourceTypes: SourceType[] = ['news', 'blog', 'product', 'press', 'jobs'];

function DiscoveredPagesSection({
  sourceId,
  onToggle,
  onDelete,
}: {
  sourceId: string;
  onToggle: (pageId: string, isActive: boolean) => void;
  onDelete: (pageId: string, sourceId: string) => void;
}) {
  const { data: pages, isLoading } = useDiscoveredPages(sourceId);

  const statusBadge = (status: DiscoveredPage['status']) => {
    const styles: Record<string, string> = {
      new: 'bg-signal-high/20 text-signal-high',
      changed: 'bg-yellow-500/20 text-yellow-400',
      known: 'bg-dark-bg text-dark-muted',
      ignored: 'bg-dark-bg text-dark-muted',
    };
    return (
      <span className={`text-xs px-1.5 py-0.5 rounded ${styles[status] ?? ''}`}>
        {status}
      </span>
    );
  };

  if (isLoading) return <p className="text-xs text-dark-muted py-2 px-4">Loading…</p>;
  if (!pages || pages.length === 0)
    return <p className="text-xs text-dark-muted py-2 px-4">No pages discovered yet.</p>;

  return (
    <table className="w-full text-xs mt-1">
      <thead>
        <tr className="border-b border-dark-border/30">
          <th className="text-left py-1 px-4 text-dark-muted font-medium">Discovered URL</th>
          <th className="text-left py-1 text-dark-muted font-medium">Status</th>
          <th className="text-left py-1 text-dark-muted font-medium">Depth</th>
          <th className="text-left py-1 text-dark-muted font-medium">Last Changed</th>
          <th className="text-left py-1 text-dark-muted font-medium">Active</th>
          <th className="text-left py-1 text-dark-muted font-medium"></th>
        </tr>
      </thead>
      <tbody>
        {pages.map((page) => (
          <tr
            key={page.id}
            className={`border-b border-dark-border/20 ${!page.is_active ? 'opacity-40' : ''}`}
          >
            <td className="py-1 px-4 max-w-sm truncate" title={page.url}>
              {page.url}
            </td>
            <td className="py-1">{statusBadge(page.status)}</td>
            <td className="py-1 text-dark-muted">{page.depth}</td>
            <td className="py-1 text-dark-muted">
              {page.last_changed_at
                ? new Date(page.last_changed_at).toLocaleDateString('de-DE')
                : '—'}
            </td>
            <td className="py-1">
              <button
                onClick={() => onToggle(page.id, !page.is_active)}
                className={`text-xs px-2 py-0.5 rounded ${
                  page.is_active
                    ? 'bg-signal-high/20 text-signal-high'
                    : 'bg-dark-bg text-dark-muted'
                }`}
              >
                {page.is_active ? 'Active' : 'Ignored'}
              </button>
            </td>
            <td className="py-1">
              <button
                onClick={() => onDelete(page.id, page.source_id)}
                className="text-signal-low hover:text-red-400"
                title="Delete"
              >
                <Trash2 size={12} />
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function SourcesAdmin() {
  const { data: companies, isLoading: companiesLoading, error: companiesError, refetch: refetchCompanies } = useCompanies();
  const { data: sources, isLoading: sourcesLoading, error: sourcesError } = useSources();
  
  const createCompany = useCreateCompany();
  const createSource = useCreateSource();
  const updateSource = useUpdateSource();
  const deleteSource = useDeleteSource();
  const deleteCompany = useDeleteCompany();
  const updateCompanyDynamic = useUpdateCompanyDynamic();
  const stream = useCrawlStream();

  const [newCompanyOpen, setNewCompanyOpen] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newCompanySlug, setNewCompanySlug] = useState('');
  const [newCompanyType, setNewCompanyType] = useState<CompanyType>('competitor');
  const [newCompanyWebsite, setNewCompanyWebsite] = useState('');

  const [newSourceCompanyId, setNewSourceCompanyId] = useState('');
  const [newSourceUrl, setNewSourceUrl] = useState('');
  const [newSourceLabel, setNewSourceLabel] = useState('');
  const [newSourceType, setNewSourceType] = useState<SourceType>('news');

  // Edit source state
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [editUrl, setEditUrl] = useState('');
  const [editLabel, setEditLabel] = useState('');
  const [editType, setEditType] = useState<SourceType>('news');

  // Edit company state
  const [editingCompany, setEditingCompany] = useState<Company | null>(null);
  const [editCompanyName, setEditCompanyName] = useState('');
  const [editCompanyType, setEditCompanyType] = useState<CompanyType>('competitor');
  const [editCompanyWebsite, setEditCompanyWebsite] = useState('');
  const [editCompanyDescription, setEditCompanyDescription] = useState('');

  const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [companyEditError, setCompanyEditError] = useState<string | null>(null);
  const toggleDiscoveredPage = useToggleDiscoveredPage();
  const deleteDiscoveredPage = useDeleteDiscoveredPage();

  function handleCreateCompany(e: React.FormEvent) {
    e.preventDefault();
    if (!newCompanyName || !newCompanySlug) return;
    createCompany.mutate(
      { name: newCompanyName, slug: newCompanySlug, type: newCompanyType, website: newCompanyWebsite || null },
      { onSuccess: async () => {
        setNewCompanyOpen(false);
        setNewCompanyName('');
        setNewCompanySlug('');
        setNewCompanyWebsite('');
        await refetchCompanies();
      }},
    );
  }

  function handleCreateSource(e: React.FormEvent) {
    e.preventDefault();
    if (!newSourceCompanyId || !newSourceUrl) return;
    setSourceError(null);
    createSource.mutate(
      { company_id: newSourceCompanyId, url: newSourceUrl, label: newSourceLabel || null, source_type: newSourceType },
      { onSuccess: () => {
        setNewSourceUrl('');
        setNewSourceLabel('');
        setNewSourceType('news');
      },
      onError: (err) => {
        setSourceError(err instanceof ApiError ? err.message : 'Failed to create source');
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

  function handleDeleteCompany(slug: string, companyName: string) {
    if (window.confirm(`Delete company "${companyName}" and all its sources? This action cannot be undone.`)) {
      deleteCompany.mutate(slug);
    }
  }

  function handleCrawlSource(sourceId: string) {
    stream.start(sourceId);
  }

  function openEditModal(source: Source) {
    setEditingSource(source);
    setEditUrl(source.url);
    setEditLabel(source.label || '');
    setEditType(source.source_type);
  }

  function closeEditModal() {
    setEditingSource(null);
    setEditUrl('');
    setEditLabel('');
    setEditType('news');
  }

  function handleSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editingSource) return;
    
    const updates: { url?: string; label?: string | null; source_type?: SourceType } = {};
    if (editUrl !== editingSource.url) updates.url = editUrl;
    if (editLabel !== (editingSource.label || '')) updates.label = editLabel || null;
    if (editType !== editingSource.source_type) updates.source_type = editType;

    if (Object.keys(updates).length > 0) {
      updateSource.mutate(
        { sourceId: editingSource.id, data: updates },
        { onSuccess: closeEditModal }
      );
    } else {
      closeEditModal();
    }
  }

  function openEditCompanyModal(company: Company) {
    setEditingCompany(company);
    setEditCompanyName(company.name);
    setEditCompanyType(company.type);
    setEditCompanyWebsite(company.website || '');
    setEditCompanyDescription(company.description || '');
  }

  function closeEditCompanyModal() {
    setEditingCompany(null);
    setEditCompanyName('');
    setEditCompanyType('competitor');
    setEditCompanyWebsite('');
    setEditCompanyDescription('');
  }

  function handleSaveCompanyEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editingCompany) return;
    setCompanyEditError(null);
    
    const updates: { name?: string; type?: CompanyType; website?: string | null; description?: string | null } = {};
    if (editCompanyName !== editingCompany.name) updates.name = editCompanyName;
    if (editCompanyType !== editingCompany.type) updates.type = editCompanyType;
    if (editCompanyWebsite !== (editingCompany.website || '')) updates.website = editCompanyWebsite || null;
    if (editCompanyDescription !== (editingCompany.description || '')) updates.description = editCompanyDescription || null;

    if (Object.keys(updates).length > 0) {
      updateCompanyDynamic.mutate({ slug: editingCompany.slug, data: updates }, { onSuccess: closeEditCompanyModal, onError: (err) => {
        setCompanyEditError(err instanceof ApiError ? err.message : 'Failed to update company');
      }});
    } else {
      closeEditCompanyModal();
    }
  }

  const isLoading = companiesLoading || sourcesLoading;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Sources Admin</h1>
        <div className="flex gap-2">
          <button onClick={() => stream.start()} disabled={stream.isRunning} className="btn-primary flex items-center gap-2">
            <Play size={16} /> {stream.isRunning ? 'Crawling...' : 'Run Full Crawl'}
          </button>
          <button onClick={() => setNewCompanyOpen(true)} className="btn-secondary flex items-center gap-2">
            <Plus size={16} /> Add Company
          </button>
        </div>
      </div>

      <CrawlProgressPanel
        isRunning={stream.isRunning}
        sourceStates={stream.sourceStates}
        summary={stream.summary}
        connectionError={stream.connectionError}
        crawlTotal={stream.crawlTotal}
        onCancel={stream.cancel}
        onDismiss={stream.reset}
      />

      {isLoading ? (
        <p className="text-dark-muted">Loading...</p>
      ) : companiesError ? (
        <p className="text-signal-low">Error loading companies: {companiesError.message}</p>
      ) : !companies || companies.length === 0 ? (
        <p className="text-dark-muted">No companies found. Create one first!</p>
      ) : (
        <div className="space-y-6">
          {companies?.map((company) => {
            const companySources = sources?.filter((s) => s.company_id === company.id) ?? [];
            return (
              <div key={company.id} className="card">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h2 className="text-lg font-semibold">{company.name}</h2>
                    <span className={`text-xs px-2 py-0.5 rounded ${company.type === 'competitor' ? 'bg-type-product_update/20 text-type-product_update' : 'bg-type-ai_announcement/20 text-type-ai_announcement'}`}>
                      {company.type === 'competitor' ? 'Competitor' : 'Market Source'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={() => openEditCompanyModal(company)} 
                      className="text-dark-muted hover:text-dark-text p-1" 
                      title="Edit company"
                    >
                      <Edit2 size={16} />
                    </button>
                    <button 
                      onClick={() => handleDeleteCompany(company.slug, company.name)} 
                      className="text-signal-low hover:text-red-400 p-1" 
                      title="Delete company"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
                {company.website && <p className="text-xs text-dark-muted mb-3">{company.website}</p>}
                {company.description && <p className="text-sm text-dark-muted mb-3">{company.description}</p>}
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
                      <React.Fragment key={source.id}>
                        <tr className="border-b border-dark-border/50">
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
                            <button 
                              onClick={() => setExpandedSourceId(expandedSourceId === source.id ? null : source.id)} 
                              className="text-dark-muted hover:text-dark-text mr-2" 
                              title="Toggle discovered pages"
                            >
                              {expandedSourceId === source.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                            </button>
                            <button onClick={() => handleCrawlSource(source.id)} className="text-dark-accent hover:text-indigo-300 mr-2" title="Crawl this source">
                              <Play size={14} />
                            </button>
                            <button onClick={() => openEditModal(source)} className="text-dark-muted hover:text-dark-text mr-2" title="Edit source">
                              <Edit2 size={14} />
                            </button>
                            <button onClick={() => handleDeleteSource(source.id)} className="text-signal-low hover:text-red-400" title="Delete source">
                              <Trash2 size={14} />
                            </button>
                          </td>
                        </tr>
                        {expandedSourceId === source.id && (
                          <tr>
                            <td colSpan={6} className="bg-dark-bg/50">
                              <DiscoveredPagesSection sourceId={source.id} onToggle={(pageId, isActive) => toggleDiscoveredPage.mutate({ pageId, isActive })} onDelete={(pageId, srcId) => deleteDiscoveredPage.mutate({ pageId, sourceId: srcId })} />
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
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
                <input value={newCompanyWebsite} onChange={(e) => setNewCompanyWebsite(e.target.value)} className="input-field w-full" placeholder="https://..." />
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
        {sourceError && <p className="text-signal-low text-sm mt-2">{sourceError}</p>}
      </div>

      {editingSource && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-8 z-50" onClick={closeEditModal}>
          <div className="card w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Edit Source</h2>
              <button onClick={closeEditModal} className="text-dark-muted hover:text-dark-text">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveEdit} className="space-y-4">
              <div>
                <label className="block text-sm text-dark-muted mb-1">URL</label>
                <input 
                  value={editUrl} 
                  onChange={(e) => setEditUrl(e.target.value)} 
                  className="input-field w-full" 
                  required 
                  placeholder="https://..." 
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-dark-muted mb-1">Label</label>
                  <input 
                    value={editLabel} 
                    onChange={(e) => setEditLabel(e.target.value)} 
                    className="input-field w-full" 
                    placeholder="News" 
                  />
                </div>
                <div>
                  <label className="block text-sm text-dark-muted mb-1">Type</label>
                  <select 
                    value={editType} 
                    onChange={(e) => setEditType(e.target.value as SourceType)} 
                    className="input-field w-full"
                  >
                    {sourceTypes.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editingSource.is_active}
                    onChange={() => handleToggleSource(editingSource.id, editingSource.is_active)}
                    id="edit-active"
                    className="accent-dark-accent"
                  />
                  <label htmlFor="edit-active" className="text-sm text-dark-text cursor-pointer">
                    Active
                  </label>
                </div>
              </div>
              <div className="flex gap-2 pt-2">
                <button type="submit" disabled={updateSource.isPending} className="btn-primary flex-1">
                  {updateSource.isPending ? 'Saving...' : 'Save Changes'}
                </button>
                <button type="button" onClick={closeEditModal} className="btn-secondary flex-1">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editingCompany && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-8 z-50" onClick={closeEditCompanyModal}>
          <div className="card w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Edit Company</h2>
              <button onClick={closeEditCompanyModal} className="text-dark-muted hover:text-dark-text">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveCompanyEdit} className="space-y-4">
              <div>
                <label className="block text-sm text-dark-muted mb-1">Name</label>
                <input 
                  value={editCompanyName} 
                  onChange={(e) => setEditCompanyName(e.target.value)} 
                  className="input-field w-full" 
                  required 
                />
              </div>
              <div>
                <label className="block text-sm text-dark-muted mb-1">Type</label>
                <select 
                  value={editCompanyType} 
                  onChange={(e) => setEditCompanyType(e.target.value as CompanyType)} 
                  className="input-field w-full"
                >
                  <option value="competitor">Competitor</option>
                  <option value="market_source">Market Source</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-dark-muted mb-1">Website</label>
                <input 
                  value={editCompanyWebsite} 
                  onChange={(e) => setEditCompanyWebsite(e.target.value)} 
                  className="input-field w-full" 
                  placeholder="https://..." 
                />
              </div>
              <div>
                <label className="block text-sm text-dark-muted mb-1">Description</label>
                <textarea 
                  value={editCompanyDescription} 
                  onChange={(e) => setEditCompanyDescription(e.target.value)} 
                  className="input-field w-full h-20" 
                  placeholder="Company description..." 
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button 
                  type="submit" 
                  className="btn-primary flex-1"
                >
                  Save Changes
                </button>
                <button type="button" onClick={closeEditCompanyModal} className="btn-secondary flex-1">Cancel</button>
              </div>
              {companyEditError && <p className="text-signal-low text-sm mt-2">{companyEditError}</p>}
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
