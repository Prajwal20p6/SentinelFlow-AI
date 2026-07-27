'use client';

import React from 'react';
import {
  RefreshCw,
  Cpu,
  Server,
  Clock,
  AlertTriangle,
  Gauge,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';

interface LiveMetricsViewProps {
  liveMetrics: any;
  fetchLiveMetrics: () => void;
  metricsLoading: boolean;
  metricsHistory: any[];
  metricsAnnotations: any[];
  selectedMetricService: string | null;
  setSelectedMetricService: (name: string | null) => void;
}

export const LiveMetricsView: React.FC<LiveMetricsViewProps> = ({
  liveMetrics,
  fetchLiveMetrics,
  metricsLoading,
  metricsHistory,
  metricsAnnotations,
  selectedMetricService,
  setSelectedMetricService,
}) => {
  return (
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
  );
};
