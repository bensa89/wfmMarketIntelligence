import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPut, apiPost } from '../api/client';

const DAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

const TIMEZONES = [
  'Europe/Berlin',
  'Europe/London',
  'Europe/Paris',
  'Europe/Zurich',
  'UTC',
];

interface ScheduleConfig {
  crawl_enabled: boolean;
  crawl_day_of_week: number;
  crawl_time: string;
  crawl_timezone: string;
  digest_after_crawl: boolean;
  digest_enabled: boolean;
  digest_day_of_week: number;
  digest_time: string;
  email_enabled: boolean;
  email_recipients: string[];
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  smtp_from: string;
  updated_at?: string;
}

interface ScheduleStatus {
  config: ScheduleConfig;
  next_crawl: string | null;
  next_digest: string | null;
}

const DEFAULT_CONFIG: ScheduleConfig = {
  crawl_enabled: false,
  crawl_day_of_week: 0,
  crawl_time: '06:00',
  crawl_timezone: 'Europe/Berlin',
  digest_after_crawl: true,
  digest_enabled: false,
  digest_day_of_week: 1,
  digest_time: '08:00',
  email_enabled: false,
  email_recipients: [],
  smtp_host: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  smtp_from: '',
};

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
      <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">{title}</h2>
      {children}
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none ${
        checked ? 'bg-blue-600' : 'bg-slate-200'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200 ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  );
}

function DayPicker({ value, onChange, disabled }: { value: number; onChange: (v: number) => void; disabled?: boolean }) {
  return (
    <div className="flex gap-1">
      {DAYS.map((day, i) => (
        <button
          key={day}
          type="button"
          disabled={disabled}
          onClick={() => onChange(i)}
          className={`w-9 h-9 rounded-lg text-xs font-medium transition-colors ${
            value === i
              ? 'bg-blue-600 text-white'
              : disabled
              ? 'bg-slate-50 text-slate-300 cursor-not-allowed'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          {day}
        </button>
      ))}
    </div>
  );
}

function NextRunBadge({ label, time }: { label: string; time: string | null }) {
  if (!time) return <p className="text-xs text-slate-400">{label}: nicht geplant</p>;
  const d = new Date(time);
  return (
    <p className="text-xs text-slate-500">
      {label}:{' '}
      <span className="font-medium text-slate-700">
        {d.toLocaleDateString('de-DE', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' })}{' '}
        {d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}
      </span>
    </p>
  );
}

export default function ScheduleAdmin() {
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [testEmailLoading, setTestEmailLoading] = useState(false);

  const { data: status, isLoading } = useQuery<ScheduleStatus>({
    queryKey: ['schedule'],
    queryFn: () => apiGet<ScheduleStatus>('/schedule'),
  });

  const [form, setForm] = useState<ScheduleConfig>(DEFAULT_CONFIG);

  const [synced, setSynced] = useState(false);
  if (status && !synced) {
    setForm(status.config);
    setSynced(true);
  }

  const saveMutation = useMutation({
    mutationFn: (payload: ScheduleConfig) =>
      apiPut<ScheduleStatus>('/schedule', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule'] });
      setSynced(false);
      showToast('success', 'Einstellungen gespeichert');
    },
    onError: (err: Error) => showToast('error', err.message),
  });

  function showToast(type: 'success' | 'error', msg: string) {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3000);
  }

  async function handleTestEmail() {
    setTestEmailLoading(true);
    try {
      await apiPost('/schedule/test-email');
      showToast('success', 'Test-E-Mail gesendet');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Fehler beim Senden';
      showToast('error', message);
    } finally {
      setTestEmailLoading(false);
    }
  }

  const set = (key: keyof ScheduleConfig, value: unknown) =>
    setForm((f) => ({ ...f, [key]: value }));

  if (isLoading) return <div className="p-8 text-slate-400 text-sm">Lade…</div>;

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Automation</h1>
        <p className="text-sm text-slate-500 mt-1">Automatische Crawl- und Digest-Zeitpläne konfigurieren</p>
      </div>

      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-2 rounded-lg text-sm font-medium shadow-lg ${
            toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
          }`}
        >
          {toast.msg}
        </div>
      )}

      <SectionCard title="Crawl-Zeitplan">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-700">Automatischer Crawl aktiv</span>
          <Toggle checked={form.crawl_enabled} onChange={(v) => set('crawl_enabled', v)} />
        </div>

        <div className={form.crawl_enabled ? '' : 'opacity-40 pointer-events-none'}>
          <label className="block text-xs font-medium text-slate-500 mb-2">Wochentag</label>
          <DayPicker
            value={form.crawl_day_of_week}
            onChange={(v) => set('crawl_day_of_week', v)}
            disabled={!form.crawl_enabled}
          />

          <div className="flex gap-4 mt-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Uhrzeit</label>
              <input
                type="time"
                value={form.crawl_time}
                onChange={(e) => set('crawl_time', e.target.value)}
                className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Zeitzone</label>
              <select
                value={form.crawl_timezone}
                onChange={(e) => set('crawl_timezone', e.target.value)}
                className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>{tz}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <NextRunBadge label="Nächste Ausführung" time={status?.next_crawl ?? null} />
      </SectionCard>

      <SectionCard title="Digest-Einstellungen">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-700">Digest direkt nach Crawl generieren</span>
          <Toggle checked={form.digest_after_crawl} onChange={(v) => set('digest_after_crawl', v)} />
        </div>

        {!form.digest_after_crawl && (
          <div className="border-t border-slate-100 pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-700">Eigener Digest-Zeitplan aktiv</span>
              <Toggle checked={form.digest_enabled} onChange={(v) => set('digest_enabled', v)} />
            </div>

            <div className={form.digest_enabled ? '' : 'opacity-40 pointer-events-none'}>
              <label className="block text-xs font-medium text-slate-500 mb-2">Wochentag</label>
              <DayPicker
                value={form.digest_day_of_week}
                onChange={(v) => set('digest_day_of_week', v)}
                disabled={!form.digest_enabled}
              />
              <div className="mt-3">
                <label className="block text-xs font-medium text-slate-500 mb-1">Uhrzeit</label>
                <input
                  type="time"
                  value={form.digest_time}
                  onChange={(e) => set('digest_time', e.target.value)}
                  className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        )}

        <NextRunBadge label="Nächste Digest-Generierung" time={status?.next_digest ?? null} />
      </SectionCard>

      <SectionCard title="E-Mail-Benachrichtigungen">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-700">E-Mail-Versand nach Crawl aktiv</span>
          <Toggle checked={form.email_enabled} onChange={(v) => set('email_enabled', v)} />
        </div>

        {form.email_enabled && (
          <div className="space-y-3 border-t border-slate-100 pt-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Empfänger (eine Adresse pro Zeile)</label>
              <textarea
                rows={3}
                value={form.email_recipients.join('\n')}
                onChange={(e) =>
                  set(
                    'email_recipients',
                    e.target.value
                      .split('\n')
                      .map((s) => s.trim())
                      .filter(Boolean),
                  )
                }
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="max@example.com&#10;lisa@example.com"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">SMTP-Host</label>
                <input
                  value={form.smtp_host}
                  onChange={(e) => set('smtp_host', e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="smtp.example.com"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Port</label>
                <input
                  type="number"
                  value={form.smtp_port}
                  onChange={(e) => set('smtp_port', parseInt(e.target.value) || 587)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Absender</label>
                <input
                  value={form.smtp_from}
                  onChange={(e) => set('smtp_from', e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="intel@example.com"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Benutzername</label>
                <input
                  value={form.smtp_user}
                  onChange={(e) => set('smtp_user', e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-slate-500 mb-1">Passwort</label>
                <input
                  type="password"
                  value={form.smtp_password}
                  onChange={(e) => set('smtp_password', e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <button
              type="button"
              onClick={handleTestEmail}
              disabled={testEmailLoading}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50"
            >
              {testEmailLoading ? 'Sende…' : 'Test-E-Mail senden'}
            </button>
          </div>
        )}
      </SectionCard>

      <div className="flex items-center justify-between">
        <div>
          {form.updated_at && (
            <p className="text-xs text-slate-400">
              Zuletzt gespeichert:{' '}
              {new Date(form.updated_at).toLocaleString('de-DE')}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => saveMutation.mutate(form)}
          disabled={saveMutation.isPending}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          {saveMutation.isPending ? 'Speichere…' : 'Einstellungen speichern'}
        </button>
      </div>
    </div>
  );
}
