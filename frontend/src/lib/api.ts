import { TokenResponse, User, Incident, IncidentDetail, AuditEntry, ClusterTopology, PromptTemplate, ObservabilitySummary, CommandResult } from '../types';

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

class APIClient {
  private token: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('sf_token');
      this.refreshToken = localStorage.getItem('sf_refresh_token');
    }
  }

  setTokens(token: string, refresh: string) {
    this.token = token;
    this.refreshToken = refresh;
    if (typeof window !== 'undefined') {
      localStorage.setItem('sf_token', token);
      localStorage.setItem('sf_refresh_token', refresh);
    }
  }

  clearTokens() {
    this.token = null;
    this.refreshToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('sf_token');
      localStorage.removeItem('sf_refresh_token');
      localStorage.removeItem('sf_user');
    }
  }

  get isLoggedIn(): boolean {
    return !!this.token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    mfaToken?: string
  ): Promise<T> {
    const headers = new Headers(options.headers || {});
    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }
    if (mfaToken) {
      headers.set('X-MFA-Token', mfaToken);
    }
    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    let response = await fetch(`${getApiBaseUrl()}${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401 && this.refreshToken && path !== '/auth/refresh' && path !== '/auth/login') {
      try {
        const refreshResp = await fetch(`${getApiBaseUrl()}/auth/refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Refresh-Token': this.refreshToken
          }
        });
        if (refreshResp.ok) {
          const refreshData = await refreshResp.json();
          this.setTokens(refreshData.access_token, refreshData.refresh_token);
          
          headers.set('Authorization', `Bearer ${refreshData.access_token}`);
          response = await fetch(`${getApiBaseUrl()}${path}`, {
            ...options,
            headers,
          });
        } else {
          this.clearTokens();
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new Event('auth_required'));
          }
          throw new Error('Unauthorized');
        }
      } catch (err) {
        this.clearTokens();
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('auth_required'));
        }
        throw new Error('Unauthorized');
      }
    } else if (response.status === 401) {
      this.clearTokens();
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('auth_required'));
      }
      throw new Error('Unauthorized');
    }

    const data = await response.json();

    if (!response.ok) {
      throw { status: response.status, data };
    }

    return data as T;
  }

  // Auth Endpoints
  async login(email: string, password: string, mfaToken?: string): Promise<any> {
    try {
      const data = await this.request<any>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }, mfaToken);
      
      if (data.detail === 'MFA_REQUIRED' || data.mfa_required) {
        return { mfaRequired: true };
      }

      if (data.access_token) {
        this.setTokens(data.access_token, data.refresh_token);
        localStorage.setItem('sf_user', JSON.stringify(data.user));
      }
      return data;
    } catch (err: any) {
      throw err;
    }
  }

  async register(params: { email: string; password: string; full_name?: string; role?: string; organization_id?: string }): Promise<any> {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async verifyEmail(token: string): Promise<any> {
    return this.request(`/auth/verify-email?token=${encodeURIComponent(token)}`, {
      method: 'POST',
    });
  }

  async forgotPassword(email: string): Promise<any> {
    return this.request('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  }

  async resetPassword(params: { token: string; new_password: string }): Promise<any> {
    return this.request('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async logout(): Promise<any> {
    const headers = new Headers();
    if (this.refreshToken) {
      headers.set('X-Refresh-Token', this.refreshToken);
    }
    const res = await this.request<any>('/auth/logout', {
      method: 'POST',
      headers,
    }).catch(() => null);
    this.clearTokens();
    return res;
  }

  async getSessions(): Promise<any[]> {
    return this.request('/auth/sessions');
  }

  async revokeSession(sessionId: number): Promise<any> {
    return this.request(`/auth/sessions/revoke/${sessionId}`, {
      method: 'POST',
    });
  }

  async setupMFA(): Promise<{ secret: string; qr_uri: string; message: string }> {
    return this.request('/auth/mfa/setup', { method: 'POST' });
  }

  async enableMFA(code: string): Promise<{ message: string; mfa_enabled: boolean; backup_codes?: string[] }> {
    return this.request('/auth/mfa/enable', {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
  }

  async disableMFA(): Promise<{ message: string; mfa_enabled: boolean }> {
    return this.request('/auth/mfa/disable', { method: 'POST' });
  }

  async getMe(): Promise<User> {
    return this.request('/auth/me');
  }

  // Incidents Endpoints
  async getIncidents(status?: string, severity?: string): Promise<{ incidents: Incident[]; total: number }> {
    let query = '';
    const params = [];
    if (status) params.push(`status=${status}`);
    if (severity) params.push(`severity=${severity}`);
    if (params.length > 0) query = `?${params.join('&')}`;
    return this.request(`/incidents${query}`);
  }

  async getIncidentDetail(id: number): Promise<IncidentDetail> {
    return this.request(`/incidents/${id}`);
  }

  private generateUUID(): string {
    if (typeof window !== 'undefined' && window.crypto && window.crypto.randomUUID) {
      return window.crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  async approveIncident(id: number): Promise<any> {
    const keyKey = `sf_idem_approve_${id}`;
    let key = typeof window !== 'undefined' ? localStorage.getItem(keyKey) : null;
    if (!key) {
      key = this.generateUUID();
      if (typeof window !== 'undefined') localStorage.setItem(keyKey, key);
    }
    return this.request(`/incidents/${id}/approve`, { 
      method: 'POST',
      headers: { 'Idempotency-Key': key }
    });
  }

  async rejectIncident(id: number): Promise<any> {
    return this.request(`/incidents/${id}/reject`, { method: 'POST' });
  }

  async getSimulation(id: number): Promise<any> {
    return this.request(`/incidents/${id}/simulation`);
  }

  async getRemediationOptions(id: number): Promise<any[]> {
    return this.request(`/incidents/${id}/remediation-options`);
  }

  async getReplay(id: number): Promise<any[]> {
    return this.request(`/incidents/${id}/replay`);
  }

  async getDecisionGraph(id: number): Promise<any> {
    return this.request(`/incidents/${id}/decision-graph`);
  }

  async getRunbooks(id: number): Promise<any[]> {
    return this.request(`/incidents/${id}/runbooks`);
  }

  async executeRemediation(id: number, optionId: string): Promise<any> {
    const keyKey = `sf_idem_exec_${id}_${optionId}`;
    let key = typeof window !== 'undefined' ? localStorage.getItem(keyKey) : null;
    if (!key) {
      key = this.generateUUID();
      if (typeof window !== 'undefined') localStorage.setItem(keyKey, key);
    }
    return this.request(`/incidents/${id}/execute-remediation`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Idempotency-Key': key
      },
      body: JSON.stringify({ option_id: optionId })
    });
  }

  async submitRunbookFeedback(id: number, runbookId: string, success: boolean): Promise<any> {
    return this.request(`/incidents/${id}/runbook-feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ runbook_id: runbookId, success })
    });
  }

  // Infrastructure Endpoints
  async getTopology(): Promise<ClusterTopology> {
    return this.request('/infra/topology');
  }

  async executeCommand(command: string, incidentId?: number): Promise<CommandResult> {
    return this.request('/infra/execute-command', {
      method: 'POST',
      body: JSON.stringify({ command, incident_id: incidentId }),
    });
  }

  async getAuditTrail(): Promise<{ audit_entries: AuditEntry[]; count: number }> {
    return this.request('/infra/audit-trail');
  }

  async verifyAuditTrail(): Promise<{ valid: boolean; message: string; count: number }> {
    return this.request('/infra/audit-trail/verify');
  }

  async archiveAuditTrail(): Promise<{ message: string; s3_uri: string; entry_count: number }> {
    return this.request('/infra/audit-trail/archive', { method: 'POST' });
  }

  // Agent Prompts & Observability
  async getPrompts(): Promise<{ templates: PromptTemplate[]; count: number }> {
    return this.request('/agent/prompts');
  }

  async ragSearch(params: { query: string; limit?: number; category?: string }): Promise<{ query: string; results: any[]; count: number }> {
    return this.request('/agent/rag/search', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async getObservabilitySummary(): Promise<ObservabilitySummary> {
    return this.request('/agent/observability/summary');
  }

  async getObservabilityTraces(correlationId?: string): Promise<{ traces: any[]; count: number }> {
    const query = correlationId ? `?correlation_id=${correlationId}` : '';
    return this.request(`/agent/observability/traces${query}`);
  }

  async getExecutiveReport(incidentId: number): Promise<any> {
    return this.request(`/incidents/${incidentId}/executive-report`);
  }

  async getExecutiveMetrics(): Promise<any> {
    return this.request('/agent/observability/executive/metrics');
  }

  async getPolicies(): Promise<any[]> {
    return this.request('/policies');
  }

  async togglePolicy(id: number): Promise<any> {
    return this.request(`/policies/${id}/toggle`, { method: 'POST' });
  }

  async dryRunPolicy(incidentId: number): Promise<any> {
    return this.request(`/policies/dry-run?incident_id=${incidentId}`, { method: 'POST' });
  }

  async getAttackGraph(incidentId: number): Promise<any> {
    return this.request(`/incidents/${incidentId}/attack-graph`);
  }

  async getPostmortem(incidentId: number): Promise<any> {
    return this.request(`/incidents/${incidentId}/postmortem`);
  }

  async generatePostmortem(incidentId: number): Promise<any> {
    return this.request(`/incidents/${incidentId}/postmortem/generate`, { method: 'POST' });
  }

  async getActiveExecution(): Promise<any> {
    return this.request('/monitor/active');
  }

  async getIncidentExecution(incidentId: number): Promise<any> {
    return this.request(`/monitor/${incidentId}/execution`);
  }
}

export const api = new APIClient();
