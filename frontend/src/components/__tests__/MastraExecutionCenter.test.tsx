import React from 'react';
import { render, screen } from '@testing-library/react';
import { MastraExecutionCenter } from '../mastra/MastraExecutionCenter';
import { useMastraStore } from '../../store/mastraStore';

describe('MastraExecutionCenter Component', () => {
  const dummyTrigger = jest.fn();

  beforeEach(() => {
    useMastraStore.setState({
      mastraEvents: [],
      mastraExecution: null,
      mastraSelectedId: null,
      mastraLoading: false,
    });
  });

  it('renders No Active Execution state when mastraExecution is null', () => {
    render(<MastraExecutionCenter onTriggerDemo={dummyTrigger} />);
    expect(screen.getByText('Mastra Live Execution Monitor')).toBeInTheDocument();
    expect(screen.getByText('No Active Execution')).toBeInTheDocument();
  });

  it('renders simulated fallback warning banner when is_simulated is true', () => {
    useMastraStore.setState({
      mastraExecution: {
        is_simulated: true,
        simulation_reason: 'Forced simulation via FORCE_SIMULATION=true',
        incident: { id: 1, metric_type: 'CPU_SPIKE', severity: 'CRITICAL', status: 'EXECUTING' },
        workflow: { name: 'IncidentResponseWorkflow', current_step: 2, total_steps: 5 },
      },
    });

    render(<MastraExecutionCenter onTriggerDemo={dummyTrigger} />);
    expect(screen.getByText(/Simulated Fallback Active — Live Agent Call Failed/i)).toBeInTheDocument();
    expect(screen.getByText(/Forced simulation via FORCE_SIMULATION=true/i)).toBeInTheDocument();
  });
});
