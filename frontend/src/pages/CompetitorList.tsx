import { Link } from 'react-router-dom';
import { useCompanies } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { Users, BarChart3 } from 'lucide-react';

export default function CompetitorList() {
  const { data: companies, isLoading } = useCompanies();
  const { data: allSignals } = useSignals();

  const competitors = companies?.filter((c) => c.type === 'competitor') ?? [];
  const marketSources = companies?.filter((c) => c.type === 'market_source') ?? [];

  function countSignals(companyId: string): number {
    return allSignals?.filter((s) => s.company_id === companyId).length ?? 0;
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Competitors & Market Sources</h1>

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
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{c.name}</h3>
                  <span className="text-sm text-accent-blue">{c.slug}</span>
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
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{c.name}</h3>
                  <span className="text-sm text-accent-blue">{c.slug}</span>
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
