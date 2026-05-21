interface Props {
  watchpoints: string[] | null | undefined;
  loading?: boolean;
}

export function WatchpointsPanel({ watchpoints, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 p-4">
        <div className="h-4 w-24 bg-gray-200 rounded mb-3 animate-pulse" />
        {[1, 2].map((i) => <div key={i} className="h-5 bg-gray-100 rounded mb-2 animate-pulse" />)}
      </div>
    );
  }

  const list = watchpoints ?? [];

  return (
    <div className="rounded-lg border border-gray-200 p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Watchpoints</h3>
      {list.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No watchpoints in this period.</p>
      ) : (
        <ul className="space-y-1.5">
          {list.map((wp, idx) => (
            <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
              <span className="mt-1 flex-shrink-0 w-1.5 h-1.5 rounded-full bg-indigo-400" />
              {wp}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
