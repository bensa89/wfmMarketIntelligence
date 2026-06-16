import { useState } from 'react';
import { useDigests, useGenerateDigest } from '../hooks/useDigests';
import { Calendar, RefreshCw } from 'lucide-react';
import type { RiskItem } from '../types/intelligence';
import type { Digest, DigestSectionItem, EventCalendarItem } from '../types';

const MOVEMENT_COLOURS: Record<string, string> = {
  weak: 'bg-gray-100 text-gray-600',
  relevant: 'bg-blue-100 text-blue-700',
  strong: 'bg-orange-100 text-orange-700',
  market_shaping: 'bg-red-100 text-red-700',
};

function movementBadge(strength: string | null): React.ReactElement | null {
  if (!strength) return null;
  const cls = MOVEMENT_COLOURS[strength] ?? 'bg-gray-100 text-gray-600';
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {strength.replace('_', ' ')}
    </span>
  );
}

function getISOWeek(dateStr: string): number {
  const d = new Date(dateStr);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + 4 - (d.getDay() || 7));
  const yearStart = new Date(d.getFullYear(), 0, 1);
  return Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

function formatDateDE(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('de-DE', { day: 'numeric', month: 'long', year: 'numeric' });
}

function formatEventDate(dateStr: string | null): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('de-DE', { day: 'numeric', month: 'long', year: 'numeric' });
}

function EventItem({ item }: { item: EventCalendarItem }) {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 text-right w-24">
        <span className="text-xs font-medium text-gray-500">{formatEventDate(item.event_date)}</span>
      </div>
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-center gap-2 flex-wrap">
          {item.source_url ? (
            <a href={item.source_url} target="_blank" rel="noopener noreferrer"
              className="font-medium text-gray-900 hover:underline text-sm">
              {item.event_name}
            </a>
          ) : (
            <span className="font-medium text-gray-900 text-sm">{item.event_name}</span>
          )}
          {item.is_new && (
            <span className="inline-block px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">Neu</span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">{item.company}</span>
          {item.event_location && (
            <span className="text-xs text-gray-400">{item.event_location}</span>
          )}
          {item.event_type && (
            <span className="text-xs text-gray-400 italic">{item.event_type}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function EventsCalendarSection({ upcoming, newly_discovered }: {
  upcoming: EventCalendarItem[];
  newly_discovered: EventCalendarItem[];
}) {
  return (
    <div className="space-y-6">
      {upcoming.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Nächste 14 Tage</p>
          <div className="space-y-3">
            {upcoming.map((item) => <EventItem key={item.signal_id} item={item} />)}
          </div>
        </div>
      )}
      {newly_discovered.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Neu entdeckt</p>
          <div className="space-y-3">
            {newly_discovered.map((item) => <EventItem key={item.signal_id} item={item} />)}
          </div>
        </div>
      )}
    </div>
  );
}

function DigestRisksOpportunities({ risks, opportunities }: { risks: RiskItem[]; opportunities: RiskItem[] }) {
  if (!risks.length && !opportunities.length) return null;
  return (
    <div className="grid grid-cols-2 gap-3 mb-6">
      {risks.length > 0 && (
        <div className="bg-red-50 border border-red-100 rounded-xl p-3">
          <p className="text-[11px] font-semibold text-red-600 uppercase tracking-wide mb-2">Emerging Risks</p>
          <ul className="space-y-1.5">
            {risks.map((item, i) => (
              <li key={i} className="flex gap-1.5">
                <span className="text-red-400 flex-shrink-0 mt-0.5">▸</span>
                <div>
                  <span className="text-[12px] text-slate-700 leading-snug">{item.text}</span>
                  {item.company_name && (
                    <span className="ml-1 text-[10px] text-slate-400">· {item.company_name}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      {opportunities.length > 0 && (
        <div className="bg-green-50 border border-green-100 rounded-xl p-3">
          <p className="text-[11px] font-semibold text-green-600 uppercase tracking-wide mb-2">Emerging Opportunities</p>
          <ul className="space-y-1.5">
            {opportunities.map((item, i) => (
              <li key={i} className="flex gap-1.5">
                <span className="text-green-400 flex-shrink-0 mt-0.5">▸</span>
                <div>
                  <span className="text-[12px] text-slate-700 leading-snug">{item.text}</span>
                  {item.company_name && (
                    <span className="ml-1 text-[10px] text-slate-400">· {item.company_name}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function OwnCompanySection({ items }: { items: DigestSectionItem[] }) {
  return (
    <div className="space-y-5">
      {items.map((item) => (
        <div key={item.signal_id} className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            {item.signal_type && (
              <span className="text-xs font-medium text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                {item.signal_type.replace(/_/g, ' ')}
              </span>
            )}
            {item.topic && (
              <span className="text-xs text-ink-muted">{item.topic}</span>
            )}
          </div>
          <div>
            {item.source_url ? (
              <a href={item.source_url} target="_blank" rel="noopener noreferrer"
                className="font-medium text-gray-900 hover:underline">
                {item.title}
              </a>
            ) : (
              <span className="font-medium text-gray-900">{item.title}</span>
            )}
          </div>
          <p className="text-sm text-gray-700">{item.summary}</p>
          {item.why_it_matters && (
            <p className="text-sm text-gray-500 italic">{item.why_it_matters}</p>
          )}
          {(item.source_domain || item.source_title) && (
            <p className="text-xs text-gray-400">
              Quelle: {[item.source_domain, item.source_title].filter(Boolean).join(' — ')}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function SectionItems({ items }: { items: DigestSectionItem[] }) {
  return (
    <div className="space-y-5">
      {items.map((item) => (
        <div key={item.signal_id} className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
              {item.company}
            </span>
            {movementBadge(item.movement_strength)}
          </div>
          <div>
            {item.source_url ? (
              <a
                href={item.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-gray-900 hover:underline"
              >
                {item.title}
              </a>
            ) : (
              <span className="font-medium text-gray-900">{item.title}</span>
            )}
          </div>
          <p className="text-sm text-gray-700">{item.narrative}</p>
          {item.implication_for_us && (
            <p className="text-sm text-gray-500 italic">{item.implication_for_us}</p>
          )}
          {(item.source_domain || item.source_title) && (
            <p className="text-xs text-gray-400">
              Quelle: {[item.source_domain, item.source_title].filter(Boolean).join(' — ')}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

export default function WeeklyDigest() {
  const { data: digests, isLoading } = useDigests();
  const generateDigest = useGenerateDigest();
  const [selectedDigestId, setSelectedDigestId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const selectedDigest = digests?.find((d: Digest) => d.id === selectedDigestId) ?? digests?.[0] ?? null;

  const handleCopyEmail = async (digest: Digest) => {
    const kw = getISOWeek(digest.week_start);
    const start = formatDateDE(digest.week_start);
    const end = formatDateDE(digest.week_end);

    let text = `WFM Market Intelligence — KW ${kw} | ${start} – ${end}\n`;
    if (digest.summary) {
      text += `\n${digest.summary}\n`;
    }
    text += '\n';

    if (digest.risks?.length || digest.opportunities?.length) {
      if (digest.risks?.length) {
        text += `Emerging Risks\n${'─'.repeat(25)}\n`;
        for (const item of digest.risks) {
          text += `▸ ${item.text}${item.company_name ? ` (${item.company_name})` : ''}\n`;
        }
        text += '\n';
      }
      if (digest.opportunities?.length) {
        text += `Emerging Opportunities\n${'─'.repeat(25)}\n`;
        for (const item of digest.opportunities) {
          text += `▸ ${item.text}${item.company_name ? ` (${item.company_name})` : ''}\n`;
        }
        text += '\n';
      }
    }

    for (const section of digest.sections ?? []) {
      text += `${section.title}\n${'─'.repeat(25)}\n`;
      if (section.key === 'events_calendar') {
        if (section.upcoming?.length) {
          text += `Nächste 14 Tage:\n`;
          for (const item of section.upcoming) {
            text += `▸ ${item.event_name} (${item.company})${item.is_new ? ' ★ Neu' : ''}\n`;
            text += `  ${formatEventDate(item.event_date)}`;
            if (item.event_location) text += ` — ${item.event_location}`;
            text += '\n';
            if (item.source_url) text += `  ${item.source_url}\n`;
            text += '\n';
          }
        }
        if (section.newly_discovered?.length) {
          text += `Neu entdeckt:\n`;
          for (const item of section.newly_discovered) {
            text += `▸ ${item.event_name} (${item.company})\n`;
            text += `  ${formatEventDate(item.event_date)}`;
            if (item.event_location) text += ` — ${item.event_location}`;
            text += '\n';
            if (item.source_url) text += `  ${item.source_url}\n`;
            text += '\n';
          }
        }
      } else if (section.key === 'own_company_communication') {
        const ownItems = section.items;
        for (const item of ownItems) {
          text += `▸ ${item.title}\n`;
          text += `  ${item.summary}`;
          if (item.why_it_matters) text += ` ${item.why_it_matters}`;
          text += '\n';
          const source = [item.source_domain, item.source_title].filter(Boolean).join(' — ');
          if (source) text += `  Quelle: ${source}\n`;
          if (item.source_url) text += `  ${item.source_url}\n`;
          text += '\n';
        }
      } else {
        for (const item of section.items) {
          text += `▸ ${item.title} (${item.company})\n`;
          text += `  ${item.narrative}`;
          if (item.implication_for_us) text += ` ${item.implication_for_us}`;
          text += '\n';
          const source = [item.source_domain, item.source_title].filter(Boolean).join(' — ');
          if (source) text += `  Quelle: ${source}\n`;
          if (item.source_url) text += `  ${item.source_url}\n`;
          text += '\n';
        }
      }
      text += '\n';
    }

    text += `${'─'.repeat(25)}\nVollständiger Digest: ${window.location.origin}/digest/${digest.id}`;

    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-4 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Calendar size={24} /> Weekly Digest
        </h1>
        <button
          onClick={() => generateDigest.mutate()}
          disabled={generateDigest.isPending}
          className="btn-primary flex items-center gap-2 flex-shrink-0"
        >
          <RefreshCw size={16} className={generateDigest.isPending ? 'animate-spin' : ''} />
          {generateDigest.isPending ? 'Generating...' : 'Generate New Digest'}
        </button>
      </div>

      {generateDigest.isError && (
        <div className="mb-4 p-3 rounded bg-signal-low/10 text-signal-low text-sm">
          Failed to generate digest. Try again.
        </div>
      )}

      {isLoading ? (
        <p className="text-ink-muted">Loading digests...</p>
      ) : digests?.length === 0 ? (
        <div className="card text-center py-8">
          <Calendar size={48} className="mx-auto text-ink-muted mb-3" />
          <p className="text-ink-muted">No digests yet. Generate one to get started.</p>
        </div>
      ) : (
        <>
        {/* Mobile: dropdown to pick a digest */}
        <select
          className="md:hidden w-full mb-4 input-field"
          value={selectedDigest?.id ?? ''}
          onChange={(e) => setSelectedDigestId(e.target.value)}
        >
          {digests?.map((digest: Digest) => (
            <option key={digest.id} value={digest.id}>
              KW {getISOWeek(digest.week_start)}: {digest.week_start} — {digest.week_end}
            </option>
          ))}
        </select>

        <div className="flex gap-6">
          {/* Desktop: sidebar button list */}
          <div className="hidden md:block w-64 shrink-0 space-y-2">
            {digests?.map((digest: Digest) => (
              <button
                key={digest.id}
                onClick={() => setSelectedDigestId(digest.id)}
                className={`w-full text-left p-3 rounded border transition-colors ${
                  selectedDigest?.id === digest.id
                    ? 'border-accent-blue bg-accent-blue/5'
                    : 'border-gray-200 bg-white hover:bg-gray-50'
                }`}
              >
                <div className="text-sm font-medium text-gray-900">
                  {digest.week_start} — {digest.week_end}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {digest.sections?.length ?? 0} sections · {digest.is_published ? 'Published' : 'Draft'}
                </div>
              </button>
            ))}
          </div>

          {selectedDigest && (
            <div className="flex-1 min-w-0">
              <div className="card">
                <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">
                      KW {getISOWeek(selectedDigest.week_start)}: {formatDateDE(selectedDigest.week_start)} – {formatDateDE(selectedDigest.week_end)}
                    </h2>
                    {selectedDigest.summary && (
                      <p className="text-sm text-gray-600 mt-1">{selectedDigest.summary}</p>
                    )}
                  </div>
                  <button
                    onClick={() => handleCopyEmail(selectedDigest)}
                    disabled={!selectedDigest.sections?.length}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border border-gray-300 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
                  >
                    {copied ? '✓ Kopiert' : 'Als E-Mail kopieren'}
                  </button>
                </div>

                <DigestRisksOpportunities
                  risks={selectedDigest.risks ?? []}
                  opportunities={selectedDigest.opportunities ?? []}
                />

                {selectedDigest.sections && selectedDigest.sections.length > 0 ? (
                  <div className="space-y-8">
                    {selectedDigest.sections.map((section) => (
                      <div key={section.key}>
                        <h3 className="text-base font-semibold text-gray-900 mb-3 pb-2 border-b border-gray-200">
                          {section.title}
                        </h3>
                        {section.key === 'events_calendar' ? (
                          <EventsCalendarSection
                            upcoming={section.upcoming ?? []}
                            newly_discovered={section.newly_discovered ?? []}
                          />
                        ) : section.key === 'own_company_communication' ? (
                          <OwnCompanySection items={section.items} />
                        ) : (
                          <SectionItems items={section.items} />
                        )}
                      </div>
                    ))}
                  </div>
                ) : selectedDigest.key_signals && selectedDigest.key_signals.length > 0 ? (
                  <ul className="space-y-3">
                    {selectedDigest.key_signals.map((sig) => (
                      <li key={sig.id} className="text-sm">
                        <span className="font-medium">{sig.company_name}</span> — {sig.title}
                        {sig.source_url && (
                          <a href={sig.source_url} target="_blank" rel="noopener noreferrer" className="ml-2 text-blue-600 hover:underline text-xs">
                            source
                          </a>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-gray-400">Keine Signale für diese Woche.</p>
                )}
              </div>
            </div>
          )}
        </div>
        </>
      )}
    </div>
  );
}