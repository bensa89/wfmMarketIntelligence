import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SignalCategoryPanel from '../SignalCategoryPanel';
import * as hookModule from '../../../hooks/useCompetitorSignalStats';
import type { SignalStatsResponse } from '../../../types/intelligence';

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('SignalCategoryPanel', () => {
  it('renders a label per non-zero category, hiding zero-count categories', () => {
    const data: SignalStatsResponse = {
      total: 3, period_days: 30, granularity: 'day', timeline: [],
      by_category: [
        { signal_type: 'product_update', count: 2 },
        { signal_type: 'hiring_signal', count: 1 },
        { signal_type: 'other', count: 0 },
      ],
    };
    vi.spyOn(hookModule, 'useCompetitorSignalStats').mockReturnValue({
      data, isLoading: false, error: null,
    } as ReturnType<typeof hookModule.useCompetitorSignalStats>);

    renderWithClient(<SignalCategoryPanel slug="acme" days={30} />);
    expect(screen.getByText(/product update/i)).toBeInTheDocument();
    expect(screen.getByText(/hiring signal/i)).toBeInTheDocument();
    expect(screen.queryByText(/^other$/i)).not.toBeInTheDocument();
  });

  it('shows an empty state when all categories are 0', () => {
    const data: SignalStatsResponse = {
      total: 0, period_days: 30, granularity: 'day', timeline: [],
      by_category: [{ signal_type: 'other', count: 0 }],
    };
    vi.spyOn(hookModule, 'useCompetitorSignalStats').mockReturnValue({
      data, isLoading: false, error: null,
    } as ReturnType<typeof hookModule.useCompetitorSignalStats>);

    renderWithClient(<SignalCategoryPanel slug="acme" days={30} />);
    expect(screen.getByText(/no signals/i)).toBeInTheDocument();
  });
});
