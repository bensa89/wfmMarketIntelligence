import { useDigests, useGenerateDigest } from '../hooks/useDigests';
import { useSignals } from '../hooks/useSignals';
import RelevanceBadge from '../components/RelevanceBadge';
import SignalTypeIcon from '../components/SignalTypeIcon';
import { Calendar, RefreshCw } from 'lucide-react';
import type { Signal } from '../types';

export default function WeeklyDigest() {
  const { data: digests, isLoading } = useDigests();
  const generateDigest = useGenerateDigest();
  const { data: allSignals } = useSignals();

  function getSignalById(id: string): Signal | undefined {
    return allSignals?.find((s) => s.id === id);
  }

  return (
    <div>
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
        <p className="text-dark-muted">Loading digests...</p>
      ) : digests?.length === 0 ? (
        <div className="card text-center py-8">
          <Calendar size={48} className="mx-auto text-dark-muted mb-3" />
          <p className="text-dark-muted">No digests yet. Generate one to get started.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {digests?.map((digest) => (
            <div key={digest.id} className="card">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold">
                  {digest.week_start} — {digest.week_end}
                </h2>
                <span className={`text-xs px-2 py-0.5 rounded ${digest.is_published ? 'bg-signal-high/20 text-signal-high' : 'bg-dark-bg text-dark-muted'}`}>
                  {digest.is_published ? 'Published' : 'Draft'}
                </span>
              </div>
              {digest.summary && (
                <div className="text-sm text-dark-text whitespace-pre-line mb-4">
                  {digest.summary}
                </div>
              )}
              {digest.key_signals.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-dark-muted mb-2">Key Signals:</h3>
                  <div className="space-y-2">
                    {digest.key_signals.map((sid) => {
                      const signal = getSignalById(sid);
                      if (!signal) return null;
                      return (
                        <div key={sid} className="flex items-center justify-between bg-dark-bg rounded p-2">
                          <div className="flex items-center gap-2">
                            <SignalTypeIcon type={signal.signal_type} size={14} />
                            <span className="text-sm">{signal.title}</span>
                          </div>
                          <RelevanceBadge score={signal.relevance_score} size="sm" />
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
