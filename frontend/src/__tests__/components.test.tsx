import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { ConfidenceBar } from '@/components/ui/ConfidenceBar';
import { PredictionLabel } from '@/components/result/PredictionLabel';
import { ReliabilityBadge } from '@/components/result/ReliabilityBadge';
import { ProbabilityChart } from '@/components/result/ProbabilityChart';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { AgreementBanner } from '@/features/analysis/AgreementBanner';
import { ResultsPanel } from '@/features/analysis/ResultsPanel';
import { useSettings } from '@/store/settingsStore';
import { makeResult } from './fixtures';

describe('ConfidenceBar', () => {
  it('exposes the value as an accessible meter', () => {
    render(<ConfidenceBar value={0.873} tone="pneumonia" label="Calibrated confidence" />);
    const meter = screen.getByRole('meter', { name: 'Calibrated confidence' });
    expect(meter).toHaveAttribute('aria-valuenow', '87');
    expect(screen.getByText('87.3%')).toBeInTheDocument();
  });

  it('clamps out-of-range values', () => {
    render(<ConfidenceBar value={1.4} tone="normal" label="c" />);
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '100');
  });
});

describe('PredictionLabel', () => {
  it('always shows the label as text, not colour alone', () => {
    render(<PredictionLabel label="PNEUMONIA" stage="Stage 1 · Detection" />);
    expect(screen.getByTestId('prediction-label')).toHaveTextContent('PNEUMONIA');
    expect(screen.getByText('Stage 1 · Detection')).toBeInTheDocument();
  });
});

describe('ReliabilityBadge', () => {
  it('flags low confidence for expert review', () => {
    render(<ReliabilityBadge reliability={{ level: 'low', threshold: 0.8, message: '' }} />);
    expect(screen.getByRole('status')).toHaveTextContent(
      'Low confidence — recommend expert review',
    );
    expect(screen.getByText('80%')).toBeInTheDocument();
  });
});

describe('ProbabilityChart', () => {
  it('renders all three classes for a pneumonia result', () => {
    render(
      <ProbabilityChart
        probabilities={{ NORMAL: 0.1, BACTERIAL: 0.6, VIRAL: 0.3 }}
        highlight="BACTERIAL"
      />,
    );
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
    expect(screen.getByText('60.0%')).toBeInTheDocument();
  });

  it('does not invent a subtype for a normal result', () => {
    render(<ProbabilityChart probabilities={{ NORMAL: 0.9, PNEUMONIA: 0.1 }} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    expect(screen.queryByText('Bacterial')).not.toBeInTheDocument();
  });
});

describe('AgreementBanner', () => {
  it('shows disagreement with a recommendation', () => {
    render(
      <AgreementBanner
        agreement={{ agree: false, message: '', labels: { densenet: 'BACTERIAL', swin: 'VIRAL' } }}
      />,
    );
    expect(screen.getByText('Models disagree — expert review recommended')).toBeInTheDocument();
    expect(screen.getByText(/DenseNet121: Bacterial/)).toBeInTheDocument();
  });
});

describe('SegmentedControl', () => {
  function Harness() {
    const [v, setV] = useState<'a' | 'b' | 'c'>('a');
    return (
      <SegmentedControl
        label="Mode"
        value={v}
        onChange={setV}
        options={[
          { value: 'a', label: 'A' },
          { value: 'b', label: 'B' },
          { value: 'c', label: 'C' },
        ]}
      />
    );
  }

  it('supports arrow-key navigation', async () => {
    render(<Harness />);
    const a = screen.getByRole('radio', { name: 'A' });
    a.focus();
    await userEvent.keyboard('{ArrowRight}');
    expect(screen.getByRole('radio', { name: 'B' })).toHaveAttribute('aria-checked', 'true');
    await userEvent.keyboard('{ArrowLeft}{ArrowLeft}');
    expect(screen.getByRole('radio', { name: 'C' })).toHaveAttribute('aria-checked', 'true');
  });
});

describe('ResultsPanel', () => {
  it('shows both stages, the subtype caveat and re-evaluates reliability against the setting', () => {
    useSettings.setState({ confidenceThreshold: 0.9 });
    render(<ResultsPanel result={makeResult()} />);
    expect(screen.getAllByTestId('prediction-label').map((e) => e.textContent)).toEqual([
      'PNEUMONIA',
      'BACTERIAL',
    ]);
    expect(
      screen.getByText(/less reliable; confirm with clinical and laboratory tests/),
    ).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Low confidence');
  });
});
