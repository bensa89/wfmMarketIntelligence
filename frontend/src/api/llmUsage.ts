import { apiGet, apiPut } from './client';
import type {
  LlmUsageBreakdownRow, LlmUsageSummary, LlmUsageTimeseriesPoint, LlmModelPrice,
} from '../types/llmUsage';

export function fetchLlmUsageSummary() {
  return apiGet<LlmUsageSummary>('/llm-usage/summary');
}

export function fetchLlmUsageTimeseries(days = 30) {
  return apiGet<LlmUsageTimeseriesPoint[]>('/llm-usage/timeseries', { days: String(days) });
}

export function fetchLlmUsageBreakdown(days = 30) {
  return apiGet<LlmUsageBreakdownRow[]>('/llm-usage/breakdown', { days: String(days) });
}

export function fetchLlmModelPrices() {
  return apiGet<LlmModelPrice[]>('/llm-usage/prices');
}

export function updateLlmModelPrice(
  model: string,
  price: { input_price_per_1m: number; output_price_per_1m: number },
) {
  return apiPut<LlmModelPrice>(`/llm-usage/prices/${encodeURIComponent(model)}`, price);
}
