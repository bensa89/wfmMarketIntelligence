import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { ExternalLink, RefreshCw } from 'lucide-react';
import { useCompetitorWorkspace } from '../hooks/useCompetitorWorkspace';
import { useSummarizeCompetitor } from '../hooks/useSummarizeCompetitor';
import { ApiError } from '../api/client';
import SummaryPeriodTabs from '../components/workspace/SummaryPeriodTabs';
import StrategicPostureCard from '../components/workspace/StrategicPostureCard';
import CapabilityRadar from '../components/workspace/CapabilityRadar';
import { RelativeCapabilityStrengthPanel } from '../components/workspace/RelativeCapabilityStrengthPanel';
import RecentMovesTimeline from '../components/workspace/RecentMovesTimeline';
import RisksOpportunitiesCards from '../components/workspace/RisksOpportunitiesCards';
import SignalDetailDrawer from '../components/signals/SignalDetailDrawer';
import type { SignalFeedItem } from '../types/intelligence';

export default function CompetitorWorkspacePage() {
  const { slug } = useParams<{ slug: string }>();
  const { data, isLoading, error } = useCompetitorWorkspace(slug ?? '');
  const [activePeriod, setActivePeriod] = useState<'30d' | '90d'>('30d');
  const [selectedSignal, setSelectedSignal] = useState<SignalFeedItem | null>(null);
  const summarize = useSummarizeCompetitor(data?.competitor_profile.id ?? '');

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <span className="text-slate-500 text-sm">Loading competitor workspace…</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <span className="text-red-400 text-sm">Competitor not found or failed to load.</span>
      </div>
    );
  }

  const activeSummary = activePeriod === '30d' ? data.summary_30d : data.summary_90d;

  return (
    <div className="flex flex-col h-full">
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex-shrink-0 flex items-start justify-between">
        <div>
          <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">{data.competitor_profile.name}</h1>
          {data.competitor_profile.description && (
            <p className="text-[12px] text-slate-500 mt-0.5">{data.competitor_profile.description}</p>
          )}
          {data.competitor_profile.website && (
            <a
              href={data.competitor_profile.website}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-700 mt-1 transition-colors"
            >
              <ExternalLink size={10} />
              {data.competitor_profile.website}
            </a>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <button
            onClick={() => summarize.mutate(activePeriod)}
            disabled={summarize.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium bg-white border border-slate-200 text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-50 flex-shrink-0"
          >
            <RefreshCw size={13} className={summarize.isPending ? 'animate-spin' : ''} />
            Refresh Summary
          </button>
          {summarize.isError && (
            <span className="text-[11px] text-red-500">
              {summarize.error instanceof ApiError ? summarize.error.message : 'Summary generation failed'}
            </span>
          )}
          {summarize.isSuccess && (
            <span className="text-[11px] text-green-600">Summary updated</span>
          )}
        </div>
      </div>
      <div className="flex-1 overflow-auto px-6 py-5">

      <SummaryPeriodTabs
        activePeriod={activePeriod}
        onChangePeriod={setActivePeriod}
        summary30d={data.summary_30d}
        summary90d={data.summary_90d}
      />

      <div className="grid grid-cols-2 gap-4 mb-4">
        <StrategicPostureCard summary={activeSummary} />
        <CapabilityRadar distribution={data.capability_distribution} />
      </div>

      <RelativeCapabilityStrengthPanel slug={slug ?? ''} />

      <RisksOpportunitiesCards summary={activeSummary} />

      <RecentMovesTimeline
        assessments={data.recent_assessments}
        onSelectSignal={setSelectedSignal}
      />

      {selectedSignal && (
        <SignalDetailDrawer
          item={selectedSignal}
          onClose={() => setSelectedSignal(null)}
        />
      )}
      </div>
    </div>
  );
}
