import React from 'react';
import { render, screen } from '@testing-library/react';
import { IncidentDetailView } from '../incidents/IncidentDetailView';

describe('IncidentDetailView Component', () => {
  const dummyProps = {
    selectedIncident: {
      id: 1,
      title: 'High CPU Spike on K8s Node',
      severity: 'CRITICAL' as const,
      status: 'EXECUTING',
      source: 'K8s Monitor',
      metric_type: 'CPU_SPIKE',
      correlation_id: 'corr-001',
      confidence_score: 0.95,
      risk_score: 0.2,
      description: 'CPU consumption exceeded 90% threshold for 5 minutes.',
      suggested_action: 'kubectl rollout restart deployment/api-service',
      assigned_to: null,
      resolved_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },

    incidents: [],
    inspectorTab: 'timeline' as const,
    setInspectorTab: jest.fn(),
    explainabilityReport: {
      overall_confidence: 95,
      overall_explanation: 'CPU spike caused by infinite loop in worker thread.',
    },
    activeAgent: null,
    wp: null,
    replayIndex: -1,
    setReplayIndex: jest.fn(),
    isPlayingReplay: false,
    setIsPlayingReplay: jest.fn(),
    fetchPostmortem: jest.fn(),
    onViewInMastra: jest.fn(),
    onSelectIncident: jest.fn(),
  };

  it('renders incident detail header, anomaly details, and suggested remediator', () => {
    render(<IncidentDetailView {...dummyProps} />);

    expect(screen.getByText('High CPU Spike on K8s Node')).toBeInTheDocument();
    expect(screen.getByText('CID: corr-001')).toBeInTheDocument();
    expect(screen.getByText('CPU consumption exceeded 90% threshold for 5 minutes.')).toBeInTheDocument();
    expect(screen.getByText('kubectl rollout restart deployment/api-service')).toBeInTheDocument();
    expect(screen.getByText('View in Mastra Live')).toBeInTheDocument();
  });
});
