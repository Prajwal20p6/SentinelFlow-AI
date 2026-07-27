'use client';

import React from 'react';
import { MastraExecutionCenter } from '../../../components/mastra/MastraExecutionCenter';
import { useMastraStore } from '../../../store/mastraStore';
import { useIncidentStore } from '../../../store/incidentStore';
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

const STEP_KEYS = ['DETECT_ANOMALY','RETRIEVE_CONTEXT','RETRIEVE_RUNBOOKS','PLAN_REMEDIATION','CONTRADICTION_CHECK','VALIDATE','APPROVE_DECISION','EXECUTE_REMEDIATION'];
const STEP_LABELS: Record<string, string> = {
  DETECT_ANOMALY: 'Anomaly Detection & Agent Selection',
  RETRIEVE_CONTEXT: 'CRISPE Prompt Template Lookup',
  RETRIEVE_RUNBOOKS: 'RAG Knowledge Retrieval',
  PLAN_REMEDIATION: 'LLM Multi-Agent Reasoning',
  CONTRADICTION_CHECK: 'Mastra Contradiction Analysis',
  VALIDATE: 'Enkrypt AI Safety Validation',
  APPROVE_DECISION: 'Confidence Gate & Governance',
  EXECUTE_REMEDIATION: 'Autonomous Remediation Execution',
};

const buildPlaceholderExecution = (incidentId: number, scenario: string) => ({
  active: true,
  incident: {
    id: incidentId,
    title: `${scenario.replace(/_/g, ' ')}`,
    metric_type: scenario,
    severity: scenario.includes('UNAUTHORIZED') || scenario.includes('DDOS') || scenario.includes('PHISHING') || scenario.includes('DATA_BREACH') || scenario.includes('ERROR_RATE') ? 'CRITICAL' : 'WARNING',
    status: 'EXECUTING',
  },
  workflow: {
    name: 'IncidentResponseWorkflow',
    is_completed: false,
    current_step: 1,
    total_steps: 8,
  },
  agent: { name: 'Pending...', sub_type: '', domain: '' },
  ai_provider: 'pending',
  confidence: 0,
  safety: { status: 'Pending', risk_score: 0 },
  pipeline: STEP_KEYS.map((key, i) => ({
    step_number: i + 1,
    step_key: key,
    label: STEP_LABELS[key],
    status: i === 0 ? 'running' : 'pending',
    duration_seconds: 0,
    error_message: null,
  })),
  timeline_events: [],
});

export default function MastraPage() {
  const { setMastraEvents, setMastraSelectedId, setMastraExecution } = useMastraStore();
  const { setIncidents, setActiveIncidentCount, setGlobalStatus } = useIncidentStore();

  const triggerDemoScenario = async (scenario: string): Promise<number | null> => {
    try {
      const token = localStorage.getItem('sf_token');
      const resp = await fetch(`${getApiBaseUrl()}/demo/trigger`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ scenario })
      });
      const data = await resp.json();
      if (resp.ok) {
        const incId = data.incident_id as number;
        try {
          const incData = await api.getIncidents();
          setIncidents(incData.incidents);
          const active = incData.incidents.filter(i => ['DETECTED', 'ANALYZING', 'PENDING_APPROVAL', 'APPROVED', 'EXECUTING'].includes(i.status));
          setActiveIncidentCount(active.length);
          setGlobalStatus(active.length > 0 ? 'THREAT_DETECTED' : 'SECURE');
        } catch (refreshErr) {
          console.error(refreshErr);
        }
        
        setMastraSelectedId(incId);
        setMastraExecution(buildPlaceholderExecution(incId, scenario));
        setMastraEvents([]);
        return incId;
      }
      return null;
    } catch (err) {
      console.error(err);
      return null;
    }
  };

  return (
    <MastraExecutionCenter
      onTriggerDemo={async (type: string) => {
        try {
          setMastraEvents([]);
          const incId = await triggerDemoScenario(type);
          if (incId) {
            setMastraSelectedId(incId);
            setMastraExecution(buildPlaceholderExecution(incId, type));
          }
          setTimeout(async () => {
            try {
              const res = await api.getActiveExecution();
              if (res && res.active) {
                setMastraExecution(res);
                setMastraSelectedId(res.incident?.id || incId);
              } else if (incId) {
                try {
                  const res2 = await api.getIncidentExecution(incId);
                  setMastraExecution(res2);
                } catch {}
              }
            } catch {}
          }, 2000);
        } catch (e) {
          console.error(e);
        }
      }}
    />
  );
}
