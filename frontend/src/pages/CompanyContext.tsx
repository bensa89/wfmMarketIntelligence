import { useState, useEffect } from 'react';
import { useContextData, useUpdateContext } from '../hooks/useContext';
import TagList from '../components/TagList';
import type { ContextUpdate } from '../types';
import { Save, Globe } from 'lucide-react';

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

  if (isLoading) return <p className="text-dark-muted">Loading context...</p>;
  if (!context) return <p className="text-signal-low">Failed to load context.</p>;

  function handleSave() {
    const payload: ContextUpdate = {};
    if (form.company_name !== context.company_name) payload.company_name = form.company_name;
    if (form.short_description !== context.short_description) payload.short_description = form.short_description;
    for (const field of listFields) {
      const key = field.key;
      if (JSON.stringify(form[key]) !== JSON.stringify(context[key as keyof typeof context])) {
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
    <div>
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
            <label className="block text-sm text-dark-muted mb-1">Company Name</label>
            {editing ? (
              <input
                value={form.company_name ?? ''}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                className="input-field w-full"
              />
            ) : (
              <p className="text-dark-text">{context.company_name || '—'}</p>
            )}
          </div>
          <div>
            <label className="block text-sm text-dark-muted mb-1">Short Description</label>
            {editing ? (
              <textarea
                value={form.short_description ?? ''}
                onChange={(e) => setForm({ ...form, short_description: e.target.value })}
                className="input-field w-full h-20"
              />
            ) : (
              <p className="text-dark-text">{context.short_description || '—'}</p>
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
                      <span key={i} className="text-xs px-2 py-0.5 rounded bg-dark-bg border border-dark-border text-dark-text flex items-center gap-1">
                        {item}
                        <button onClick={() => handleRemoveItem(key, i)} className="text-signal-low hover:text-red-400">×</button>
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

      <p className="text-xs text-dark-muted mt-4">
        Last updated: {new Date(context.updated_at).toLocaleString('de-DE')}
      </p>
    </div>
  );
}
