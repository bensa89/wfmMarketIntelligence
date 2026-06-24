import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RotateCcw, Save } from 'lucide-react';
import { fetchAppSettings, resetAppSetting, updateAppSetting } from '../api/settingsAdmin';
import type { AppSetting } from '../types/settings';

type FieldKind = 'select' | 'number' | 'boolean' | 'text';

interface FieldDef {
  key: string;
  label: string;
  kind: FieldKind;
  options?: { value: string; label: string }[];
  step?: string;
}

const FIELD_GROUPS: { title: string; fields: FieldDef[] }[] = [
  {
    title: 'LLM-Provider',
    fields: [
      {
        key: 'llm_provider', label: 'Provider', kind: 'select', options: [
          { value: 'claude', label: 'Claude' },
          { value: 'ollama', label: 'Ollama' },
          { value: 'opencode', label: 'Opencode' },
        ],
      },
      { key: 'claude_model', label: 'Claude-Modell', kind: 'text' },
      { key: 'ollama_base_url', label: 'Ollama Base URL', kind: 'text' },
      { key: 'ollama_model', label: 'Ollama-Modell', kind: 'text' },
      { key: 'opencode_model', label: 'Opencode-Modell', kind: 'text' },
      { key: 'opencode_base_url', label: 'Opencode Base URL', kind: 'text' },
    ],
  },
  {
    title: 'Crawling',
    fields: [
      { key: 'discovery_depth', label: 'Discovery-Tiefe', kind: 'number' },
      { key: 'js_rendering_enabled', label: 'JS-Rendering aktiv', kind: 'boolean' },
      { key: 'crawl_concurrency', label: 'Crawl-Concurrency', kind: 'number' },
      { key: 'discovery_concurrency', label: 'Discovery-Concurrency', kind: 'number' },
      { key: 'analysis_concurrency', label: 'Analyse-Concurrency', kind: 'number' },
    ],
  },
  {
    title: 'Suche & Bewertung',
    fields: [
      { key: 'search_relevance_threshold', label: 'Such-Relevanz-Schwelle', kind: 'number', step: '0.05' },
      { key: 'search_queries_per_company', label: 'Suchanfragen pro Unternehmen', kind: 'number' },
      { key: 'assessment_threshold', label: 'Assessment-Schwelle', kind: 'number', step: '0.05' },
    ],
  },
];

function FieldRow({ def, setting, onSaved }: { def: FieldDef; setting: AppSetting; onSaved: () => void }) {
  const [value, setValue] = useState(setting.current_value);

  const saveMutation = useMutation({
    mutationFn: (v: string) => updateAppSetting(def.key, v),
    onSuccess: onSaved,
  });
  const resetMutation = useMutation({
    mutationFn: () => resetAppSetting(def.key),
    onSuccess: onSaved,
  });

  const dirty = value !== setting.current_value;

  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-slate-100 last:border-b-0">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-700">{def.label}</span>
          {setting.is_override && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">
              Override
            </span>
          )}
        </div>
        <span className="text-[11px] text-slate-400">Default: {setting.default_value}</span>
      </div>

      {def.kind === 'select' && (
        <select
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm bg-white"
        >
          {def.options!.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      )}

      {def.kind === 'boolean' && (
        <select
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm bg-white"
        >
          <option value="true">An</option>
          <option value="false">Aus</option>
        </select>
      )}

      {def.kind === 'number' && (
        <input
          type="number"
          step={def.step ?? '1'}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm w-28"
        />
      )}

      {def.kind === 'text' && (
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm w-56"
        />
      )}

      <button
        onClick={() => saveMutation.mutate(value)}
        disabled={!dirty || saveMutation.isPending}
        className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
        title="Speichern"
      >
        <Save size={14} />
      </button>

      {setting.is_override && (
        <button
          onClick={() => resetMutation.mutate()}
          disabled={resetMutation.isPending}
          className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
          title="Auf Default zurücksetzen"
        >
          <RotateCcw size={14} />
        </button>
      )}
    </div>
  );
}

export default function SettingsAdmin() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['app-settings'], queryFn: fetchAppSettings });

  function refetchSettings() {
    queryClient.invalidateQueries({ queryKey: ['app-settings'] });
  }

  if (isLoading || !data) {
    return <div className="p-6 text-sm text-slate-500">Lade Einstellungen…</div>;
  }

  const byKey = new Map(data.map((s) => [s.key, s]));

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Runtime-Settings</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Änderungen wirken sofort und überleben Deployments. Felder ohne Override nutzen
          den Wert aus .env/GitHub-Variablen.
        </p>
      </div>

      {FIELD_GROUPS.map((group) => (
        <div key={group.title} className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-2">
            {group.title}
          </h2>
          {group.fields.map((def) => {
            const setting = byKey.get(def.key);
            if (!setting) return null;
            return <FieldRow key={def.key} def={def} setting={setting} onSaved={refetchSettings} />;
          })}
        </div>
      ))}
    </div>
  );
}
