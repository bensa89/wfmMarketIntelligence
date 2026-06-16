import { useState, useEffect } from 'react';
import { useContextData, useUpdateContext, useExternalView, useSynthesizeExternalView } from '../hooks/useContext';
import TagList from '../components/TagList';
import type { ContextUpdate } from '../types';
import { Save, Globe, RefreshCw, Eye } from 'lucide-react';

const listFields: { key: keyof ContextUpdate; label: string; placeholder: string }[] = [
  { key: 'target_industries', label: 'Target Industries', placeholder: 'Add industry...' },
  { key: 'target_segments', label: 'Target Segments', placeholder: 'Add segment...' },
  { key: 'core_capabilities', label: 'Core Capabilities', placeholder: 'Add capability...' },
  { key: 'strategic_priorities', label: 'Strategic Priorities', placeholder: 'Add priority...' },
  { key: 'differentiators', label: 'Differentiators', placeholder: 'Add differentiator...' },
  { key: 'relevant_competitive_areas', label: 'Relevant Competitive Areas', placeholder: 'Add area...' },
  { key: 'non_focus_areas', label: 'Non-Focus Areas', placeholder: 'Add area...' },
];

export default function CompanyContext() {
  const { data: context, isLoading } = useContextData();
  const updateContext = useUpdateContext();
  const { data: externalView, isLoading: externalViewLoading } = useExternalView();
  const synthesize = useSynthesizeExternalView();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<ContextUpdate>({});
  const [inputValues, setInputValues] = useState<Record<string, string>>({});

  useEffect(() => {
    if (context && !editing) {
      setForm({
        company_name: context.company_name ?? '',
        short_description: context.short_description ?? '',
        target_industries: context.target_industries,
        target_segments: context.target_segments,
        core_capabilities: context.core_capabilities,
        strategic_priorities: context.strategic_priorities,
        differentiators: context.differentiators,
        relevant_competitive_areas: context.relevant_competitive_areas,
        non_focus_areas: context.non_focus_areas,
      });
    }
  }, [context, editing]);

  if (isLoading) return <p className="text-ink-muted">Loading context...</p>;
  if (!context) return <p className="text-signal-low">Failed to load context.</p>;

  const ctx = context;

  function handleSave() {
    const payload: ContextUpdate = {};
    if (form.company_name !== ctx.company_name) payload.company_name = form.company_name;
    if (form.short_description !== ctx.short_description) payload.short_description = form.short_description;
    for (const field of listFields) {
      const key = field.key;
      if (JSON.stringify(form[key]) !== JSON.stringify(ctx[key as keyof typeof ctx])) {
        (payload as Record<string, string[]>)[key as string] = form[key] as string[];
      }
    }
    updateContext.mutate(payload, { onSuccess: () => setEditing(false) });
  }

  function handleAddItem(key: string) {
    const val = inputValues[key]?.trim();
    if (!val) return;
    const currentList = (form[key as keyof ContextUpdate] as string[]) ?? [];
    setForm({ ...form, [key]: [...currentList, val] });
    setInputValues({ ...inputValues, [key]: '' });
  }

  function handleRemoveItem(key: string, index: number) {
    const currentList = (form[key as keyof ContextUpdate] as string[]) ?? [];
    setForm({ ...form, [key]: currentList.filter((_, i) => i !== index) });
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Globe size={24} /> Company Context
        </h1>
        <div className="flex gap-2">
          {editing ? (
            <>
              <button onClick={handleSave} disabled={updateContext.isPending} className="btn-primary flex items-center gap-2">
                <Save size={16} /> {updateContext.isPending ? 'Saving...' : 'Save'}
              </button>
              <button onClick={() => setEditing(false)} className="btn-secondary">Cancel</button>
            </>
          ) : (
            <button onClick={() => setEditing(true)} className="btn-primary">Edit</button>
          )}
        </div>
      </div>

      <div className="card mb-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm text-ink-muted mb-1">Company Name</label>
            {editing ? (
              <input
                value={form.company_name ?? ''}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                className="input-field w-full"
              />
            ) : (
              <p className="text-ink">{context.company_name || '—'}</p>
            )}
          </div>
          <div>
            <label className="block text-sm text-ink-muted mb-1">Short Description</label>
            {editing ? (
              <textarea
                value={form.short_description ?? ''}
                onChange={(e) => setForm({ ...form, short_description: e.target.value })}
                className="input-field w-full h-20"
              />
            ) : (
              <p className="text-ink">{context.short_description || '—'}</p>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {listFields.map(({ key, label, placeholder }) => {
          const items = (form[key] as string[]) ?? [];
          return (
            <div key={key} className="card">
              <h3 className="text-sm font-semibold mb-2">{label}</h3>
              {editing ? (
                <div>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {items.map((item, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded bg-app-bg border border-app-border text-ink flex items-center gap-1">
                        {item}
                        <button onClick={() => handleRemoveItem(key, i)} className="text-ink-muted hover:text-ink">×</button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={inputValues[key] ?? ''}
                      onChange={(e) => setInputValues({ ...inputValues, [key]: e.target.value })}
                      className="input-field flex-1"
                      placeholder={placeholder}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddItem(key); } }}
                    />
                    <button onClick={() => handleAddItem(key)} className="btn-secondary text-sm">Add</button>
                  </div>
                </div>
              ) : (
                <TagList items={items} />
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-ink-muted mt-4">
        Last updated: {new Date(context.updated_at).toLocaleString('de-DE')}
      </p>

      {/* ExternalCompanyView Panel */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Eye size={20} /> Außensicht
          </h2>
          <button
            onClick={() => synthesize.mutate()}
            disabled={synthesize.isPending}
            className="btn-secondary flex items-center gap-2 text-sm"
          >
            <RefreshCw size={14} className={synthesize.isPending ? 'animate-spin' : ''} />
            {synthesize.isPending ? 'Wird analysiert…' : 'Außensicht aktualisieren'}
          </button>
        </div>
        {synthesize.isError && (
          <p className="text-sm text-signal-low mb-3">
            {(synthesize.error as { message?: string })?.message ?? 'Synthese fehlgeschlagen.'}
          </p>
        )}
        {externalViewLoading ? (
          <p className="text-sm text-ink-muted">Lade Außensicht…</p>
        ) : !externalView ? (
          <div className="card text-center py-6 text-ink-muted text-sm">
            Noch keine Außensicht vorhanden. Zuerst die eigene Website crawlen, dann "Außensicht aktualisieren" klicken.
          </div>
        ) : (
          <div className="space-y-4">
            {externalView.summary && (
              <div className="card">
                <h3 className="text-sm font-semibold mb-2">Zusammenfassung</h3>
                <p className="text-sm text-ink">{externalView.summary}</p>
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {externalView.key_messages?.length > 0 && (
                <div className="card">
                  <h3 className="text-sm font-semibold mb-2">Kernbotschaften</h3>
                  <TagList items={externalView.key_messages} />
                </div>
              )}
              {externalView.observed_capabilities?.length > 0 && (
                <div className="card">
                  <h3 className="text-sm font-semibold mb-2">Kommunizierte Capabilities</h3>
                  <TagList items={externalView.observed_capabilities} />
                </div>
              )}
              {externalView.observed_differentiators?.length > 0 && (
                <div className="card">
                  <h3 className="text-sm font-semibold mb-2">Kommunizierte Differenzierungsmerkmale</h3>
                  <TagList items={externalView.observed_differentiators} />
                </div>
              )}
              {externalView.observed_target_markets?.length > 0 && (
                <div className="card">
                  <h3 className="text-sm font-semibold mb-2">Kommunizierte Zielmärkte</h3>
                  <TagList items={externalView.observed_target_markets} />
                </div>
              )}
            </div>
            {externalView.tone_and_positioning && (
              <div className="card">
                <h3 className="text-sm font-semibold mb-2">Tone & Positioning</h3>
                <p className="text-sm text-ink">{externalView.tone_and_positioning}</p>
              </div>
            )}
            <p className="text-xs text-ink-muted">
              Basiert auf {externalView.signal_count_used} Signals
              {externalView.generated_at && ` · Zuletzt generiert: ${new Date(externalView.generated_at).toLocaleString('de-DE')}`}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
