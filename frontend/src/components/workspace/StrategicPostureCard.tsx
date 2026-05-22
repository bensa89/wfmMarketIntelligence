import type { CompetitorSummary } from '../../types/intelligence';
import { getCapabilityLabel } from '../../constants/capabilities';

interface Props {
  summary: CompetitorSummary | null;
}

function postureLabel(raw: string | null): string {
  if (!raw) return 'Unknown';
  return raw.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function postureColor(raw: string | null): string {
  if (!raw) return '#64748b';
  if (raw.includes('aggressive')) return '#f97316';
  if (raw.includes('expansion')) return '#fb923c';
  if (raw.includes('defensive')) return '#94a3b8';
  if (raw.includes('niche')) return '#60a5fa';
  return '#a78bfa';
}

export default function StrategicPostureCard({ summary }: Props) {
  if (!summary) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-4 h-full">
        <p className="text-slate-400 text-[12px]">No summary available yet. Run a crawl to generate.</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <span
          className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
          style={{
            background: `${postureColor(summary.strategic_posture)}22`,
            color: postureColor(summary.strategic_posture),
          }}
        >
          {postureLabel(summary.strategic_posture)}
        </span>
        <span className="text-[11px] text-slate-500">{summary.signal_count} signals</span>
      </div>

      {summary.positioning_summary && (
        <p className="text-[13px] text-slate-700 leading-relaxed mb-3">{summary.positioning_summary}</p>
      )}

      {summary.what_changed && (
        <p className="text-[11px] text-slate-500 italic leading-snug mb-3 flex items-start gap-1">
          <span className="flex-shrink-0">↺</span>
          {summary.what_changed}
        </p>
      )}

      {summary.top_capabilities.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {summary.top_capabilities.slice(0, 4).map((key) => (
            <span
              key={key}
              className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600"
            >
              {getCapabilityLabel(key)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
