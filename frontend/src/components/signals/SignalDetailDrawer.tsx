import { useEffect } from 'react';
import { X, ExternalLink } from 'lucide-react';
import type { SignalFeedItem, SignalClass, VisibilityImpact } from '../../types/intelligence';
import MovementBadge from './MovementBadge';
import ConfidenceBar from './ConfidenceBar';
import { getCapabilityLabel } from '../../constants/capabilities';
import { useAssessSignal } from '../../hooks/useAssessSignal';
import DateWithTooltip from '../DateWithTooltip';

interface Props {
  item: SignalFeedItem;
  onClose: () => void;
}

const SIGNAL_CLASS_LABELS: Record<SignalClass, string> = {
  product_capability_move: 'Product Capability Move',
  positioning_move:        'Positioning Move',
  ecosystem_move:          'Ecosystem Move',
  thought_leadership_signal: 'Thought Leadership',
  hiring_signal:           'Hiring Signal',
  weak_signal:             'Weak Signal',
  market_expansion_move:   'Market Expansion',
};

const VISIBILITY_LABELS: Record<VisibilityImpact, { label: string; color: string }> = {
  low:    { label: 'Low',    color: 'text-slate-500 bg-slate-100' },
  medium: { label: 'Medium', color: 'text-blue-600 bg-blue-50' },
  high:   { label: 'High',   color: 'text-orange-600 bg-orange-50' },
};

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
        className="bg-white rounded-xl max-w-5xl w-full max-h-[85vh] flex flex-col overflow-hidden"
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
            <div id="signal-modal-title" className="text-[16px] font-semibold text-slate-900 leading-snug">{item.title}</div>
          </div>
          <button onClick={onClose} aria-label="Schließen" className="text-slate-400 hover:text-slate-700 transition-colors flex-shrink-0">
            <X size={16} />
          </button>
        </div>

        {/* Two-column body */}
        <div className="flex-1 overflow-y-auto">
          <div className="grid grid-cols-3 gap-0 min-h-full">

            {/* Left — 2/3: textual content */}
            <div className="col-span-2 p-5 space-y-5 border-r border-slate-100">
              {item.topic && (
                <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">{item.topic}</div>
              )}

              {item.summary && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Summary</h4>
                  <p className="text-[13px] text-slate-700 leading-relaxed">{item.summary}</p>
                </section>
              )}

              {item.why_it_matters && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Why It Matters</h4>
                  <p className="text-[13px] text-slate-700 leading-relaxed">{item.why_it_matters}</p>
                </section>
              )}

              {a?.assessment_summary && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Assessment</h4>
                  <p className="text-[13px] text-slate-700 leading-relaxed">{a.assessment_summary}</p>
                </section>
              )}

              {a?.implication_for_us && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Implication for Us</h4>
                  <p className="text-[13px] text-amber-700 leading-relaxed">{a.implication_for_us}</p>
                </section>
              )}

              {a?.strategic_intent_guess && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Strategic Intent</h4>
                  <p className="text-[13px] text-slate-600 leading-relaxed italic">"{a.strategic_intent_guess}"</p>
                </section>
              )}

              {a?.watch_items && a.watch_items.length > 0 && (
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

            {/* Right — 1/3: metadata */}
            <div className="col-span-1 p-5 space-y-5 bg-slate-50">
              {/* Competitor */}
              <section>
                <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Competitor</h4>
                <span className="text-[12px] text-slate-700">{item.company_name}</span>
              </section>

              {/* Movement + Confidence */}
              <div className="flex gap-8">
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Bewegung</h4>
                  <MovementBadge strength={a?.movement_strength} size="md" score={a?.movement_score} />
                </section>
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Konfidenz</h4>
                  <ConfidenceBar value={a?.confidence} />
                </section>
              </div>

              {/* Signal Class */}
              {a?.signal_class && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Signal Type</h4>
                  <span className="text-[12px] px-2 py-0.5 rounded-full bg-white border border-slate-200 text-slate-600">
                    {SIGNAL_CLASS_LABELS[a.signal_class]}
                  </span>
                </section>
              )}

              {/* Evidence Strength + Visibility Impact */}
              <div className="flex gap-8">
                {a?.evidence_strength != null && (
                  <section>
                    <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Evidenz</h4>
                    <div className="flex items-center gap-0.5">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <span
                          key={i}
                          className={`w-2.5 h-2.5 rounded-sm ${i < a.evidence_strength! ? 'bg-slate-700' : 'bg-slate-200'}`}
                        />
                      ))}
                      <span className="text-[11px] text-slate-500 ml-1.5">{a.evidence_strength}/5</span>
                    </div>
                  </section>
                )}

                {a?.visibility_impact && (
                  <section>
                    <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Sichtbarkeit</h4>
                    <span className={`text-[12px] px-2 py-0.5 rounded-full font-medium ${VISIBILITY_LABELS[a.visibility_impact].color}`}>
                      {VISIBILITY_LABELS[a.visibility_impact].label}
                    </span>
                  </section>
                )}
              </div>

              {/* Relevance Score */}
              {item.relevance_score != null && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Relevanz</h4>
                  <span className="text-[12px] font-semibold text-slate-900">{item.relevance_score}</span>
                  <span className="text-[11px] text-slate-400"> / 100</span>
                </section>
              )}

              {/* Capabilities */}
              {a?.capability_primary && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Capability</h4>
                  <div className="flex flex-wrap gap-1.5">
                    <span className="text-[12px] px-2 py-0.5 rounded-full bg-white border border-slate-200 text-slate-600">
                      {getCapabilityLabel(a.capability_primary)}
                    </span>
                    {a.capability_secondary.map((k) => (
                      <span key={k} className="text-[12px] px-2 py-0.5 rounded-full bg-white border border-slate-200 text-slate-600">
                        {getCapabilityLabel(k)}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {/* Gameplay Tags */}
              {a?.gameplay_tags && a.gameplay_tags.length > 0 && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Gameplay Tags</h4>
                  <div className="flex flex-wrap gap-1">
                    {a.gameplay_tags.map((tag) => (
                      <span key={tag} className="text-[11px] px-2 py-0.5 rounded-full bg-white border border-slate-200 text-slate-600">
                        {tag}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {/* Dates */}
              <section>
                <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Datum</h4>
                <div className="space-y-1">
                  {item.published_at && (
                    <div className="text-[12px] text-slate-500">Artikel: <DateWithTooltip date={item.published_at} /></div>
                  )}
                  <div className="text-[12px] text-slate-500">Analysiert: <DateWithTooltip date={item.created_at} /></div>
                </div>
              </section>

              {/* Source */}
              {item.source_url && (
                <section>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Source</h4>
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 text-[12px] text-blue-600 hover:text-blue-700 transition-colors break-all"
                  >
                    <ExternalLink size={12} className="flex-shrink-0" />
                    {item.document_title || item.source_url}
                  </a>
                </section>
              )}
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
