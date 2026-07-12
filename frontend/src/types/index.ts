/* SentinelFlow AI — TypeScript Type Definitions */

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'engineer' | 'viewer';
  is_active: boolean;
  mfa_enabled: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Incident {
  id: number;
  correlation_id: string;
  source: string;
  metric_type: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  title: string;
  description: string;
  status: string;
  alert_count?: number;
  confidence_score: number;
  suggested_action: string | null;
  assigned_to: string | null;
  parent_incident_id?: number | null;
  resolved_at: string | null;
  k8s_analysis_json?: string | null;
  explainability_json?: string | null;
  priority_score?: number;
  sla_target?: string | null;
  sla_breach_at?: string | null;
  simulation_json?: string | null;
  remediation_options_json?: string | null;
  decision_graph_json?: string | null;
  recommended_runbooks_json?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentLog {
  id: number;
  stage: string;
  message: string;
  metadata_json: string | null;
  timestamp: string;
}

export interface TimelineEvent {
  id: number;
  event_type: string;
  title: string;
  description: string | null;
  actor: string;
  decision_rationale: string | null;
  confidence_at_step: number | null;
  duration_ms: number | null;
  timestamp: string;
}

export interface Alert {
  id: number;
  source: string;
  alert_type: string;
  service: string;
  message: string;
  timestamp: string;
}

export interface AlertFingerprint {
  id: number;
  fingerprint_hash: string;
  first_alert: string;
  last_alert_time: string;
  alert_count: number;
  alerts: Alert[];
}

export interface IncidentDetail extends Incident {
  logs: IncidentLog[];
  timeline_events: TimelineEvent[];
  fingerprints?: AlertFingerprint[];
}

export interface AuditEntry {
  id: number;
  incident_id: number | null;
  command_checked: string;
  status: 'ALLOWED' | 'BLOCKED';
  risk_score: number;
  risk_assessment: string | null;
  remediation_action: string | null;
  performed_by: string;
  hash: string | null;
  prev_hash: string | null;
  timestamp: string;
}

export interface PodInfo {
  name: string;
  namespace: string;
  status: string;
  node: string;
  service: string;
  cpu_usage: number;
  memory_usage: number;
  restart_count: number;
  containers: Array<{ name: string; ready: boolean; image: string }>;
  labels: Record<string, string>;
}

export interface NodeInfo {
  name: string;
  role: string;
  status: string;
  cpu_capacity: number;
  memory_gb: number;
  pod_count: number;
  cpu_usage: number;
  memory_usage: number;
}

export interface ClusterTopology {
  nodes: NodeInfo[];
  pods: PodInfo[];
  services: Array<{ name: string; type: string; port: number; endpoints: number }>;
}

export interface PromptTemplate {
  id: string;
  name: string;
  capacity: string;
  role: string;
  intent: string;
  subject: string;
  premium_response: string;
  evaluation: string;
  category: string;
  is_active: boolean;
  updated_at: string;
}

export interface ObservabilitySummary {
  total_traces: number;
  avg_latency_ms: number;
  total_input_tokens: number;
  total_output_tokens: number;
  error_count: number;
  traces_by_step: Record<string, number>;
}

export interface CommandResult {
  command: string;
  status: 'ALLOWED' | 'BLOCKED';
  risk_score: number;
  risk_assessment: string;
  execution_output: string | null;
  audit_id: number;
}

export type NavSection =
  | 'dashboard'
  | 'executive'
  | 'incidents'
  | 'topology'
  | 'audit'
  | 'prompts'
  | 'observability'
  | 'knowledge'
  | 'settings'
  | 'metrics'
  | 'playbooks'
  | 'mastra';

export interface ExecutiveReport {
  summary: string;
  business_impact: {
    affected_users: number;
    revenue_lost_usd: number;
    risk_score: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    impact_score: number;
  };
  estimated_recovery_time_mins: number;
  compliance: {
    regulations_applicable: string[];
    compliance_status: 'MET' | 'VIOLATED' | 'PENDING';
    required_notifications: string[];
  };
}
