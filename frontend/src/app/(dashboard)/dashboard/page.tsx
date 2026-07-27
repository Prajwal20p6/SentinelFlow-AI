'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { CyberDashboard } from '../../../components/dashboard/CyberDashboard';
import { useAuthStore } from '../../../store/authStore';
import { useIncidentStore } from '../../../store/incidentStore';
import { useLiveStore } from '../../../store/liveStore';
import { api } from '../../../lib/api';

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const {
    incidents,
    setIncidents,
    topology,
    setTopology,
    activeIncidentCount,
    serverHealth,
    circuitBreakers,
  } = useIncidentStore();

  const { obsSummary } = useLiveStore();

  useEffect(() => {
    api.getIncidents()
      .then((res) => setIncidents(res.incidents))
      .catch(console.error);

    api.getTopology()
      .then(setTopology)
      .catch(console.error);
  }, [setIncidents, setTopology]);

  const mockChartData = topology?.pods?.filter(Boolean).slice(0, 5).map((pod, i) => ({
    name: (pod.name || `pod-${i}`).split('-')[0],
    cpu: pod.cpu_usage,
    memory: pod.memory_usage,
    latency: pod.cpu_usage * 2 + 10,
  })) || [];

  return (
    <CyberDashboard
      obsSummary={obsSummary}
      activeIncidentCount={activeIncidentCount}
      mockChartData={mockChartData}
      user={user}
      serverHealth={serverHealth}
      executiveMetrics={null}
      incidents={incidents}
      circuitBreakers={circuitBreakers}
      onNavigateToIncidents={() => router.push('/incidents')}
    />
  );
}
