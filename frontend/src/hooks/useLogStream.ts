import { useState, useEffect, useRef, useCallback } from 'react';

export interface LogEntry {
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  name: string;
  message: string;
}

export type StreamStatus = 'connecting' | 'connected' | 'paused' | 'disconnected' | 'error';

const MAX_BUFFER = 1000;
const MAX_RETRIES = 5;
const RETRY_DELAY_MS = 2000;

function buildAuthHeader(): Record<string, string> {
  const stored = localStorage.getItem('wfm_credentials');
  if (!stored) return {};
  try {
    const { username, password } = JSON.parse(stored);
    if (!username || !password) return {};
    return { Authorization: `Basic ${btoa(`${username}:${password}`)}` };
  } catch {
    return {};
  }
}

export function useLogStream() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<StreamStatus>('connecting');
  const [modules, setModules] = useState<string[]>([]);

  const abortRef = useRef<AbortController | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);
  const pausedRef = useRef(false);
  const modulesSetRef = useRef<Set<string>>(new Set());

  const connect = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    if (retryTimerRef.current) clearTimeout(retryTimerRef.current);

    const controller = new AbortController();
    abortRef.current = controller;

    if (!pausedRef.current) setStatus('connecting');

    (async () => {
      try {
        const authHeader = buildAuthHeader();
        const res = await fetch('/api/logs/stream', {
          headers: authHeader,
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          setStatus('error');
          return;
        }

        setStatus('connected');
        retryCountRef.current = 0;

        const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += value;
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            if (pausedRef.current) continue;
            try {
              const entry: LogEntry = JSON.parse(line.slice(6));
              setLogs((prev) => {
                const next = [...prev, entry];
                return next.length > MAX_BUFFER ? next.slice(next.length - MAX_BUFFER) : next;
              });
              if (!modulesSetRef.current.has(entry.name)) {
                modulesSetRef.current.add(entry.name);
                setModules(Array.from(modulesSetRef.current).sort());
              }
            } catch {
              // ignore malformed frames
            }
          }
        }

        if (!controller.signal.aborted) scheduleRetry();
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        scheduleRetry();
      }
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function scheduleRetry() {
    if (retryCountRef.current >= MAX_RETRIES) {
      setStatus('error');
      return;
    }
    retryCountRef.current++;
    setStatus('disconnected');
    retryTimerRef.current = setTimeout(() => connect(), RETRY_DELAY_MS);
  }

  useEffect(() => {
    connect();
    return () => {
      abortRef.current?.abort();
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    };
  }, [connect]);

  const pause = useCallback(() => {
    pausedRef.current = true;
    setStatus('paused');
  }, []);

  const resume = useCallback(() => {
    pausedRef.current = false;
    setStatus('connected');
  }, []);

  const clear = useCallback(() => setLogs([]), []);

  const reconnect = useCallback(() => {
    retryCountRef.current = 0;
    pausedRef.current = false;
    connect();
  }, [connect]);

  return { logs, status, modules, pause, resume, clear, reconnect };
}
