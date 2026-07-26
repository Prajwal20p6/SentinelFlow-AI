import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExecutiveDashboard } from '../dashboard/ExecutiveDashboard';

describe('ExecutiveDashboard Component', () => {
  const dummySelect = jest.fn();

  const mockMetrics = {
    mttd_seconds: 24.5,
    mttr_seconds: 180,
    resolution_rate: 98.5,
    false_positive_rate: 1.2,
  };

  const mockIncidents: any[] = [
    {
      id: 1,
      title: 'DDoS Attack Mitigated',
      severity: 'CRITICAL',
      status: 'EXECUTED',
      correlation_id: 'corr-001',
      created_at: new Date().toISOString(),
    },
  ];

  it('renders metric cards and empty report state when selectedExecutiveIncident is null', () => {
    render(
      <ExecutiveDashboard
        executiveMetrics={mockMetrics}
        incidents={mockIncidents}
        selectedExecutiveIncident={null}
        onSelectExecutiveIncident={dummySelect}
        executiveReport={null}
        executiveReportLoading={false}
      />
    );

    expect(screen.getByText('Executive SecOps Intelligence')).toBeInTheDocument();
    expect(screen.getByText('24.5 s')).toBeInTheDocument();
    expect(screen.getByText('3.0 m')).toBeInTheDocument();
    expect(screen.getByText('DDoS Attack Mitigated')).toBeInTheDocument();
    expect(screen.getByText('Select an incident from the index to inspect its business-level impact score, regulatory exposure compliance status, and AI executive summary.')).toBeInTheDocument();
  });

  it('renders report details when selectedExecutiveIncident is set', () => {
    const report = {
      summary: 'DDoS traffic of 50Gbps mitigated using eBPF rules.',
      simplified_explanation: 'Safely dropped bad packets at kernel layer.',
      business_impact: {
        affected_users: 500,
        revenue_lost_usd: 1250,
        risk_score: 'HIGH',
      },
      estimated_recovery_time_mins: 15,
      compliance: {
        compliance_status: 'MET',
        compliance_score_percent: 100,
        regulations_applicable: ['SOC2', 'GDPR'],
        checklist: [{ id: 1, task: 'Audit log exported', status: true }],
      },
    };

    render(
      <ExecutiveDashboard
        executiveMetrics={mockMetrics}
        incidents={mockIncidents}
        selectedExecutiveIncident={mockIncidents[0]}
        onSelectExecutiveIncident={dummySelect}
        executiveReport={report}
        executiveReportLoading={false}
      />
    );

    expect(screen.getByText(/DDoS traffic of 50Gbps mitigated using eBPF rules/i)).toBeInTheDocument();
    expect(screen.getByText(/Safely dropped bad packets at kernel layer/i)).toBeInTheDocument();
    expect(screen.getByText(/\$1,250/i)).toBeInTheDocument();
    expect(screen.getByText('Audit log exported')).toBeInTheDocument();
  });
});
