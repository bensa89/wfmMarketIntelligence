import { useEffect } from 'react';
import { X, ExternalLink } from 'lucide-react';
import type { SignalFeedItem } from '../../types/intelligence';
import MovementBadge from './MovementBadge';
import ConfidenceBar from './ConfidenceBar';
import { getCapabilityLabel } from '../../constants/capabilities';
import { useAssessSignal } from '../../hooks/useAssessSignal';
import DateWithTooltip from '../DateWithTooltip';

interface Props {
  item: SignalFeedItem;
  onClose: () => void;
}

export default function SignalDetailDrawer({ item, onClose }: Props) {
  const assess = useAssessSignal();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const a = item.assessment;

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      {/* Modal */}
      <div
        className="bg-white rounded-xl max-w-3xl w-full max-h-[85vh] flex flex-col overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="signal-modal-title"
        tabIndex={-1}
        autoFocus
        onClick={(e) => e.stopPropagation()}
      >
          {/* Header */}
          <div className="flex items-start justify-between p-5 border-b border-slate-200 flex-shrink-0">
            <div className="flex-1 pr-4">
              <div id="signal-modal-title" className="text-[13px] font-semibold text-slate-900 leading-snug">{item.title}</div>
              <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                <span className="text-[11px] text-slate-500">{item.company_name}</span>
                {item.published_at && (
                  <>
                    <span className="text-slate-300">·</span>
                    <span className="text-[11px] text-slate-500">
                      Artikel: <DateWithTooltip date={item.published_at} />
                    </span>
                  </>
                )}
                <span className="text-slate-300">·</span>
                <span className="text-[11px] text-slate-500">
                  Analysiert: <DateWithTooltip date={item.created_at} />
                </span>
                {item.source_url && (
                  <>
                    <span className="text-slate-300">·</span>
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-700 transition-colors"
                    >
                      <ExternalLink size={11} className="flex-shrink-0" />
                      {item.document_title || 'Source'}
                    </a>
                  </>
                )}
              </div>
            </div>
            <button onClick={onClose} aria-label="Schließen" className="text-slate-400 hover:text-slate-700 transition-colors flex-shrink-0">
              <X size={16} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-5">
            {/* Assessment header */}
            <div className="flex items-center gap-3 flex-wrap">
              <MovementBadge strength={a?.movement_strength} size="md" />
              {a?.movement_score != null && (
                <span className="text-[12px] text-slate-500">Score: <span className="font-semibold text-slate-900">{a.movement_score}</span></span>
              )}
              <span className="flex items-center gap-1.5 text-[12px] text-slate-500">
                Konfidenz: <ConfidenceBar value={a?.confidence} />
              </span>
              {a?.gameplay_tags && a.gameplay_tags.map((tag) => (
                <span key={tag} className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {tag}
                </span>
              ))}
            </div>

            {/* Signal basics */}
            {item.summary && (
              <section>
                <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Summary</h4>
                <p className="text-[13px] text-slate-700 leading-relaxed">{item.summary}</p>
              </section>
            )}

            {/* Assessment details */}
            {a && (
              <>
                {a.capability_primary && (
                  <section>
                    <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Capability</h4>
                    <div className="flex flex-wrap gap-1.5">
                      <span className="text-[12px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                        {getCapabilityLabel(a.capability_primary)}
                      </span>
                      {a.capability_secondary.map((k) => (
                        <span key={k} className="text-[12px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                          {getCapabilityLabel(k)}
                        </span>
                      ))}
                    </div>
                  </section>
                )}

            {item.why_it_matters && (
              <section>
                <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Why It Matters</h4>
                <p className="text-[13px] text-slate-700 leading-relaxed">{item.why_it_matters}</p>
              </section>
            )}

                {a.assessment_summary && (
                  <section>
                    <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Assessment</h4>
                    <p className="text-[13px] text-slate-700 leading-relaxed">{a.assessment_summary}</p>
                  </section>
                )}

                {a.implication_for_us && (
                  <section>
                    <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Implication for Us</h4>
                    <p className="text-[13px] text-amber-700 leading-relaxed">{a.implication_for_us}</p>
                  </section>
                )}

                {a.strategic_intent_guess && (
                  <section>
                    <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Strategic Intent</h4>
                    <p className="text-[13px] text-slate-600 leading-relaxed italic">"{a.strategic_intent_guess}"</p>
                  </section>
                )}

                {a.watch_items.length > 0 && (
                  <section>
                    <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Watch Items</h4>
                    <ul className="space-y-1">
                      {a.watch_items.map((w, i) => (
                        <li key={i} className="text-[12px] text-slate-700 flex gap-2">
                          <span className="text-amber-500 flex-shrink-0 mt-0.5">◈</span>
                          {w}
                        </li>
                      ))}
                    </ul>
                  </section>
                )}


              </>
            )}

            {/* Re-assess button */}
            {!a && (
              <button
                onClick={() => assess.mutate(item.id)}
                disabled={assess.isPending}
                className="w-full py-2 rounded-lg text-[12px] font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {assess.isPending ? 'Generating assessment…' : 'Generate Assessment'}
              </button>
            )}
          </div>
      </div>
    </div>
  );
}
