import { useRef, useEffect, useState, useMemo } from 'react';
import { Play, Pause, Trash2, RefreshCw, Circle } from 'lucide-react';
import { useLogStream, type LogEntry, type StreamStatus } from '../hooks/useLogStream';

const LEVEL_ORDER = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const;

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: 'text-slate-400',
  INFO: 'text-blue-300',
  WARNING: 'text-yellow-300',
  ERROR: 'text-red-400',
  CRITICAL: 'text-red-300 font-bold',
};

const STATUS_CONFIG: Record<StreamStatus, { label: string; color: string }> = {
  connecting: { label: 'Verbinde…', color: 'text-yellow-400' },
  connected: { label: 'Verbunden', color: 'text-green-400' },
  paused: { label: 'Pausiert', color: 'text-slate-400' },
  disconnected: { label: 'Getrennt – reconnecting…', color: 'text-orange-400' },
  error: { label: 'Fehler', color: 'text-red-400' },
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('de-DE', { hour12: false });
  } catch {
    return iso;
  }
}

function LogLine({ entry }: { entry: LogEntry }) {
  const color = LEVEL_COLORS[entry.level] ?? 'text-slate-300';
  return (
    <div className="flex gap-2 px-3 py-0.5 hover:bg-white/5 leading-5 min-w-0">
      <span className="text-slate-500 flex-shrink-0 tabular-nums text-[11px] pt-px">
        {formatTime(entry.timestamp)}
      </span>
      <span className={`flex-shrink-0 w-16 text-[11px] pt-px font-semibold ${color}`}>
        {entry.level}
      </span>
      <span className="text-slate-500 flex-shrink-0 max-w-[180px] truncate text-[11px] pt-px">
        {entry.name}
      </span>
      <span className="text-slate-200 text-[12px] break-all">{entry.message}</span>
    </div>
  );
}

export default function LogsAdmin() {
  const { logs, status, modules, pause, resume, clear, reconnect } = useLogStream();

  const [levelFilter, setLevelFilter] = useState<string>('ALL');
  const [moduleFilter, setModuleFilter] = useState<string>('ALL');
  const [isPaused, setIsPaused] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const userScrolledRef = useRef(false);

  const filteredLogs = useMemo(() => {
    return logs.filter((e) => {
      const levelOk =
        levelFilter === 'ALL' ||
        LEVEL_ORDER.indexOf(e.level as any) >= LEVEL_ORDER.indexOf(levelFilter as any);
      const moduleOk = moduleFilter === 'ALL' || e.name === moduleFilter;
      return levelOk && moduleOk;
    });
  }, [logs, levelFilter, moduleFilter]);

  useEffect(() => {
    if (!userScrolledRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'instant' });
    }
  }, [filteredLogs]);

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    userScrolledRef.current = !atBottom;
  }

  function togglePause() {
    if (isPaused) {
      resume();
      setIsPaused(false);
    } else {
      pause();
      setIsPaused(true);
    }
  }

  const { label: statusLabel, color: statusColor } = STATUS_CONFIG[status];

  return (
    <div className="p-6 max-w-full h-screen flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Backend Logs</h1>
          <p className="text-sm text-slate-500 mt-0.5">Live-Stream aller Backend-Ereignisse</p>
        </div>
        <div className={`flex items-center gap-1.5 text-sm font-medium ${statusColor}`}>
          <Circle size={8} className="fill-current" />
          {statusLabel}
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Level filter */}
        <div className="flex items-center gap-1.5">
          <label className="text-xs text-slate-500 font-medium">Level</label>
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="ALL">Alle</option>
            {LEVEL_ORDER.map((l) => (
              <option key={l} value={l}>
                {l}+
              </option>
            ))}
          </select>
        </div>

        {/* Module filter */}
        <div className="flex items-center gap-1.5">
          <label className="text-xs text-slate-500 font-medium">Modul</label>
          <select
            value={moduleFilter}
            onChange={(e) => setModuleFilter(e.target.value)}
            className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="ALL">Alle</option>
            {modules.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1" />

        {/* Action buttons */}
        <button
          onClick={togglePause}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
        >
          {isPaused ? <Play size={14} /> : <Pause size={14} />}
          {isPaused ? 'Weiter' : 'Pausieren'}
        </button>

        <button
          onClick={clear}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
        >
          <Trash2 size={14} />
          Leeren
        </button>

        {status === 'error' && (
          <button
            onClick={reconnect}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-200 text-sm text-red-600 hover:bg-red-50 transition-colors"
          >
            <RefreshCw size={14} />
            Neu verbinden
          </button>
        )}
      </div>

      {/* Log panel */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto rounded-xl font-mono text-[12px] min-h-0"
        style={{ background: '#0f172a' }}
      >
        {filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500 text-sm">
            {status === 'connecting' ? 'Verbinde mit Backend…' : 'Keine Logs vorhanden.'}
          </div>
        ) : (
          <div className="py-2">
            {filteredLogs.map((entry, i) => (
              <LogLine key={i} entry={entry} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <p className="text-xs text-slate-400 text-right">
        {filteredLogs.length} Einträge · Buffer max. 1000
      </p>
    </div>
  );
}
