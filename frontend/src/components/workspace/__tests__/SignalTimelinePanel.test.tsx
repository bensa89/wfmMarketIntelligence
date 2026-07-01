import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SignalTimelinePanel from '../SignalTimelinePanel';
import * as hookModule from '../../../hooks/useCompetitorSignalStats';
import type { SignalStatsResponse } from '../../../types/intelligence';

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('SignalTimelinePanel', () => {
  it('shows the total count and chart when data is present', () => {
    const data: SignalStatsResponse = {
      total: 5,
      period_days: 30,
      granularity: 'day',
      timeline: [
        { bucket: '2026-06-01', count: 2 },
        { bucket: '2026-06-02', count: 3 },
      ],
      by_category: [],
    };
    vi.spyOn(hookModule, 'useCompetitorSignalStats').mockReturnValue({
      data, isLoading: false, error: null,
    } as ReturnType<typeof hookModule.useCompetitorSignalStats>);

    renderWithClient(<SignalTimelinePanel slug="acme" days={30} />);
    expect(screen.getByText(/5/)).toBeInTheDocument();
  });

  it('shows an empty state when total is 0', () => {
    const data: SignalStatsResponse = {
      total: 0, period_days: 30, granularity: 'day', timeline: [], by_category: [],
    };
    vi.spyOn(hookModule, 'useCompetitorSignalStats').mockReturnValue({
      data, isLoading: false, error: null,
    } as ReturnType<typeof hookModule.useCompetitorSignalStats>);

    renderWithClient(<SignalTimelinePanel slug="acme" days={30} />);
    expect(screen.getByText(/no signals/i)).toBeInTheDocument();
  });

  it('shows an error state when the request fails', () => {
    vi.spyOn(hookModule, 'useCompetitorSignalStats').mockReturnValue({
      data: undefined, isLoading: false, error: new Error('fail'),
    } as ReturnType<typeof hookModule.useCompetitorSignalStats>);

    renderWithClient(<SignalTimelinePanel slug="acme" days={30} />);
    expect(screen.getByText(/failed/i)).toBeInTheDocument();
  });
});
