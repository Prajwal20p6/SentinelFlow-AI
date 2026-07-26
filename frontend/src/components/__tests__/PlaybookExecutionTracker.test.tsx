import React from 'react';
import { render, screen } from '@testing-library/react';
import { PlaybookExecutionTracker } from '../playbooks/PlaybookExecutionTracker';
import { usePlaybookStore } from '../../store/playbookStore';

describe('PlaybookExecutionTracker Component', () => {
  const dummyProps = {
    onStartExecution: jest.fn(),
    onCancelExecution: jest.fn(),
    onRefresh: jest.fn(),
  };

  beforeEach(() => {
    usePlaybookStore.setState({
      playbookExecutions: [],
      selectedExecution: null,
      playbookLoading: false,
      playbookName: 'K8s OOM Remediation',
      playbookTargetIncident: null,
      playbookMsg: undefined,
    });
  });

  it('renders start playbook form and empty history message', () => {
    render(<PlaybookExecutionTracker {...dummyProps} />);
    expect(screen.getByText('Playbook Execution Tracker')).toBeInTheDocument();
    expect(screen.getByText('No executions yet. Start a playbook above.')).toBeInTheDocument();
  });

  it('renders active execution details when selectedExecution is set', () => {
    usePlaybookStore.setState({
      selectedExecution: {
        execution_id: 'exec-1234567890',
        playbook_name: 'K8s OOM Remediation',
        status: 'RUNNING',
        current_step: 2,
        total_steps: 4,
        progress_pct: 50,
        incident_id: 101,
        steps: [
          { name: 'Fetch Metrics', status: 'COMPLETE' },
          { name: 'Restart Pod', status: 'RUNNING' },
        ],
        log: ['Execution started'],
      },
    });

    render(<PlaybookExecutionTracker {...dummyProps} />);
    expect(screen.getByText('K8s OOM Remediation')).toBeInTheDocument();
    expect(screen.getByText('Overall Progress')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
  });
});
