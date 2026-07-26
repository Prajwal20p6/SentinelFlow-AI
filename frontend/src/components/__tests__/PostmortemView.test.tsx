import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { PostmortemView } from '../postmortem/PostmortemView';
import { usePostmortemStore } from '../../store/postmortemStore';

describe('PostmortemView Component', () => {
  const dummyGenerate = jest.fn();

  beforeEach(() => {
    usePostmortemStore.setState({
      postmortemData: null,
      postmortemLoading: false,
      postmortemGenerating: false,
    });
  });

  it('renders title and empty state message when postmortemData is null', () => {
    render(<PostmortemView onGeneratePostmortem={dummyGenerate} />);
    expect(screen.getByText('Incident Postmortem Report')).toBeInTheDocument();
    expect(screen.getByText('No postmortem report available for this incident.')).toBeInTheDocument();
  });

  it('renders report data when postmortemData is set', () => {
    usePostmortemStore.setState({
      postmortemData: {
        executive_summary: 'High CPU spike resolved via pod restart.',
        incident_details: {
          id: 42,
          title: 'API Gateway CPU Spike',
          metric_type: 'CPU_SPIKE',
          status: 'EXECUTED',
        },
        impact: {
          severity_description: 'Critical',
          estimated_affected_users: 1200,
          downtime_cost_estimate_usd: 450.0,
        },
      },
    });

    render(<PostmortemView onGeneratePostmortem={dummyGenerate} />);
    expect(screen.getByText(/High CPU spike resolved via pod restart/i)).toBeInTheDocument();
    expect(screen.getByText(/API Gateway CPU Spike/i)).toBeInTheDocument();
    expect(screen.getByText('$450.00')).toBeInTheDocument();
  });
});
