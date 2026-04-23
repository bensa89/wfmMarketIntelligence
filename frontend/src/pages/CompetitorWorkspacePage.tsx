import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useCompetitorWorkspace } from '../hooks/useCompetitorWorkspace';
import CompetitorHeader from '../components/workspace/CompetitorHeader';
import SummaryPeriodTabs from '../components/workspace/SummaryPeriodTabs';
import StrategicPostureCard from '../components/workspace/StrategicPostureCard';
import CapabilityRadar from '../components/workspace/CapabilityRadar';
import RecentMovesTimeline from '../components/workspace/RecentMovesTimeline';
import RisksOpportunitiesCards from '../components/workspace/RisksOpportunitiesCards';
import SignalDetailDrawer from '../components/signals/SignalDetailDrawer';
import type { SignalFeedItem } from '../types/intelligence';

export default function CompetitorWorkspacePage() {
  const { slug } = useParams<{ slug: string }>();
  const { data, isLoading, error } = useCompetitorWorkspace(slug ?? '');
  const [activePeriod, setActivePeriod] = useState<'30d' | '90d'>('30d');
  const [selectedSignal, setSelectedSignal] = useState<SignalFeedItem | null>(null);

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
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex-shrink-0">
        <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">{data.competitor_profile.name}</h1>
        {data.competitor_profile.description && (
          <p className="text-[12px] text-slate-500 mt-0.5">{data.competitor_profile.description}</p>
        )}
      </div>
      <div className="flex-1 overflow-auto px-6 py-5">
      <CompetitorHeader profile={data.competitor_profile} />

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

      <RecentMovesTimeline
        assessments={data.recent_assessments}
        onSelectSignal={setSelectedSignal}
      />

      <RisksOpportunitiesCards summary={activeSummary} />

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
