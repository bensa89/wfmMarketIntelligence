import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  fetchLlmModelPrices, fetchLlmUsageBreakdown, fetchLlmUsageSummary, fetchLlmUsageTimeseries,
  updateLlmModelPrice,
} from '../api/llmUsage';
import type { LlmUsageTimeseriesPoint, LlmUsageTotals } from '../types/llmUsage';

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function formatCost(n: number): string {
  return `$${n.toFixed(2)}`;
}

function SummaryTile({ label, totals }: { label: string; totals: LlmUsageTotals }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-2xl font-semibold text-slate-800 mt-1">{formatTokens(totals.total_tokens)}</p>
      <p className="text-xs text-slate-400 mt-0.5">{formatCost(totals.cost_usd)}</p>
    </div>
  );
}

function Sparkbars({ points }: { points: LlmUsageTimeseriesPoint[] }) {
  const max = Math.max(1, ...points.map((p) => p.total_tokens));
  return (
    <div className="flex items-end gap-1 h-32">
      {points.map((p) => (
        <div
          key={p.date}
          className="flex-1 bg-blue-500/70 rounded-t hover:bg-blue-500 transition-colors min-h-[2px]"
          style={{ height: `${Math.max(2, (p.total_tokens / max) * 100)}%` }}
          title={`${p.date}: ${formatTokens(p.total_tokens)} Tokens · ${formatCost(p.cost_usd)}`}
        />
      ))}
    </div>
  );
}

function PriceEditorRow({ model, inputPrice, outputPrice, onSaved }: {
  model: string; inputPrice: number; outputPrice: number; onSaved: () => void;
}) {
  const [input, setInput] = useState(String(inputPrice));
  const [output, setOutput] = useState(String(outputPrice));

  const saveMutation = useMutation({
    mutationFn: () => updateLlmModelPrice(model, {
      input_price_per_1m: parseFloat(input) || 0,
      output_price_per_1m: parseFloat(output) || 0,
    }),
    onSuccess: onSaved,
  });

  return (
    <tr className="border-b border-slate-100">
      <td className="py-2 text-sm text-slate-700">{model}</td>
      <td className="py-2">
        <input
          type="number" step="0.01" value={input} onChange={(e) => setInput(e.target.value)}
          className="border border-slate-200 rounded-lg px-2 py-1 text-sm w-24"
        />
      </td>
      <td className="py-2">
        <input
          type="number" step="0.01" value={output} onChange={(e) => setOutput(e.target.value)}
          className="border border-slate-200 rounded-lg px-2 py-1 text-sm w-24"
        />
      </td>
      <td className="py-2">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="text-xs px-2.5 py-1 rounded-lg border border-slate-200 hover:bg-slate-50"
        >
          Speichern
        </button>
      </td>
    </tr>
  );
}

const KNOWN_MODELS = ['claude-haiku-4-5-20251001', 'claude-sonnet-4-6', 'claude-opus-4-8'];

export default function LlmUsageAdmin() {
  const queryClient = useQueryClient();
  const [days, setDays] = useState(30);

  const { data: summary } = useQuery({ queryKey: ['llm-usage-summary'], queryFn: fetchLlmUsageSummary });
  const { data: timeseries } = useQuery({
    queryKey: ['llm-usage-timeseries', days],
    queryFn: () => fetchLlmUsageTimeseries(days),
  });
  const { data: breakdown } = useQuery({
    queryKey: ['llm-usage-breakdown', days],
    queryFn: () => fetchLlmUsageBreakdown(days),
  });
  const { data: prices } = useQuery({ queryKey: ['llm-model-prices'], queryFn: fetchLlmModelPrices });

  function refetchAll() {
    queryClient.invalidateQueries({ queryKey: ['llm-model-prices'] });
    queryClient.invalidateQueries({ queryKey: ['llm-usage-summary'] });
    queryClient.invalidateQueries({ queryKey: ['llm-usage-timeseries', days] });
    queryClient.invalidateQueries({ queryKey: ['llm-usage-breakdown', days] });
  }

  const priceByModel = new Map((prices ?? []).map((p) => [p.model, p]));
  const allModels = Array.from(new Set([...KNOWN_MODELS, ...(prices ?? []).map((p) => p.model)]));

  return (
    <div className="p-6 max-w-5xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">LLM-Token-Nutzung</h1>
        <p className="text-sm text-slate-500 mt-0.5">Token-Verbrauch und Kosten über alle Pipelines</p>
      </div>

      {summary && (
        <div className="grid grid-cols-4 gap-3">
          <SummaryTile label="Heute" totals={summary.today} />
          <SummaryTile label="7 Tage" totals={summary.last_7_days} />
          <SummaryTile label="30 Tage" totals={summary.last_30_days} />
          <SummaryTile label="Gesamt" totals={summary.all_time} />
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Verlauf</h2>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm bg-white"
          >
            <option value={7}>7 Tage</option>
            <option value={30}>30 Tage</option>
            <option value={90}>90 Tage</option>
          </select>
        </div>
        {timeseries && timeseries.length > 0 ? (
          <Sparkbars points={timeseries} />
        ) : (
          <p className="text-sm text-slate-400">Keine Daten im Zeitraum.</p>
        )}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 overflow-x-auto">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-3">
          Aufschlüsselung nach Caller / Provider / Modell
        </h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-400 border-b border-slate-200">
              <th className="py-2">Caller</th>
              <th className="py-2">Provider</th>
              <th className="py-2">Modell</th>
              <th className="py-2 text-right">Calls</th>
              <th className="py-2 text-right">Tokens</th>
              <th className="py-2 text-right">Kosten</th>
            </tr>
          </thead>
          <tbody>
            {(breakdown ?? []).map((row) => (
              <tr key={`${row.caller}-${row.provider}-${row.model}`} className="border-b border-slate-100">
                <td className="py-2 text-slate-700">{row.caller}</td>
                <td className="py-2 text-slate-500">{row.provider}</td>
                <td className="py-2 text-slate-500">{row.model}</td>
                <td className="py-2 text-right">{row.call_count}</td>
                <td className="py-2 text-right">{formatTokens(row.total_tokens)}</td>
                <td className="py-2 text-right">{formatCost(row.cost_usd)}</td>
              </tr>
            ))}
            {(breakdown ?? []).length === 0 && (
              <tr><td colSpan={6} className="py-4 text-center text-slate-400">Keine Daten im Zeitraum.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 overflow-x-auto">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-3">
          Preistabelle ($ pro 1M Tokens)
        </h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-400 border-b border-slate-200">
              <th className="py-2">Modell</th>
              <th className="py-2">Input</th>
              <th className="py-2">Output</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {allModels.map((model) => {
              const price = priceByModel.get(model);
              return (
                <PriceEditorRow
                  key={model}
                  model={model}
                  inputPrice={price?.input_price_per_1m ?? 0}
                  outputPrice={price?.output_price_per_1m ?? 0}
                  onSaved={refetchAll}
                />
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
