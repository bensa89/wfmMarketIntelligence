import { ExternalLink, RefreshCw } from 'lucide-react';
import { useSummarizeCompetitor } from '../../hooks/useSummarizeCompetitor';
import type { WorkspaceResponse } from '../../types/intelligence';

interface Props {
  profile: WorkspaceResponse['competitor_profile'];
}

export default function CompetitorHeader({ profile }: Props) {
  const summarize = useSummarizeCompetitor(profile.id);

  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">{profile.name}</h1>
        {profile.description && (
          <p className="text-[13px] text-slate-600 mt-0.5 max-w-2xl">{profile.description}</p>
        )}
        {profile.website && (
          <a
            href={profile.website}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-[12px] text-blue-600 hover:text-blue-700 mt-1 transition-colors"
          >
            <ExternalLink size={11} />
            {profile.website}
          </a>
        )}
      </div>
      <button
        onClick={() => summarize.mutate('30d')}
        disabled={summarize.isPending}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium bg-white border border-slate-200 text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-50"
        title="Regenerate 30d summary"
      >
        <RefreshCw size={13} className={summarize.isPending ? 'animate-spin' : ''} />
        Refresh Summary
      </button>
    </div>
  );
}
