import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPut, apiPost } from '../api/client';
import { useCompanies } from '../hooks/useCompanies';

const SIGNAL_TYPES = [
  { value: 'product_update', label: 'Produkt-Update' },
  { value: 'ai_announcement', label: 'KI-Ankündigung' },
  { value: 'partnership', label: 'Partnership' },
  { value: 'positioning_change', label: 'Positioning-Änderung' },
  { value: 'target_market_change', label: 'Zielmarkt-Änderung' },
  { value: 'event_or_thought_leadership', label: 'Event / Thought Leadership' },
  { value: 'hiring_signal', label: 'Hiring-Signal' },
  { value: 'other', label: 'Sonstige' },
];

const REANALYSIS_JOB_KEY = 'reanalysis_job_id';

interface ReanalysisJob {
  job_id: string;
  status: 'running' | 'completed' | 'failed';
  queued: number;
  done: number;
  errors: number;
}

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
  const [testDigestEmailLoading, setTestDigestEmailLoading] = useState(false);

  const { data: companies = [] } = useCompanies();
  const competitors = companies.filter((c) => c.type === 'competitor');

  const [reanalysisForm, setReanalysisForm] = useState({ days: 30, company_id: '', signal_type: '' });
  const [reanalysisLoading, setReanalysisLoading] = useState(false);
  const [reanalysisJob, setReanalysisJob] = useState<ReanalysisJob | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const storedJobId = localStorage.getItem(REANALYSIS_JOB_KEY);
    if (storedJobId) {
      startPolling(storedJobId);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  function startPolling(jobId: string) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const job = await apiGet<ReanalysisJob>(`/signals/reanalyse/${jobId}`);
        setReanalysisJob(job);
        if (job.status === 'completed' || job.status === 'failed') {
          clearInterval(pollRef.current!);
          pollRef.current = null;
        }
      } catch {
        clearInterval(pollRef.current!);
        pollRef.current = null;
        localStorage.removeItem(REANALYSIS_JOB_KEY);
      }
    }, 2000);
  }

  async function handleStartReanalysis() {
    setReanalysisLoading(true);
    try {
      const params = new URLSearchParams({ days: String(reanalysisForm.days) });
      if (reanalysisForm.company_id) params.set('company_id', reanalysisForm.company_id);
      if (reanalysisForm.signal_type) params.set('signal_type', reanalysisForm.signal_type);
      const result = await apiPost<{ job_id: string; documents_queued: number }>(`/signals/reanalyse?${params}`);
      localStorage.setItem(REANALYSIS_JOB_KEY, result.job_id);
      setReanalysisJob({ job_id: result.job_id, status: 'running', queued: result.documents_queued, done: 0, errors: 0 });
      startPolling(result.job_id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Fehler beim Starten';
      showToast('error', message);
    } finally {
      setReanalysisLoading(false);
    }
  }

  function handleResetReanalysis() {
    localStorage.removeItem(REANALYSIS_JOB_KEY);
    setReanalysisJob(null);
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }

  const { data: status, isLoading } = useQuery<ScheduleStatus>({
    queryKey: ['schedule'],
    queryFn: () => apiGet<ScheduleStatus>('/schedule'),
  });

  const [form, setForm] = useState<ScheduleConfig>(DEFAULT_CONFIG);
  const [recipientsText, setRecipientsText] = useState('');

  const [synced, setSynced] = useState(false);
  if (status && !synced) {
    setForm(status.config);
    setRecipientsText(status.config.email_recipients.join('\n'));
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

  async function handleTestDigestEmail() {
    setTestDigestEmailLoading(true);
    try {
      await apiPost('/schedule/test-digest-email');
      showToast('success', 'Test Digest-E-Mail gesendet');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Fehler beim Senden';
      showToast('error', message);
    } finally {
      setTestDigestEmailLoading(false);
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
                value={recipientsText}
                onChange={(e) => {
                  setRecipientsText(e.target.value);
                  set(
                    'email_recipients',
                    e.target.value
                      .split('\n')
                      .map((s) => s.trim())
                      .filter(Boolean),
                  );
                }}
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

            <div className="flex gap-4">
              <button
                type="button"
                onClick={handleTestEmail}
                disabled={testEmailLoading}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50"
              >
                {testEmailLoading ? 'Sende…' : 'Test-Crawl-Mail senden'}
              </button>
              <button
                type="button"
                onClick={handleTestDigestEmail}
                disabled={testDigestEmailLoading}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50"
              >
                {testDigestEmailLoading ? 'Sende…' : 'Test Digest-Mail senden'}
              </button>
            </div>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Re-Analyse">
        <p className="text-xs text-slate-500">
          Bestehende Signals löschen und Dokumente der letzten X Tage erneut durch den LLM analysieren lassen.
        </p>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Letzte X Tage</label>
            <input
              type="number"
              min={1}
              max={365}
              value={reanalysisForm.days}
              onChange={(e) => setReanalysisForm((f) => ({ ...f, days: parseInt(e.target.value) || 30 }))}
              disabled={reanalysisJob?.status === 'running'}
              className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-40"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Competitor</label>
            <select
              value={reanalysisForm.company_id}
              onChange={(e) => setReanalysisForm((f) => ({ ...f, company_id: e.target.value }))}
              disabled={reanalysisJob?.status === 'running'}
              className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-40"
            >
              <option value="">Alle</option>
              {competitors.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Signal-Typ</label>
            <select
              value={reanalysisForm.signal_type}
              onChange={(e) => setReanalysisForm((f) => ({ ...f, signal_type: e.target.value }))}
              disabled={reanalysisJob?.status === 'running'}
              className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-40"
            >
              <option value="">Alle</option>
              {SIGNAL_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
        </div>

        {reanalysisJob && (
          <div className={`rounded-lg px-4 py-3 text-sm ${
            reanalysisJob.status === 'running' ? 'bg-blue-50 text-blue-700' :
            reanalysisJob.status === 'completed' ? 'bg-green-50 text-green-700' :
            'bg-red-50 text-red-700'
          }`}>
            {reanalysisJob.status === 'running' && (
              <span>Läuft… {reanalysisJob.done} / {reanalysisJob.queued} Dokumente analysiert</span>
            )}
            {reanalysisJob.status === 'completed' && (
              <span>Abgeschlossen — {reanalysisJob.done} analysiert{reanalysisJob.errors > 0 ? `, ${reanalysisJob.errors} Fehler` : ', 0 Fehler'}</span>
            )}
            {reanalysisJob.status === 'failed' && (
              <span>Fehlgeschlagen</span>
            )}
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleStartReanalysis}
            disabled={reanalysisLoading || reanalysisJob?.status === 'running'}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {reanalysisLoading ? 'Starte…' : 'Re-Analyse starten'}
          </button>
          {reanalysisJob && reanalysisJob.status !== 'running' && (
            <button
              type="button"
              onClick={handleResetReanalysis}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg transition-colors"
            >
              Zurücksetzen
            </button>
          )}
        </div>
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
