// src/components/dashboard/BriefingPanel.tsx
import { RefreshCw } from 'lucide-react';
import { useLatestBriefing, useGenerateBriefing } from '../../hooks/useBriefing';
import MarkdownViewer from '../MarkdownViewer';

export default function BriefingPanel() {
  const { data: briefing, isLoading } = useLatestBriefing();
  const generate = useGenerateBriefing();

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">
          Intelligence Briefing
        </p>
        <button
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
          className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={11} className={generate.isPending ? 'animate-spin' : ''} />
          {generate.isPending ? 'Generiere...' : 'Neu generieren'}
        </button>
      </div>

      {isLoading ? (
        <p className="text-[12px] text-slate-400">Lade Briefing...</p>
      ) : briefing ? (
        <>
          <div className="text-[12px] text-slate-700 leading-relaxed">
            <MarkdownViewer content={briefing.content} />
          </div>
          <p className="text-[10px] text-slate-400 mt-3">
            Generiert:{' '}
            {new Date(briefing.generated_at).toLocaleString('de-DE', {
              day: '2-digit',
              month: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </>
      ) : (
        <p className="text-[12px] text-slate-400">
          Noch kein Briefing vorhanden. Starte einen Crawl oder klicke auf "Neu generieren".
        </p>
      )}
    </div>
  );
}
