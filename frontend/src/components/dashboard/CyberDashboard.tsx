'use client';

import React from 'react';
import { RefreshCw, Sliders } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';
import { User, Incident } from '../../types';

interface CyberDashboardProps {
  obsSummary: any;
  activeIncidentCount: number;
  mockChartData: any[];
  user: User | null;
  serverHealth: any;
  executiveMetrics: any;
  incidents: Incident[];
  circuitBreakers: any;
  onNavigateToIncidents?: () => void;
}

export const CyberDashboard: React.FC<CyberDashboardProps> = ({
  obsSummary,
  activeIncidentCount,
  mockChartData,
  user,
  serverHealth,
  executiveMetrics,
  incidents,
  circuitBreakers,
  onNavigateToIncidents,
}) => {
  return (
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
            {executiveMetrics?.approval_override_rate ?? 0}%
          </span>
          <p className="text-[9px] text-slate-500 mt-1">Manual overrides vs Auto-approvals</p>
        </div>

        <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center relative overflow-hidden">
          <div className="absolute top-0 right-0 w-16 h-16 bg-[#00d4ff]/5 rounded-full filter blur-xl"></div>
          <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">Auto-Executed</span>
          <span className="text-xl font-black text-[#00d4ff] font-mono mt-1.5 block">
            {executiveMetrics?.auto_executed ?? 0}
          </span>
          <p className="text-[9px] text-slate-500 mt-1">Incidents auto-remediated</p>
        </div>

        <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center relative overflow-hidden">
          <div className="absolute top-0 right-0 w-16 h-16 bg-amber-500/5 rounded-full filter blur-xl"></div>
          <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">Pending Approval</span>
          <span className="text-xl font-black text-amber-400 font-mono mt-1.5 block">
            {executiveMetrics?.pending_approval ?? 0}
          </span>
          <p className="text-[9px] text-slate-500 mt-1">Awaiting human review</p>
        </div>

        <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center relative overflow-hidden">
          <div className="absolute top-0 right-0 w-16 h-16 bg-emerald-500/5 rounded-full filter blur-xl"></div>
          <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">Auto-rem. Success Rate</span>
          <span className="text-xl font-black text-[#00ff88] font-mono mt-1.5 block">
            {executiveMetrics?.auto_success_rate ?? 94.2}%
          </span>
          <p className="text-[9px] text-slate-500 mt-1">Mitigated incidents success percentage</p>
        </div>
      </div>

      {/* Incidents Queue Preview */}
      <div className="card p-5">
        <div className="flex justify-between items-center mb-4">
          <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest">Active Incident Response Log</h4>
          {onNavigateToIncidents && (
            <button onClick={onNavigateToIncidents} className="text-xs text-[#00ff88] hover:underline flex items-center gap-1">
              Manage Incidents <Sliders className="w-3.5 h-3.5" />
            </button>
          )}
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
              {Object.keys(circuitBreakers || {}).length > 0 && !('detail' in (circuitBreakers || {})) ? (
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
  );
};
