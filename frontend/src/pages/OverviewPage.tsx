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
      <div className="p-6 flex items-center justify-center h-64" style={{ background: '#0a0f1e', minHeight: '100%' }}>
        <span className="text-slate-500 text-sm">Loading intelligence overview…</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 flex items-center justify-center h-64" style={{ background: '#0a0f1e', minHeight: '100%' }}>
        <span className="text-red-400 text-sm">Failed to load overview. Is the backend running?</span>
      </div>
    );
  }

  return (
    <div style={{ background: '#0a0f1e', minHeight: '100%' }}>
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-100">Executive Overview</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">Market intelligence summary · last 30 days</p>
      </div>

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
