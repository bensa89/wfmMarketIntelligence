export interface LlmUsageTotals {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface LlmUsageSummary {
  today: LlmUsageTotals;
  last_7_days: LlmUsageTotals;
  last_30_days: LlmUsageTotals;
  all_time: LlmUsageTotals;
}

export interface LlmUsageTimeseriesPoint {
  date: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface LlmUsageBreakdownRow {
  caller: string;
  provider: string;
  model: string;
  call_count: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface LlmModelPrice {
  model: string;
  input_price_per_1m: number;
  output_price_per_1m: number;
}
