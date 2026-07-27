'use client';

import React, { useState, useEffect } from 'react';
import { ExecutiveDashboard } from '../../../components/dashboard/ExecutiveDashboard';
import { useIncidentStore } from '../../../store/incidentStore';
import { Incident } from '../../../types';
import { api } from '../../../lib/api';

export default function ExecutivePage() {
  const { incidents } = useIncidentStore();
  const [executiveMetrics, setExecutiveMetrics] = useState<any>(null);
  const [selectedExecutiveIncident, setSelectedExecutiveIncident] = useState<Incident | null>(null);
  const [executiveReport, setExecutiveReport] = useState<any>(null);
  const [executiveReportLoading, setExecutiveReportLoading] = useState(false);

  useEffect(() => {
    api.getExecutiveMetrics()
      .then(setExecutiveMetrics)
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedExecutiveIncident) {
      setExecutiveReportLoading(true);
      api.getExecutiveReport(selectedExecutiveIncident.id)
        .then((report) => {
          setExecutiveReport(report);
        })
        .catch(console.error)
        .finally(() => setExecutiveReportLoading(false));
    }
  }, [selectedExecutiveIncident]);

  return (
    <ExecutiveDashboard
      executiveMetrics={executiveMetrics}
      incidents={incidents}
      selectedExecutiveIncident={selectedExecutiveIncident}
      onSelectExecutiveIncident={setSelectedExecutiveIncident}
      executiveReport={executiveReport}
      executiveReportLoading={executiveReportLoading}
    />
  );
}
