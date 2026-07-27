'use client';

import React, { useState, useEffect } from 'react';
import { ClusterTopologyView } from '../../../components/dashboard/ClusterTopologyView';
import { useIncidentStore } from '../../../store/incidentStore';
import { PodInfo } from '../../../types';
import { api } from '../../../lib/api';

export default function TopologyPage() {
  const { topology, setTopology, selectedPod, setSelectedPod } = useIncidentStore();

  const [commandInput, setCommandInput] = useState('');
  const [commandLoading, setCommandLoading] = useState(false);
  const [commandResult, setCommandResult] = useState<any>(null);
  const [podLogStream, setPodLogStream] = useState<string[]>([]);
  const [logIntervalId, setLogIntervalId] = useState<any>(null);

  useEffect(() => {
    api.getTopology()
      .then(setTopology)
      .catch(console.error);
  }, [setTopology]);

  const selectPodForInspection = (pod: PodInfo) => {
    setSelectedPod(pod);
    if (logIntervalId) clearInterval(logIntervalId);

    setPodLogStream([
      `[${new Date().toLocaleTimeString()}] Connected to container logs for ${pod.service} (${pod.node})`,
      `[${new Date().toLocaleTimeString()}] Fetching stdout stream for ${pod.name}...`,
      `[${new Date().toLocaleTimeString()}] CPU utilization nominal at ${pod.cpu_usage}%`
    ]);

    const interval = setInterval(() => {
      const mockLogLines = [
        `[${new Date().toLocaleTimeString()}] GET /api/v1/health 200 OK - 1.2ms`,
        `[${new Date().toLocaleTimeString()}] INFO: Active connection pool size: 14`,
        `[${new Date().toLocaleTimeString()}] DEBUG: Processing background telemetry span trace...`,
        `[${new Date().toLocaleTimeString()}] WARN: Memory heap usage at ${pod.memory_usage}%`
      ];
      const randomLine = mockLogLines[Math.floor(Math.random() * mockLogLines.length)];
      setPodLogStream(prev => [...prev.slice(-40), randomLine]);
    }, 3000);

    setLogIntervalId(interval);
  };

  const submitGuardedCommand = async () => {
    if (!commandInput.trim()) return;
    setCommandLoading(true);
    try {
      const result = await api.executeCommand(commandInput);
      setCommandResult(result);
    } catch (e: any) {
      setCommandResult({
        status: 'BLOCKED',
        command: commandInput,
        risk_score: 1.0,
        risk_assessment: e.message || 'Execution error encountered'
      });
    } finally {
      setCommandLoading(false);
    }
  };

  return (
    <ClusterTopologyView
      topology={topology}
      selectedPod={selectedPod}
      selectPodForInspection={selectPodForInspection}
      commandInput={commandInput}
      setCommandInput={setCommandInput}
      commandLoading={commandLoading}
      submitGuardedCommand={submitGuardedCommand}
      commandResult={commandResult}
      podLogStream={podLogStream}
    />
  );
}
