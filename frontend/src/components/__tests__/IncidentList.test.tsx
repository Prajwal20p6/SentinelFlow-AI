import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { IncidentList } from '../incidents/IncidentList';

describe('IncidentList Component', () => {
  const mockIncidents: any[] = [
    {
      id: 1,
      title: 'High CPU Spike on API Gateway',
      severity: 'CRITICAL',
      status: 'DETECTED',
      metric_type: 'CPU_SPIKE',
      created_at: new Date().toISOString(),
      priority_score: 90,
      sla_target: 'P0',
    },
    {
      id: 2,
      title: 'Memory Leak on Node Service',
      severity: 'WARNING',
      status: 'EXECUTING',
      metric_type: 'MEMORY_EXHAUSTION',
      created_at: new Date().toISOString(),
      priority_score: 60,
      sla_target: 'P2',
    },
  ];

  it('renders incident list with incident titles and total count', () => {
    const onSelect = jest.fn();
    render(<IncidentList incidents={mockIncidents} selectedIncident={null} onSelectIncident={onSelect} />);

    expect(screen.getByText(/Total: 2/i)).toBeInTheDocument();
    expect(screen.getByText('High CPU Spike on API Gateway')).toBeInTheDocument();
    expect(screen.getByText('Memory Leak on Node Service')).toBeInTheDocument();
  });

  it('triggers onSelectIncident when an incident card is clicked', () => {
    const onSelect = jest.fn();
    render(<IncidentList incidents={mockIncidents} selectedIncident={null} onSelectIncident={onSelect} />);

    fireEvent.click(screen.getByText('High CPU Spike on API Gateway'));
    expect(onSelect).toHaveBeenCalledWith(mockIncidents[0]);
  });
});
