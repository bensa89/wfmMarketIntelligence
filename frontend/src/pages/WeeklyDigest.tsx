import { useState } from 'react';
import { useDigests, useGenerateDigest } from '../hooks/useDigests';
import { Calendar, RefreshCw } from 'lucide-react';
import type { Digest, DigestSectionItem } from '../types';

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

    for (const section of digest.sections ?? []) {
      text += `${section.title}\n${'─'.repeat(25)}\n`;
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
      text += '\n';
    }

    text += `${'─'.repeat(25)}\nVollständiger Digest: ${window.location.origin}/digest/${digest.id}`;

    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Calendar size={24} /> Weekly Digest
        </h1>
        <button
          onClick={() => generateDigest.mutate()}
          disabled={generateDigest.isPending}
          className="btn-primary flex items-center gap-2"
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
        <div className="flex gap-6">
          <div className="w-64 shrink-0 space-y-2">
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
                <div className="flex items-center justify-between mb-4">
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
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border border-gray-300 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {copied ? '✓ Kopiert' : 'Als E-Mail kopieren'}
                  </button>
                </div>

                {selectedDigest.sections && selectedDigest.sections.length > 0 ? (
                  <div className="space-y-8">
                    {selectedDigest.sections.map((section) => (
                      <div key={section.key}>
                        <h3 className="text-base font-semibold text-gray-900 mb-3 pb-2 border-b border-gray-200">
                          {section.title}
                        </h3>
                        <SectionItems items={section.items} />
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
      )}
    </div>
  );
}