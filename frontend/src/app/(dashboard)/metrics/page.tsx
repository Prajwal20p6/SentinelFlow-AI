'use client';

import React, { useEffect } from 'react';
import { LiveMetricsView } from '../../../components/dashboard/LiveMetricsView';
import { useLiveStore } from '../../../store/liveStore';
import { api } from '../../../lib/api';

const getApiBaseUrl = () => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== 'undefined') {
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      return 'https://backend-production-f51a.up.railway.app/api/v1';
    }
  }
  return 'http://127.0.0.1:8000/api/v1';
};

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
