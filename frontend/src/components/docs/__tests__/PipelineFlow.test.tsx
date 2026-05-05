import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PipelineFlow } from '../PipelineFlow';
import { vi } from 'vitest';

const steps = [
  { id: 'quellen', label: 'Quellen', type: 'rule' as const, description: 'Quellen verwalten' },
  { id: 'crawlen', label: 'Crawlen', type: 'rule' as const, description: 'Inhalte laden' },
  { id: 'analyse', label: 'Signal-Analyse', type: 'ai' as const, description: 'KI analysiert' },
];

describe('PipelineFlow', () => {
  it('renders all step labels', () => {
    render(<PipelineFlow steps={steps} activeStep={null} onStepClick={() => {}} />);
    expect(screen.getByText('Quellen')).toBeInTheDocument();
    expect(screen.getByText('Crawlen')).toBeInTheDocument();
    expect(screen.getByText('Signal-Analyse')).toBeInTheDocument();
  });

  it('calls onStepClick with the step id when clicked', async () => {
    const onClick = vi.fn();
    render(<PipelineFlow steps={steps} activeStep={null} onStepClick={onClick} />);
    await userEvent.click(screen.getByText('Quellen'));
    expect(onClick).toHaveBeenCalledWith('quellen');
  });

  it('applies active styling to the active step', () => {
    render(<PipelineFlow steps={steps} activeStep="crawlen" onStepClick={() => {}} />);
    const activeBtn = screen.getByText('Crawlen').closest('button');
    expect(activeBtn?.className).toMatch(/border-blue-500/);
  });
});
