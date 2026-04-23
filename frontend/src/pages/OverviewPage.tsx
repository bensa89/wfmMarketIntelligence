import { useOverview } from '../hooks/useOverview';
import OverviewKPIBar from '../components/overview/OverviewKPIBar';
import TopMoversList from '../components/overview/TopMoversList';
import CapabilityHeatmapV2 from '../components/overview/CapabilityHeatmapV2';
import MarketShapingFeed from '../components/overview/MarketShapingFeed';
import RisksOpportunitiesPanel from '../components/overview/RisksOpportunitiesPanel';

export default function OverviewPage() {
  const { data, isLoading, error } = useOverview();

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-center h-64">
          <span className="text-slate-500 text-sm">Loading intelligence overview…</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-center h-64">
          <span className="text-red-500 text-sm">Failed to load overview. Is the backend running?</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex-shrink-0">
        <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">Executive Overview</h1>
        <p className="text-[12px] text-slate-500 mt-0.5">Market intelligence summary · last 30 days</p>
      </div>
      <div className="flex-1 overflow-auto px-6 py-5">
      <OverviewKPIBar data={data} />

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="col-span-1">
          <TopMoversList movers7d={data.top_movers_7d} movers30d={data.top_movers_30d} />
        </div>
        <div className="col-span-2">
          <CapabilityHeatmapV2 rows={data.capability_heatmap} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <MarketShapingFeed signals={data.recent_market_shaping} />
        <RisksOpportunitiesPanel
          risks={data.emerging_risks}
          opportunities={data.emerging_opportunities}
        />
      </div>
      </div>
    </div>
  );
}
