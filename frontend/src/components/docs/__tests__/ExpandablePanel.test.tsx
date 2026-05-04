import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExpandablePanel } from '../ExpandablePanel';

describe('ExpandablePanel', () => {
  it('renders the title and hides children by default', () => {
    render(
      <ExpandablePanel title="Datenstruktur anzeigen">
        <p>hidden content</p>
      </ExpandablePanel>
    );
    expect(screen.getByText('Datenstruktur anzeigen')).toBeInTheDocument();
    expect(screen.queryByText('hidden content')).not.toBeInTheDocument();
  });

  it('shows children after clicking the title button', async () => {
    render(
      <ExpandablePanel title="Datenstruktur anzeigen">
        <p>hidden content</p>
      </ExpandablePanel>
    );
    await userEvent.click(screen.getByText('Datenstruktur anzeigen'));
    expect(screen.getByText('hidden content')).toBeInTheDocument();
  });

  it('hides children again after a second click', async () => {
    render(
      <ExpandablePanel title="Datenstruktur anzeigen">
        <p>hidden content</p>
      </ExpandablePanel>
    );
    await userEvent.click(screen.getByText('Datenstruktur anzeigen'));
    await userEvent.click(screen.getByText('Datenstruktur anzeigen'));
    expect(screen.queryByText('hidden content')).not.toBeInTheDocument();
  });
});
