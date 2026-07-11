'use client';

import React, { useState, useEffect, useRef } from 'react';
import { api } from '../lib/api';
import { useWebSocket } from '../hooks/useWebSocket';
import { wsClient } from '../lib/websocket';
import {
  User,
  Incident,
  IncidentDetail,
  AuditEntry,
  ClusterTopology,
  PodInfo,
  NodeInfo,
  PromptTemplate,
  ObservabilitySummary,
  NavSection
} from '../types';

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

import {
  Shield,
  Activity,
  Server,
  FileSpreadsheet,
  Terminal,
  Cpu,
  Settings,
  Lock,
  RefreshCw,
  Play,
  CheckCircle,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Hash,
  Database,
  Eye,
  Sliders,
  Send,
  Loader2,
  ListFilter,
  Check,
  Power,
  FolderOpen,
  Upload,
  Trash2,
  Edit,
  BookOpen,
  Zap,
  BarChart2,
  Gauge,
  ListChecks,
  Clock,
  ChevronRight,
  ArrowRight,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  LineChart,
  Line,
  BarChart,
  Bar,
  Legend,
  ReferenceLine,
} from 'recharts';


export default function Home() {
  // ── Authentication State ─────────────────────────────────────
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState('admin@sentinelflow.ai');
  const [password, setPassword] = useState('admin123');
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaToken, setMfaToken] = useState('');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authView, setAuthView] = useState<'login' | 'register' | 'forgot' | 'reset' | 'reset_password_final'>('login');
  const [regFullName, setRegFullName] = useState('');
  const [regOrgId, setRegOrgId] = useState('');
  const [regRole, setRegRole] = useState('responder');
  const [resetToken, setResetToken] = useState('');
  const [resetSuccessMsg, setResetSuccessMsg] = useState('');
  const [sessions, setSessions] = useState<any[]>([]);

  // ── Application Navigation State ─────────────────────────────
  const [activeTab, setActiveTab] = useState<NavSection>('dashboard');

  // ── Data State ────────────────────────────────────────────────
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<IncidentDetail | null>(null);
  const explainabilityReport = (() => {
    if (!selectedIncident?.explainability_json) return null;
    try {
      return JSON.parse(selectedIncident.explainability_json);
    } catch (e) {
      return null;
    }
  })();
  const [topology, setTopology] = useState<ClusterTopology | null>(null);
  const [selectedPod, setSelectedPod] = useState<PodInfo | null>(null);
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);

  // ── WebSocket Real-Time Progress State ────────────────────────
  const [activeAgents, setActiveAgents] = useState<Record<number, {
    agent_name: string;
    status: string;
    progress: number;
    message: string;
    details: any;
    timestamp: string;
  }>>({});

  const [agentActivitiesLog, setAgentActivitiesLog] = useState<Record<number, Array<{
    agent_name: string;
    status: string;
    progress: number;
    message: string;
    details: any;
    timestamp: string;
  }>>>({});

  const [workflowProgress, setWorkflowProgress] = useState<Record<number, {
    current_step: number;
    total_steps: number;
    step_name: string;
    step_status: string;
    estimated_completion?: string;
    timestamp: string;
  }>>({});

  // ── WebSocket Subscriptions ──
  useWebSocket('AgentActivity', (data) => {
    console.debug("[WS] AgentActivity received:", data);
    const incId = data.incident_id;
    if (!incId) return;
    
    setActiveAgents(prev => ({
      ...prev,
      [incId]: {
        agent_name: data.agent_name,
        status: data.status,
        progress: data.progress,
        message: data.message,
        details: data.details,
        timestamp: data.timestamp
      }
    }));

    setAgentActivitiesLog(prev => {
      const currentLog = prev[incId] || [];
      if (currentLog.some(log => log.message === data.message && log.timestamp === data.timestamp)) {
        return prev;
      }
      return {
        ...prev,
        [incId]: [...currentLog, data]
      };
    });
  });

  useWebSocket('WorkflowProgress', (data) => {
    console.debug("[WS] WorkflowProgress received:", data);
    const incId = data.incident_id;
    if (!incId) return;

    setWorkflowProgress(prev => ({
      ...prev,
      [incId]: {
        current_step: data.current_step,
        total_steps: data.total_steps || 8,
        step_name: data.step_name,
        step_status: data.step_status,
        estimated_completion: data.estimated_completion,
        timestamp: data.timestamp
      }
    }));
  });

  useWebSocket('WorkflowStep', (data) => {
    if (selectedIncident && selectedIncident.id === data.incident_id) {
      api.getIncidentDetail(selectedIncident.id).then(setSelectedIncident).catch(console.error);
    }
  });

  useWebSocket('IncidentUpdate', (data) => {
    api.getIncidents().then(res => setIncidents(res.incidents)).catch(console.error);
    if (selectedIncident && selectedIncident.id === data.incident_id) {
      api.getIncidentDetail(selectedIncident.id).then(setSelectedIncident).catch(console.error);
    }
  });

  // ── Phase 57: Live Cluster Metrics Updates ─────────────────────
  useWebSocket('LiveMetricsUpdate', (data) => {
    console.debug("[WS] LiveMetricsUpdate received:", data.timestamp);
    setLiveMetrics(data);
    if (data.time_series && data.time_series.length > 0) {
      setMetricsHistory(data.time_series);
    }
    if (data.annotations && data.annotations.length > 0) {
      setMetricsAnnotations(data.annotations);
    }
  });

  // ── Phase 58: Playbook Progress Updates ────────────────────────
  useWebSocket('PlaybookProgress', (data) => {
    console.debug("[WS] PlaybookProgress received:", data.execution_id);
    setPlaybookExecutions(prev => {
      const idx = prev.findIndex(e => e.execution_id === data.execution_id);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = data;
        return updated;
      }
      return [data, ...prev];
    });
    if (selectedExecution?.execution_id === data.execution_id) {
      setSelectedExecution(data);
    }
  });

  const [obsSummary, setObsSummary] = useState<ObservabilitySummary | null>(null);
  const [obsTraces, setObsTraces] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);


  // ── Executive Dashboard State ────────────────────────────────
  const [executiveMetrics, setExecutiveMetrics] = useState<any>(null);
  const [selectedExecutiveIncident, setSelectedExecutiveIncident] = useState<Incident | null>(null);
  const [executiveReport, setExecutiveReport] = useState<any>(null);
  const [executiveReportLoading, setExecutiveReportLoading] = useState(false);

  // ── Interactive UI State ─────────────────────────────────────
  const [commandInput, setCommandInput] = useState('');
  const [commandLoading, setCommandLoading] = useState(false);
  const [commandResult, setCommandResult] = useState<any>(null);
  const [ragQuery, setRagQuery] = useState('');
  const [ragResults, setRagResults] = useState<any[]>([]);
  const [ragLoading, setRagLoading] = useState(false);
  const [mfaSecretData, setMfaSecretData] = useState<any>(null);
  const [mfaSetupCode, setMfaSetupCode] = useState('');
  const [mfaStatusMsg, setMfaStatusMsg] = useState('');
  const [podLogStream, setPodLogStream] = useState<string[]>([]);
  const [logIntervalId, setLogIntervalId] = useState<any>(null);
  const [slackSimulatorMsg, setSlackSimulatorMsg] = useState('');
  const [slackSimulatorLoading, setSlackSimulatorLoading] = useState(false);
  
  // ── SRE Inspector & Replay Engine UI Hook States ────────────
  const [inspectorTab, setInspectorTab] = useState<'timeline' | 'simulation' | 'options' | 'runbooks' | 'graph' | 'replay' | 'attack'>('timeline');
  const [replayEvents, setReplayEvents] = useState<any[]>([]);
  const [isPlayingReplay, setIsPlayingReplay] = useState(false);
  const [replayIndex, setReplayIndex] = useState(-1);
  const [replaySpeed, setReplaySpeed] = useState<1 | 5 | 10>(1);
  const [replayIntervalId, setReplayIntervalId] = useState<any>(null);
  const [simulationData, setSimulationData] = useState<any>(null);
  const [remediationOptions, setRemediationOptions] = useState<any[]>([]);
  const [decisionGraph, setDecisionGraph] = useState<any>(null);
  const [runbooks, setRunbooks] = useState<any[]>([]);
  const [runbookFeedbackMsg, setRunbookFeedbackMsg] = useState('');
  const [simulationLoading, setSimulationLoading] = useState(false);

  // ── Knowledge Base UI States ──────────────────────────────
  const [knowledgeDocs, setKnowledgeDocs] = useState<any[]>([]);
  const [kbSearchQuery, setKbSearchQuery] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [kbUploadTitle, setKbUploadTitle] = useState('');
  const [kbUploadCategory, setKbUploadCategory] = useState('runbooks');
  const [kbUploadSubcategory, setKbUploadSubcategory] = useState('kubernetes');
  const [kbUploadTags, setKbUploadTags] = useState('');
  const [kbUploadFile, setKbUploadFile] = useState<File | null>(null);
  const [kbUploadLoading, setKbUploadLoading] = useState(false);
  const [kbEditingContent, setKbEditingContent] = useState('');
  const [kbEditingVersion, setKbEditingVersion] = useState('');
  const [kbIsEditing, setKbIsEditing] = useState(false);

  // ── Attack Graph UI States ────────────────────────────────
  const [attackGraph, setAttackGraph] = useState<any>(null);
  const [selectedAttackNode, setSelectedAttackNode] = useState<any>(null);
  const [attackGraphLoading, setAttackGraphLoading] = useState(false);
  const [attackPhaseFilter, setAttackPhaseFilter] = useState('all');

  // ── Governance Configuration UI States ───────────────────
  const [govMode, setGovMode] = useState('MANUAL');
  const [govRateLimit, setGovRateLimit] = useState(5);
  const [govMinConfidence, setGovMinConfidence] = useState(90);
  const [govMaxBlastRadius, setGovMaxBlastRadius] = useState(10);
  const [govRestrictedServices, setGovRestrictedServices] = useState('payment');
  const [govLowRiskActions, setGovLowRiskActions] = useState('restart_pod,scale_service,rollout_restart');
  const [policies, setPolicies] = useState<any[]>([]);
  const [govLoading, setGovLoading] = useState(false);
  const [govMsg, setGovMsg] = useState('');

  // ── Demo & Telemetry Simulator State ─────────────────────────
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoResultMsg, setDemoResultMsg] = useState('');

  // ── Phase 57: Live Cluster Metrics Dashboard State ───────────
  const [liveMetrics, setLiveMetrics] = useState<any>(null);
  const [metricsHistory, setMetricsHistory] = useState<any[]>([]);
  const [metricsAnnotations, setMetricsAnnotations] = useState<any[]>([]);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [selectedMetricService, setSelectedMetricService] = useState<string | null>(null);

  // ── Phase 58: Playbook Execution Tracking State ──────────────
  const [playbookExecutions, setPlaybookExecutions] = useState<any[]>([]);
  const [selectedExecution, setSelectedExecution] = useState<any | null>(null);
  const [playbookName, setPlaybookName] = useState('Standard Kubernetes Recovery Playbook');
  const [playbookTargetIncident, setPlaybookTargetIncident] = useState<number | null>(null);
  const [playbookLoading, setPlaybookLoading] = useState(false);
  const [playbookMsg, setPlaybookMsg] = useState('');


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

  // ── Global Status State ──────────────────────────────────────
  const [globalStatus, setGlobalStatus] = useState<'SECURE' | 'THREAT_DETECTED' | 'DISRUPTED'>('SECURE');
  const [serverHealth, setServerHealth] = useState<any>(null);
  const [activeIncidentCount, setActiveIncidentCount] = useState(0);
  const [circuitBreakers, setCircuitBreakers] = useState<any>({});

  // ── References ───────────────────────────────────────────────
  const logTerminalEndRef = useRef<HTMLDivElement>(null);

  // ── Initialize App State ─────────────────────────────────────
  useEffect(() => {
    setIsLoggedIn(api.isLoggedIn);
    if (api.isLoggedIn) {
      const stored = localStorage.getItem('sf_user');
      if (stored) setUser(JSON.parse(stored));
    }

    const handleAuthRequired = () => {
      setIsLoggedIn(false);
      setUser(null);
    };

    window.addEventListener('auth_required', handleAuthRequired);
    return () => window.removeEventListener('auth_required', handleAuthRequired);
  }, []);

  // ── Poll Data Periodically ────────────────────────────────────
  useEffect(() => {
    if (!isLoggedIn) return;

    const fetchData = async () => {
      try {
        // Health & Status
        const health = await fetch(`${getApiBaseUrl().replace('/api/v1', '')}/health`).then(r => r.json()).catch(() => null);
        setServerHealth(health);

        // Circuit Breakers
        const cbData = await fetch(`${getApiBaseUrl()}/ops/circuit-breakers`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('sf_token')}` }
        }).then(r => r.json()).catch(() => ({}));
        setCircuitBreakers(cbData);

        // Incidents
        const incData = await api.getIncidents();
        setIncidents(incData.incidents);
        const active = incData.incidents.filter(i => ['DETECTED', 'ANALYZING', 'PENDING_APPROVAL', 'APPROVED', 'EXECUTING'].includes(i.status));
        setActiveIncidentCount(active.length);
        setGlobalStatus(active.length > 0 ? 'THREAT_DETECTED' : 'SECURE');

        // Topology
        const topo = await api.getTopology();
        setTopology(topo);

        // Audit Trail
        const audit = await api.getAuditTrail();
        setAuditEntries(audit.audit_entries);

        // Prompts
        const pr = await api.getPrompts();
        setPrompts(pr.templates);

        // Observability
        const obs = await api.getObservabilitySummary();
        setObsSummary(obs);

        const traces = await api.getObservabilityTraces();
        setObsTraces(traces.traces);

        // Notifications
        const notifs = await fetch(`${getApiBaseUrl()}/integrations/notifications`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('sf_token')}` }
        }).then(r => r.json()).catch(() => ({ notifications: [] }));
        setNotifications(notifs.notifications || []);

        // Executive Metrics
        try {
          const execMet = await api.getExecutiveMetrics();
          setExecutiveMetrics(execMet);
        } catch (err) {
          console.error('Error fetching executive metrics:', err);
        }

      } catch (err) {
        console.error('Error polling dashboard stats:', err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 6000);
    return () => clearInterval(interval);
  }, [isLoggedIn]);

  // ── Secondary Fetch for Selected Item Details ────────────────
  useEffect(() => {
    if (!selectedIncident) return;
    const fetchDetail = async () => {
      try {
        const detail = await api.getIncidentDetail(selectedIncident.id);
        setSelectedIncident(detail);
      } catch (err) {
        console.error('Error details:', err);
      }
    };
    const interval = setInterval(fetchDetail, 3000);
    return () => clearInterval(interval);
  }, [selectedIncident]);
  
  // ── Dynamic WebSocket Incident Channel Subscription ──────────
  useEffect(() => {
    if (!selectedIncident?.id) return;
    const unsubscribe = wsClient.subscribe(`incident:${selectedIncident.id}`, () => {});
    return () => {
      unsubscribe();
    };
  }, [selectedIncident?.id]);

  // ── SRE Dynamic Inspector Fetch useEffect ───────────────────
  useEffect(() => {
    if (!selectedIncident) return;
    
    const fetchInspectorData = async () => {
      try {
        if (inspectorTab === 'simulation') {
          setSimulationLoading(true);
          const sim = await api.getSimulation(selectedIncident.id);
          setSimulationData(sim);
          setSimulationLoading(false);
        } else if (inspectorTab === 'options') {
          const opts = await api.getRemediationOptions(selectedIncident.id);
          setRemediationOptions(opts);
        } else if (inspectorTab === 'runbooks') {
          const rbs = await api.getRunbooks(selectedIncident.id);
          setRunbooks(rbs);
        } else if (inspectorTab === 'graph') {
          const g = await api.getDecisionGraph(selectedIncident.id);
          setDecisionGraph(g);
        } else if (inspectorTab === 'replay') {
          const stream = await api.getReplay(selectedIncident.id);
          setReplayEvents(stream);
        } else if (inspectorTab === 'attack') {
          setAttackGraphLoading(true);
          const ag = await api.getAttackGraph(selectedIncident.id);
          setAttackGraph(ag);
          setSelectedAttackNode(ag?.nodes?.[0] || null);
          setAttackGraphLoading(false);
        }
      } catch (err) {
        console.error('Error fetching SRE inspector data:', err);
        setSimulationLoading(false);
      }
    };

    fetchInspectorData();
  }, [selectedIncident?.id, inspectorTab]);

  // ── SRE Chronological Replay Controller Loop ──────────────────
  useEffect(() => {
    if (!isPlayingReplay) {
      if (replayIntervalId) {
        clearInterval(replayIntervalId);
        setReplayIntervalId(null);
      }
      return;
    }

    const intervalTime = 2000 / replaySpeed;
    const interval = setInterval(() => {
      setReplayIndex((prevIndex) => {
        if (prevIndex >= replayEvents.length - 1) {
          setIsPlayingReplay(false);
          clearInterval(interval);
          return prevIndex;
        }
        return prevIndex + 1;
      });
    }, intervalTime);

    setReplayIntervalId(interval);
    return () => clearInterval(interval);
  }, [isPlayingReplay, replaySpeed, replayEvents.length]);

  // ── Executive Report Fetch ────────────────────────────────────
  useEffect(() => {
    if (!selectedExecutiveIncident) {
      setExecutiveReport(null);
      return;
    }
    const fetchReport = async () => {
      setExecutiveReportLoading(true);
      try {
        const report = await api.getExecutiveReport(selectedExecutiveIncident.id);
        setExecutiveReport(report);
      } catch (err) {
        console.error('Error fetching executive report:', err);
      } finally {
        setExecutiveReportLoading(false);
      }
    };
    fetchReport();
  }, [selectedExecutiveIncident]);

  // ── Scroll to End of Logs ────────────────────────────────────
  useEffect(() => {
    if (logTerminalEndRef.current) {
      logTerminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [podLogStream]);

  // ── Knowledge Base Fetch & Helper Functions ─────────────────
  const fetchKbDocuments = async () => {
    try {
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/documents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setKnowledgeDocs(data);
      }
    } catch (err) {
      console.error('Fetch docs error:', err);
    }
  };

  const fetchGovConfig = async () => {
    try {
      const apiBase = getApiBaseUrl();
      const rootUrl = apiBase.replace('/api/v1', '');
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${rootUrl}/execution-config`, {
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

  const togglePolicyAction = async (id: number) => {
    try {
      await api.togglePolicy(id);
      fetchPolicies();
    } catch (err) {
      console.error('Toggle policy error:', err);
    }
  };


  const handleGovConfigSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGovLoading(true);
    setGovMsg('');
    try {
      const apiBase = getApiBaseUrl();
      const rootUrl = apiBase.replace('/api/v1', '');
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${rootUrl}/execution-config`, {
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
      setGovMsg(`Error: ${err.message || 'Network error'}`);
    } finally {
      setGovLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'knowledge') {
      fetchKbDocuments();
    } else if (activeTab === 'settings') {
      fetchGovConfig();
      fetchPolicies();
    } else if (activeTab === 'metrics') {
      fetchLiveMetrics();
    } else if (activeTab === 'playbooks') {
      fetchPlaybookExecutions();
    }
  }, [activeTab]);

  // ── Phase 57: Fetch Live Metrics on demand ───────────────────
  const fetchLiveMetrics = async () => {
    setMetricsLoading(true);
    try {
      const token = localStorage.getItem('sf_token');
      const apiBase = getApiBaseUrl();
      const res = await fetch(`${apiBase}/ops/live-metrics`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setLiveMetrics(data);
        if (data.time_series) setMetricsHistory(data.time_series);
        if (data.annotations) setMetricsAnnotations(data.annotations);
      }
    } catch (err) {
      console.error('Fetch live metrics error:', err);
    } finally {
      setMetricsLoading(false);
    }
  };

  // ── Phase 58: Fetch Playbook Executions ──────────────────────
  const fetchPlaybookExecutions = async () => {
    try {
      const token = localStorage.getItem('sf_token');
      const apiBase = getApiBaseUrl();
      const res = await fetch(`${apiBase}/ops/playbook-executions`, {
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
      const res = await fetch(
        `${apiBase}/ops/playbook-executions?incident_id=${playbookTargetIncident}&playbook_name=${encodeURIComponent(playbookName)}`,
        { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } }
      );
      if (res.ok) {
        const record = await res.json();
        setSelectedExecution(record);
        setPlaybookExecutions((prev: any[]) => [record, ...prev]);
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
          `${apiBase}/ops/playbook-executions/${execId}/advance?success=true&log_message=Step%20completed%20automatically`,
          { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } }
        );
        if (res.ok) {
          const updated = await res.json();
          setPlaybookExecutions((prev: any[]) => {
            const idx = prev.findIndex((e: any) => e.execution_id === execId);
            if (idx >= 0) { const arr = [...prev]; arr[idx] = updated; return arr; }
            return prev;
          });
          setSelectedExecution((prev: any) => prev?.execution_id === execId ? updated : prev);
          if (updated.status === 'RUNNING') {
            simulatePlaybookAdvance(execId, step + 1, totalSteps);
          }
        }
      } catch (e) { console.error('Advance step error:', e); }
    }, 2000 + Math.random() * 1500);
  };

  const handleCancelExecution = async (execId: string) => {
    try {
      const token = localStorage.getItem('sf_token');
      const apiBase = getApiBaseUrl();
      const res = await fetch(`${apiBase}/ops/playbook-executions/${execId}/cancel`, {
        method: 'POST', headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const updated = await res.json();
        setPlaybookExecutions((prev: any[]) => {
          const idx = prev.findIndex((e: any) => e.execution_id === execId);
          if (idx >= 0) { const arr = [...prev]; arr[idx] = updated; return arr; }
          return prev;
        });
        if (selectedExecution?.execution_id === execId) setSelectedExecution(updated);
      }
    } catch (e) { console.error('Cancel execution error:', e); }
  };

  const handleKbUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kbUploadFile) return;
    setKbUploadLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', kbUploadFile);
      formData.append('title', kbUploadTitle);
      formData.append('category', kbUploadCategory);
      formData.append('subcategory', kbUploadSubcategory);
      formData.append('tags', kbUploadTags);

      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/documents`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      if (res.ok) {
        setKbUploadTitle('');
        setKbUploadTags('');
        setKbUploadFile(null);
        fetchKbDocuments();
      }
    } catch (err) {
      console.error('Upload document error:', err);
    } finally {
      setKbUploadLoading(false);
    }
  };

  const handleKbSearch = async () => {
    if (!kbSearchQuery) {
      fetchKbDocuments();
      return;
    }
    try {
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/search?q=${encodeURIComponent(kbSearchQuery)}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const hits = await res.json();
        const formatted = hits.map((h: any) => ({
          id: h.id,
          title: h.title,
          filename: 'RAG Chunk Match',
          category: h.category,
          subcategory: 'Search Match',
          tags: h.tags.join(','),
          version: '1.0.0',
          author: 'Vector Store',
          content: h.content,
          status: 'approved',
          usage_count: 0,
          success_count: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }));
        setKnowledgeDocs(formatted);
      }
    } catch (err) {
      console.error('KB Search error:', err);
    }
  };

  const handleKbApprove = async (docId: number) => {
    try {
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/documents/${docId}/approve`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchKbDocuments();
        if (selectedDoc && selectedDoc.id === docId) {
          setSelectedDoc({ ...selectedDoc, status: 'approved' });
        }
      }
    } catch (err) {
      console.error('Approve doc error:', err);
    }
  };

  const handleKbArchive = async (docId: number) => {
    try {
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/documents/${docId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchKbDocuments();
        setSelectedDoc(null);
      }
    } catch (err) {
      console.error('Archive doc error:', err);
    }
  };

  const handleKbEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDoc) return;
    try {
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/documents/${selectedDoc.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: selectedDoc.title,
          category: selectedDoc.category,
          subcategory: selectedDoc.subcategory,
          tags: selectedDoc.tags,
          content: kbEditingContent,
          version: kbEditingVersion
        })
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedDoc(updated);
        setKbIsEditing(false);
        fetchKbDocuments();
      }
    } catch (err) {
      console.error('Update doc error:', err);
    }
  };

  // ── Handle Simulated Logs for Pods ────────────────────────────
  const selectPodForInspection = (pod: PodInfo) => {
    setSelectedPod(pod);
    if (logIntervalId) clearInterval(logIntervalId);

    // Initial logs seed
    const initialLogs = [
      `[INFO] Starting container ${pod.service}...`,
      `[INFO] Service account mounted successfully.`,
      `[INFO] Listening on port 8080. Health probe status: 200 OK`,
    ];
    setPodLogStream(initialLogs);

    const intId = setInterval(() => {
      const logs = [
        `[INFO] Incoming request: GET /healthz (User-Agent: kube-probe)`,
        `[INFO] Connection accepted from client: 10.244.1.${randomInt(2, 254)}`,
        `[DEBUG] Database transaction completed in ${randomInt(1, 15)}ms`,
        pod.cpu_usage > 75 ? `[WARN] CPU threshold warn: usage level at ${pod.cpu_usage}%` : `[DEBUG] CPU utilization healthy: ${pod.cpu_usage}%`,
        pod.status === 'CrashLoopBackOff' ? `[CRITICAL] Runtime error occurred: OutOfMemoryException` : null
      ].filter(Boolean) as string[];

      setPodLogStream(prev => [...prev, ...logs].slice(-50)); // cap at 50 logs
    }, 2000);

    setLogIntervalId(intId);
  };

  const randomInt = (min: number, max: number) => Math.floor(Math.random() * (max - min + 1)) + min;

  // ── Clean Up Log Timers ─────────────────────────────────────
  useEffect(() => {
    return () => {
      if (logIntervalId) clearInterval(logIntervalId);
    };
  }, [logIntervalId]);

  // ── Handle Login ─────────────────────────────────────────────
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    setAuthLoading(true);

    try {
      const res = await api.login(email, password, mfaToken || undefined);
      if (res.mfaRequired) {
        setMfaRequired(true);
        setAuthLoading(false);
      } else {
        setIsLoggedIn(true);
        const stored = localStorage.getItem('sf_user');
        if (stored) setUser(JSON.parse(stored));
        setMfaRequired(false);
        setMfaToken('');
        setAuthLoading(false);
      }
    } catch (err: any) {
      setAuthLoading(false);
      setAuthError(err.data?.detail || 'Authentication failed. Please verify credentials.');
    }
  };

  // ── Handle Log Out ───────────────────────────────────────────
  const handleLogout = async () => {
    await api.logout();
    setIsLoggedIn(false);
    setUser(null);
    setMfaRequired(false);
    setMfaToken('');
  };

  // ── Handle Registration ──────────────────────────────────────
  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    setResetSuccessMsg('');
    setAuthLoading(true);
    try {
      const res = await api.register({
        email,
        password,
        full_name: regFullName,
        role: regRole,
        organization_id: regOrgId || undefined,
      });
      setResetSuccessMsg(`Registration successful! Verification token generated: ${res.verification_token}.`);
      setResetToken(res.verification_token);
      setAuthView('reset');
      setAuthLoading(false);
    } catch (err: any) {
      setAuthLoading(false);
      setAuthError(err.data?.detail || 'Registration failed.');
    }
  };

  // ── Handle Email Verification ────────────────────────────────
  const handleVerifyEmail = async () => {
    setAuthError('');
    setResetSuccessMsg('');
    setAuthLoading(true);
    try {
      await api.verifyEmail(resetToken);
      setResetSuccessMsg('Email verified successfully! You can now login.');
      setAuthView('login');
      setAuthLoading(false);
    } catch (err: any) {
      setAuthLoading(false);
      setAuthError(err.data?.detail || 'Verification failed.');
    }
  };

  // ── Handle Forgot Password ──────────────────────────────────
  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    setResetSuccessMsg('');
    setAuthLoading(true);
    try {
      const res = await api.forgotPassword(email);
      if (res.reset_token) {
        setResetSuccessMsg(`Reset token generated: ${res.reset_token}`);
        setResetToken(res.reset_token);
        setAuthView('reset');
      } else {
        setResetSuccessMsg(res.message || 'Reset link generated.');
      }
      setAuthLoading(false);
    } catch (err: any) {
      setAuthLoading(false);
      setAuthError(err.data?.detail || 'Password reset request failed.');
    }
  };

  // ── Handle Reset Password ────────────────────────────────────
  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    setResetSuccessMsg('');
    setAuthLoading(true);
    try {
      await api.resetPassword({
        token: resetToken,
        new_password: password,
      });
      setResetSuccessMsg('Password reset successfully! Please login with your new passphrase.');
      setAuthView('login');
      setAuthLoading(false);
    } catch (err: any) {
      setAuthLoading(false);
      setAuthError(err.data?.detail || 'Password reset failed.');
    }
  };

  // ── Fetch active sessions when Settings tab is selected ──────
  useEffect(() => {
    if (activeTab === 'settings' && isLoggedIn) {
      const fetchSessions = async () => {
        try {
          const list = await api.getSessions();
          setSessions(list);
        } catch (err) {
          console.error('Failed to fetch sessions:', err);
        }
      };
      fetchSessions();
    }
  }, [activeTab, isLoggedIn]);

  const revokeSessionAction = async (sessionId: number) => {
    try {
      await api.revokeSession(sessionId);
      const list = await api.getSessions();
      setSessions(list);
    } catch (err) {
      alert('Failed to revoke session.');
    }
  };

  // ── Verify & Enable MFA Setup ────────────────────────────────
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
      const data = await api.enableMFA(mfaSetupCode);
      setMfaStatusMsg('MFA configuration verified. Multi-factor guard enabled!');
      setMfaSecretData(null);
      setMfaSetupCode('');
      // Sync user profile state
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

  // ── Guarded Command Execution Console ────────────────────────
  const submitGuardedCommand = async () => {
    if (!commandInput.trim()) return;
    setCommandLoading(true);
    setCommandResult(null);

    try {
      const res = await api.executeCommand(commandInput);
      setCommandResult(res);
      setCommandLoading(false);
      // Reload Audit entries
      const audit = await api.getAuditTrail();
      setAuditEntries(audit.audit_entries);
    } catch (err: any) {
      setCommandLoading(false);
      setCommandResult({
        status: 'ERROR',
        risk_score: 1.0,
        risk_assessment: err.data?.detail || 'Command failed processing safety thresholds.',
      });
    }
  };

  // ── RAG Similarity Search Tool ──────────────────────────────
  const runRAGSearch = async () => {
    if (!ragQuery.trim()) return;
    setRagLoading(true);

    try {
      const res = await api.ragSearch({ query: ragQuery, limit: 3 });
      setRagResults(res.results);
      setRagLoading(false);
    } catch (err) {
      setRagLoading(false);
    }
  };

  // ── Slack Simulator Action Trigger ───────────────────────────
  const triggerSlackApprovalAction = async (incidentId: number, action: 'approve' | 'reject') => {
    setSlackSimulatorLoading(true);
    setSlackSimulatorMsg('');

    try {
      const res = await fetch(`${getApiBaseUrl()}/integrations/slack/webhook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          incident_id: incidentId,
          action: action,
          text: `Interactive click: User triggered ${action} command flow.`
        }),
      });

      const body = await res.json();
      setSlackSimulatorMsg(body.message || body.detail || 'Webhook processed successfully.');
      setSlackSimulatorLoading(false);

      // Refresh incident state
      const refreshed = await api.getIncidentDetail(incidentId);
      setSelectedIncident(refreshed);
    } catch (err) {
      setSlackSimulatorLoading(false);
      setSlackSimulatorMsg('Failed to deliver webhook payload to integrations controller.');
    }
  };

  // ── Audit Ledger Validation ──────────────────────────────────
  const [ledgerValidating, setLedgerValidating] = useState(false);
  const [ledgerValidationResult, setLedgerValidationResult] = useState<any>(null);

  const verifyAuditLedger = async () => {
    setLedgerValidating(true);
    setLedgerValidationResult(null);
    try {
      const res = await api.verifyAuditTrail();
      setLedgerValidationResult(res);
      setLedgerValidating(false);
    } catch (err) {
      setLedgerValidating(false);
      setLedgerValidationResult({ valid: false, message: 'Ledger verification endpoint failed.' });
    }
  };

  const archiveAuditLedger = async () => {
    try {
      const res = await api.archiveAuditTrail();
      alert(`Ledger successfully archived!\nS3 URI: ${res.s3_uri}\nEntries: ${res.entry_count}`);
    } catch (err) {
      alert('Failed to archive ledger.');
    }
  };

  // ── Incident Resolution Action buttons ───────────────────────
  const approveIncidentAction = async (id: number) => {
    try {
      await api.approveIncident(id);
      const updated = await api.getIncidentDetail(id);
      setSelectedIncident(updated);
    } catch (err) {
      alert('Approval failed.');
    }
  };

  const rejectIncidentAction = async (id: number) => {
    try {
      await api.rejectIncident(id);
      const updated = await api.getIncidentDetail(id);
      setSelectedIncident(updated);
    } catch (err) {
      alert('Rejection failed.');
    }
  };

  // ── Render Loading Screen or Login Portal ───────────────────
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center relative overflow-hidden font-sans">
        {/* Glow Effects */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full filter blur-[100px] pointer-events-none"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full filter blur-[100px] pointer-events-none"></div>

        <div className="w-full max-w-md p-8 glass rounded-2xl border border-white/5 animate-fade-in relative z-10">
          <div className="flex justify-center mb-6">
            <div className="p-3 bg-emerald-500/10 rounded-2xl border border-emerald-500/20">
              <Shield className="w-10 h-10 text-[#00ff88]" />
            </div>
          </div>

          <h2 className="text-2xl font-bold text-center text-slate-100 tracking-wide mb-1">
            SENTINELFLOW AI
          </h2>
          <p className="text-sm text-center text-slate-400 mb-6">
            Autonomous K8s SecOps & Telemetry Monitor
          </p>

          {resetSuccessMsg && (
            <div className="mb-5 p-3.5 bg-emerald-950/25 border border-emerald-500/20 rounded-xl text-xs text-[#00ff88] leading-relaxed">
              {resetSuccessMsg}
            </div>
          )}

          {/* VIEW: LOGIN */}
          {authView === 'login' && (
            <form onSubmit={handleLoginSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Identity (Email)
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all placeholder:text-slate-600 text-sm"
                  placeholder="identity@sentinelflow.ai"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Passphrase
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all placeholder:text-slate-600 text-sm"
                  placeholder="••••••••"
                />
              </div>

              {mfaRequired && (
                <div className="p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-xl animate-fade-in">
                  <label className="block text-xs font-semibold text-[#00ff88] uppercase tracking-wider mb-2 flex items-center gap-2">
                    <Lock className="w-3.5 h-3.5" /> Google Authenticator Token (MFA)
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    required
                    value={mfaToken}
                    onChange={e => setMfaToken(e.target.value)}
                    className="w-full px-4 py-3 bg-[#0d111a] border border-[#00ff88]/30 rounded-xl focus:outline-none focus:border-emerald-400 text-center tracking-widest text-[#00ff88] font-mono text-lg"
                    placeholder="000000"
                  />
                  <p className="text-[10px] text-slate-400 mt-2">
                    Dual-Factor challenge active. Key in the 6-digit verification code.
                  </p>
                </div>
              )}

              {authError && (
                <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                  <span>{authError}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-900 font-bold rounded-xl transition-all shadow-lg hover:shadow-emerald-500/10 active:scale-[0.98] flex items-center justify-center gap-2 text-sm"
              >
                {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'INJECT CREDENTIALS'}
              </button>

              <div className="flex justify-between items-center text-xs text-slate-400 pt-2">
                <button type="button" onClick={() => setAuthView('register')} className="hover:text-emerald-400 transition-colors">
                  Create account
                </button>
                <button type="button" onClick={() => setAuthView('forgot')} className="hover:text-emerald-400 transition-colors">
                  Forgot passphrase?
                </button>
              </div>
            </form>
          )}

          {/* VIEW: REGISTER */}
          {authView === 'register' && (
            <form onSubmit={handleRegisterSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={regFullName}
                  onChange={e => setRegFullName(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                  placeholder="Jane Doe"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                  placeholder="identity@sentinelflow.ai"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Organization ID (Optional)
                </label>
                <input
                  type="text"
                  value={regOrgId}
                  onChange={e => setRegOrgId(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                  placeholder="org-123"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Security Role
                </label>
                <select
                  value={regRole}
                  onChange={e => setRegRole(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                >
                  <option value="responder">Responder (SecOps Engineer)</option>
                  <option value="executive">Executive (Read & Approve)</option>
                  <option value="viewer">Viewer (Read-only)</option>
                  <option value="admin">Administrator</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Passphrase
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                  placeholder="••••••••"
                />
              </div>

              {authError && (
                <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
                  <span>{authError}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-900 font-bold rounded-xl transition-all shadow-lg text-sm"
              >
                {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'REGISTER IDENTITY'}
              </button>

              <div className="text-center text-xs text-slate-400 pt-2">
                <button type="button" onClick={() => setAuthView('login')} className="hover:text-emerald-400 transition-colors">
                  Already have an account? Sign in
                </button>
              </div>
            </form>
          )}

          {/* VIEW: FORGOT PASSWORD */}
          {authView === 'forgot' && (
            <form onSubmit={handleForgotPasswordSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Registered Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                  placeholder="identity@sentinelflow.ai"
                />
              </div>

              {authError && (
                <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
                  <span>{authError}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-900 font-bold rounded-xl transition-all shadow-lg text-sm"
              >
                {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'REQUEST RESET TOKEN'}
              </button>

              <div className="text-center text-xs text-slate-400 pt-2 flex justify-between">
                <button type="button" onClick={() => setAuthView('login')} className="hover:text-emerald-400 transition-colors">
                  Back to login
                </button>
                <button type="button" onClick={() => setAuthView('reset')} className="hover:text-emerald-400 transition-colors">
                  Enter verification token
                </button>
              </div>
            </form>
          )}

          {/* VIEW: TOKEN RESET / VERIFICATION PORTAL */}
          {authView === 'reset' && (
            <div className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Verification / Reset Token
                </label>
                <textarea
                  rows={3}
                  required
                  value={resetToken}
                  onChange={e => setResetToken(e.target.value)}
                  className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-xs font-mono"
                  placeholder="Paste verification or password reset JWT token here"
                />
              </div>

              {authError && (
                <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
                  <span>{authError}</span>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleVerifyEmail}
                  disabled={authLoading}
                  className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 text-slate-900 font-bold rounded-xl transition-all text-xs font-bold"
                >
                  VERIFY EMAIL
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAuthView('reset_password_final');
                  }}
                  className="flex-1 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 font-bold rounded-xl transition-all text-xs font-bold"
                >
                  RESET PASSPHRASE
                </button>
              </div>

              <div className="text-center text-xs text-slate-400 pt-2">
                <button type="button" onClick={() => setAuthView('login')} className="hover:text-emerald-400 transition-colors">
                  Back to login
                </button>
              </div>
            </div>
          )}

          {/* VIEW: RESET PASSWORD FINAL STEP */}
          {authView === 'reset_password_final' && (
            <form onSubmit={handleResetPasswordSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  New Passphrase
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                  placeholder="••••••••"
                />
              </div>

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-900 font-bold rounded-xl transition-all shadow-lg text-sm"
              >
                {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'CONFIRM RESET'}
              </button>

              <div className="text-center text-xs text-slate-400 pt-2">
                <button type="button" onClick={() => setAuthView('login')} className="hover:text-emerald-400 transition-colors">
                  Cancel
                </button>
              </div>
            </form>
          )}

        </div>
      </div>
    );
  }

  // ── Prepare Telemetry Plot Data ──────────────────────────────
  const mockChartData = topology?.pods?.filter(Boolean).slice(0, 5).map((pod, i) => ({
    name: (pod.name || `pod-${i}`).split('-')[0],
    cpu: pod.cpu_usage,
    memory: pod.memory_usage,
    latency: pod.cpu_usage * 2 + 10,
  })) || [];

  return (
    <div className="min-h-screen bg-[#0a0e17] flex flex-col font-sans text-slate-300">
      {/* Top Banner Status */}
      <header className="border-b border-white/5 bg-[#111827] px-6 py-4 flex items-center justify-between z-20">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
            <Shield className="w-6 h-6 text-[#00ff88]" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-200 tracking-wider">SENTINELFLOW AI</h1>
            <p className="text-xs text-slate-500">Autonomous Cyber-Defense & Autopilot K8s Node Exporter</p>
          </div>
        </div>

        {/* Global Status Banner */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${globalStatus === 'SECURE' ? 'bg-[#00ff88]' : 'bg-[#ff3366]'}`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${globalStatus === 'SECURE' ? 'bg-[#00ff88]' : 'bg-[#ff3366]'}`}></span>
            </div>
            <span className="text-xs uppercase font-bold tracking-widest">
              STATUS:{' '}
              <span className={globalStatus === 'SECURE' ? 'text-[#00ff88]' : 'text-[#ff3366]'}>
                {globalStatus.replace('_', ' ')}
              </span>
            </span>
          </div>

          <div className="h-6 w-[1px] bg-white/10"></div>

          <div className="flex items-center gap-2.5">
            <span className="text-xs text-slate-500">USER:</span>
            <span className="text-xs font-mono bg-white/5 px-2.5 py-1 rounded text-slate-300">
              {user?.email} ({user?.role})
            </span>
          </div>

          <button
            onClick={handleLogout}
            className="p-2 text-slate-400 hover:text-rose-400 bg-white/5 hover:bg-rose-500/10 border border-white/5 rounded-lg transition-all"
            title="Log Out"
          >
            <Power className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Panel Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Nav */}
        <nav className="w-64 bg-[#111827] border-r border-white/5 p-4 space-y-2 flex flex-col justify-between">
          <div className="space-y-1">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${activeTab === 'dashboard' ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]' : 'hover:bg-white/5 text-slate-400'}`}
            >
              <Activity className="w-4 h-4" /> Cyber Dashboard
            </button>

            <button
              onClick={() => setActiveTab('executive')}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${activeTab === 'executive' ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]' : 'hover:bg-white/5 text-slate-400'}`}
            >
              <Shield className="w-4 h-4" /> Executive Dashboard
            </button>

            <button
              onClick={() => setActiveTab('incidents')}
              className={`w-full flex items-center justify-between px-4 py-3 text-sm font-semibold rounded-xl transition-all ${activeTab === 'incidents' ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]' : 'hover:bg-white/5 text-slate-400'}`}
            >
              <span className="flex items-center gap-3">
                <Sliders className="w-4 h-4" /> Active Incidents
              </span>
              {activeIncidentCount > 0 && (
                <span className="px-2 py-0.5 bg-[#ff3366] text-white rounded-full text-[10px]">
                  {activeIncidentCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('topology')}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${activeTab === 'topology' ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]' : 'hover:bg-white/5 text-slate-400'}`}
            >
              <Server className="w-4 h-4" /> Cluster Topology
            </button>

            <button
              onClick={() => setActiveTab('audit')}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${activeTab === 'audit' ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]' : 'hover:bg-white/5 text-slate-400'}`}
            >
              <FileSpreadsheet className="w-4 h-4" /> Safety Audit Logs
            </button>

            <button
              onClick={() => setActiveTab('prompts')}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${activeTab === 'prompts' ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]' : 'hover:bg-white/5 text-slate-400'}`}
            >
              <Database className="w-4 h-4" /> Prompt & RAG Store
            </button>

            <button
              onClick={() => setActiveTab('observability')}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${activeTab === 'observability' ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]' : 'hover:bg-white/5 text-slate-400'}`}
            >
              <Cpu className="w-4 h-4" /> Observability Traces
            </button>

            <button
              onClick={() => setActiveTab('knowledge')}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${activeTab === 'knowledge' ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]' : 'hover:bg-white/5 text-slate-400'}`}
            >
              <FolderOpen className="w-4 h-4" /> Runbook & SOP Store
            </button>

            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${activeTab === 'settings' ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]' : 'hover:bg-white/5 text-slate-400'}`}
            >
              <Settings className="w-4 h-4" /> Security Settings
            </button>

            <button
              onClick={() => setActiveTab('metrics')}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${activeTab === 'metrics' ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]' : 'hover:bg-white/5 text-slate-400'}`}
            >
              <Gauge className="w-4 h-4" /> Live Metrics
            </button>

            <button
              onClick={() => setActiveTab('playbooks')}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${activeTab === 'playbooks' ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]' : 'hover:bg-white/5 text-slate-400'}`}
            >
              <ListChecks className="w-4 h-4" /> Playbook Tracker
            </button>
          </div>

          {/* Quick Metrics mini card */}
          <div className="p-4 bg-[#1a1f2e] border border-white/5 rounded-2xl">
            <div className="flex items-center gap-2 mb-2">
              <Terminal className="w-3.5 h-3.5 text-[#00d4ff]" />
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Rate Limiter</span>
            </div>
            <div className="flex justify-between text-xs text-slate-500">
              <span>Requests</span>
              <span className="text-slate-300 font-mono">
                {serverHealth?.services?.websocket || '0 clients'}
              </span>
            </div>
            <div className="w-full bg-white/5 h-1.5 rounded-full mt-2 overflow-hidden">
              <div className="bg-[#00d4ff] h-full" style={{ width: '35%' }}></div>
            </div>
          </div>

          {/* Autopilot Mode Dashboard Indicator */}
          <div className="p-4 bg-[#1a1f2e] border border-white/5 rounded-2xl mt-3">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-3.5 h-3.5 text-[#00ff88]" />
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest font-mono">Autopilot Mode</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500 font-mono text-[10px]">Governance</span>
              <span className={`font-mono font-bold text-[9px] px-1.5 py-0.5 rounded ${
                govMode === 'FULLY_AUTONOMOUS' ? 'bg-emerald-500/10 text-[#00ff88] border border-emerald-500/20' :
                govMode === 'SEMI_AUTONOMOUS' ? 'bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/20' :
                'bg-slate-800 text-slate-400 border border-slate-700'
              }`}>
                {govMode}
              </span>
            </div>
            <div className="flex justify-between text-[10px] text-slate-500 mt-2 font-mono">
              <span>Confidence Gate</span>
              <span className="text-slate-300 font-mono">{govMinConfidence}%</span>
            </div>
          </div>
        </nav>

        {/* Content Panel Area */}
        <main className="flex-1 p-8 overflow-y-auto z-10 relative">
          {/* TAB: EXECUTIVE DASHBOARD */}
          {activeTab === 'executive' && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-bold text-slate-100">Executive SecOps Intelligence</h2>
                  <p className="text-xs text-slate-500 mt-1">High-level financial, operational, and compliance impact summaries for board-level reporting</p>
                </div>
                <div className="text-xs text-slate-500 bg-white/5 px-4 py-2 rounded-lg border border-white/5 flex items-center gap-2">
                  <RefreshCw className="w-3 h-3 animate-spin" /> Live Financial Sync
                </div>
              </div>

              {/* C-Suite Metrics Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
                <div className="p-5 card relative overflow-hidden">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Mean Time to Detect (MTTD)</p>
                  <h3 className="text-2xl font-black text-[#00ff88] mt-2 font-mono">
                    {executiveMetrics?.mttd_seconds || 34.2} s
                  </h3>
                  <p className="text-[10px] text-slate-500 mt-1">Instant telemetry alerts ingest rate</p>
                </div>

                <div className="p-5 card relative overflow-hidden">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Mean Time to Respond (MTTR)</p>
                  <h3 className="text-2xl font-black text-[#00d4ff] mt-2 font-mono">
                    {executiveMetrics?.mttr_seconds ? `${(executiveMetrics.mttr_seconds / 60).toFixed(1)} m` : '0.0 m'}
                  </h3>
                  <p className="text-[10px] text-slate-500 mt-1">Resolution workflow cycle length</p>
                </div>

                <div className="p-5 card relative overflow-hidden">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Incident Resolution Rate</p>
                  <h3 className="text-2xl font-black text-amber-400 mt-2 font-mono">
                    {executiveMetrics?.resolution_rate || 100.0}%
                  </h3>
                  <p className="text-[10px] text-slate-500 mt-1">Completed autopilot actions</p>
                </div>

                <div className="p-5 card relative overflow-hidden">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">AI False Positive Rate</p>
                  <h3 className="text-2xl font-black text-rose-500 mt-2 font-mono">
                    {executiveMetrics?.false_positive_rate || 0.0}%
                  </h3>
                  <p className="text-[10px] text-slate-500 mt-1">Rejected actions percentage</p>
                </div>
              </div>

              {/* Lower Section: Incident Selector & Report view */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Incident Selector List */}
                <div className="lg:col-span-1 space-y-4">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-sm font-bold text-slate-200">Incident Index</h3>
                    <span className="text-xs bg-white/5 px-2.5 py-1 rounded text-slate-500">
                      Total: {incidents.length}
                    </span>
                  </div>

                  <div className="space-y-3 overflow-y-auto max-h-[500px] pr-2">
                    {incidents.map(inc => (
                      <div
                        key={inc.id}
                        onClick={() => setSelectedExecutiveIncident(inc)}
                        className={`p-4 card cursor-pointer transition-all border ${selectedExecutiveIncident?.id === inc.id ? 'border-[#00ff88] bg-emerald-500/5' : 'border-white/5'}`}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <span className="text-[10px] font-mono text-slate-400 font-semibold">#{inc.id}</span>
                          <span className={`badge text-[9px] ${inc.severity === 'CRITICAL' ? 'badge-critical' : inc.severity === 'WARNING' ? 'badge-warning' : 'badge-info'}`}>
                            {inc.severity}
                          </span>
                        </div>
                        <h4 className="text-xs font-bold text-slate-200 truncate mb-1">{inc.title}</h4>
                        <div className="flex justify-between items-center text-[10px] text-slate-500">
                          <span>{inc.status}</span>
                          <span>{new Date(inc.created_at).toLocaleTimeString()}</span>
                        </div>
                      </div>
                    ))}
                    {incidents.length === 0 && (
                      <div className="p-8 text-center text-slate-500 text-xs font-mono border border-white/5 rounded-2xl">
                        No incidents logged.
                      </div>
                    )}
                  </div>
                </div>

                {/* Executive Report View */}
                <div className="lg:col-span-2">
                  {!selectedExecutiveIncident ? (
                    <div className="h-full min-h-[300px] flex flex-col items-center justify-center text-center p-8 card border border-white/5 border-dashed rounded-2xl">
                      <Shield className="w-12 h-12 text-slate-600 mb-4 animate-pulse" />
                      <h4 className="text-sm font-bold text-slate-300">Executive Report View</h4>
                      <p className="text-xs text-slate-500 max-w-sm mt-2">
                        Select an incident from the index to inspect its business-level impact score, regulatory exposure compliance status, and AI executive summary.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-5 animate-fade-in card p-6">
                      
                      {/* Report Header */}
                      <div className="flex justify-between items-start border-b border-white/5 pb-4">
                        <div>
                          <div className="flex items-center gap-3">
                            <h3 className="text-base font-bold text-slate-100">{selectedExecutiveIncident.title}</h3>
                            {executiveReport?.business_impact?.risk_score && (
                              <span className={`badge text-[9px] ${executiveReport.business_impact.risk_score === 'CRITICAL' ? 'badge-critical' : executiveReport.business_impact.risk_score === 'HIGH' ? 'badge-warning' : 'badge-info'}`}>
                                RISK: {executiveReport.business_impact.risk_score}
                              </span>
                            )}
                          </div>
                          <p className="text-[10px] text-slate-500 font-mono mt-1">Correlation: {selectedExecutiveIncident.correlation_id}</p>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-slate-500 font-bold block uppercase">Resolution status</span>
                          <span className="text-xs font-bold text-[#00ff88] mt-1 block">{selectedExecutiveIncident.status}</span>
                        </div>
                      </div>

                      {/* Loading State */}
                      {executiveReportLoading ? (
                        <div className="py-12 flex flex-col items-center justify-center gap-3">
                          <Loader2 className="w-8 h-8 text-[#00ff88] animate-spin" />
                          <span className="text-xs text-slate-400 font-mono">Synthesizing executive board summary...</span>
                        </div>
                      ) : (
                        <div className="space-y-6">
                          
                          {/* Executive Summary Card */}
                          <div className="p-4 bg-white/5 border border-white/5 rounded-xl space-y-4">
                            <div>
                              <h4 className="text-xs font-bold text-[#00ff88] uppercase tracking-wider mb-2">AI Non-Technical Narrative</h4>
                              <p className="text-xs text-slate-300 leading-relaxed font-sans">{executiveReport?.summary}</p>
                            </div>
                            
                            {executiveReport?.simplified_explanation && (
                              <div className="pt-3 border-t border-white/5">
                                <h4 className="text-xs font-bold text-[#00d4ff] uppercase tracking-wider mb-2">AI Decision Rationale</h4>
                                <p className="text-xs text-slate-300 leading-relaxed font-sans italic">"{executiveReport.simplified_explanation}"</p>
                              </div>
                            )}
                          </div>

                          {/* Impact Metrics grid */}
                          <div>
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Valuation & Operational Impacts</h4>
                            <div className="grid grid-cols-3 gap-4">
                              <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center">
                                <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">Affected Customers</span>
                                <span className="text-lg font-black text-slate-100 font-mono mt-1.5 block">
                                  {executiveReport?.business_impact?.affected_users || 0}
                                </span>
                              </div>
                              <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center">
                                <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">Financial Downtime Cost</span>
                                <span className="text-lg font-black text-[#ff3366] font-mono mt-1.5 block">
                                  ${executiveReport?.business_impact?.revenue_lost_usd?.toLocaleString() || '0.00'}
                                </span>
                              </div>
                              <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center">
                                <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">Downtime Duration</span>
                                <span className="text-lg font-black text-[#00d4ff] font-mono mt-1.5 block">
                                  {executiveReport?.estimated_recovery_time_mins || 0} mins
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Compliance Assessment */}
                          <div className="border-t border-white/5 pt-4">
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Regulatory Audit & Compliance checklist</h4>
                            <div className="p-4 bg-white/5 border border-white/5 rounded-xl space-y-3">
                              <div className="flex justify-between items-center">
                                <span className="text-xs font-semibold">Regulatory Framework status</span>
                                <span className={`badge ${executiveReport?.compliance?.compliance_status === 'MET' ? 'badge-success' : executiveReport?.compliance?.compliance_status === 'PENDING' ? 'badge-warning' : 'badge-critical'}`}>
                                  {executiveReport?.compliance?.compliance_status || 'PENDING'}
                                </span>
                              </div>

                              <div className="flex justify-between items-start">
                                <span className="text-xs font-semibold">Applicable Regs</span>
                                <div className="flex gap-2">
                                  {executiveReport?.compliance?.regulations_applicable?.map((reg: string) => (
                                    <span key={reg} className="bg-white/10 px-2 py-0.5 rounded text-[9px] font-bold text-slate-300">
                                      {reg}
                                    </span>
                                  ))}
                                </div>
                              </div>

                              {/* Compliance Checklist Score */}
                              <div className="space-y-1 mt-2 border-t border-white/5 pt-3">
                                <div className="flex justify-between text-xs font-semibold">
                                  <span>Checklist Score</span>
                                  <span className="text-[#00ff88]">{executiveReport?.compliance?.compliance_score_percent || 0}%</span>
                                </div>
                                <div className="w-full bg-white/5 h-2 rounded-full overflow-hidden border border-white/5">
                                  <div 
                                    className="bg-gradient-to-r from-emerald-500 to-[#00ff88] h-full transition-all duration-500" 
                                    style={{ width: `${executiveReport?.compliance?.compliance_score_percent || 0}%` }}
                                  ></div>
                                </div>
                              </div>

                              {/* Checklist Items */}
                              {executiveReport?.compliance?.checklist?.length > 0 && (
                                <div className="border-t border-white/5 pt-3 mt-3 space-y-2">
                                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">Checklist Items</span>
                                  <div className="space-y-2">
                                    {executiveReport.compliance.checklist.map((item: any) => (
                                      <div key={item.id} className="flex items-center justify-between p-2.5 bg-white/5 border border-white/5 rounded-lg text-xs">
                                        <span className="text-slate-300 font-medium">{item.task}</span>
                                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-black tracking-widest ${
                                          item.status 
                                            ? 'bg-emerald-950/20 text-[#00ff88] border border-emerald-500/20' 
                                            : 'bg-rose-950/20 text-rose-400 border border-rose-500/20'
                                        }`}>
                                          {item.status ? 'PASSED' : 'PENDING'}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {executiveReport?.compliance?.required_notifications?.length > 0 && (
                                <div className="border-t border-white/5 pt-3 mt-2">
                                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-2">Required Compliance Reports</span>
                                  <ul className="text-xs text-slate-400 space-y-1.5 list-disc pl-4">
                                    {executiveReport.compliance.required_notifications.map((rep: string) => (
                                      <li key={rep}>{rep}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </div>

                        </div>
                      )}

                    </div>
                  )}
                </div>

              </div>
            </div>
          )}

          {/* TAB 1: CYBER DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-bold text-slate-100">Executive Threat Intel</h2>
                  <p className="text-xs text-slate-500 mt-1">Real-time status analysis aggregated from cluster telemetry and agent workflows</p>
                </div>
                <div className="text-xs text-slate-500 bg-white/5 px-4 py-2 rounded-lg border border-white/5 flex items-center gap-2">
                  <RefreshCw className="w-3 h-3 animate-spin" /> Automatic Polling
                </div>
              </div>

              {/* Status Grid Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
                <div className="p-5 card relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full filter blur-xl"></div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Autopilot Decisions</p>
                  <h3 className="text-2xl font-black text-[#00ff88] mt-2 font-mono">
                    {obsSummary?.total_traces || 0}
                  </h3>
                  <p className="text-[10px] text-slate-500 mt-1">Telemetry & prompt cycles processed</p>
                </div>

                <div className="p-5 card relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-rose-500/5 rounded-full filter blur-xl"></div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active Anomalies</p>
                  <h3 className={`text-2xl font-black mt-2 font-mono ${activeIncidentCount > 0 ? 'text-[#ff3366]' : 'text-slate-400'}`}>
                    {activeIncidentCount}
                  </h3>
                  <p className="text-[10px] text-slate-500 mt-1">Requiring manual checkout</p>
                </div>

                <div className="p-5 card relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full filter blur-xl"></div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Average Workflow Latency</p>
                  <h3 className="text-2xl font-black text-[#00d4ff] mt-2 font-mono">
                    {obsSummary?.avg_latency_ms || 0} ms
                  </h3>
                  <p className="text-[10px] text-slate-500 mt-1">Ingester to remediation executor</p>
                </div>

                <div className="p-5 card relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-full filter blur-xl"></div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">LLM Model API Token Count</p>
                  <h3 className="text-2xl font-black text-amber-400 mt-2 font-mono">
                    {obsSummary?.total_input_tokens ? Math.round(obsSummary.total_input_tokens / 1000) : 0}k
                  </h3>
                  <p className="text-[10px] text-slate-500 mt-1">Total aggregated model tokens</p>
                </div>
              </div>

              {/* Chart Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-5 card md:col-span-2">
                  <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-6">Cluster Utilization Metrics</h4>
                  <div className="h-64">
                    {mockChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={mockChartData}>
                          <defs>
                            <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#00ff88" stopOpacity={0.2}/>
                              <stop offset="95%" stopColor="#00ff88" stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id="colorMem" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.2}/>
                              <stop offset="95%" stopColor="#00d4ff" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                          <YAxis stroke="#64748b" fontSize={10} />
                          <Tooltip contentStyle={{ backgroundColor: '#1a1f2e', borderColor: '#334155' }} />
                          <Area type="monotone" dataKey="cpu" stroke="#00ff88" strokeWidth={2} fillOpacity={1} fill="url(#colorCpu)" name="CPU Usage (%)" />
                          <Area type="monotone" dataKey="memory" stroke="#00d4ff" strokeWidth={2} fillOpacity={1} fill="url(#colorMem)" name="Memory Usage (%)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-slate-500 text-xs font-mono">
                        Telemetry feed syncing...
                      </div>
                    )}
                  </div>
                </div>

                <div className="p-5 card flex flex-col justify-between">
                  <div>
                    <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-4">Security Integrations</h4>
                    <p className="text-xs text-slate-500">MFA & Slack notifications controllers current operational status.</p>
                  </div>
                  
                  <div className="space-y-4 my-6">
                    <div className="flex justify-between items-center p-3 bg-white/5 border border-white/5 rounded-xl">
                      <span className="text-xs font-semibold">Dual-Factor MFA Gate</span>
                      <span className={`badge ${user?.mfa_enabled ? 'badge-success' : 'badge-warning'}`}>
                        {user?.mfa_enabled ? 'MFA_ACTIVE' : 'MFA_INACTIVE'}
                      </span>
                    </div>

                    <div className="flex justify-between items-center p-3 bg-white/5 border border-white/5 rounded-xl">
                      <span className="text-xs font-semibold">Slack Bot Connection</span>
                      <span className={`badge ${serverHealth?.services?.redis ? 'badge-success' : 'badge-info'}`}>
                        MOCK_CONNECTED
                      </span>
                    </div>

                    <div className="flex justify-between items-center p-3 bg-white/5 border border-white/5 rounded-xl">
                      <span className="text-xs font-semibold">Database Schema Mode</span>
                      <span className="badge badge-info">
                        SQLITE_WAL
                      </span>
                    </div>
                  </div>

                  <div className="p-3 bg-emerald-950/20 border border-emerald-500/20 rounded-xl text-center">
                    <p className="text-[10px] text-slate-400">
                      Enkrypt AI Safety Policy is actively checking pipeline executions under Strict mode.
                    </p>
                  </div>
                </div>
              </div>

              {/* Autopilot Governance KPI Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
                <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-16 h-16 bg-[#00ff88]/5 rounded-full filter blur-xl"></div>
                  <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">Approval Override Rate</span>
                  <span className="text-xl font-black text-slate-100 font-mono mt-1.5 block">
                    8%
                  </span>
                  <p className="text-[9px] text-slate-500 mt-1">Manual overrides vs Auto-approvals</p>
                </div>

                <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-16 h-16 bg-[#00d4ff]/5 rounded-full filter blur-xl"></div>
                  <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">Auto-Execution Speed</span>
                  <span className="text-xl font-black text-[#00d4ff] font-mono mt-1.5 block">
                    2.4s
                  </span>
                  <p className="text-[9px] text-slate-500 mt-1">Mean autonomous reaction delay</p>
                </div>

                <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-16 h-16 bg-amber-500/5 rounded-full filter blur-xl"></div>
                  <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">Manual Resolution Speed</span>
                  <span className="text-xl font-black text-amber-400 font-mono mt-1.5 block">
                    185.0s
                  </span>
                  <p className="text-[9px] text-slate-500 mt-1">Mean operator reaction delay</p>
                </div>

                <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-16 h-16 bg-emerald-500/5 rounded-full filter blur-xl"></div>
                  <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">Auto-rem. Success Rate</span>
                  <span className="text-xl font-black text-[#00ff88] font-mono mt-1.5 block">
                    94.2%
                  </span>
                  <p className="text-[9px] text-slate-500 mt-1">Mitigated incidents success percentage</p>
                </div>
              </div>

              {/* Incidents Queue Preview */}
              <div className="card p-5">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest">Active Incident Response Log</h4>
                  <button onClick={() => setActiveTab('incidents')} className="text-xs text-[#00ff88] hover:underline flex items-center gap-1">
                    Manage Incidents <Sliders className="w-3.5 h-3.5" />
                  </button>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/5 text-slate-500 font-bold">
                        <th className="py-2.5">ID</th>
                        <th className="py-2.5">Correlation ID</th>
                        <th className="py-2.5">Anomaly Type</th>
                        <th className="py-2.5">Severity</th>
                        <th className="py-2.5">Status</th>
                        <th className="py-2.5">Confidence</th>
                        <th className="py-2.5">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {incidents.slice(0, 5).map(inc => (
                        <tr key={inc.id} className="hover:bg-white/5 transition-all">
                          <td className="py-3 font-semibold font-mono text-slate-400">#{inc.id}</td>
                          <td className="py-3 font-mono text-[#00d4ff]">{inc.correlation_id}</td>
                          <td className="py-3 font-bold">{inc.metric_type}</td>
                          <td className="py-3">
                            <span className={`badge ${inc.severity === 'CRITICAL' ? 'badge-critical' : inc.severity === 'WARNING' ? 'badge-warning' : 'badge-info'}`}>
                              {inc.severity}
                            </span>
                          </td>
                          <td className="py-3">
                            <span className="font-semibold text-slate-300">{inc.status}</span>
                          </td>
                          <td className="py-3 font-mono text-[#00ff88]">{Math.round(inc.confidence_score * 100)}%</td>
                          <td className="py-3 text-slate-500">{new Date(inc.created_at).toLocaleString()}</td>
                        </tr>
                      ))}
                      {incidents.length === 0 && (
                        <tr>
                          <td colSpan={7} className="py-8 text-center text-slate-500 font-mono">
                            No telemetry violations detected in database.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              {/* Circuit Breaker Status Widget */}
              <div className="card p-5 space-y-4">
                <div>
                  <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest">Dependency Circuit Breakers & Fallback Status</h4>
                  <p className="text-xs text-slate-500 mt-1">Real-time health monitoring of AI models, vectors, caches, and notification triggers</p>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead>
                      <tr className="border-b border-white/5 text-slate-500 font-bold">
                        <th className="py-2.5">Service Name</th>
                        <th className="py-2.5">Breaker State</th>
                        <th className="py-2.5">Consecutive Failures</th>
                        <th className="py-2.5">Last Failure Time</th>
                        <th className="py-2.5">Active Fallback</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {Object.keys(circuitBreakers).length > 0 && !('detail' in circuitBreakers) ? (
                        Object.values(circuitBreakers)
                          .filter((cb: any) => cb && typeof cb === 'object' && 'name' in cb)
                          .map((cb: any) => (
                            <tr key={cb.name} className="hover:bg-white/5 transition-all">
                            <td className="py-3 font-semibold text-slate-300 capitalize">{cb.name} API</td>
                            <td className="py-3">
                              <span className={`badge ${
                                cb.state === 'CLOSED' ? 'badge-success' : 
                                cb.state === 'OPEN' ? 'badge-critical' : 'badge-warning'
                              }`}>
                                {cb.state}
                              </span>
                            </td>
                            <td className="py-3 text-slate-400">{cb.failure_count} / 5</td>
                            <td className="py-3 text-slate-500">
                              {cb.last_failure_time ? new Date(cb.last_failure_time * 1000).toLocaleTimeString() : 'Never'}
                            </td>
                            <td className="py-3">
                              {cb.fallback_active ? (
                                <span className="text-[#00ff88] font-bold">● Active Fallback</span>
                              ) : (
                                <span className="text-slate-600">None</span>
                              )}
                            </td>
                          </tr>
                        ))
                      ) : (
                        ['openai', 'anthropic', 'gemini', 'virustotal', 'qdrant', 'redis', 'smtp', 'cloud_provider'].map((s) => (
                          <tr key={s} className="hover:bg-white/5 transition-all">
                            <td className="py-3 font-semibold text-slate-300 capitalize">{s} API</td>
                            <td className="py-3"><span className="badge badge-success">CLOSED</span></td>
                            <td className="py-3 text-slate-400">0 / 5</td>
                            <td className="py-3 text-slate-500">Never</td>
                            <td className="py-3"><span className="text-slate-600">None</span></td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: ACTIVE INCIDENTS */}
          {activeTab === 'incidents' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
              {/* Incident List */}
              <div className="lg:col-span-1 space-y-4">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-base font-bold text-slate-200">System Incidents</h3>
                  <span className="text-xs bg-white/5 px-2.5 py-1 rounded text-slate-500">
                    Total: {incidents.length}
                  </span>
                </div>

                <div className="space-y-3 overflow-y-auto max-h-[calc(100vh-180px)] pr-2">
                  {incidents.slice().sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0)).map(inc => {
                    const slaInfo = (() => {
                      if (!inc.sla_breach_at) return null;
                      const diffMs = new Date(inc.sla_breach_at).getTime() - new Date().getTime();
                      if (diffMs <= 0) return { text: "SLA BREACHED", color: "text-rose-500 font-bold" };
                      const diffMins = Math.floor(diffMs / 60000);
                      if (diffMins < 60) return { text: `${diffMins}m remaining`, color: "text-amber-400 animate-pulse font-bold" };
                      const diffHours = Math.floor(diffMins / 60);
                      return { text: `${diffHours}h remaining`, color: "text-slate-400 font-mono" };
                    })();

                    const isRoot = incidents.some(i => i.parent_incident_id === inc.id);
                    const cascadingCount = incidents.filter(i => i.parent_incident_id === inc.id).length;
                    const isCascading = !!inc.parent_incident_id;

                    return (
                      <div
                        key={inc.id}
                        onClick={() => setSelectedIncident(inc as any)}
                        className={`p-4 card cursor-pointer transition-all border ${selectedIncident?.id === inc.id ? 'border-[#00ff88] bg-emerald-500/5' : 'border-white/5'}`}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-xs font-bold text-slate-500 font-mono">#{inc.id}</span>
                            {isRoot && (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-emerald-950/20 text-[#00ff88] border border-emerald-500/30">
                                ROOT ({cascadingCount} CASC)
                              </span>
                            )}
                            {isCascading && (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-rose-950/20 text-rose-400 border border-rose-500/30">
                                CASCADING (#{inc.parent_incident_id})
                              </span>
                            )}
                            {inc.sla_target && (
                              <span className={`px-1.5 py-0.5 rounded text-[9px] font-black tracking-widest ${
                                inc.sla_target === 'P0' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                                inc.sla_target === 'P1' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                                inc.sla_target === 'P2' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                                'bg-slate-500/20 text-slate-400 border border-slate-500/30'
                              }`}>
                                {inc.sla_target} (Score: {inc.priority_score})
                              </span>
                            )}
                          </div>
                          <span className={`badge ${inc.severity === 'CRITICAL' ? 'badge-critical' : inc.severity === 'WARNING' ? 'badge-warning' : 'badge-info'}`}>
                            {inc.severity}
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-slate-200 line-clamp-1">{inc.title}</h4>
                        <div className="flex items-center justify-between mt-1">
                          <p className="text-xs text-slate-500 font-mono">{inc.metric_type}</p>
                          {(inc.alert_count ?? 1) > 1 && (
                            <span className="px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 font-mono text-[9px] font-bold">
                              {inc.alert_count} alerts grouped
                            </span>
                          )}
                        </div>
                        
                        <div className="flex justify-between items-center mt-3 pt-3 border-t border-white/5 text-[10px]">
                          <span className="text-slate-400 font-bold uppercase tracking-wider">{inc.status}</span>
                          {slaInfo ? (
                            <span className={slaInfo.color}>{slaInfo.text}</span>
                          ) : (
                            <span className="text-slate-500">{new Date(inc.created_at).toLocaleTimeString()}</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                  {incidents.length === 0 && (
                    <div className="text-center py-8 text-slate-500 font-mono text-xs">
                      No incident telemetry records loaded.
                    </div>
                  )}
                </div>
              </div>

              {/* Incident Inspector */}
              <div className="lg:col-span-2">
                {selectedIncident ? (
                  <div className="card p-6 space-y-6 animate-fade-in">
                    <div className="flex justify-between items-start border-b border-white/5 pb-4">
                      <div>
                        <div className="flex items-center gap-3">
                          <h3 className="text-lg font-bold text-slate-100">{selectedIncident.title}</h3>
                          <span className={`badge ${selectedIncident.severity === 'CRITICAL' ? 'badge-critical' : selectedIncident.severity === 'WARNING' ? 'badge-warning' : 'badge-info'}`}>
                            {selectedIncident.severity}
                          </span>
                        </div>
                        <p className="text-xs text-[#00d4ff] font-mono mt-1.5">CID: {selectedIncident.correlation_id}</p>
                      </div>

                      <div className="flex items-center gap-2">
                        {selectedIncident.status === 'PENDING_APPROVAL' && (
                          <>
                            <button
                              onClick={() => approveIncidentAction(selectedIncident.id)}
                              className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-xs rounded-lg transition-all"
                            >
                              APPROVE REMEDIATION
                            </button>
                            <button
                              onClick={() => rejectIncidentAction(selectedIncident.id)}
                              className="px-4 py-2 bg-white/5 hover:bg-rose-500/15 border border-white/10 hover:border-rose-500/20 text-rose-400 font-bold text-xs rounded-lg transition-all"
                            >
                              REJECT
                            </button>
                          </>
                        )}
                        {['EXECUTED', 'REJECTED'].includes(selectedIncident.status) && (
                          <div className="flex items-center gap-1.5 text-slate-500 text-xs uppercase font-bold tracking-widest bg-white/5 px-3 py-1.5 rounded-lg border border-white/5">
                            <CheckCircle className="w-3.5 h-3.5 text-slate-500" /> CLOSED
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Real-time Agent activity & Workflow progress */}
                    {(() => {
                      const activeAgent = activeAgents[selectedIncident.id];
                      const wp = workflowProgress[selectedIncident.id];
                      if (!activeAgent && !wp) return null;
                      return (
                        <div className="p-5 bg-[#00ff88]/5 border border-[#00ff88]/20 rounded-xl space-y-4">
                          <div className="flex items-center justify-between">
                            <h4 className="text-xs font-bold text-[#00ff88] uppercase tracking-widest flex items-center gap-2">
                              <Loader2 className="w-4 h-4 text-[#00ff88] animate-spin" /> Active Autonomous SecOps Agent
                            </h4>
                            {wp && (
                              <span className="text-[10px] text-slate-400 font-mono">
                                Workflow Step {wp.current_step} of {wp.total_steps}
                              </span>
                            )}
                          </div>
                          
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono text-slate-300">
                            <div>
                              <p className="text-slate-400 font-bold">Agent:</p>
                              <p className="text-slate-100 font-semibold">{activeAgent?.agent_name || "Mastra Agent Orchestrator"}</p>
                            </div>
                            <div>
                              <p className="text-slate-400 font-bold">Status:</p>
                              <p className="text-slate-100 font-semibold capitalize">{activeAgent?.status || "Executing..."}</p>
                            </div>
                            <div className="md:col-span-2">
                              <p className="text-slate-400 font-bold">Message:</p>
                              <p className="text-slate-100 italic">"{activeAgent?.message || wp?.step_name || 'Running automated diagnosis steps...'}"</p>
                            </div>
                          </div>

                          {/* Progress bar */}
                          <div className="space-y-1.5">
                            <div className="flex justify-between text-[10px] font-mono text-slate-400">
                              <span>Progress</span>
                              <span>{activeAgent ? `${activeAgent.progress}%` : wp ? `${Math.round((wp.current_step / wp.total_steps) * 100)}%` : '0%'}</span>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                              <div 
                                className="bg-[#00ff88] h-1.5 rounded-full transition-all duration-500" 
                                style={{ width: `${activeAgent ? activeAgent.progress : wp ? (wp.current_step / wp.total_steps) * 100 : 0}%` }}
                              />
                            </div>
                          </div>

                          {/* Estimated Completion Time */}
                          {wp?.estimated_completion && wp.step_status === 'in_progress' && (
                            <div className="text-[10px] text-right text-slate-400 font-mono">
                              Estimated completion: {new Date(wp.estimated_completion).toLocaleTimeString()}
                            </div>
                          )}
                        </div>
                      );
                    })()}

                    {/* SRE Inspector Tab Selector */}
                    <div className="flex flex-wrap gap-2 border-b border-white/5 pb-2.5 mb-4 text-xs font-mono">
                      {[
                        { id: 'timeline', label: 'Timeline & RCA' },
                        { id: 'attack', label: 'Attack Graph' },
                        { id: 'simulation', label: 'What-If Simulation' },
                        { id: 'options', label: 'Remediation Agent' },
                        { id: 'runbooks', label: 'Runbook RAG' },
                        { id: 'graph', label: 'Decision DAG' },
                        { id: 'replay', label: 'Interactive Replay' },
                      ].map(t => (
                        <button
                          key={t.id}
                          onClick={() => {
                            setInspectorTab(t.id as any);
                            if (t.id === 'replay') {
                              setReplayIndex(-1);
                              setIsPlayingReplay(false);
                            }
                          }}
                          className={`px-3 py-1.5 rounded transition-all ${
                            inspectorTab === t.id
                              ? 'bg-[#00ff88]/10 text-[#00ff88] border border-[#00ff88]/20 font-bold'
                              : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'
                          }`}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>

                    {/* TAB 1: TIMELINE & RCA */}
                    {inspectorTab === 'timeline' && (
                      <>
                        {/* Incident Correlation & Cascading Dependencies */}
                        {(() => {
                          const isRoot = incidents.some(i => i.parent_incident_id === selectedIncident.id);
                          const isCascading = !!selectedIncident.parent_incident_id;
                          
                          if (!isRoot && !isCascading) return null;
                          
                          const parentIncident = isCascading 
                            ? incidents.find(i => i.id === selectedIncident.parent_incident_id)
                            : null;
                            
                          const cascadingChildren = isRoot
                            ? incidents.filter(i => i.parent_incident_id === selectedIncident.id)
                            : [];

                          return (
                            <div className="p-5 bg-[#00d4ff]/5 border border-[#00d4ff]/20 rounded-xl space-y-4 mb-4">
                              <div className="flex items-center justify-between border-b border-white/5 pb-2">
                                <h4 className="text-xs font-bold text-[#00d4ff] uppercase tracking-widest flex items-center gap-1.5">
                                  <Activity className="w-4 h-4 text-[#00d4ff]" /> Incident Correlation & Cascading Failure Path
                                </h4>
                                <span className={`px-2 py-0.5 rounded text-[10px] font-black tracking-widest ${
                                  isRoot 
                                    ? 'bg-emerald-950/20 text-[#00ff88] border border-emerald-500/30' 
                                    : 'bg-rose-950/20 text-rose-400 border border-rose-500/30'
                                }`}>
                                  {isRoot ? 'PRIMARY ROOT CAUSE' : 'CASCADING FAILURE'}
                                </span>
                              </div>

                              {isRoot && (
                                <div className="space-y-3">
                                  <p className="text-xs text-slate-300 font-mono">
                                    This incident has been identified as the <span className="text-[#00ff88] font-bold">Root Cause</span> of the following cascading failures:
                                  </p>
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {cascadingChildren.map(child => (
                                      <div 
                                        key={child.id}
                                        onClick={() => api.getIncidentDetail(child.id).then(setSelectedIncident).catch(console.error)} 
                                        className="p-3 bg-white/5 border border-white/5 hover:border-[#00ff88]/30 rounded-xl transition-all cursor-pointer space-y-2"
                                      >
                                        <div className="flex justify-between items-center text-[10px]">
                                          <span className="font-mono text-slate-400">#{child.id}</span>
                                          <span className={`badge ${child.severity === 'CRITICAL' ? 'badge-critical' : child.severity === 'WARNING' ? 'badge-warning' : 'badge-info'}`}>
                                            {child.severity}
                                          </span>
                                        </div>
                                        <h5 className="text-xs font-bold text-slate-200 truncate">{child.title}</h5>
                                        <p className="text-[10px] text-slate-500 font-mono">{child.metric_type}</p>
                                        <div className="flex justify-between items-center text-[9px] text-slate-400 pt-1.5 border-t border-white/5">
                                          <span className="uppercase">{child.status}</span>
                                          <span>{new Date(child.created_at).toLocaleTimeString()}</span>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {isCascading && parentIncident && (
                                <div className="space-y-3">
                                  <p className="text-xs text-slate-300 font-mono">
                                    This incident is a <span className="text-rose-400 font-bold">Cascading Consequence</span> of the primary root cause incident:
                                  </p>
                                  <div 
                                    onClick={() => api.getIncidentDetail(parentIncident.id).then(setSelectedIncident).catch(console.error)}
                                    className="p-4 bg-white/5 border border-white/5 hover:border-[#00ff88]/30 rounded-xl transition-all cursor-pointer space-y-2"
                                  >
                                    <div className="flex justify-between items-center text-[10px]">
                                      <span className="font-mono text-[#00ff88] font-bold">ROOT CAUSE #{parentIncident.id}</span>
                                      <span className={`badge ${parentIncident.severity === 'CRITICAL' ? 'badge-critical' : parentIncident.severity === 'WARNING' ? 'badge-warning' : 'badge-info'}`}>
                                        {parentIncident.severity}
                                      </span>
                                    </div>
                                    <h5 className="text-xs font-bold text-slate-200">{parentIncident.title}</h5>
                                    <p className="text-[10px] text-slate-500 font-mono">{parentIncident.metric_type}</p>
                                    <div className="flex justify-between items-center text-[9px] text-slate-400 pt-1.5 border-t border-white/5">
                                      <span className="uppercase font-bold text-[#00ff88]">{parentIncident.status}</span>
                                      <span>{new Date(parentIncident.created_at).toLocaleTimeString()}</span>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })()}

                        {/* Reasoning Details */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                          <div className="md:col-span-2 space-y-4">
                            <div>
                              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1.5">Anomaly Analysis Details</h4>
                              <div className="p-4 bg-white/5 rounded-xl border border-white/5 text-sm leading-relaxed text-slate-300">
                                {selectedIncident.description}
                              </div>
                            </div>

                            {selectedIncident.suggested_action && (
                              <div>
                                <h4 className="text-xs font-bold text-[#00ff88] uppercase tracking-widest mb-1.5">Suggested Autopilot Remediator</h4>
                                <div className="terminal p-4 flex justify-between items-center text-xs">
                                  <span className="text-emerald-400 font-mono">{selectedIncident.suggested_action}</span>
                                  <span className="badge badge-success shrink-0 font-bold">100% SAFE ENVELOPE VERIFIED</span>
                                </div>
                              </div>
                            )}

                            {/* AI Explainability & Decision Transparency Layer */}
                            {explainabilityReport && (
                              <div className="p-5 bg-gradient-to-br from-indigo-950/20 to-purple-950/20 border border-[#00d4ff]/20 rounded-xl space-y-4">
                                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                                  <h4 className="text-xs font-bold text-[#00d4ff] uppercase tracking-widest flex items-center gap-1.5">
                                    <HelpCircle className="w-4 h-4 text-[#00d4ff]" /> AI Explainability & Decision Path
                                  </h4>
                                  <span className="badge badge-info text-[9px] font-mono">
                                    {Math.round(explainabilityReport.overall_confidence || selectedIncident.confidence_score * 100)}% CONFIDENCE
                                  </span>
                                </div>
                                
                                <p className="text-xs text-slate-300 leading-relaxed italic bg-white/5 p-3 rounded-lg border border-white/5">
                                  "{explainabilityReport.overall_explanation}"
                                </p>

                                <div className="grid grid-cols-1 gap-4 pt-1">
                                  {/* 1. RCA Explanation */}
                                  {explainabilityReport.rca && (
                                    <div className="space-y-1.5">
                                      <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#00ff88]"></span> 1. Root Cause Analysis Reasoning
                                      </h5>
                                      <div className="p-3.5 bg-white/5 rounded-xl border border-white/5 text-[11px] text-slate-400 space-y-2">
                                        <p><strong className="text-slate-300">How analyzed:</strong> {explainabilityReport.rca.how_analyzed}</p>
                                        <p><strong className="text-slate-300">Conclusion:</strong> {explainabilityReport.rca.why_conclusion}</p>
                                        <p><strong className="text-slate-300">Sources Cited:</strong> {explainabilityReport.rca.sources?.join(', ')}</p>
                                        {explainabilityReport.rca.alternatives && explainabilityReport.rca.alternatives.length > 0 && (
                                          <div className="mt-2.5 border-t border-white/5 pt-2">
                                            <p className="text-slate-500 font-bold text-[9px] uppercase tracking-wider">Alternatives Evaluated & Rejected:</p>
                                            {explainabilityReport.rca.alternatives.map((alt: any, idx: number) => (
                                              <div key={idx} className="mt-1.5 pl-2 border-l border-rose-500/30 text-[10px]">
                                                <p className="text-rose-400 font-medium">{alt.option}</p>
                                                <p className="text-slate-500 italic mt-0.5">{alt.reason}</p>
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  )}

                                  {/* 2. Threat Intel Explanation */}
                                  {explainabilityReport.threat_intel && (
                                    <div className="space-y-1.5">
                                      <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#00d4ff]"></span> 2. Threat Intelligence Enrichment
                                      </h5>
                                      <div className="p-3.5 bg-white/5 rounded-xl border border-white/5 text-[11px] text-slate-400 space-y-2">
                                        <p><strong className="text-slate-300">How analyzed:</strong> {explainabilityReport.threat_intel.how_analyzed}</p>
                                        <p><strong className="text-slate-300">Conclusion:</strong> {explainabilityReport.threat_intel.why_conclusion}</p>
                                        <p><strong className="text-slate-300">Sources Cited:</strong> {explainabilityReport.threat_intel.sources?.join(', ')}</p>
                                        {explainabilityReport.threat_intel.alternatives && explainabilityReport.threat_intel.alternatives.length > 0 && (
                                          <div className="mt-2.5 border-t border-white/5 pt-2">
                                            <p className="text-slate-500 font-bold text-[9px] uppercase tracking-wider">Alternatives Evaluated & Rejected:</p>
                                            {explainabilityReport.threat_intel.alternatives.map((alt: any, idx: number) => (
                                              <div key={idx} className="mt-1.5 pl-2 border-l border-rose-500/30 text-[10px]">
                                                <p className="text-rose-400 font-medium">{alt.option}</p>
                                                <p className="text-slate-500 italic mt-0.5">{alt.reason}</p>
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  )}

                                  {/* 3. Remediation Explanation */}
                                  {explainabilityReport.remediation && (
                                    <div className="space-y-1.5">
                                      <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span> 3. Alternate Action Plan Evaluations
                                      </h5>
                                      <div className="p-3.5 bg-white/5 rounded-xl border border-white/5 text-[11px] text-slate-400 space-y-2">
                                        <p><strong className="text-slate-300">Why recommended:</strong> {explainabilityReport.remediation.why_conclusion}</p>
                                        <p><strong className="text-slate-300">Decision Path:</strong> {explainabilityReport.remediation.decision_path}</p>
                                        {explainabilityReport.remediation.alternatives && explainabilityReport.remediation.alternatives.length > 0 && (
                                          <div className="mt-2.5 border-t border-white/5 pt-2">
                                            <p className="text-slate-500 font-bold text-[9px] uppercase tracking-wider">Alternatives Evaluated & Rejected:</p>
                                            {explainabilityReport.remediation.alternatives.map((alt: any, idx: number) => (
                                              <div key={idx} className="mt-1.5 pl-2 border-l border-amber-500/30 text-[10px]">
                                                <p className="text-amber-400 font-medium">{alt.option}</p>
                                                <p className="text-slate-500 italic mt-0.5">{alt.reason}</p>
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Mastra Reasoning Gate Info */}
                          <div className="space-y-4">
                            <div className="p-4 bg-[#1a1f2e] border border-white/5 rounded-xl">
                              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Mastra Agent Assessment</h4>
                              
                              <div className="space-y-3 text-xs">
                                <div className="flex justify-between">
                                  <span className="text-slate-500">Confidence Gate</span>
                                  <span className="font-mono text-[#00ff88] font-bold">
                                    {Math.round(selectedIncident.confidence_score * 100)}%
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-slate-500">Safety Status</span>
                                  <span className="font-semibold text-emerald-400">PASSED</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-slate-500">Autopilot Route</span>
                                  <span className="font-semibold text-slate-400">
                                    {selectedIncident.confidence_score >= 0.80 ? 'BYPASSED (Auto)' : 'HITL_REQUIRED'}
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* Slack Webhook manual executor simulator */}
                            {selectedIncident.status === 'PENDING_APPROVAL' && (
                              <div className="p-4 bg-slate-900/40 border border-white/5 rounded-xl">
                                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2.5">Simulate Slack Actions</h4>
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => triggerSlackApprovalAction(selectedIncident.id, 'approve')}
                                    disabled={slackSimulatorLoading}
                                    className="flex-1 py-2 bg-emerald-600/10 hover:bg-emerald-500/20 text-emerald-400 font-bold text-[10px] rounded border border-emerald-500/20 transition-all uppercase"
                                  >
                                    SLACK_APPROVE
                                  </button>
                                  <button
                                    onClick={() => triggerSlackApprovalAction(selectedIncident.id, 'reject')}
                                    disabled={slackSimulatorLoading}
                                    className="flex-1 py-2 bg-rose-600/10 hover:bg-rose-500/20 text-rose-400 font-bold text-[10px] rounded border border-rose-500/20 transition-all uppercase"
                                  >
                                    SLACK_REJECT
                                  </button>
                                </div>
                                {slackSimulatorMsg && (
                                  <p className="text-[10px] text-amber-400 mt-2 font-mono leading-tight">{slackSimulatorMsg}</p>
                                )}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Real-time Workflow Step Visualizer */}
                        {(() => {
                          const wp = workflowProgress[selectedIncident.id];
                          const steps = [
                            { name: "DETECT_ANOMALY", label: "Detection" },
                            { name: "RETRIEVE_CONTEXT", label: "CRISPE Lookup" },
                            { name: "RETRIEVE_RUNBOOKS", label: "RAG Retrieve" },
                            { name: "PLAN_REMEDIATION", label: "LLM Plan" },
                            { name: "CONTRADICTION_CHECK", label: "Mastra Audit" },
                            { name: "VALIDATE", label: "Safety Gate" },
                            { name: "APPROVE_DECISION", label: "Gov Check" },
                            { name: "EXECUTE_REMEDIATION", label: "Execution" }
                          ];
                          const currentStepNum = wp ? wp.current_step : 0;
                          return (
                            <div className="space-y-4 pt-4 border-t border-white/5">
                              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Autonomous Workflow Ingestion Path</h4>
                              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 pt-2">
                                {steps.map((st, index) => {
                                  const stepIndex = index + 1;
                                  
                                  let isCompleted = false;
                                  let isCurrent = false;
                                  
                                  if (currentStepNum > 0) {
                                    isCompleted = stepIndex < currentStepNum || (st.name === "EXECUTE_REMEDIATION" && selectedIncident.status === "EXECUTED");
                                    isCurrent = stepIndex === currentStepNum;
                                  } else {
                                    const stat = (selectedIncident.status || "").toUpperCase();
                                    const isClosed = selectedIncident.resolved_at || stat === "EXECUTED" || stat === "BYPASSED" || stat === "CLOSED" || stat === "RESOLVED";
                                    
                                    if (isClosed) {
                                      isCompleted = true;
                                      isCurrent = false;
                                    } else if (stat === "REJECTED") {
                                      isCompleted = stepIndex < 8;
                                      isCurrent = false;
                                    } else if (stat === "APPROVED" || stat === "EXECUTING") {
                                      isCompleted = stepIndex < 8;
                                      isCurrent = stepIndex === 8;
                                    } else if (stat === "PENDING_APPROVAL") {
                                      isCompleted = stepIndex < 7;
                                      isCurrent = stepIndex === 7;
                                    } else if (stat === "ANALYZING") {
                                      isCompleted = stepIndex < 6;
                                      isCurrent = stepIndex === 6;
                                    } else {
                                      isCompleted = stepIndex < 2;
                                      isCurrent = stepIndex === 2;
                                    }
                                  }
                                  
                                  return (
                                    <div 
                                      key={st.name} 
                                      className={`p-3 rounded-xl border flex flex-col items-center justify-between text-center transition-all ${
                                        isCurrent 
                                          ? 'border-[#00ff88] bg-[#00ff88]/5 shadow-[0_0_10px_rgba(0,255,136,0.1)]' 
                                          : isCompleted 
                                            ? 'border-emerald-500/20 bg-emerald-950/10' 
                                            : 'border-white/5 bg-white/5 opacity-40'
                                      }`}
                                    >
                                      <div className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-900 border text-[10px] font-mono mb-2">
                                        {isCompleted ? (
                                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                                        ) : (
                                          <span className={isCurrent ? "text-[#00ff88] font-bold" : "text-slate-500"}>{stepIndex}</span>
                                        )}
                                      </div>
                                      <span className="text-[10px] font-bold block truncate max-w-full text-slate-300">{st.label}</span>
                                      <span className="text-[9px] text-slate-500 block truncate max-w-full mt-1">
                                        {isCurrent ? 'Active' : isCompleted ? 'Completed' : 'Pending'}
                                      </span>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          );
                        })()}

                        {/* Real-time Agent activity logs */}
                        {(() => {
                          const logs = agentActivitiesLog[selectedIncident.id] || [];
                          if (logs.length === 0) return null;
                          return (
                            <div className="space-y-4 pt-4 border-t border-white/5">
                              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Active Agent Workspace Timeline</h4>
                              <div className="max-h-60 overflow-y-auto space-y-3 pr-2 scrollbar-thin">
                                {logs.map((log, i) => (
                                  <div key={i} className="p-3 bg-white/5 border border-white/5 rounded-xl font-mono text-xs text-slate-300">
                                    <div className="flex justify-between items-center text-[10px] text-slate-400 mb-1 border-b border-white/5 pb-1">
                                      <span className="text-[#00ff88] font-bold">{log.agent_name}</span>
                                      <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                                    </div>
                                    <p className="text-slate-100">{log.message}</p>
                                    {log.details && Object.keys(log.details).length > 0 && (
                                      <div className="mt-2 grid grid-cols-3 gap-2 bg-[#111827]/40 p-2 rounded-lg border border-white/5 text-[9px] text-slate-400">
                                        {Object.entries(log.details).map(([k, v]: any) => (
                                          <div key={k}>
                                            <span className="capitalize">{k.replace('_', ' ')}: </span>
                                            <span className="text-slate-200 font-semibold">{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          );
                        })()}

                        {/* Grouped alerts expander */}
                        {selectedIncident.fingerprints && selectedIncident.fingerprints.length > 0 && (
                          <div className="space-y-4 pt-4 border-t border-white/5">
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center justify-between">
                              Deduplicated Alerts Group ({selectedIncident.fingerprints.reduce((acc, f) => acc + f.alert_count, 0)} alerts)
                            </h4>
                            <div className="space-y-3">
                              {selectedIncident.fingerprints.map(fp => (
                                <div key={fp.id} className="p-4 bg-white/5 rounded-xl border border-white/5 space-y-3">
                                  <div className="flex justify-between items-center text-xs font-mono">
                                    <span className="text-[#00ff88]">Fingerprint: {fp.fingerprint_hash.substring(0, 12)}...</span>
                                    <span className="badge badge-warning font-bold">{fp.alert_count} Grouped</span>
                                  </div>
                                  <p className="text-[10px] text-slate-500 font-mono">
                                    First alert: {new Date(fp.first_alert).toLocaleString()} | Last alert: {new Date(fp.last_alert_time).toLocaleString()}
                                  </p>
                                  
                                  {/* List of raw alerts */}
                                  <div className="border-t border-white/5 pt-2.5 space-y-2 max-h-48 overflow-y-auto pr-1">
                                    {fp.alerts?.map(alert => (
                                      <div key={alert.id} className="p-2.5 bg-black/30 rounded-lg border border-white/5 space-y-1">
                                        <div className="flex justify-between text-[9px] font-mono text-slate-400">
                                          <span className="font-bold text-slate-300">{alert.source} | {alert.service}</span>
                                          <span>{new Date(alert.timestamp).toLocaleTimeString()}</span>
                                        </div>
                                        <p className="text-[11px] text-slate-300 leading-normal">{alert.message}</p>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Timeline Tracker */}
                        <div className="space-y-4 pt-4 border-t border-white/5">
                          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Workflow Timeline Events</h4>
                          <div className="relative pl-6 border-l border-white/10 space-y-5">
                            {selectedIncident.timeline_events?.map(evt => (
                              <div key={evt.id} className="relative">
                                {/* Bullet icon indicator */}
                                <span className="absolute -left-[30px] top-1 p-1 bg-[#111827] rounded-full border border-white/10">
                                  <div className="w-1.5 h-1.5 rounded-full bg-[#00d4ff]"></div>
                                </span>
                                
                                <div className="flex justify-between items-start">
                                  <h5 className="text-xs font-bold text-slate-200">{evt.title}</h5>
                                  <span className="text-[9px] text-slate-500 font-mono">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                                </div>
                                {evt.description && <p className="text-xs text-slate-500 mt-1">{evt.description}</p>}
                                {evt.decision_rationale && (
                                  <p className="text-[10px] font-mono text-slate-400 bg-white/5 p-2 rounded border border-white/5 mt-2 leading-relaxed">
                                    <span className="text-[#00ff88] font-bold">RATIONALE:</span> {evt.decision_rationale}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    )}

                    {/* TAB: ATTACK GRAPH VISUALIZATION */}
                    {inspectorTab === 'attack' && (
                      <div className="space-y-6 animate-fade-in text-xs">
                        {attackGraphLoading ? (
                          <div className="text-center py-8 font-mono text-xs text-slate-500">Loading lateral movement compromise path...</div>
                        ) : attackGraph ? (
                          <div className="space-y-5">
                            {/* Analytics Summary Banner */}
                            <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5 text-center font-mono">
                              <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                                <span className="text-slate-500 block uppercase text-[9px] font-bold">Compromised Users</span>
                                <span className="text-base text-amber-400 font-black mt-1 block">
                                  {attackGraph.summary?.compromised_users || 0}
                                </span>
                              </div>
                              <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                                <span className="text-slate-500 block uppercase text-[9px] font-bold">Devices Affected</span>
                                <span className="text-base text-orange-400 font-black mt-1 block">
                                  {attackGraph.summary?.compromised_devices || 0}
                                </span>
                              </div>
                              <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                                <span className="text-slate-500 block uppercase text-[9px] font-bold">Services Exposed</span>
                                <span className="text-base text-rose-500 font-black mt-1 block">
                                  {attackGraph.summary?.compromised_services || 0}
                                </span>
                              </div>
                              <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                                <span className="text-slate-500 block uppercase text-[9px] font-bold">Dwell Time</span>
                                <span className="text-base text-[#00ff88] font-black mt-1 block">
                                  {attackGraph.summary?.dwell_time_mins || 0} mins
                                </span>
                              </div>
                              <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                                <span className="text-slate-500 block uppercase text-[9px] font-bold">Attack Risk Index</span>
                                <span className="text-base text-[#00d4ff] font-black mt-1 block">
                                  {attackGraph.summary?.risk_index || 0}/100
                                </span>
                              </div>
                            </div>

                            {/* Main Visualization Interface */}
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                              {/* Attack Graph Node Sequence Canvas */}
                              <div className="lg:col-span-2 space-y-4">
                                <div className="flex justify-between items-center mb-1">
                                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Compromise Progression Flow</h4>
                                  <div className="flex gap-2">
                                    <select
                                      value={attackPhaseFilter}
                                      onChange={e => setAttackPhaseFilter(e.target.value)}
                                      className="px-2 py-1 bg-[#0d111a] border border-white/10 rounded font-mono text-[9px] text-slate-300 focus:outline-none"
                                    >
                                      <option value="all">All Phases</option>
                                      <option value="initial_access">Initial Access</option>
                                      <option value="lateral_movement">Lateral Movement</option>
                                      <option value="exfiltration">Exfiltration</option>
                                    </select>
                                  </div>
                                </div>

                                <div className="p-6 bg-black/40 border border-white/5 rounded-2xl flex flex-col gap-6 relative min-h-[300px] justify-center items-center overflow-x-auto">
                                  {/* Render Flow Progression Line */}
                                  <div className="flex flex-col md:flex-row items-center gap-6 md:gap-12 relative z-10 w-full max-w-lg justify-between">
                                    {attackGraph.nodes.map((node: any, idx: number) => {
                                      // Node status coloring
                                      const isCompromised = node.details?.status === 'compromised' || node.details?.exfiltration_status === 'exfiltrated';
                                      const isSuspicious = node.details?.status === 'suspicious';
                                      const ringColor = isCompromised ? 'border-rose-500 shadow-[0_0_15px_rgba(239,68,68,0.2)]' : isSuspicious ? 'border-amber-500' : 'border-[#00ff88]';
                                      const badgeColor = isCompromised ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : isSuspicious ? 'bg-amber-500/10 text-amber-400' : 'bg-[#00ff88]/10 text-[#00ff88]';

                                      return (
                                        <div key={node.id} className="flex flex-col items-center shrink-0">
                                          {idx > 0 && (
                                            <div className="md:hidden flex flex-col items-center gap-1.5 py-2">
                                              <div className="w-0.5 h-6 bg-dashed border-l-2 border-white/15"></div>
                                              <span className="text-[8px] font-mono text-slate-500">
                                                {attackGraph.edges[idx - 1]?.mitre_technique}
                                              </span>
                                            </div>
                                          )}

                                          <div
                                            onClick={() => setSelectedAttackNode(node)}
                                            className={`w-24 h-24 rounded-full border-2 flex flex-col items-center justify-center p-3 text-center cursor-pointer transition-all bg-[#0d111a]/80 hover:scale-105 ${ringColor} ${
                                              selectedAttackNode?.id === node.id ? 'scale-105 ring-2 ring-[#00ff88]/30' : ''
                                            }`}
                                          >
                                            <span className={`px-1.5 py-0.5 rounded text-[7px] uppercase font-bold tracking-wider ${badgeColor}`}>
                                              {node.type}
                                            </span>
                                            <span className="font-bold text-[10px] text-slate-200 mt-2 block truncate w-full">
                                              {node.label}
                                            </span>
                                          </div>

                                          {/* Horizontal lateral line connectors with MITRE tagging */}
                                          {idx < attackGraph.nodes.length - 1 && (
                                            <div className="hidden md:flex absolute items-center justify-center" style={{
                                              left: `calc(${(idx * 100) / (attackGraph.nodes.length - 1)}% + 55px)`,
                                              width: `calc(${100 / (attackGraph.nodes.length - 1)}% - 110px)`,
                                              top: '44px'
                                            }}>
                                              <div className="w-full h-0.5 border-t border-dashed border-white/20 relative">
                                                <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 text-[8px] font-mono text-slate-500 tracking-wider whitespace-nowrap bg-slate-900 px-1">
                                                  {attackGraph.edges[idx]?.mitre_technique.split(' ')[0]}
                                                </span>
                                              </div>
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              </div>

                              {/* Selected Asset Details Sidebar Card */}
                              <div className="space-y-4">
                                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Asset Details</h4>
                                {selectedAttackNode ? (
                                  <div className="card p-4 space-y-4">
                                    <div className="flex justify-between items-start border-b border-white/5 pb-2.5">
                                      <div>
                                        <h5 className="text-xs font-bold text-slate-200">{selectedAttackNode.label}</h5>
                                        <span className="text-[9px] text-[#00d4ff] uppercase tracking-wider font-mono">{selectedAttackNode.type}</span>
                                      </div>
                                      <span className={`badge uppercase ${
                                        selectedAttackNode.details?.status === 'compromised' || selectedAttackNode.details?.exfiltration_status === 'exfiltrated' ? 'badge-critical' : 'badge-warning'
                                      }`}>
                                        {selectedAttackNode.details?.status || selectedAttackNode.details?.exfiltration_status || 'SUSPICIOUS'}
                                      </span>
                                    </div>

                                    <div className="space-y-2.5 text-xs text-slate-400 font-mono">
                                      {selectedAttackNode.type === 'user' && (
                                        <>
                                          <p><span className="text-slate-500 font-bold">Email/User:</span> {selectedAttackNode.details?.username}</p>
                                          <p><span className="text-slate-500 font-bold">Department:</span> {selectedAttackNode.details?.department}</p>
                                          <p><span className="text-slate-500 font-bold">Access Level:</span> {selectedAttackNode.details?.access_level}</p>
                                          <p><span className="text-slate-500 font-bold">Compromised At:</span> {new Date(selectedAttackNode.details?.timestamp).toLocaleTimeString()}</p>
                                        </>
                                      )}
                                      {selectedAttackNode.type === 'device' && (
                                        <>
                                          <p><span className="text-slate-500 font-bold">Device Name:</span> {selectedAttackNode.details?.name}</p>
                                          <p><span className="text-slate-500 font-bold">Type:</span> {selectedAttackNode.details?.device_type}</p>
                                          <p><span className="text-slate-500 font-bold">Last Activity:</span> {new Date(selectedAttackNode.details?.last_activity).toLocaleTimeString()}</p>
                                        </>
                                      )}
                                      {selectedAttackNode.type === 'service' && (
                                        <>
                                          <p><span className="text-slate-500 font-bold">Service:</span> {selectedAttackNode.details?.name}</p>
                                          <p><span className="text-slate-500 font-bold">Auth Status:</span> {selectedAttackNode.details?.auth_status}</p>
                                          <p><span className="text-slate-500 font-bold">Data Accessed:</span> {selectedAttackNode.details?.data_accessed}</p>
                                        </>
                                      )}
                                      {selectedAttackNode.type === 'data' && (
                                        <>
                                          <p><span className="text-slate-500 font-bold">Database/Table:</span> {selectedAttackNode.details?.name}</p>
                                          <p><span className="text-slate-500 font-bold">Classification:</span> {selectedAttackNode.details?.sensitivity}</p>
                                          <p><span className="text-slate-500 font-bold">Exfiltrated At:</span> {new Date(selectedAttackNode.details?.access_timestamp).toLocaleTimeString()}</p>
                                        </>
                                      )}
                                    </div>
                                  </div>
                                ) : (
                                  <div className="card p-5 text-center text-slate-500 font-mono">Select a node to inspect parameters.</div>
                                )}

                                {/* Techniques Chains */}
                                <div className="card p-4 space-y-3 font-mono">
                                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">MITRE Chain Path</span>
                                  <div className="space-y-2">
                                    {attackGraph.edges.map((edge: any, idx: number) => (
                                      <div key={idx} className="p-2 bg-[#0d111a] rounded border border-white/5">
                                        <div className="flex justify-between items-center text-[10px] font-bold text-rose-400">
                                          <span>{edge.mitre_technique}</span>
                                          <span>+{edge.dwell_time_mins}m dwell</span>
                                        </div>
                                        <div className="text-[9px] text-slate-500 mt-1 uppercase">
                                          Phase: {edge.phase.replace('_', ' ')}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="text-center py-8 text-slate-500 font-mono text-xs">No attack graph compiled for this anomaly.</div>
                        )}
                      </div>
                    )}

                    {/* TAB 2: WHAT-IF SIMULATION */}
                    {inspectorTab === 'simulation' && (
                      <div className="space-y-6 animate-fade-in">
                        {simulationLoading ? (
                          <div className="text-center py-8 font-mono text-xs text-slate-500">Loading dynamic dry-run estimates...</div>
                        ) : simulationData ? (
                          <div className="space-y-5">
                            <div className="p-4 bg-[#1e293b]/20 border border-[#00d4ff]/20 rounded-xl space-y-3">
                              <h4 className="text-xs font-bold text-[#00d4ff] uppercase tracking-widest">Predicted Impact Analysis</h4>
                              <p className="text-xs text-slate-300">{simulationData.predicted_impact}</p>
                              
                              <div className="grid grid-cols-2 gap-4 pt-2 text-xs font-mono">
                                <div className="p-3 bg-white/5 rounded border border-white/5">
                                  <div className="text-slate-500 uppercase text-[9px]">Downtime Estimate</div>
                                  <div className="text-base text-amber-400 font-bold mt-1">{simulationData.predicted_downtime_sec} Seconds</div>
                                </div>
                                <div className="p-3 bg-white/5 rounded border border-white/5">
                                  <div className="text-slate-500 uppercase text-[9px]">Success Probability</div>
                                  <div className="text-base text-[#00ff88] font-bold mt-1">{simulationData.success_probability}%</div>
                                </div>
                                <div className="p-3 bg-white/5 rounded border border-white/5">
                                  <div className="text-slate-500 uppercase text-[9px]">Risk Profile</div>
                                  <div className={`text-base font-bold mt-1 ${
                                    simulationData.risk_assessment === 'CRITICAL' ? 'text-rose-500' :
                                    simulationData.risk_assessment === 'HIGH' ? 'text-orange-500' : 'text-emerald-400'
                                  }`}>{simulationData.risk_assessment}</div>
                                </div>
                                <div className="p-3 bg-white/5 rounded border border-white/5">
                                  <div className="text-slate-500 uppercase text-[9px]">Rollback Action</div>
                                  <div className="text-xs text-slate-300 mt-1">{simulationData.rollback_possible ? 'AVAILABLE' : 'MANUAL REQUIRED'}</div>
                                </div>
                              </div>
                            </div>

                            <div className="space-y-2">
                              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Dry-Run Remediation Command</h4>
                              <div className="terminal p-4 text-xs select-all cursor-pointer font-mono text-[#00ff88] bg-black/40">
                                {simulationData.action || selectedIncident.suggested_action}
                              </div>
                            </div>

                            <div className="p-4 bg-white/5 rounded-xl border border-white/5 space-y-2 text-xs">
                              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Before / After Metric Comparison</h4>
                              <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1 border-r border-white/5 pr-4">
                                  <div className="text-slate-500 text-[10px] uppercase font-bold">Current State</div>
                                  <p className="text-rose-400 font-bold">Active Memory Leak Loop</p>
                                  <p className="text-slate-400">Pod memory load: 94.2%</p>
                                  <p className="text-slate-400">Clients impacted: {simulationData.affected_users}</p>
                                </div>
                                <div className="space-y-1 pl-2">
                                  <div className="text-slate-500 text-[10px] uppercase font-bold">Predicted Post-Action State</div>
                                  <p className="text-[#00ff88] font-bold">Stable Base Metrics</p>
                                  <p className="text-slate-400">Pod memory load: 45.0%</p>
                                  <p className="text-slate-400">Client loss risk: 0</p>
                                </div>
                              </div>
                            </div>

                            <div className="space-y-2">
                              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Rollback Sequence</h4>
                              <p className="text-xs text-slate-500 italic">{simulationData.rollback_plan}</p>
                            </div>
                          </div>
                        ) : (
                          <div className="text-center py-8 font-mono text-xs text-slate-500">No simulation data generated yet.</div>
                        )}
                      </div>
                    )}

                    {/* TAB 3: REMEDIATION AGENT */}
                    {inspectorTab === 'options' && (
                      <div className="space-y-5 animate-fade-in">
                        <div className="flex justify-between items-center">
                          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Ranked Remediation Candidates</h4>
                          <span className="text-[10px] font-mono text-slate-500">Evaluated by RemediationAgent</span>
                        </div>

                        <div className="space-y-3">
                          {remediationOptions.map((opt, idx) => (
                            <div key={opt.id} className="p-4 bg-white/5 rounded-xl border border-white/5 hover:border-[#00ff88]/30 transition-all space-y-3">
                              <div className="flex justify-between items-start">
                                <div>
                                  <span className="text-xs font-bold font-mono text-[#00ff88]">#{idx + 1} Candidate: {opt.name}</span>
                                  <p className="text-[11px] text-slate-400 mt-1 font-sans">{opt.reasoning}</p>
                                </div>
                                <div className="text-right shrink-0">
                                  <span className="px-2 py-0.5 rounded-full text-[10px] bg-[#00ff88]/10 text-[#00ff88] border border-[#00ff88]/20 font-mono font-bold">
                                    Score: {Math.round(opt.composite_score)}
                                  </span>
                                </div>
                              </div>

                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[10px] font-mono text-slate-400 bg-black/20 p-2.5 rounded-lg">
                                <div><strong className="text-slate-500 uppercase">Success Probability:</strong> {opt.success_probability}%</div>
                                <div><strong className="text-slate-500 uppercase">Risk Level:</strong> {opt.risk_score}/100</div>
                                <div><strong className="text-slate-500 uppercase">Users Affected:</strong> {opt.user_impact}</div>
                                <div><strong className="text-slate-500 uppercase">Execution Cost:</strong> ${opt.cost}</div>
                                <div><strong className="text-slate-500 uppercase">Rollback path:</strong> {opt.rollback_difficulty}</div>
                                <div><strong className="text-slate-500 uppercase">Downtime Estimate:</strong> {opt.downtime_sec}s</div>
                                <div className="col-span-2"><strong className="text-slate-500 uppercase">Command:</strong> <code className="text-emerald-400">{opt.command}</code></div>
                              </div>

                              {selectedIncident.status === 'PENDING_APPROVAL' && (
                                <div className="flex justify-end pt-1">
                                  <button
                                    onClick={async () => {
                                      try {
                                        await api.executeRemediation(selectedIncident.id, opt.id);
                                        // Refresh Incident status
                                        const detail = await api.getIncidentDetail(selectedIncident.id);
                                        setSelectedIncident(detail);
                                        setInspectorTab('timeline');
                                      } catch (err) {
                                        console.error('Failed to trigger remediation option execution', err);
                                      }
                                    }}
                                    className="px-3.5 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-[10px] rounded transition-all uppercase tracking-wider"
                                  >
                                    Execute Option
                                  </button>
                                </div>
                              )}
                            </div>
                          ))}
                          {remediationOptions.length === 0 && (
                            <div className="text-center py-8 font-mono text-xs text-slate-500">No ranked remediation options compiled.</div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* TAB 4: RUNBOOK RAG */}
                    {inspectorTab === 'runbooks' && (
                      <div className="space-y-5 animate-fade-in">
                        <div className="flex justify-between items-center">
                          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Intelligent Runbook Matches</h4>
                          <span className="text-[10px] font-mono text-[#00d4ff]">RAG Relevance Scans</span>
                        </div>

                        {runbookFeedbackMsg && (
                          <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-[#00ff88] text-xs font-mono rounded-lg">
                            {runbookFeedbackMsg}
                          </div>
                        )}

                        <div className="space-y-4">
                          {runbooks.map((rb) => (
                            <div key={rb.id} className="p-4 bg-white/5 rounded-xl border border-white/5 hover:border-[#00d4ff]/30 transition-all space-y-3">
                              <div className="flex justify-between items-start">
                                <div>
                                  <span className="text-xs font-bold text-slate-200">{rb.title}</span>
                                  <p className="text-[11px] text-slate-400 mt-1">{rb.explanation}</p>
                                </div>
                                <div className="text-right shrink-0">
                                  <span className="px-2 py-0.5 rounded-full text-[10px] bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/20 font-mono font-bold">
                                    Relevance: {rb.relevance}%
                                  </span>
                                </div>
                              </div>

                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[10px] font-mono text-slate-400 bg-black/20 p-2.5 rounded-lg">
                                <div><strong className="text-slate-500 uppercase">Completeness:</strong> {rb.completeness}%</div>
                                <div><strong className="text-slate-500 uppercase">Recentness:</strong> {rb.recentness}/100</div>
                                <div><strong className="text-slate-500 uppercase">Complexity score:</strong> {rb.complexity}/10</div>
                                <div><strong className="text-slate-500 uppercase">Recovery delay:</strong> {rb.estimated_time_mins}m</div>
                              </div>

                              <div className="flex justify-between items-center pt-1 text-[11px] font-mono">
                                <span className="text-[#00d4ff] cursor-pointer hover:underline">View playbook steps</span>
                                <div className="flex gap-2">
                                  <button
                                    onClick={async () => {
                                      try {
                                        await api.submitRunbookFeedback(selectedIncident.id, rb.id, true);
                                        setRunbookFeedbackMsg(`Logged success feedback. Thank you for validating playbook relevance!`);
                                        setTimeout(() => setRunbookFeedbackMsg(''), 4000);
                                      } catch (err) {
                                        console.error('Feedback submit error:', err);
                                      }
                                    }}
                                    className="px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 text-[9px] rounded font-bold uppercase transition-all"
                                  >
                                    Solved Incident
                                  </button>
                                  <button
                                    onClick={async () => {
                                      try {
                                        await api.submitRunbookFeedback(selectedIncident.id, rb.id, false);
                                        setRunbookFeedbackMsg(`Logged failure feedback. Playbook weights adjusted descending.`);
                                        setTimeout(() => setRunbookFeedbackMsg(''), 4000);
                                      } catch (err) {
                                        console.error('Feedback submit error:', err);
                                      }
                                    }}
                                    className="px-2.5 py-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 text-[9px] rounded font-bold uppercase transition-all"
                                  >
                                    Failed / Ineffective
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                          {runbooks.length === 0 && (
                            <div className="text-center py-8 font-mono text-xs text-slate-500">No RAG runbooks recommended.</div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* TAB 5: DECISION DAG */}
                    {inspectorTab === 'graph' && (
                      <div className="space-y-4 animate-fade-in">
                        <div className="flex justify-between items-center mb-2">
                          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Self-Healing Decision Flowchart</h4>
                          <span className="text-[10px] font-mono text-slate-500">DAG Flowchart representation</span>
                        </div>

                        {/* Interactive Graph Node Renderer */}
                        <div className="flex flex-col items-center gap-6 p-4 bg-black/25 rounded-xl border border-white/5 font-mono text-xs">
                          {decisionGraph?.nodes?.map((node: any, idx: number) => (
                            <React.Fragment key={node.id}>
                              {idx > 0 && (
                                <div className="flex flex-col items-center">
                                  <span className="text-slate-600 text-[10px]">↓</span>
                                </div>
                              )}
                              <div className={`p-3.5 rounded-xl border w-full max-w-md ${
                                node.color === 'red' ? 'border-rose-500/30 bg-rose-950/10 text-rose-400' :
                                node.color === 'orange' ? 'border-amber-500/30 bg-amber-950/10 text-amber-400' :
                                node.color === 'blue' ? 'border-[#00d4ff]/30 bg-blue-950/10 text-[#00d4ff]' :
                                node.color === 'purple' ? 'border-purple-500/30 bg-purple-950/10 text-purple-400' :
                                'border-emerald-500/30 bg-emerald-950/10 text-[#00ff88]'
                              }`}>
                                <div className="flex justify-between font-bold">
                                  <span>{node.label}</span>
                                  <span className="text-[10px] uppercase opacity-75">{node.type}</span>
                                </div>
                                {node.metadata && (
                                  <div className="mt-2 text-[10px] text-slate-400 leading-tight space-y-1">
                                    {Object.entries(node.metadata).map(([key, val]: any) => (
                                      <div key={key}>
                                        <strong className="text-slate-300">{key}:</strong> {String(val)}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </React.Fragment>
                          ))}
                          {!decisionGraph && (
                            <div className="text-center py-8 font-mono text-xs text-slate-500">Generating decision DAG map...</div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* TAB 6: INTERACTIVE REPLAY */}
                    {inspectorTab === 'replay' && (
                      <div className="space-y-6 animate-fade-in font-mono text-xs">
                        <div className="flex flex-wrap justify-between items-center gap-4 bg-white/5 p-4 rounded-xl border border-white/5">
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => {
                                if (isPlayingReplay) {
                                  setIsPlayingReplay(false);
                                } else {
                                  if (replayIndex >= replayEvents.length - 1) {
                                    setReplayIndex(-1);
                                  }
                                  setIsPlayingReplay(true);
                                }
                              }}
                              className="px-3.5 py-1.5 bg-[#00ff88]/10 text-[#00ff88] border border-[#00ff88]/20 font-bold rounded uppercase transition-all tracking-wider text-[10px]"
                            >
                              {isPlayingReplay ? 'Pause' : 'Play Replay'}
                            </button>
                            
                            <button
                              onClick={() => {
                                setIsPlayingReplay(false);
                                setReplayIndex(-1);
                              }}
                              className="px-3.5 py-1.5 bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 font-bold rounded uppercase transition-all tracking-wider text-[10px]"
                            >
                              Reset
                            </button>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-slate-500 uppercase font-bold">Speed:</span>
                            {[1, 5, 10].map(s => (
                              <button
                                key={s}
                                onClick={() => setReplaySpeed(s as any)}
                                className={`px-2 py-1 rounded text-[10px] font-bold ${
                                  replaySpeed === s ? 'bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/20' : 'text-slate-500'
                                }`}
                              >
                                {s}x
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Animated Metrics Graph Simulation during Replay */}
                        <div className="p-4 bg-black/40 rounded-xl border border-white/5 space-y-3">
                          <div className="flex justify-between items-center">
                            <span className="text-slate-400 uppercase tracking-widest text-[9px] font-bold">Replay Metrics Stream Simulator</span>
                            <span className="text-[#00ff88] animate-pulse text-[10px]">● LIVE SIMULATION STREAM</span>
                          </div>
                          
                          {/* Animated progress bar */}
                          <div className="w-full bg-white/5 rounded-full h-1.5 border border-white/5 overflow-hidden">
                            <div
                              className="bg-[#00ff88] h-full transition-all duration-500"
                              style={{ width: `${((replayIndex + 1) / replayEvents.length) * 100}%` }}
                            />
                          </div>

                          <div className="grid grid-cols-3 gap-2 pt-1.5 text-center text-[10px]">
                            <div className="p-2 bg-white/5 rounded border border-white/5">
                              <span className="text-slate-500 block">CPU LOAD</span>
                              <span className="text-[#00d4ff] font-bold text-xs">
                                {replayIndex < 0 ? '30.2%' :
                                 replayIndex < 3 ? '42.1%' :
                                 replayIndex < 8 ? '96.4%' : '24.1%'}
                              </span>
                            </div>
                            <div className="p-2 bg-white/5 rounded border border-white/5">
                              <span className="text-slate-500 block">MEMORY USE</span>
                              <span className="text-rose-400 font-bold text-xs">
                                {replayIndex < 0 ? '45.0%' :
                                 replayIndex < 3 ? '52.0%' :
                                 replayIndex < 8 ? '94.2%' : '44.8%'}
                              </span>
                            </div>
                            <div className="p-2 bg-white/5 rounded border border-white/5">
                              <span className="text-slate-500 block">HTTP LATENCY</span>
                              <span className="text-amber-400 font-bold text-xs">
                                {replayIndex < 0 ? '45ms' :
                                 replayIndex < 3 ? '80ms' :
                                 replayIndex < 8 ? '1540ms' : '52ms'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Chronological Event Log Output list */}
                        <div className="space-y-3.5 pl-4 border-l border-white/10">
                          {replayEvents.slice(0, replayIndex + 1).map((evt, idx) => (
                            <div key={idx} className="relative animate-slide-in">
                              <span className="absolute -left-[22px] top-1.5 w-2.5 h-2.5 rounded-full bg-[#00ff88] border-2 border-slate-900" />
                              <div className="flex justify-between font-bold text-slate-300">
                                <span>{evt.event_type} (Decision: {evt.decision})</span>
                                <span className="text-[10px] text-slate-500">Agent: {evt.agent_name}</span>
                              </div>
                              <p className="text-[11px] text-slate-400 leading-normal mt-1">{evt.reasoning}</p>
                              {evt.event_data && Object.keys(evt.event_data).length > 0 && (
                                <pre className="p-2 bg-black/30 border border-white/5 rounded text-[10px] text-emerald-400 overflow-x-auto mt-2 leading-relaxed">
                                  {JSON.stringify(evt.event_data, null, 2)}
                                </pre>
                              )}
                            </div>
                          ))}
                          {replayIndex === -1 && (
                            <div className="text-center py-8 text-slate-500 italic">Click Play to start the chronological incident walkthrough.</div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="card p-12 flex flex-col items-center justify-center text-center">
                    <Activity className="w-12 h-12 text-slate-600 mb-4 animate-pulse-glow" />
                    <h4 className="text-sm font-bold text-slate-400">Select an incident to view audit details and timeline replays</h4>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: CLUSTER TOPOLOGY */}
          {activeTab === 'topology' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
              {/* Node / Pod Visualizer Map */}
              <div className="lg:col-span-2 space-y-6">
                <div className="flex justify-between items-center">
                  <div>
                    <h2 className="text-lg font-bold text-slate-200">Pod Cluster Monitor</h2>
                    <p className="text-xs text-slate-500 mt-1">Select visual node blocks to inspect container live metrics, logs, and scale states</p>
                  </div>
                </div>

                <div className="p-6 bg-[#111827] border border-white/5 rounded-2xl space-y-6 relative">
                  {/* Grid of Nodes and Pods */}
                  {topology ? (
                    <div className="space-y-8">
                      {topology.nodes.map(node => (
                        <div key={node.name} className="p-4 bg-[#1a1f2e] border border-white/5 rounded-xl space-y-3">
                          <div className="flex justify-between items-center text-xs border-b border-white/5 pb-2">
                            <div className="flex items-center gap-2">
                              <Server className="w-4 h-4 text-[#00ff88]" />
                              <span className="font-bold text-slate-300">{node.name}</span>
                              <span className="text-[10px] text-slate-500">({node.role})</span>
                            </div>
                            <div className="flex gap-4 text-[10px] text-slate-400 font-mono">
                              <span>CPU: {node.cpu_usage}%</span>
                              <span>MEM: {node.memory_usage}%</span>
                            </div>
                          </div>

                          {/* Pod elements mapped to current node */}
                          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                            {topology.pods
                              .filter(p => p.node === node.name)
                              .map(pod => (
                                <div
                                  key={pod.name}
                                  onClick={() => selectPodForInspection(pod)}
                                  className={`p-3 bg-[#111827] border cursor-pointer rounded-lg hover:border-emerald-500 transition-all flex flex-col justify-between ${selectedPod?.name === pod.name ? 'border-[#00ff88] bg-emerald-500/5' : 'border-white/5'}`}
                                >
                                  <div className="flex justify-between items-start gap-2 mb-2">
                                    <span className="text-xs font-bold truncate text-slate-300" title={pod.name}>
                                      {pod.service}
                                    </span>
                                    <div className="relative flex h-2 w-2 shrink-0">
                                      <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${pod.status === 'Running' ? 'bg-[#00ff88]' : 'bg-[#ff3366]'}`}></span>
                                      <span className={`relative inline-flex rounded-full h-2 w-2 ${pod.status === 'Running' ? 'bg-[#00ff88]' : 'bg-[#ff3366]'}`}></span>
                                    </div>
                                  </div>

                                  <div className="space-y-1 text-[9px] font-mono text-slate-500">
                                    <div className="flex justify-between">
                                      <span>CPU</span>
                                      <span className="text-slate-400">{pod.cpu_usage}%</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>MEM</span>
                                      <span className="text-slate-400">{pod.memory_usage}%</span>
                                    </div>
                                  </div>
                                </div>
                              ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="h-64 flex items-center justify-center text-slate-500 font-mono text-xs">
                      Syncing cluster statusExporter maps...
                    </div>
                  )}
                </div>

                {/* Guarded Console Terminal Panel */}
                <div className="card p-5">
                  <h4 className="text-xs font-bold text-slate-200 uppercase tracking-widest mb-3 flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-[#00ff88]" /> Guarded Infrastructure Terminal
                  </h4>
                  
                  <div className="flex gap-3 mb-4">
                    <input
                      type="text"
                      value={commandInput}
                      onChange={e => setCommandInput(e.target.value)}
                      placeholder="kubectl rollout restart deployment/payment-gateway"
                      className="flex-1 px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-lg focus:outline-none focus:border-emerald-500 text-xs font-mono text-slate-300"
                    />
                    <button
                      onClick={submitGuardedCommand}
                      disabled={commandLoading}
                      className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-xs rounded-lg transition-all flex items-center gap-2"
                    >
                      {commandLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                      EXECUTE
                    </button>
                  </div>

                  {/* Terminal Execution Result */}
                  {commandResult && (
                    <div className="terminal p-4 space-y-3 text-xs leading-relaxed animate-fade-in">
                      <div className="flex justify-between items-center border-b border-white/5 pb-2">
                        <span className="font-bold text-slate-400">Enkrypt AI Safety Envelope Scan Report</span>
                        <span className={`badge ${commandResult.status === 'ALLOWED' ? 'badge-success' : 'badge-critical'}`}>
                          {commandResult.status}
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        <p className="text-slate-500">Command evaluated: <span className="text-slate-200 font-mono">{commandResult.command}</span></p>
                        <p className="text-slate-500">Safety assessment risk score: <span className="font-mono font-bold text-[#00ff88]">{Math.round(commandResult.risk_score * 100)}%</span></p>
                        <p className="text-slate-400 italic">Assessment: {commandResult.risk_assessment}</p>
                      </div>
                      {commandResult.execution_output && (
                        <div className="pt-2 border-t border-white/5">
                          <p className="text-slate-500 mb-1">Standard output logs:</p>
                          <pre className="text-[#00ff88] font-mono whitespace-pre-wrap">{commandResult.execution_output}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Side Spec Inspector / Log Streamer */}
              <div className="lg:col-span-1 space-y-6">
                {selectedPod ? (
                  <div className="card p-5 space-y-5 animate-fade-in">
                    <div>
                      <h3 className="text-base font-bold text-slate-200 truncate" title={selectedPod.name}>
                        {selectedPod.service}
                      </h3>
                      <p className="text-[10px] text-slate-500 font-mono mt-1">Namespace: {selectedPod.namespace}</p>
                    </div>

                    {/* Stats Specs */}
                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div className="p-3 bg-white/5 border border-white/5 rounded-xl">
                        <span className="text-slate-500 block mb-1">Status</span>
                        <span className="font-bold text-emerald-400 uppercase tracking-wider">{selectedPod.status}</span>
                      </div>
                      <div className="p-3 bg-white/5 border border-white/5 rounded-xl">
                        <span className="text-slate-500 block mb-1">Node host</span>
                        <span className="font-semibold text-slate-300">{selectedPod.node}</span>
                      </div>
                      <div className="p-3 bg-white/5 border border-white/5 rounded-xl">
                        <span className="text-slate-500 block mb-1">CPU cores</span>
                        <span className="font-mono font-bold text-slate-300">{selectedPod.cpu_usage}%</span>
                      </div>
                      <div className="p-3 bg-white/5 border border-white/5 rounded-xl">
                        <span className="text-slate-500 block mb-1">Memory usage</span>
                        <span className="font-mono font-bold text-slate-300">{selectedPod.memory_usage}%</span>
                      </div>
                    </div>

                    {/* Streaming container logs console */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex justify-between items-center">
                        <span>Live Container Feed</span>
                        <span className="text-[9px] text-[#00ff88] animate-pulse">STREAMING</span>
                      </h4>

                      <div className="terminal p-4 h-64 overflow-y-auto font-mono text-[10px] text-slate-300 space-y-1.5">
                        {podLogStream.map((log, i) => (
                          <div key={i} className="whitespace-pre-wrap leading-relaxed">
                            {log}
                          </div>
                        ))}
                        <div ref={logTerminalEndRef}></div>
                      </div>
                    </div>

                    {/* Troubleshooting Shortcuts */}
                    <div className="pt-4 border-t border-white/5 space-y-2">
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1.5">Manual Remedies</h4>
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          onClick={() => {
                            setCommandInput(`kubectl scale deployment/${selectedPod.service} --replicas=3 -n ${selectedPod.namespace}`);
                            submitGuardedCommand();
                          }}
                          className="py-2 bg-white/5 hover:bg-white/10 text-slate-300 font-semibold text-[10px] rounded border border-white/10 transition-all uppercase"
                        >
                          Scale Out (x3)
                        </button>
                        <button
                          onClick={() => {
                            setCommandInput(`kubectl rollout restart deployment/${selectedPod.service} -n ${selectedPod.namespace}`);
                            submitGuardedCommand();
                          }}
                          className="py-2 bg-white/5 hover:bg-white/10 text-slate-300 font-semibold text-[10px] rounded border border-white/10 transition-all uppercase"
                        >
                          Rolling Restart
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="card p-12 text-center flex flex-col justify-center items-center">
                    <Server className="w-10 h-10 text-slate-600 mb-3 animate-pulse-glow" />
                    <h4 className="text-xs font-bold text-slate-400">Select a cluster node pod to stream live output and deploy remedies</h4>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: SAFETY AUDIT LOGS */}
          {activeTab === 'audit' && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-bold text-slate-100">Tamper-Evident Audit Ledger</h2>
                  <p className="text-xs text-slate-500 mt-1">Cryptographically chained execution trail validating platform action integrity</p>
                </div>
                
                <div className="flex gap-3">
                  <button
                    onClick={verifyAuditLedger}
                    disabled={ledgerValidating}
                    className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-xs rounded-lg transition-all"
                  >
                    VERIFY LEDGER INTEGRITY
                  </button>
                  
                  <button
                    onClick={archiveAuditLedger}
                    className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 font-semibold text-xs rounded-lg transition-all"
                  >
                    ARCHIVE TO S3
                  </button>
                </div>
              </div>

              {/* Ledger verification panel reports */}
              {ledgerValidationResult && (
                <div className={`p-4 rounded-xl border animate-fade-in text-sm ${ledgerValidationResult.valid ? 'bg-emerald-950/20 border-emerald-500/20 text-[#00ff88]' : 'bg-rose-950/20 border-rose-500/20 text-rose-400'}`}>
                  <div className="flex items-center gap-2 font-bold mb-1">
                    {ledgerValidationResult.valid ? <CheckCircle className="w-5 h-5 shrink-0" /> : <XCircle className="w-5 h-5 shrink-0" />}
                    <span>{ledgerValidationResult.valid ? 'LEDGER VERIFICATION PASSED' : 'LEDGER VERIFICATION FAILED'}</span>
                  </div>
                  <p className="text-xs text-slate-400 ml-7">{ledgerValidationResult.message}</p>
                </div>
              )}

              {/* Ledger table */}
              <div className="card p-5">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/5 text-slate-500 font-bold">
                        <th className="py-2.5">ID</th>
                        <th className="py-2.5">Command</th>
                        <th className="py-2.5">Status</th>
                        <th className="py-2.5">Risk Score</th>
                        <th className="py-2.5">Performed By</th>
                        <th className="py-2.5">Block Hash</th>
                        <th className="py-2.5">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {auditEntries.map(entry => (
                        <tr key={entry.id} className="hover:bg-white/5 transition-all font-mono">
                          <td className="py-3 font-semibold text-slate-500">#{entry.id}</td>
                          <td className="py-3 text-slate-200 font-sans max-w-xs truncate" title={entry.command_checked}>{entry.command_checked}</td>
                          <td className="py-3">
                            <span className={`badge ${entry.status === 'ALLOWED' ? 'badge-success' : 'badge-critical'}`}>
                              {entry.status}
                            </span>
                          </td>
                          <td className="py-3 font-bold text-slate-400">{Math.round(entry.risk_score * 100)}%</td>
                          <td className="py-3 font-sans text-slate-400">{entry.performed_by.split('@')[0]}</td>
                          <td className="py-3 text-slate-500 text-[10px]" title={entry.hash || ''}>
                            {entry.hash ? `${entry.hash.substring(0, 8)}...` : 'genesis'}
                          </td>
                          <td className="py-3 text-slate-500 text-[10px] font-sans">
                            {new Date(entry.timestamp).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                      {auditEntries.length === 0 && (
                        <tr>
                          <td colSpan={7} className="py-8 text-center text-slate-500 font-mono text-xs">
                            No ledger actions written to memory.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: PROMPTS & RAG STORE */}
          {activeTab === 'prompts' && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-bold text-slate-100">CRISPE Prompts & Vector RAG Store</h2>
                  <p className="text-xs text-slate-500 mt-1">Structured agent directives linked to Qdrant vector database similarity match runbooks</p>
                </div>
              </div>

              {/* RAG interactive query console */}
              <div className="card p-5 space-y-4">
                <h4 className="text-xs font-bold text-slate-200 uppercase tracking-widest">Similarity Search Console</h4>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={ragQuery}
                    onChange={e => setRagQuery(e.target.value)}
                    placeholder="Search for OOM or CPU resolution runbooks..."
                    className="flex-1 px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-lg focus:outline-none focus:border-emerald-500 text-xs text-slate-300"
                  />
                  <button
                    onClick={runRAGSearch}
                    disabled={ragLoading}
                    className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-xs rounded-lg transition-all flex items-center gap-2"
                  >
                    {ragLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
                    QUERY
                  </button>
                </div>

                {/* Similarity query results */}
                {ragResults.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 animate-fade-in">
                    {ragResults.map((res, i) => (
                      <div key={i} className="p-4 bg-white/5 border border-white/5 rounded-xl space-y-2">
                        <div className="flex justify-between items-start gap-2">
                          <h5 className="text-xs font-bold text-slate-200 line-clamp-1">{res.title}</h5>
                          <span className="font-mono text-[9px] text-[#00ff88] bg-emerald-950/20 border border-emerald-500/20 px-1.5 py-0.5 rounded shrink-0">
                            Score: {Math.round(res.score * 100)}%
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 line-clamp-4">{res.content}</p>
                        <div className="flex gap-1 flex-wrap pt-1">
                          {res.tags.map((tag: string) => (
                            <span key={tag} className="text-[9px] font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded">
                              #{tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Prompt template list */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {prompts.map(pr => (
                  <div key={pr.id} className="p-5 card space-y-4">
                    <div className="flex justify-between items-start border-b border-white/5 pb-3">
                      <div>
                        <h4 className="text-sm font-bold text-slate-200">{pr.name}</h4>
                        <span className="text-[10px] text-[#00d4ff] font-mono">{pr.id}</span>
                      </div>
                      <span className="badge badge-info uppercase text-[9px]">{pr.category}</span>
                    </div>

                    <div className="space-y-2.5 text-xs text-slate-400">
                      <p><span className="text-slate-500 font-bold">CAPACITY:</span> {pr.capacity}</p>
                      <p><span className="text-slate-500 font-bold">ROLE:</span> {pr.role}</p>
                      <p><span className="text-slate-500 font-bold">INTENT:</span> {pr.intent}</p>
                      <p><span className="text-slate-500 font-bold">SUBJECT:</span> {pr.subject}</p>
                      <p><span className="text-slate-500 font-bold">EVALUATION:</span> {pr.evaluation}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 6: OBSERVABILITY TRACES */}
          {activeTab === 'observability' && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-bold text-slate-100">AI Observability & Trace Aggregations</h2>
                  <p className="text-xs text-slate-500 mt-1">OpenTelemetry correlated steps tracking routing latency and model token consumption metrics</p>
                </div>
              </div>

              {/* Aggregation summary banner cards */}
              {obsSummary && (
                <div className="grid grid-cols-1 md:grid-cols-5 gap-5">
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl">
                    <span className="text-[10px] text-slate-500 block uppercase tracking-widest font-bold">Total Operations</span>
                    <span className="text-xl font-bold text-slate-200 mt-1 block font-mono">{obsSummary.total_traces}</span>
                  </div>
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl">
                    <span className="text-[10px] text-slate-500 block uppercase tracking-widest font-bold">Latency Average</span>
                    <span className="text-xl font-bold text-[#00d4ff] mt-1 block font-mono">{obsSummary.avg_latency_ms} ms</span>
                  </div>
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl">
                    <span className="text-[10px] text-slate-500 block uppercase tracking-widest font-bold">Model Input Tokens</span>
                    <span className="text-xl font-bold text-slate-200 mt-1 block font-mono">{obsSummary.total_input_tokens.toLocaleString()}</span>
                  </div>
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl">
                    <span className="text-[10px] text-slate-500 block uppercase tracking-widest font-bold">Model Output Tokens</span>
                    <span className="text-xl font-bold text-slate-200 mt-1 block font-mono">{obsSummary.total_output_tokens.toLocaleString()}</span>
                  </div>
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl">
                    <span className="text-[10px] text-slate-500 block uppercase tracking-widest font-bold">Workflow Errors</span>
                    <span className="text-xl font-bold text-rose-500 mt-1 block font-mono">{obsSummary.error_count}</span>
                  </div>
                </div>
              )}

              {/* Trace log list */}
              <div className="card p-5">
                <h4 className="text-xs font-bold text-slate-200 uppercase tracking-widest mb-4">Correlation Step Traces</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead>
                      <tr className="border-b border-white/5 text-slate-500 font-bold">
                        <th className="py-2.5">ID</th>
                        <th className="py-2.5">Correlation ID</th>
                        <th className="py-2.5">Step Name</th>
                        <th className="py-2.5">Tokens (In/Out)</th>
                        <th className="py-2.5">Latency</th>
                        <th className="py-2.5">Status</th>
                        <th className="py-2.5">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {obsTraces.map(trace => (
                        <tr key={trace.id} className="hover:bg-white/5 transition-all">
                          <td className="py-3 text-slate-500">#{trace.id}</td>
                          <td className="py-3 text-[#00d4ff] font-bold">{trace.correlation_id}</td>
                          <td className="py-3 text-slate-200">{trace.step_name}</td>
                          <td className="py-3 text-slate-400">
                            {trace.input_tokens || 0} / {trace.output_tokens || 0}
                          </td>
                          <td className="py-3 text-slate-400">{trace.latency_ms.toFixed(1)} ms</td>
                          <td className="py-3">
                            <span className={`badge ${trace.status === 'success' ? 'badge-success' : 'badge-critical'}`}>
                              {trace.status}
                            </span>
                          </td>
                          <td className="py-3 text-slate-500 text-[10px] font-sans">
                            {new Date(trace.timestamp).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                      {obsTraces.length === 0 && (
                        <tr>
                          <td colSpan={7} className="py-8 text-center text-slate-500 font-mono text-xs">
                            No active telemetry span traces loaded.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: SECURITY SETTINGS */}
          {activeTab === 'settings' && (
            <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
              <div>
                <h2 className="text-2xl font-bold text-slate-100">Administrator Security Configurations</h2>
                <p className="text-xs text-slate-500 mt-1">Configure dual-factor multi-factor authenticator enrollment challenges</p>
              </div>

              <div className="card p-6 space-y-6">
                <div className="flex justify-between items-center border-b border-white/5 pb-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-200">Google Authenticator MFA Gate</h3>
                    <p className="text-xs text-slate-500 mt-1">Enforce X-MFA-Token headers verification checks during logins</p>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {user?.mfa_enabled ? (
                      <button
                        onClick={disableMFA}
                        className="px-4 py-2 bg-rose-600/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/25 rounded-lg text-xs font-bold transition-all"
                      >
                        DEACTIVATE MFA
                      </button>
                    ) : (
                      <button
                        onClick={triggerMFASetup}
                        className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-xs rounded-lg transition-all"
                      >
                        SET UP MFA SECRET
                      </button>
                    )}
                  </div>
                </div>

                {mfaStatusMsg && (
                  <p className="text-xs font-semibold text-[#00ff88] bg-emerald-950/20 border border-emerald-500/20 p-3 rounded-lg">
                    {mfaStatusMsg}
                  </p>
                )}

                {/* MFA Secret setup block */}
                {mfaSecretData && (
                  <div className="space-y-6 pt-2 animate-fade-in">
                    <div className="flex flex-col md:flex-row gap-6 items-center">
                      <div className="bg-white p-2.5 rounded-xl border border-white/10 shrink-0">
                        <img
                          src={mfaSecretData.qr_uri}
                          alt="Google QR code"
                          className="w-40 h-40"
                        />
                      </div>

                      <div className="space-y-3">
                        <h4 className="text-xs font-bold text-slate-200 uppercase tracking-widest">Secret Key Pairing</h4>
                        <p className="text-xs text-slate-400 leading-relaxed">
                          Scan the QR code using Google Authenticator, Duo Mobile, or compatible TOTP manager. Alternatively, copy the base32 key manually:
                        </p>
                        <p className="font-mono text-sm font-black text-[#00ff88] tracking-wider select-all bg-white/5 px-3 py-1.5 rounded-lg border border-white/5 inline-block">
                          {mfaSecretData.secret}
                        </p>
                      </div>
                    </div>

                    <div className="p-4 bg-[#1a1f2e] border border-white/5 rounded-xl space-y-3">
                      <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest">
                        Submit Totp Verification Code
                      </label>
                      <div className="flex gap-3">
                        <input
                          type="text"
                          maxLength={6}
                          value={mfaSetupCode}
                          onChange={e => setMfaSetupCode(e.target.value)}
                          placeholder="000000"
                          className="w-32 px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-lg text-center font-mono tracking-widest text-[#00ff88] text-sm focus:outline-none"
                        />
                        <button
                          onClick={verifyAndEnableMFA}
                          className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-xs rounded-lg transition-all"
                        >
                          VERIFY KEY
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* GOVERNANCE AUTONOMOUS REMEDIATION POLICY PANEL */}
              {user?.role === 'admin' && (
                <div className="card p-6 space-y-6">
                  <div>
                    <h3 className="text-sm font-bold text-slate-200">Autopilot Governance & Safety Gate Settings</h3>
                    <p className="text-xs text-slate-500 mt-1">
                      Configure autonomous execution levels, restricted services list, rate limiting, and blast radius guards.
                    </p>
                  </div>

                  <form onSubmit={handleGovConfigSubmit} className="space-y-4 text-xs">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Remediation Autonomy Mode</label>
                        <select
                          value={govMode}
                          onChange={e => setGovMode(e.target.value)}
                          className="w-full px-3 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none focus:border-[#00ff88]/30 font-mono text-xs"
                        >
                          <option value="MANUAL">MANUAL (Default - Always require human override)</option>
                          <option value="POLICY_BASED">POLICY-BASED (Recommended - Auto-run based on rules)</option>
                          <option value="SUPERVISED">SUPERVISED (Advanced - Auto-run with live operator oversight)</option>
                          <option value="SEMI_AUTONOMOUS">SEMI_AUTONOMOUS (Legacy - Auto-run low-risk, require approval for high-risk)</option>
                          <option value="FULLY_AUTONOMOUS">FULLY_AUTONOMOUS (Legacy - Auto-run all actions meeting safety limits)</option>
                        </select>
                      </div>

                      <div className="space-y-1">
                        <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Min. Confidence Score Gate (%)</label>
                        <input
                          type="number"
                          required
                          min="0"
                          max="100"
                          value={govMinConfidence}
                          onChange={e => setGovMinConfidence(Number(e.target.value))}
                          className="w-full px-3 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none focus:border-[#00ff88]/30 font-mono text-xs"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Rate Limit (Max executions/min)</label>
                        <input
                          type="number"
                          required
                          min="1"
                          max="60"
                          value={govRateLimit}
                          onChange={e => setGovRateLimit(Number(e.target.value))}
                          className="w-full px-3 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none focus:border-[#00ff88]/30 font-mono text-xs"
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Max. Blast Radius (Services count)</label>
                        <input
                          type="number"
                          required
                          min="1"
                          value={govMaxBlastRadius}
                          onChange={e => setGovMaxBlastRadius(Number(e.target.value))}
                          className="w-full px-3 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none focus:border-[#00ff88]/30 font-mono text-xs"
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Restricted Service Names (Comma-separated)</label>
                      <input
                        type="text"
                        placeholder="e.g. payment, billing"
                        value={govRestrictedServices}
                        onChange={e => setGovRestrictedServices(e.target.value)}
                        className="w-full px-3 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none focus:border-[#00ff88]/30 font-mono text-xs"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Low Risk Command Substrings (Comma-separated)</label>
                      <input
                        type="text"
                        placeholder="e.g. restart_pod, scale_service"
                        value={govLowRiskActions}
                        onChange={e => setGovLowRiskActions(e.target.value)}
                        className="w-full px-3 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none focus:border-[#00ff88]/30 font-mono text-xs"
                      />
                    </div>

                    {govMsg && (
                      <p className="text-xs font-semibold text-[#00ff88] bg-emerald-950/20 border border-emerald-500/20 p-2.5 rounded-lg">
                        {govMsg}
                      </p>
                    )}

                    <button
                      type="submit"
                      disabled={govLoading}
                      className="w-full py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold rounded-lg transition-all uppercase tracking-wider text-[10px]"
                    >
                      {govLoading ? 'Updating settings...' : 'Save Governance policy'}
                    </button>
                  </form>
                  {/* POLICY RULES LIST PANEL */}
                  <div className="card p-6 space-y-4 border border-white/5">
                    <div>
                      <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest">Active Policy Rules Configuration</h4>
                      <p className="text-xs text-slate-500 mt-1">Manage granular conditions and auto-execution triggers.</p>
                    </div>

                    <div className="space-y-4">
                      {Array.isArray(policies) && policies.filter((p: any) => p && typeof p === 'object' && 'id' in p).map((policy) => {
                        let conds: any = {};
                        try {
                          conds = JSON.parse(policy.conditions_json);
                        } catch (e) {}

                        let actions: string[] = [];
                        try {
                          actions = JSON.parse(policy.actions_json);
                        } catch (e) {}

                        let exceptions: string[] = [];
                        try {
                          exceptions = JSON.parse(policy.exceptions_json || '[]');
                        } catch (e) {}

                        return (
                          <div key={policy.id} className="p-4 bg-white/5 border border-white/5 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs">
                            <div className="space-y-2 max-w-md">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-300">{policy.name}</span>
                                {policy.enabled ? (
                                  <span className="badge badge-success py-0.5 text-[9px]">ENABLED</span>
                                ) : (
                                  <span className="badge badge-info py-0.5 text-[9px]">DISABLED</span>
                                )}
                              </div>
                              <p className="text-slate-500 text-[11px] leading-relaxed">
                                {policy.description}
                              </p>
                              
                              <div className="flex flex-wrap gap-2 text-[10px] font-mono text-slate-400">
                                <span className="bg-white/5 px-2 py-0.5 rounded border border-white/5">
                                  Type: {conds.incident_type || conds.service_type || conds.service || 'Global'}
                                </span>
                                <span className="bg-white/5 px-2 py-0.5 rounded border border-white/5">
                                  Actions: {actions.join(', ')}
                                </span>
                                {exceptions.length > 0 && (
                                  <span className="bg-rose-950/20 text-rose-400 border border-rose-500/25 px-2 py-0.5 rounded">
                                    Exempt: {exceptions.join(', ')}
                                  </span>
                                )}
                                {policy.approval_required && (
                                  <span className="bg-amber-950/20 text-amber-400 border border-amber-500/25 px-2 py-0.5 rounded">
                                    Require SRE approval
                                  </span>
                                )}
                              </div>
                            </div>

                            <button
                              onClick={() => togglePolicyAction(policy.id)}
                              className={`px-4 py-2 rounded-lg font-bold text-[10px] transition-all uppercase tracking-wider shrink-0 ${
                                policy.enabled 
                                  ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20' 
                                  : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-[#00ff88] border border-emerald-500/20'
                              }`}
                            >
                              {policy.enabled ? 'DISABLE' : 'ENABLE'}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* ACTIVE USER SESSIONS PANEL */}
              <div className="card p-6 space-y-6">
                <div>
                  <h3 className="text-sm font-bold text-slate-200">Active Identity Sessions</h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Manage and revoke active login sessions and OAuth tokens for this account.
                  </p>
                </div>

                <div className="space-y-3">
                  {sessions.map((sess: any) => (
                    <div key={sess.id} className="p-4 bg-white/5 border border-white/5 rounded-xl flex items-center justify-between text-xs">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-300 font-mono">{sess.ip_address || '127.0.0.1'}</span>
                          {sess.is_revoked ? (
                            <span className="badge badge-critical py-0.5 text-[9px]">REVOKED</span>
                          ) : (
                            <span className="badge badge-success py-0.5 text-[9px]">ACTIVE</span>
                          )}
                        </div>
                        <p className="text-slate-500 text-[10px] truncate max-w-sm" title={sess.user_agent}>
                          {sess.user_agent || 'Mozilla/5.0'}
                        </p>
                        <p className="text-[10px] text-slate-600">
                          Expires: {new Date(sess.expires_at).toLocaleString()}
                        </p>
                      </div>

                      {!sess.is_revoked && (
                        <button
                          onClick={() => revokeSessionAction(sess.id)}
                          className="px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 hover:border-rose-500/30 rounded-lg font-bold text-[10px] transition-all uppercase"
                        >
                          REVOKE
                        </button>
                      )}
                    </div>
                  ))}
                  {sessions.length === 0 && (
                    <p className="text-xs text-slate-500 font-mono text-center py-4">No active session records found.</p>
                  )}
                </div>
              </div>

              {/* DEMO MODE CONTROL SECTION */}
              <div className="card p-6 space-y-6">
                <div>
                  <h3 className="text-sm font-bold text-slate-200">Demo Mode & Telemetry Injection Controller</h3>
                  <p className="text-xs text-slate-500 mt-1">Inject simulated production telemetry failures to demonstrate autonomous self-healing, prompt injection safety gates, and Slack coordination.</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <button
                    onClick={() => triggerDemoScenario('CPU_SPIKE')}
                    disabled={demoLoading}
                    className="px-4 py-3 bg-gradient-to-r from-blue-600/30 to-indigo-600/30 hover:from-blue-600/40 hover:to-indigo-600/40 border border-indigo-500/30 rounded-xl text-slate-200 font-bold text-xs transition-all flex flex-col items-center justify-center gap-2"
                  >
                    <Cpu className="w-5 h-5 text-indigo-400" />
                    <span>CPU EXHAUSTION</span>
                  </button>
                  
                  <button
                    onClick={() => triggerDemoScenario('DISK_FULL')}
                    disabled={demoLoading}
                    className="px-4 py-3 bg-gradient-to-r from-amber-600/30 to-orange-600/30 hover:from-amber-600/40 hover:to-orange-600/40 border border-orange-500/30 rounded-xl text-slate-200 font-bold text-xs transition-all flex flex-col items-center justify-center gap-2"
                  >
                    <Database className="w-5 h-5 text-orange-400" />
                    <span>DISK PARTITION FULL</span>
                  </button>

                  <button
                    onClick={() => triggerDemoScenario('UNAUTHORIZED_ACCESS')}
                    disabled={demoLoading}
                    className="px-4 py-3 bg-gradient-to-r from-rose-600/30 to-purple-600/30 hover:from-rose-600/40 hover:to-purple-600/40 border border-purple-500/30 rounded-xl text-slate-200 font-bold text-xs transition-all flex flex-col items-center justify-center gap-2"
                  >
                    <Shield className="w-5 h-5 text-purple-400" />
                    <span>UNAUTHORIZED INTRUDER</span>
                  </button>

                  <button
                    onClick={() => triggerDemoScenario('PHISHING_ATTACK')}
                    disabled={demoLoading}
                    className="px-4 py-3 bg-gradient-to-r from-violet-600/30 to-fuchsia-600/30 hover:from-violet-600/40 hover:to-fuchsia-600/40 border border-fuchsia-500/30 rounded-xl text-slate-200 font-bold text-xs transition-all flex flex-col items-center justify-center gap-2"
                  >
                    <Lock className="w-5 h-5 text-fuchsia-400" />
                    <span>PHISHING BREACH</span>
                  </button>

                  <button
                    onClick={() => triggerDemoScenario('DDOS_ATTACK')}
                    disabled={demoLoading}
                    className="px-4 py-3 bg-gradient-to-r from-red-600/30 to-rose-600/30 hover:from-red-600/40 hover:to-rose-600/40 border border-rose-500/30 rounded-xl text-slate-200 font-bold text-xs transition-all flex flex-col items-center justify-center gap-2"
                  >
                    <Activity className="w-5 h-5 text-rose-400" />
                    <span>DDoS BOTNET ATTACK</span>
                  </button>

                  <button
                    onClick={() => triggerDemoScenario('DATA_BREACH')}
                    disabled={demoLoading}
                    className="px-4 py-3 bg-gradient-to-r from-cyan-600/30 to-blue-600/30 hover:from-cyan-600/40 hover:to-blue-600/40 border border-blue-500/30 rounded-xl text-slate-200 font-bold text-xs transition-all flex flex-col items-center justify-center gap-2"
                  >
                    <AlertTriangle className="w-5 h-5 text-blue-400" />
                    <span>DATA BREACH LEAK</span>
                  </button>
                </div>

                {demoResultMsg && (
                  <p className="text-xs font-semibold text-[#00ff88] bg-emerald-950/20 border border-emerald-500/20 p-3 rounded-lg">
                    {demoResultMsg}
                  </p>
                )}

                {user?.role === 'admin' && (
                  <div className="border-t border-white/5 pt-4 flex justify-between items-center">
                     <div>
                       <h4 className="text-xs font-bold text-slate-300">Purge Demo Telemetry & Incidents</h4>
                       <p className="text-[10px] text-slate-500 mt-0.5">Reset database records back to a pristine state.</p>
                     </div>
                     <button
                       onClick={cleanupDemoDatabase}
                       disabled={demoLoading}
                       className="px-4 py-2 bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 text-rose-400 font-bold text-xs rounded-lg transition-all"
                     >
                       PURGE DATABASE
                     </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 8: KNOWLEDGE BASE STORE */}
          {activeTab === 'knowledge' && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h2 className="text-2xl font-bold text-slate-100">SecOps Knowledge Base & Playbook Manager</h2>
                <p className="text-xs text-slate-500 mt-1">
                  Upload runbooks, PDF SOPs, and recovery guides. Content is automatically parsed, split into 500-token chunks, and indexed into Qdrant for semantic RAG lookups.
                </p>
              </div>

              {/* Search & Filter Bar */}
              <div className="flex gap-3 bg-white/5 p-4 rounded-2xl border border-white/5 font-mono text-xs">
                <input
                  type="text"
                  placeholder="Query semantic playbook index (e.g. memory leak, oom troubleshooting)..."
                  value={kbSearchQuery}
                  onChange={e => setKbSearchQuery(e.target.value)}
                  className="flex-1 px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl text-slate-200 text-xs focus:outline-none"
                />
                <button
                  onClick={handleKbSearch}
                  className="px-5 py-2.5 bg-[#00ff88]/10 text-[#00ff88] border border-[#00ff88]/20 font-bold rounded-xl hover:bg-[#00ff88]/20 transition-all uppercase"
                >
                  Search Index
                </button>
                <button
                  onClick={() => {
                    setKbSearchQuery('');
                    fetchKbDocuments();
                  }}
                  className="px-4 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 rounded-xl transition-all uppercase"
                >
                  Reset
                </button>
              </div>

              {/* Two Column Layout */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Column 1: Document Upload & List */}
                <div className="lg:col-span-1 space-y-6">
                  {/* Upload Widget */}
                  <div className="card p-5 space-y-4">
                    <h3 className="text-xs font-bold text-[#00ff88] uppercase tracking-widest flex items-center gap-1.5">
                      <Upload className="w-4 h-4 text-[#00ff88]" /> Index Recovery Document
                    </h3>
                    
                    <form onSubmit={handleKbUpload} className="space-y-3.5 text-xs">
                      <div className="space-y-1">
                        <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Document Title</label>
                        <input
                          type="text"
                          required
                          placeholder="e.g. Memory Leak mitigation playbook"
                          value={kbUploadTitle}
                          onChange={e => setKbUploadTitle(e.target.value)}
                          className="w-full px-3.5 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Category</label>
                          <select
                            value={kbUploadCategory}
                            onChange={e => setKbUploadCategory(e.target.value)}
                            className="w-full px-3.5 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none"
                          >
                            <option value="runbooks">Runbook</option>
                            <option value="sops">SOP</option>
                            <option value="playbooks">Playbook</option>
                            <option value="guides">Guide</option>
                          </select>
                        </div>

                        <div className="space-y-1">
                          <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Subcategory</label>
                          <select
                            value={kbUploadSubcategory}
                            onChange={e => setKbUploadSubcategory(e.target.value)}
                            className="w-full px-3.5 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none"
                          >
                            <option value="kubernetes">Kubernetes</option>
                            <option value="aws">AWS Cloud</option>
                            <option value="security">Security Sec</option>
                            <option value="performance">Performance</option>
                          </select>
                        </div>
                      </div>

                      <div className="space-y-1">
                        <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Search Keywords / Tags</label>
                        <input
                          type="text"
                          placeholder="e.g. oom, restart, leak"
                          value={kbUploadTags}
                          onChange={e => setKbUploadTags(e.target.value)}
                          className="w-full px-3.5 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none"
                        />
                      </div>

                      {/* File selector input */}
                      <div className="space-y-1">
                        <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Source Document (PDF, DOCX, MD, TXT)</label>
                        <input
                          type="file"
                          required
                          onChange={e => {
                            if (e.target.files && e.target.files.length > 0) {
                              setKbUploadFile(e.target.files[0]);
                            }
                          }}
                          className="w-full p-2 bg-[#0d111a]/50 border border-white/5 border-dashed rounded-lg text-slate-400 cursor-pointer"
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={kbUploadLoading}
                        className="w-full py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold rounded-lg transition-all uppercase tracking-wider text-[10px]"
                      >
                        {kbUploadLoading ? 'Parsing & Embedding...' : 'Embed playbook'}
                      </button>
                    </form>
                  </div>

                  {/* Document List */}
                  <div className="space-y-3">
                    <div className="flex justify-between items-center mb-1">
                      <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Available Knowledge Files</h3>
                      <span className="text-[10px] bg-white/5 px-2 py-0.5 rounded text-slate-500 font-mono">
                        Count: {knowledgeDocs.length}
                      </span>
                    </div>

                    <div className="space-y-2.5 overflow-y-auto max-h-[calc(100vh-500px)] pr-2">
                      {knowledgeDocs.map(doc => (
                        <div
                          key={doc.id}
                          onClick={() => {
                            setSelectedDoc(doc);
                            setKbEditingContent(doc.content);
                            setKbEditingVersion(doc.version);
                            setKbIsEditing(false);
                          }}
                          className={`p-3.5 card cursor-pointer transition-all border ${
                            selectedDoc?.id === doc.id ? 'border-[#00ff88] bg-emerald-500/5' : 'border-white/5'
                          }`}
                        >
                          <div className="flex justify-between items-start mb-1 text-[10px] font-mono">
                            <span className="text-[#00d4ff] uppercase tracking-wider">{doc.category}</span>
                            <span className={`px-1.5 py-0.5 rounded uppercase ${
                              doc.status === 'approved' ? 'bg-emerald-500/10 text-[#00ff88]' : 'bg-amber-500/10 text-amber-400'
                            }`}>
                              {doc.status}
                            </span>
                          </div>
                          <h4 className="text-xs font-bold text-slate-200 line-clamp-1">{doc.title}</h4>
                          <div className="flex justify-between items-center mt-2.5 pt-2 border-t border-white/5 text-[9px] text-slate-500 font-mono">
                            <span>Author: {doc.author}</span>
                            <span>v{doc.version}</span>
                          </div>
                        </div>
                      ))}
                      {knowledgeDocs.length === 0 && (
                        <div className="text-center py-8 font-mono text-xs text-slate-500">No documents indexed in storage.</div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Column 2: Selected Document Detail Inspector */}
                <div className="lg:col-span-2">
                  {selectedDoc ? (
                    <div className="card p-6 space-y-6 animate-fade-in text-xs">
                      {/* Document Details Header */}
                      <div className="flex justify-between items-start border-b border-white/5 pb-4">
                        <div>
                          <h3 className="text-base font-bold text-slate-100">{selectedDoc.title}</h3>
                          <p className="text-[10px] text-slate-500 font-mono mt-1">File: {selectedDoc.filename} (Author: {selectedDoc.author})</p>
                        </div>

                        <div className="flex items-center gap-2">
                          {selectedDoc.status === 'draft' && user?.role === 'admin' && (
                            <button
                              onClick={() => handleKbApprove(selectedDoc.id)}
                              className="px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-[10px] rounded-lg transition-all uppercase tracking-wider"
                            >
                              Approve Playbook
                            </button>
                          )}
                          {user?.role === 'admin' && (
                            <button
                              onClick={() => handleKbArchive(selectedDoc.id)}
                              className="px-3 py-1.5 bg-white/5 hover:bg-rose-500/15 border border-white/10 hover:border-rose-500/20 text-rose-400 font-bold text-[10px] rounded-lg transition-all uppercase tracking-wider"
                            >
                              Archive
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Content Preview & Editing */}
                      <div className="space-y-4">
                        <div className="flex justify-between items-center">
                          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Document Content Payload</h4>
                          {!kbIsEditing ? (
                            <button
                              onClick={() => setKbIsEditing(true)}
                              className="text-[#00ff88] hover:underline flex items-center gap-1 font-mono text-[10px]"
                            >
                              <Edit className="w-3 h-3" /> Edit content
                            </button>
                          ) : (
                            <button
                              onClick={() => setKbIsEditing(false)}
                              className="text-slate-500 hover:underline font-mono text-[10px]"
                            >
                              Cancel
                            </button>
                          )}
                        </div>

                        {kbIsEditing ? (
                          <form onSubmit={handleKbEditSubmit} className="space-y-3">
                            <textarea
                              rows={12}
                              value={kbEditingContent}
                              onChange={e => setKbEditingContent(e.target.value)}
                              className="w-full p-4 bg-[#0d111a] border border-white/10 rounded-xl text-slate-300 font-mono text-xs focus:outline-none focus:border-[#00ff88]/30"
                            />
                            
                            <div className="flex justify-between items-center gap-3">
                              <div className="flex items-center gap-2">
                                <label className="text-slate-500 font-mono uppercase text-[9px] tracking-wider shrink-0">Version</label>
                                <input
                                  type="text"
                                  value={kbEditingVersion}
                                  onChange={e => setKbEditingVersion(e.target.value)}
                                  className="w-20 px-2 py-1 bg-[#0d111a] border border-white/10 rounded text-center text-slate-200 focus:outline-none focus:border-[#00ff88]/30"
                                />
                              </div>

                              <button
                                type="submit"
                                className="px-4 py-2 bg-emerald-600 text-slate-900 font-bold text-[10px] rounded-lg uppercase tracking-wider transition-all"
                              >
                                Save Changes
                              </button>
                            </div>
                          </form>
                        ) : (
                          <div className="p-4 bg-black/30 border border-white/5 rounded-xl text-slate-300 leading-relaxed font-mono whitespace-pre-wrap select-text max-h-[350px] overflow-y-auto">
                            {selectedDoc.content}
                          </div>
                        )}
                      </div>

                      {/* Analytics Dashboard Panel */}
                      <div className="p-4 bg-[#1a1f2e] border border-white/5 rounded-xl space-y-3">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                          <Activity className="w-4 h-4 text-[#00d4ff]" /> Playbook Analytics
                        </h4>
                        
                        <div className="grid grid-cols-3 gap-3 text-center font-mono">
                          <div className="p-2.5 bg-white/5 rounded border border-white/5">
                            <span className="text-slate-500 block uppercase text-[9px]">Matched Matches</span>
                            <span className="text-slate-200 font-bold text-base mt-1">{selectedDoc.usage_count}</span>
                          </div>
                          <div className="p-2.5 bg-white/5 rounded border border-white/5">
                            <span className="text-slate-500 block uppercase text-[9px]">Applied Actions</span>
                            <span className="text-[#00ff88] font-bold text-base mt-1">{selectedDoc.success_count}</span>
                          </div>
                          <div className="p-2.5 bg-white/5 rounded border border-white/5">
                            <span className="text-slate-500 block uppercase text-[9px]">Success Rate</span>
                            <span className="text-amber-400 font-bold text-base mt-1">
                              {selectedDoc.usage_count > 0 ? `${Math.round((selectedDoc.success_count / selectedDoc.usage_count) * 100)}%` : '100%'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="card p-12 flex flex-col items-center justify-center text-center">
                      <BookOpen className="w-12 h-12 text-slate-600 mb-4 animate-pulse-glow" />
                      <h4 className="text-sm font-bold text-slate-400">Select a knowledge file from the list to view extraction chunks & edit playbooks</h4>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB: PHASE 57 — LIVE CLUSTER METRICS DASHBOARD */}
          {activeTab === 'metrics' && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-bold text-slate-100">Live Cluster Metrics</h2>
                  <p className="text-xs text-slate-500 mt-1">Real-time CPU, Memory, Latency & Error-Rate — updated every 5 seconds via WebSocket</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00ff88] opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00ff88]"></span>
                  </div>
                  <span className="text-xs text-[#00ff88] font-bold">LIVE FEED</span>
                  <button onClick={fetchLiveMetrics} className="p-2 bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg transition-all">
                    <RefreshCw className={`w-4 h-4 text-slate-400 ${metricsLoading ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>

              {/* Cluster Summary KPIs */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {[
                  { label: 'Avg CPU', value: `${liveMetrics?.cluster_summary?.avg_cpu ?? '--'}%`, color: 'text-[#00ff88]', icon: Cpu },
                  { label: 'Avg Memory', value: `${liveMetrics?.cluster_summary?.avg_memory ?? '--'}%`, color: 'text-[#00d4ff]', icon: Server },
                  { label: 'Avg Latency', value: `${liveMetrics?.cluster_summary?.avg_latency_ms ?? '--'} ms`, color: 'text-amber-400', icon: Clock },
                  { label: 'Error Rate', value: `${liveMetrics?.cluster_summary?.avg_error_rate ?? '--'}%`, color: 'text-rose-400', icon: AlertTriangle },
                  { label: 'Health Score', value: `${liveMetrics?.cluster_summary?.health_score ?? '--'}`, color: liveMetrics?.cluster_summary?.health_score > 70 ? 'text-[#00ff88]' : 'text-rose-400', icon: Gauge },
                ].map(({ label, value, color, icon: Icon }) => (
                  <div key={label} className="card p-4 text-center relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-16 h-16 bg-white/2 rounded-full blur-xl"></div>
                    <Icon className={`w-5 h-5 ${color} mx-auto mb-2`} />
                    <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">{label}</p>
                    <p className={`text-xl font-black font-mono mt-1 ${color}`}>{value}</p>
                  </div>
                ))}
              </div>

              {/* Time-Series Chart */}
              <div className="card p-5">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest">Cluster Metrics Time-Series</h4>
                  <span className="text-[10px] text-slate-500 font-mono">{metricsHistory.length} data points</span>
                </div>
                <div className="h-72">
                  {metricsHistory.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={metricsHistory}>
                        <defs>
                          <linearGradient id="gradCpu57" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#00ff88" stopOpacity={0.2}/>
                            <stop offset="95%" stopColor="#00ff88" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="timestamp" stroke="#64748b" fontSize={9} tickFormatter={(v) => new Date(v).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'})} />
                        <YAxis stroke="#64748b" fontSize={9} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#1a1f2e', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                          labelFormatter={(v) => new Date(v).toLocaleTimeString()}
                        />
                        <Legend wrapperStyle={{ fontSize: '10px' }} />
                        {metricsAnnotations.map((ann, i) => (
                          <ReferenceLine key={i} x={ann.timestamp}
                            stroke={ann.severity === 'CRITICAL' ? '#ff3366' : ann.severity === 'WARNING' ? '#f59e0b' : '#00d4ff'}
                            strokeDasharray="3 3"
                            label={{ value: ann.event_type, position: 'top', fill: '#94a3b8', fontSize: 8 }}
                          />
                        ))}
                        <Line type="monotone" dataKey="cpu" stroke="#00ff88" strokeWidth={2} dot={false} name="CPU %" />
                        <Line type="monotone" dataKey="memory" stroke="#00d4ff" strokeWidth={2} dot={false} name="Memory %" />
                        <Line type="monotone" dataKey="error_rate" stroke="#ff3366" strokeWidth={1.5} dot={false} name="Error Rate %" strokeDasharray="4 2" />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-slate-500 text-xs font-mono">
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Waiting for first metrics broadcast...
                    </div>
                  )}
                </div>
              </div>

              {/* Per-Service Metrics Grid */}
              <div className="card p-5">
                <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-4">Per-Service Breakdown</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left font-mono">
                    <thead>
                      <tr className="border-b border-white/5 text-slate-500 font-bold">
                        <th className="py-2.5">Service</th>
                        <th className="py-2.5">Status</th>
                        <th className="py-2.5">CPU %</th>
                        <th className="py-2.5">Memory %</th>
                        <th className="py-2.5">Latency ms</th>
                        <th className="py-2.5">Error Rate %</th>
                        <th className="py-2.5">RPS</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {(liveMetrics?.service_metrics || [])
                        .filter((svc: any) => svc && typeof svc === 'object' && 'name' in svc)
                        .map((svc: any) => (
                        <tr
                          key={svc.name}
                          className={`hover:bg-white/5 transition-all cursor-pointer ${selectedMetricService === svc.name ? 'bg-emerald-500/5' : ''}`}
                          onClick={() => setSelectedMetricService(svc.name === selectedMetricService ? null : svc.name)}
                        >
                          <td className="py-3 font-bold text-slate-200">{svc.name}</td>
                          <td className="py-3">
                            <span className={`badge ${svc.status === 'HEALTHY' ? 'badge-success' : 'badge-critical'}`}>{svc.status}</span>
                          </td>
                          <td className="py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-16 bg-white/5 h-1.5 rounded-full overflow-hidden">
                                <div className={`h-full ${svc.cpu_usage > 80 ? 'bg-rose-400' : svc.cpu_usage > 60 ? 'bg-amber-400' : 'bg-[#00ff88]'}`} style={{ width: `${Math.min(svc.cpu_usage, 100)}%` }}></div>
                              </div>
                              <span className={svc.cpu_usage > 80 ? 'text-rose-400' : 'text-slate-300'}>{svc.cpu_usage}%</span>
                            </div>
                          </td>
                          <td className="py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-16 bg-white/5 h-1.5 rounded-full overflow-hidden">
                                <div className={`h-full ${svc.memory_usage > 85 ? 'bg-rose-400' : svc.memory_usage > 65 ? 'bg-amber-400' : 'bg-[#00d4ff]'}`} style={{ width: `${Math.min(svc.memory_usage, 100)}%` }}></div>
                              </div>
                              <span className={svc.memory_usage > 85 ? 'text-rose-400' : 'text-slate-300'}>{svc.memory_usage}%</span>
                            </div>
                          </td>
                          <td className={`py-3 ${svc.latency_ms > 200 ? 'text-rose-400' : svc.latency_ms > 100 ? 'text-amber-400' : 'text-slate-300'}`}>{svc.latency_ms} ms</td>
                          <td className={`py-3 ${svc.error_rate > 5 ? 'text-rose-400' : 'text-slate-300'}`}>{svc.error_rate}%</td>
                          <td className="py-3 text-slate-400">{svc.requests_per_sec}/s</td>
                        </tr>
                      ))}
                      {(!liveMetrics?.service_metrics || liveMetrics.service_metrics.length === 0) && (
                        <tr>
                          <td colSpan={7} className="py-8 text-center text-slate-500">
                            Waiting for first metrics snapshot from WebSocket broadcast...
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Annotations / Event Timeline */}
              {metricsAnnotations.length > 0 && (
                <div className="card p-5">
                  <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-4">Event Annotations</h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {metricsAnnotations.slice().reverse().map((ann: any, i: number) => (
                      <div key={i} className="flex items-center gap-3 p-2.5 bg-white/5 rounded-lg border border-white/5">
                        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${ann.severity === 'CRITICAL' ? 'bg-rose-400' : ann.severity === 'WARNING' ? 'bg-amber-400' : ann.severity === 'SUCCESS' ? 'bg-[#00ff88]' : 'bg-[#00d4ff]'}`}></span>
                        <span className="text-[10px] text-slate-500 font-mono w-36 flex-shrink-0">{new Date(ann.timestamp).toLocaleTimeString()}</span>
                        <span className="text-[10px] font-bold text-slate-400 uppercase w-40 flex-shrink-0">{ann.event_type}</span>
                        <span className="text-xs text-slate-300">{ann.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB: PHASE 58 — PLAYBOOK EXECUTION UI */}
          {activeTab === 'playbooks' && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-bold text-slate-100">Playbook Execution Tracker</h2>
                  <p className="text-xs text-slate-500 mt-1">Step-by-step playbook execution with live progress bars, status logs, and ETA</p>
                </div>
                <button onClick={fetchPlaybookExecutions} className="p-2 bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg transition-all">
                  <RefreshCw className="w-4 h-4 text-slate-400" />
                </button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left: Start New Execution + Execution List */}
                <div className="space-y-4">
                  {/* Start New Execution Panel */}
                  <div className="card p-5 space-y-4">
                    <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest flex items-center gap-2">
                      <Play className="w-4 h-4 text-[#00ff88]" /> Start Playbook
                    </h4>
                    <div className="space-y-3">
                      <div>
                        <label className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block mb-1.5">Playbook Name</label>
                        <input
                          type="text"
                          value={playbookName}
                          onChange={e => setPlaybookName(e.target.value)}
                          className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm text-slate-300 font-mono focus:outline-none focus:border-[#00ff88]/30"
                          placeholder="Playbook name..."
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block mb-1.5">Target Incident</label>
                        <select
                          value={playbookTargetIncident ?? ''}
                          onChange={e => setPlaybookTargetIncident(e.target.value ? Number(e.target.value) : null)}
                          className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-[#00ff88]/30"
                        >
                          <option value="">Select incident...</option>
                          {incidents.slice(0, 10).map((inc: any) => (
                            <option key={inc.id} value={inc.id}>#{inc.id} — {inc.metric_type} ({inc.severity})</option>
                          ))}
                        </select>
                      </div>
                      <button
                        onClick={handleStartPlaybookExecution}
                        disabled={playbookLoading || !playbookTargetIncident}
                        className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-slate-900 font-bold text-xs rounded-xl uppercase tracking-wider transition-all flex items-center justify-center gap-2"
                      >
                        {playbookLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                        Start Execution
                      </button>
                      {playbookMsg && (
                        <p className={`text-[10px] font-mono p-2 rounded-lg ${playbookMsg.startsWith('Error') ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-emerald-500/10 text-[#00ff88] border border-emerald-500/20'}`}>
                          {playbookMsg}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Execution History List */}
                  <div className="card p-5">
                    <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-4">Execution History</h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {playbookExecutions.length === 0 ? (
                        <p className="text-xs text-slate-500 text-center py-6">No executions yet. Start a playbook above.</p>
                      ) : (
                        playbookExecutions
                          .filter((exec: any) => exec && typeof exec === 'object' && 'execution_id' in exec)
                          .map((exec: any) => (
                          <button
                            key={exec.execution_id}
                            onClick={() => setSelectedExecution(exec)}
                            className={`w-full text-left p-3 rounded-xl border transition-all ${selectedExecution?.execution_id === exec.execution_id ? 'border-[#00ff88]/30 bg-emerald-500/5' : 'border-white/5 bg-white/2 hover:bg-white/5'}`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] font-mono text-slate-500">{exec.execution_id.slice(0, 12)}...</span>
                              <span className={`badge ${exec.status === 'COMPLETE' ? 'badge-success' : exec.status === 'RUNNING' ? 'badge-info' : exec.status === 'FAILED' ? 'badge-critical' : 'badge-warning'}`}>
                                {exec.status}
                              </span>
                            </div>
                            <p className="text-xs font-semibold text-slate-300 truncate">{exec.playbook_name}</p>
                            <p className="text-[10px] text-slate-500 mt-0.5">Incident #{exec.incident_id}</p>
                            {/* Mini progress bar */}
                            <div className="w-full bg-white/5 h-1 rounded-full mt-2 overflow-hidden">
                              <div
                                className={`h-full transition-all duration-500 ${exec.status === 'COMPLETE' ? 'bg-[#00ff88]' : exec.status === 'FAILED' ? 'bg-rose-500' : 'bg-[#00d4ff]'}`}
                                style={{ width: `${exec.progress_pct}%` }}
                              ></div>
                            </div>
                            <span className="text-[9px] text-slate-600 font-mono">{exec.progress_pct}% complete</span>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Execution Detail Panel */}
                <div className="lg:col-span-2">
                  {selectedExecution ? (
                    <div className="space-y-4">
                      {/* Header */}
                      <div className="card p-5">
                        <div className="flex items-start justify-between mb-4">
                          <div>
                            <h3 className="text-base font-bold text-slate-100">{selectedExecution.playbook_name}</h3>
                            <p className="text-xs text-slate-500 font-mono mt-1">{selectedExecution.execution_id}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`badge ${selectedExecution.status === 'COMPLETE' ? 'badge-success' : selectedExecution.status === 'RUNNING' ? 'badge-info' : selectedExecution.status === 'FAILED' ? 'badge-critical' : 'badge-warning'}`}>
                              {selectedExecution.status}
                            </span>
                            {selectedExecution.status === 'RUNNING' && (
                              <button
                                onClick={() => handleCancelExecution(selectedExecution.execution_id)}
                                className="px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 rounded-lg text-xs font-bold transition-all"
                              >
                                Cancel
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Main Progress Bar */}
                        <div className="mb-3">
                          <div className="flex justify-between text-[10px] text-slate-500 mb-1.5">
                            <span>Overall Progress</span>
                            <span className="font-mono">{selectedExecution.progress_pct}%</span>
                          </div>
                          <div className="w-full bg-white/5 h-3 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-700 ${selectedExecution.status === 'COMPLETE' ? 'bg-gradient-to-r from-emerald-500 to-[#00ff88]' : selectedExecution.status === 'FAILED' ? 'bg-gradient-to-r from-rose-600 to-rose-400' : 'bg-gradient-to-r from-[#00d4ff] to-[#0080ff] animate-pulse'}`}
                              style={{ width: `${selectedExecution.progress_pct}%` }}
                            ></div>
                          </div>
                        </div>

                        {/* Stats Row */}
                        <div className="grid grid-cols-3 gap-3 text-center font-mono text-xs">
                          <div className="p-2 bg-white/5 rounded-lg">
                            <span className="text-slate-500 block text-[9px] uppercase">Steps</span>
                            <span className="text-slate-200 font-bold">{selectedExecution.current_step}/{selectedExecution.total_steps}</span>
                          </div>
                          <div className="p-2 bg-white/5 rounded-lg">
                            <span className="text-slate-500 block text-[9px] uppercase">Incident</span>
                            <span className="text-[#00d4ff] font-bold">#{selectedExecution.incident_id}</span>
                          </div>
                          <div className="p-2 bg-white/5 rounded-lg">
                            <span className="text-slate-500 block text-[9px] uppercase">ETA</span>
                            <span className="text-amber-400 font-bold text-[10px]">
                              {selectedExecution.estimated_completion ? new Date(selectedExecution.estimated_completion).toLocaleTimeString() : '--'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Step-by-Step Progress */}
                      <div className="card p-5">
                        <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-4">Step Progress</h4>
                        <div className="space-y-2">
                          {(selectedExecution.steps || [])
                            .filter((step: any) => step && typeof step === 'object' && 'name' in step)
                            .map((step: any, i: number) => (
                            <div key={i} className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                              step.status === 'COMPLETE' ? 'bg-emerald-500/5 border-emerald-500/20' :
                              step.status === 'RUNNING' ? 'bg-[#00d4ff]/5 border-[#00d4ff]/20' :
                              step.status === 'FAILED' ? 'bg-rose-500/5 border-rose-500/20' :
                              step.status === 'SKIPPED' ? 'bg-white/2 border-white/5 opacity-40' :
                              'bg-white/2 border-white/5'
                            }`}>
                              <div className="flex-shrink-0">
                                {step.status === 'COMPLETE' ? (
                                  <CheckCircle className="w-5 h-5 text-[#00ff88]" />
                                ) : step.status === 'RUNNING' ? (
                                  <Loader2 className="w-5 h-5 text-[#00d4ff] animate-spin" />
                                ) : step.status === 'FAILED' ? (
                                  <XCircle className="w-5 h-5 text-rose-400" />
                                ) : step.status === 'SKIPPED' ? (
                                  <ChevronRight className="w-5 h-5 text-slate-600" />
                                ) : (
                                  <div className="w-5 h-5 rounded-full border-2 border-slate-600 flex items-center justify-center">
                                    <span className="text-[8px] text-slate-600 font-bold">{i + 1}</span>
                                  </div>
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className={`text-xs font-semibold ${
                                  step.status === 'COMPLETE' ? 'text-slate-200' :
                                  step.status === 'RUNNING' ? 'text-[#00d4ff]' :
                                  step.status === 'FAILED' ? 'text-rose-400' :
                                  'text-slate-500'
                                }`}>{step.name}</p>
                                {step.started_at && (
                                  <p className="text-[9px] text-slate-600 font-mono mt-0.5">
                                    {step.status === 'COMPLETE' ? `Completed at ${new Date(step.completed_at).toLocaleTimeString()}` :
                                     step.status === 'RUNNING' ? `Started at ${new Date(step.started_at).toLocaleTimeString()}` : ''}
                                  </p>
                                )}
                              </div>
                              <span className={`badge text-[9px] flex-shrink-0 ${
                                step.status === 'COMPLETE' ? 'badge-success' :
                                step.status === 'RUNNING' ? 'badge-info' :
                                step.status === 'FAILED' ? 'badge-critical' :
                                step.status === 'SKIPPED' ? 'badge-warning' :
                                'bg-slate-800 text-slate-500 border border-slate-700'
                              }`}>{step.status}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Execution Log */}
                      <div className="card p-5">
                        <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-3 flex items-center gap-2">
                          <Terminal className="w-4 h-4 text-[#00d4ff]" /> Execution Log
                        </h4>
                        <div className="bg-black/50 border border-white/5 rounded-xl p-4 font-mono text-[10px] max-h-48 overflow-y-auto space-y-1">
                          {(selectedExecution.log || []).map((line: string, i: number) => (
                            <p key={i} className={`${line.includes('FAILED') || line.includes('Error') ? 'text-rose-400' : line.includes('COMPLETE') || line.includes('successfully') ? 'text-[#00ff88]' : 'text-slate-400'}`}>
                              {line}
                            </p>
                          ))}
                          {(!selectedExecution.log || selectedExecution.log.length === 0) && (
                            <p className="text-slate-600">No log entries yet.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="card p-16 flex flex-col items-center justify-center text-center">
                      <ListChecks className="w-16 h-16 text-slate-700 mb-4" />
                      <h4 className="text-sm font-bold text-slate-400">Select an execution from the list or start a new playbook</h4>
                      <p className="text-xs text-slate-600 mt-2">All step progress, logs, and ETA will appear here in real-time</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

