'use client';

import React, { useEffect } from 'react';
import { LiveMetricsView } from '../../../components/dashboard/LiveMetricsView';
import { useLiveStore } from '../../../store/liveStore';
import { api, getApiBaseUrl } from '../../../lib/api';

export default function MetricsPage() {
  const {
    liveMetrics,
    setLiveMetrics,
    metricsHistory,
    setMetricsHistory,
    metricsAnnotations,
    setMetricsAnnotations,
    metricsLoading,
    setMetricsLoading,
    selectedMetricService,
    setSelectedMetricService,
  } = useLiveStore();

  useEffect(() => {
    fetchLiveMetrics();
  }, []);

  const fetchLiveMetrics = async () => {
    setMetricsLoading(true);
    try {
      const token = localStorage.getItem('sf_token');
      const apiBase = getApiBaseUrl();
      const res = await fetch(`${apiBase}/live-metrics`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setLiveMetrics(data);
        if (data.time_series) setMetricsHistory(data.time_series);
        if (data.annotations) setMetricsAnnotations(data.annotations);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setMetricsLoading(false);
    }
  };

  return (
    <LiveMetricsView
      liveMetrics={liveMetrics}
      fetchLiveMetrics={fetchLiveMetrics}
      metricsLoading={metricsLoading}
      metricsHistory={metricsHistory}
      metricsAnnotations={metricsAnnotations}
      selectedMetricService={selectedMetricService}
      setSelectedMetricService={setSelectedMetricService}
    />
  );
}
