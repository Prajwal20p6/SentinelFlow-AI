'use client';

import React, { useEffect } from 'react';
import { ObservabilityTracesView } from '../../../components/dashboard/ObservabilityTracesView';
import { useLiveStore } from '../../../store/liveStore';
import { api } from '../../../lib/api';

export default function ObservabilityPage() {
  const { obsSummary, obsTraces, setObsSummary, setObsTraces } = useLiveStore();

  useEffect(() => {
    api.getObservabilitySummary()
      .then(setObsSummary)
      .catch(console.error);

    api.getObservabilityTraces()
      .then((res) => setObsTraces(res.traces || []))
      .catch(console.error);
  }, [setObsSummary, setObsTraces]);

  return (
    <ObservabilityTracesView
      obsSummary={obsSummary}
      obsTraces={obsTraces}
    />
  );
}
