'use client';

import React from 'react';
import { ObservabilitySummary } from '../../types';

interface ObservabilityTracesViewProps {
  obsSummary: ObservabilitySummary | null;
  obsTraces: any[];
}

export const ObservabilityTracesView: React.FC<ObservabilityTracesViewProps> = ({
  obsSummary,
  obsTraces,
}) => {
  return (
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
  );
};
