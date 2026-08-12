'use client';

import React from 'react';
import {
  Cpu,
  Database,
  Shield,
  Lock,
  Activity,
  AlertTriangle,
  Gauge,
  Clock,
  XCircle,
  Network,
} from 'lucide-react';
import { User } from '../../types';

interface SecuritySettingsViewProps {
  user: User | null;
  disableMFA: () => void;
  triggerMFASetup: () => void;
  mfaStatusMsg: string;
  mfaSecretData: any;
  mfaSetupCode: string;
  setMfaSetupCode: (code: string) => void;
  verifyAndEnableMFA: () => void;
  govMode: string;
  setGovMode: (mode: string) => void;
  govMinConfidence: number;
  setGovMinConfidence: (val: number) => void;
  govRateLimit: number;
  setGovRateLimit: (val: number) => void;
  govMaxBlastRadius: number;
  setGovMaxBlastRadius: (val: number) => void;
  govRestrictedServices: string;
  setGovRestrictedServices: (services: string) => void;
  govLowRiskActions: string;
  setGovLowRiskActions: (actions: string) => void;
  handleGovConfigSubmit: (e: React.FormEvent) => void;
  govLoading: boolean;
  govMsg: string;
  policies: any[];
  togglePolicyAction: (id: number) => void;
  sessions: any[];
  revokeSessionAction: (id: number) => void;
  triggerDemoScenario: (scenario: string) => void;
  demoLoading: boolean;
  demoResultMsg: string;
  cleanupDemoDatabase: () => void;
}

export const SecuritySettingsView: React.FC<SecuritySettingsViewProps> = ({
  user,
  disableMFA,
  triggerMFASetup,
  mfaStatusMsg,
  mfaSecretData,
  mfaSetupCode,
  setMfaSetupCode,
  verifyAndEnableMFA,
  govMode,
  setGovMode,
  govMinConfidence,
  setGovMinConfidence,
  govRateLimit,
  setGovRateLimit,
  govMaxBlastRadius,
  setGovMaxBlastRadius,
  govRestrictedServices,
  setGovRestrictedServices,
  govLowRiskActions,
  setGovLowRiskActions,
  handleGovConfigSubmit,
  govLoading,
  govMsg,
  policies,
  togglePolicyAction,
  sessions,
  revokeSessionAction,
  triggerDemoScenario,
  demoLoading,
  demoResultMsg,
  cleanupDemoDatabase,
}) => {
  return (
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
                  <option value="MANUAL">MANUAL (Require human approval for all actions)</option>
                  <option value="ASSISTED">ASSISTED (Default - AI analyzes & validates, human approves execution)</option>
                  <option value="AUTONOMOUS">AUTONOMOUS (Auto-run policy-approved actions meeting safety gates)</option>
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

          <button
            onClick={() => triggerDemoScenario('MEMORY_EXHAUSTION')}
            disabled={demoLoading}
            className="px-4 py-3 bg-gradient-to-r from-yellow-600/30 to-amber-600/30 hover:from-yellow-600/40 hover:to-amber-600/40 border border-yellow-500/30 rounded-xl text-slate-200 font-bold text-xs transition-all flex flex-col items-center justify-center gap-2"
          >
            <Gauge className="w-5 h-5 text-yellow-400" />
            <span>MEMORY OOMKILLED</span>
          </button>

          <button
            onClick={() => triggerDemoScenario('HIGH_LATENCY')}
            disabled={demoLoading}
            className="px-4 py-3 bg-gradient-to-r from-teal-600/30 to-emerald-600/30 hover:from-teal-600/40 hover:to-emerald-600/40 border border-emerald-500/30 rounded-xl text-slate-200 font-bold text-xs transition-all flex flex-col items-center justify-center gap-2"
          >
            <Clock className="w-5 h-5 text-emerald-400" />
            <span>HIGH LATENCY</span>
          </button>

          <button
            onClick={() => triggerDemoScenario('ERROR_RATE_SPIKE')}
            disabled={demoLoading}
            className="px-4 py-3 bg-gradient-to-r from-pink-600/30 to-red-600/30 hover:from-pink-600/40 hover:to-red-600/40 border border-red-500/30 rounded-xl text-slate-200 font-bold text-xs transition-all flex flex-col items-center justify-center gap-2"
          >
            <XCircle className="w-5 h-5 text-red-400" />
            <span>ERROR RATE SPIKE</span>
          </button>

          <button
            onClick={() => triggerDemoScenario('NETWORK_OUTAGE')}
            disabled={demoLoading}
            className="px-4 py-3 bg-gradient-to-r from-slate-600/30 to-zinc-600/30 hover:from-slate-600/40 hover:to-zinc-600/40 border border-zinc-500/30 rounded-xl text-slate-200 font-bold text-xs transition-all flex flex-col items-center justify-center gap-2"
          >
            <Network className="w-5 h-5 text-zinc-400" />
            <span>NETWORK OUTAGE</span>
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
  );
};
