'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { SecuritySettingsView } from '../../../components/dashboard/SecuritySettingsView';
import { useAuthStore } from '../../../store/authStore';
import { useIncidentStore } from '../../../store/incidentStore';
import { useMastraStore } from '../../../store/mastraStore';
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

export default function SettingsPage() {
  const router = useRouter();
  const { user, setUser, sessions, setSessions } = useAuthStore();
  const { setIncidents, setSelectedIncident, setActiveIncidentCount, setGlobalStatus } = useIncidentStore();
  const { setMastraSelectedId, setMastraExecution, setMastraEvents } = useMastraStore();

  const [mfaSecretData, setMfaSecretData] = useState<any>(null);
  const [mfaSetupCode, setMfaSetupCode] = useState('');
  const [mfaStatusMsg, setMfaStatusMsg] = useState('');

  const [govMode, setGovMode] = useState('MANUAL');
  const [govRateLimit, setGovRateLimit] = useState(5);
  const [govMinConfidence, setGovMinConfidence] = useState(90);
  const [govMaxBlastRadius, setGovMaxBlastRadius] = useState(10);
  const [govRestrictedServices, setGovRestrictedServices] = useState('payment');
  const [govLowRiskActions, setGovLowRiskActions] = useState('restart_pod,scale_service,rollout_restart');
  const [policies, setPolicies] = useState<any[]>([]);
  const [govLoading, setGovLoading] = useState(false);
  const [govMsg, setGovMsg] = useState('');

  const [demoLoading, setDemoLoading] = useState(false);
  const [demoResultMsg, setDemoResultMsg] = useState('');

  useEffect(() => {
    fetchGovConfig();
    fetchPolicies();
    fetchSessions();
  }, []);

  const fetchGovConfig = async () => {
    try {
      const apiBase = getApiBaseUrl();
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${apiBase}/execution-config`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setGovMode(data.mode);
        setGovRateLimit(data.rate_limit_per_minute);
        setGovMinConfidence(data.min_confidence_score);
        setGovMaxBlastRadius(data.max_blast_radius);
        setGovRestrictedServices(data.restricted_services);
        setGovLowRiskActions(data.low_risk_actions);
      }
    } catch (err) {
      console.error('Fetch gov config error:', err);
    }
  };

  const fetchPolicies = async () => {
    try {
      const data = await api.getPolicies();
      setPolicies(data);
    } catch (err) {
      console.error('Fetch policies error:', err);
    }
  };

  const fetchSessions = async () => {
    try {
      const list = await api.getSessions();
      setSessions(list);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  };

  const triggerMFASetup = async () => {
    try {
      const data = await api.setupMFA();
      setMfaSecretData(data);
      setMfaStatusMsg('');
    } catch (err) {
      setMfaStatusMsg('Failed to initialize MFA setup keys.');
    }
  };

  const verifyAndEnableMFA = async () => {
    try {
      await api.enableMFA(mfaSetupCode);
      setMfaStatusMsg('MFA configuration verified. Multi-factor guard enabled!');
      setMfaSecretData(null);
      setMfaSetupCode('');
      const me = await api.getMe();
      setUser(me);
      localStorage.setItem('sf_user', JSON.stringify(me));
    } catch (err: any) {
      setMfaStatusMsg(err.data?.detail || 'Verification code failed. Please check device.');
    }
  };

  const disableMFA = async () => {
    try {
      await api.disableMFA();
      setMfaStatusMsg('MFA deactivated. Profile fallback to password verification only.');
      const me = await api.getMe();
      setUser(me);
      localStorage.setItem('sf_user', JSON.stringify(me));
    } catch (err) {
      setMfaStatusMsg('Failed to disable MFA.');
    }
  };

  const handleGovConfigSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGovLoading(true);
    setGovMsg('');
    try {
      const apiBase = getApiBaseUrl();
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${apiBase}/execution-config`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          mode: govMode,
          rate_limit_per_minute: Number(govRateLimit),
          min_confidence_score: Number(govMinConfidence),
          max_blast_radius: Number(govMaxBlastRadius),
          restricted_services: govRestrictedServices,
          low_risk_actions: govLowRiskActions
        })
      });
      if (res.ok) {
        setGovMsg('Autopilot governance configuration successfully updated.');
        setTimeout(() => setGovMsg(''), 4000);
      } else {
        const errData = await res.json();
        setGovMsg(`Error: ${errData.detail || 'Failed to update governance configurations'}`);
      }
    } catch (err: any) {
      setGovMsg(`Network Error: ${err.message || err}`);
    } finally {
      setGovLoading(false);
    }
  };

  const togglePolicyAction = async (id: number) => {
    try {
      await api.togglePolicy(id);
      fetchPolicies();
    } catch (err) {
      console.error('Toggle policy error:', err);
    }
  };

  const revokeSessionAction = async (sessionId: number) => {
    try {
      await api.revokeSession(sessionId);
      fetchSessions();
    } catch (err) {
      alert('Failed to revoke session.');
    }
  };

  const triggerDemoScenario = async (scenario: string) => {
    setDemoLoading(true);
    setDemoResultMsg('');
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
        setDemoResultMsg(`Success: Demo scenario ${scenario} triggered! Generated Incident #${data.incident_id}`);
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
        setMastraExecution({
          active: true,
          pipeline: [],
          incident: { id: incId, metric_type: scenario, severity: 'CRITICAL', status: 'EXECUTING' },
          agent: { name: 'SentinelFlow Agent', sub_type: 'RCA', domain: 'Kubernetes' },
          ai_provider: 'simulation',
          confidence: 0.95,
          safety: { status: 'SAFE', risk_score: 0.05 },
          workflow: { current_step: 1 }
        });
        setMastraEvents([]);
        router.push('/mastra');
      } else {
        setDemoResultMsg(`Error: ${data.detail || 'Trigger failed'}`);
      }
    } catch (err: any) {
      setDemoResultMsg(`Network Error: ${err.message || err}`);
    } finally {
      setDemoLoading(false);
    }
  };

  const cleanupDemoDatabase = async () => {
    if (!confirm('Are you sure you want to purge all demo logs and incidents? This action is irreversible.')) return;
    setDemoLoading(true);
    setDemoResultMsg('');
    try {
      const token = localStorage.getItem('sf_token');
      const resp = await fetch(`${getApiBaseUrl()}/demo/cleanup`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await resp.json();
      if (resp.ok) {
        setDemoResultMsg('Success: Database purged. All incidents reset.');
        setIncidents([]);
        setSelectedIncident(null);
      } else {
        setDemoResultMsg(`Error: ${data.detail || 'Purge failed'}`);
      }
    } catch (err: any) {
      setDemoResultMsg(`Network Error: ${err.message || err}`);
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <SecuritySettingsView
      user={user}
      disableMFA={disableMFA}
      triggerMFASetup={triggerMFASetup}
      mfaStatusMsg={mfaStatusMsg}
      mfaSecretData={mfaSecretData}
      mfaSetupCode={mfaSetupCode}
      setMfaSetupCode={setMfaSetupCode}
      verifyAndEnableMFA={verifyAndEnableMFA}
      govMode={govMode}
      setGovMode={setGovMode}
      govMinConfidence={govMinConfidence}
      setGovMinConfidence={setGovMinConfidence}
      govRateLimit={govRateLimit}
      setGovRateLimit={setGovRateLimit}
      govMaxBlastRadius={govMaxBlastRadius}
      setGovMaxBlastRadius={setGovMaxBlastRadius}
      govRestrictedServices={govRestrictedServices}
      setGovRestrictedServices={setGovRestrictedServices}
      govLowRiskActions={govLowRiskActions}
      setGovLowRiskActions={setGovLowRiskActions}
      handleGovConfigSubmit={handleGovConfigSubmit}
      govLoading={govLoading}
      govMsg={govMsg}
      policies={policies}
      togglePolicyAction={togglePolicyAction}
      sessions={sessions}
      revokeSessionAction={revokeSessionAction}
      triggerDemoScenario={triggerDemoScenario}
      demoLoading={demoLoading}
      demoResultMsg={demoResultMsg}
      cleanupDemoDatabase={cleanupDemoDatabase}
    />
  );
}
