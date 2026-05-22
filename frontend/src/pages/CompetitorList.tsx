import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useBenchmarkOverview, useRecomputeBenchmarks } from '../hooks/useBenchmark';
import type { BenchmarkPeriodType } from '../types/benchmark';
import { CapabilityStrengthMatrix } from '../components/benchmark/CapabilityStrengthMatrix';
import { CapabilityLeaderboardDrawer } from '../components/benchmark/CapabilityLeaderboardDrawer';
import { Users, BarChart3 } from 'lucide-react';
import CompanyLogo from '../components/CompanyLogo';
import { useBenchmarkScorecard } from '../hooks/useScorecard';
import { ScorecardSummaryStrip } from '../components/scorecard/ScorecardSummaryStrip';
import type { ScorecardPeriodType } from '../types/scorecard';

export default function CompetitorList() {
  const { data: companies, isLoading } = useCompanies();
  const { data: allSignals } = useSignals();

  const [benchmarkPeriod, setBenchmarkPeriod] = useState<BenchmarkPeriodType>('30d');
  const [drawerCapKey, setDrawerCapKey] = useState<string | null>(null);
  const navigate = useNavigate();
  const { data: benchmarkData, isLoading: benchmarkLoading } = useBenchmarkOverview(benchmarkPeriod);
  const recompute = useRecomputeBenchmarks();

  const [scorecardPeriod, setScorecardPeriod] = useState<ScorecardPeriodType>('30d');
  const { data: scorecardBenchmark, isLoading: scorecardLoading } = useBenchmarkScorecard(scorecardPeriod);
  const scorecardByCompanyId = Object.fromEntries(
    (scorecardBenchmark?.items ?? []).map((item) => [item.company_id, item])
  );

  const competitors = companies?.filter((c) => c.type === 'competitor') ?? [];
  const marketSources = companies?.filter((c) => c.type === 'market_source') ?? [];

  function countSignals(companyId: string): number {
    return allSignals?.filter((s) => s.company_id === companyId).length ?? 0;
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Competitors & Market Sources</h1>

      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-slate-900">Capability Strength Matrix</h2>
          <div className="flex items-center gap-3">
            <div className="flex gap-1">
              {(['30d', '90d', '180d'] as BenchmarkPeriodType[]).map(p => (
                <button
                  key={p}
                  onClick={() => setBenchmarkPeriod(p)}
                  className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                    benchmarkPeriod === p
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
            <button
              onClick={() => recompute.mutate(benchmarkPeriod)}
              disabled={recompute.isPending}
              className="px-3 py-1.5 text-xs rounded-md bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {recompute.isPending ? 'Recomputing…' : 'Recompute'}
            </button>
            {/* Scorecard period selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Scorecard period:</span>
              {(['30d', '90d', '180d'] as ScorecardPeriodType[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setScorecardPeriod(p)}
                  className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                    scorecardPeriod === p
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>

        {benchmarkLoading && <p className="text-sm text-slate-400">Loading matrix…</p>}
        {benchmarkData && benchmarkData.competitors.length > 0 && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 overflow-x-auto">
            <CapabilityStrengthMatrix
              data={benchmarkData}
              onCapabilityClick={setDrawerCapKey}
              onCompetitorClick={(slug) => navigate(`/competitors/${slug}`)}
            />
          </div>
        )}
        {benchmarkData && benchmarkData.competitors.length === 0 && (
          <p className="text-sm text-slate-400">No competitor benchmarks yet. Add competitors and run Recompute.</p>
        )}
      </div>

      <CapabilityLeaderboardDrawer
        capKey={drawerCapKey}
        periodType={benchmarkPeriod}
        onClose={() => setDrawerCapKey(null)}
      />

      {isLoading ? (
        <p className="text-ink-muted">Loading...</p>
      ) : (
        <>
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Users size={20} /> Competitors
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {competitors.map((c) => (
              <Link
                key={c.id}
                to={`/competitors/${c.slug}`}
                className="card hover:border-accent-blue/40 transition-colors"
              >
                <div className="flex items-center gap-2 mb-2">
                  <CompanyLogo
                    name={c.name}
                    slug={c.slug}
                    logo_path={c.logo_path}
                    size="md"
                    companyId={c.id}
                  />
                  <div className="flex items-center justify-between flex-1 min-w-0">
                    <h3 className="font-semibold truncate">{c.name}</h3>
                    <span className="text-sm text-accent-blue ml-2 shrink-0">{c.slug}</span>
                  </div>
                </div>
                {c.description && (
                  <p className="text-sm text-ink-muted line-clamp-2 mb-2">{c.description}</p>
                )}
                <div className="flex items-center gap-1 text-sm text-ink-muted">
                  <BarChart3 size={14} />
                  {countSignals(c.id)} signals
                </div>
                <ScorecardSummaryStrip
                  scorecard={scorecardByCompanyId[c.id] ?? null}
                  loading={scorecardLoading}
                />
              </Link>
            ))}
            {competitors.length === 0 && (
              <p className="text-ink-muted text-sm">No competitors configured yet.</p>
            )}
          </div>

          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <BarChart3 size={20} /> Market Sources
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {marketSources.map((c) => (
              <Link
                key={c.id}
                to={`/competitors/${c.slug}`}
                className="card hover:border-accent-blue/40 transition-colors"
              >
                <div className="flex items-center gap-2 mb-2">
                  <CompanyLogo
                    name={c.name}
                    slug={c.slug}
                    logo_path={c.logo_path}
                    size="md"
                    companyId={c.id}
                  />
                  <div className="flex items-center justify-between flex-1 min-w-0">
                    <h3 className="font-semibold truncate">{c.name}</h3>
                    <span className="text-sm text-accent-blue ml-2 shrink-0">{c.slug}</span>
                  </div>
                </div>
                {c.description && (
                  <p className="text-sm text-ink-muted line-clamp-2 mb-2">{c.description}</p>
                )}
                <div className="flex items-center gap-1 text-sm text-ink-muted">
                  <BarChart3 size={14} />
                  {countSignals(c.id)} signals
                </div>
              </Link>
            ))}
            {marketSources.length === 0 && (
              <p className="text-ink-muted text-sm">No market sources configured yet.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
