'use client';

import React, { useEffect } from 'react';
import { PlaybookExecutionTracker } from '../../../components/playbooks/PlaybookExecutionTracker';
import { usePlaybookStore } from '../../../store/playbookStore';

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

export default function PlaybooksPage() {
  const {
    playbookExecutions,
    setPlaybookExecutions,
    selectedExecution,
    setSelectedExecution,
    playbookName,
    playbookTargetIncident,
    setPlaybookLoading,
    setPlaybookMsg,
  } = usePlaybookStore();

  useEffect(() => {
    fetchPlaybookExecutions();
  }, []);

  const fetchPlaybookExecutions = async () => {
    try {
      const token = localStorage.getItem('sf_token');
      const apiBase = getApiBaseUrl();
      const res = await fetch(`${apiBase}/playbook-executions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPlaybookExecutions(data);
        if (data.length > 0 && !selectedExecution) {
          setSelectedExecution(data[0]);
        }
      }
    } catch (err) {
      console.error('Fetch playbook executions error:', err);
    }
  };

  const handleStartPlaybookExecution = async () => {
    if (!playbookTargetIncident) {
      setPlaybookMsg('Please select a target incident first.');
      return;
    }
    setPlaybookLoading(true);
    setPlaybookMsg('');
    try {
      const token = localStorage.getItem('sf_token');
      const apiBase = getApiBaseUrl();
      const formData = new FormData();
      formData.append('incident_id', playbookTargetIncident.toString());
      formData.append('playbook_name', playbookName);
      const res = await fetch(
        `${apiBase}/playbook-executions`,
        { method: 'POST', headers: { 'Authorization': `Bearer ${token}` }, body: formData }
      );
      if (res.ok) {
        const record = await res.json();
        setSelectedExecution(record);
        setPlaybookExecutions([record, ...playbookExecutions]);
        setPlaybookMsg(`Execution started: ${record.execution_id.slice(0, 8)}...`);
        simulatePlaybookAdvance(record.execution_id, 0, record.total_steps);
      } else {
        const err = await res.json();
        setPlaybookMsg(`Error: ${err.detail || 'Failed to start playbook'}`);
      }
    } catch (err: any) {
      setPlaybookMsg(`Network Error: ${err.message}`);
    } finally {
      setPlaybookLoading(false);
    }
  };

  const simulatePlaybookAdvance = (execId: string, step: number, totalSteps: number) => {
    if (step >= totalSteps) return;
    setTimeout(async () => {
      try {
        const token = localStorage.getItem('sf_token');
        const apiBase = getApiBaseUrl();
        const res = await fetch(
          `${apiBase}/playbook-executions/${execId}/advance?success=true&log_message=Step%20completed%20automatically`,
          { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } }
        );
        if (res.ok) {
          const updated = await res.json();
          setPlaybookExecutions(playbookExecutions.map((e: any) => e.execution_id === execId ? updated : e));
          if (selectedExecution?.execution_id === execId) {
            setSelectedExecution(updated);
          }
          if (updated.status === 'RUNNING') {
            simulatePlaybookAdvance(execId, step + 1, totalSteps);
          }
        }
      } catch (e) {
        console.error('Advance step error:', e);
      }
    }, 2000 + Math.random() * 1500);
  };

  const handleCancelExecution = async (execId: string) => {
    try {
      const token = localStorage.getItem('sf_token');
      const apiBase = getApiBaseUrl();
      const res = await fetch(`${apiBase}/playbook-executions/${execId}/cancel`, {
        method: 'POST', headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const updated = await res.json();
        setPlaybookExecutions(playbookExecutions.map((e: any) => e.execution_id === execId ? updated : e));
        if (selectedExecution?.execution_id === execId) {
          setSelectedExecution(updated);
        }
      }
    } catch (e) {
      console.error('Cancel execution error:', e);
    }
  };

  return (
    <PlaybookExecutionTracker
      onStartExecution={handleStartPlaybookExecution}
      onCancelExecution={handleCancelExecution}
      onRefresh={fetchPlaybookExecutions}
    />
  );
}
