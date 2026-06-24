import { RefreshCw } from 'lucide-react';
import { useLatestIntelligenceBriefing, useGenerateIntelligenceBriefing } from '../../hooks/useIntelligenceBriefing';
import MarkdownViewer from '../MarkdownViewer';
import CompanyLogo from '../CompanyLogo';
import { ApiError } from '../../api/client';

function formatTimeAgo(isoString: string): string {
  const seconds = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (seconds < 60) return 'gerade eben';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `vor ${minutes} Min.`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `vor ${hours} Std.`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'gestern';
  return `vor ${days} Tagen`;
}

interface Props {
  onSelectSignal?: (signalId: string) => void;
}

export default function IntelligenceBriefingPanel({ onSelectSignal }: Props) {
  const { data: briefing, isLoading } = useLatestIntelligenceBriefing();
  const generate = useGenerateIntelligenceBriefing();

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider inline">
            Intelligence Briefing
          </p>
          {briefing && (
            <span className="text-[10px] font-normal normal-case tracking-normal text-slate-400 ml-2">
              {formatTimeAgo(briefing.generated_at)} ·{' '}
              {new Date(briefing.generated_at).toLocaleString('de-DE', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
              {' · Letzte 7 Tage · '}
              {briefing.signal_count === 0
                ? 'Keine neuen Signale'
                : `${briefing.signal_count} Signale, ${briefing.assessment_count} Assessments`}
            </span>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={11} className={generate.isPending ? 'animate-spin' : ''} />
            {generate.isPending ? 'Generiere...' : 'Neu generieren'}
          </button>
          {generate.isError && (
            <span className="text-[11px] text-red-500">
              {generate.error instanceof ApiError ? generate.error.message : 'Generierung fehlgeschlagen'}
            </span>
          )}
        </div>
      </div>

      {isLoading ? (
        <p className="text-[12px] text-slate-400">Lade Briefing...</p>
      ) : briefing ? (
        <div className="text-[12px] text-slate-700 leading-relaxed">
          <MarkdownViewer
            content={briefing.content}
            className="prose-headings:mt-2 prose-headings:mb-1 prose-p:my-1 prose-hr:my-2"
          />
          {briefing.curated_recommendations && briefing.curated_recommendations.length > 0 && (
            <div className="mt-3">
              <h4 className="text-[12px] font-semibold text-slate-900 mb-2">Handlungsempfehlungen</h4>
              <ul className="space-y-2">
                {briefing.curated_recommendations.map((rec) => {
                  const clickable = !!onSelectSignal;
                  return (
                    <li
                      key={rec.signal_id}
                      onClick={clickable ? () => onSelectSignal!(rec.signal_id) : undefined}
                      className={`flex gap-2 p-1.5 -mx-1.5 rounded ${clickable ? 'cursor-pointer hover:bg-slate-50 group' : ''}`}
                    >
                      <span className="flex-shrink-0 text-[10px] font-semibold text-slate-400 mt-0.5">
                        #{rec.priority}
                      </span>
                      <div className="flex-1">
                        <span className={`text-[12px] text-slate-700 leading-snug ${clickable ? 'group-hover:underline' : ''}`}>
                          {rec.recommendation}
                        </span>
                        {rec.company_name && rec.company_slug && (
                          <div className="flex items-center gap-1 mt-0.5">
                            <CompanyLogo
                              name={rec.company_name}
                              slug={rec.company_slug}
                              companyId={rec.company_id}
                              logo_path={rec.logo_path}
                              size="sm"
                            />
                            <span className="text-[10px] text-slate-400">{rec.company_name} · {rec.title}</span>
                          </div>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <p className="text-[12px] text-slate-400">
          Noch kein Intelligence Briefing vorhanden. Klicke auf "Neu generieren".
        </p>
      )}
    </div>
  );
}
