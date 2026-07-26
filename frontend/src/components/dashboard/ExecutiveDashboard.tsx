'use client';

import React from 'react';
import { RefreshCw, Shield, Loader2 } from 'lucide-react';
import { Incident } from '../../types';

interface ExecutiveDashboardProps {
  executiveMetrics: any;
  incidents: Incident[];
  selectedExecutiveIncident: Incident | null;
  onSelectExecutiveIncident: (inc: Incident) => void;
  executiveReport: any;
  executiveReportLoading: boolean;
}

export const ExecutiveDashboard: React.FC<ExecutiveDashboardProps> = ({
  executiveMetrics,
  incidents,
  selectedExecutiveIncident,
  onSelectExecutiveIncident,
  executiveReport,
  executiveReportLoading,
}) => {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Executive SecOps Intelligence</h2>
          <p className="text-xs text-slate-500 mt-1">
            High-level financial, operational, and compliance impact summaries for board-level reporting
          </p>
        </div>
        <div className="text-xs text-slate-500 bg-white/5 px-4 py-2 rounded-lg border border-white/5 flex items-center gap-2">
          <RefreshCw className="w-3 h-3 animate-spin" /> Live Financial Sync
        </div>
      </div>

      {/* C-Suite Metrics Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="p-5 card relative overflow-hidden">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Mean Time to Detect (MTTD)
          </p>
          <h3 className="text-2xl font-black text-[#00ff88] mt-2 font-mono">
            {executiveMetrics?.mttd_seconds || 34.2} s
          </h3>
          <p className="text-[10px] text-slate-500 mt-1">Instant telemetry alerts ingest rate</p>
        </div>

        <div className="p-5 card relative overflow-hidden">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Mean Time to Respond (MTTR)
          </p>
          <h3 className="text-2xl font-black text-[#00d4ff] mt-2 font-mono">
            {executiveMetrics?.mttr_seconds
              ? `${(executiveMetrics.mttr_seconds / 60).toFixed(1)} m`
              : '0.0 m'}
          </h3>
          <p className="text-[10px] text-slate-500 mt-1">Resolution workflow cycle length</p>
        </div>

        <div className="p-5 card relative overflow-hidden">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Incident Resolution Rate
          </p>
          <h3 className="text-2xl font-black text-amber-400 mt-2 font-mono">
            {executiveMetrics?.resolution_rate || 100.0}%
          </h3>
          <p className="text-[10px] text-slate-500 mt-1">Completed autopilot actions</p>
        </div>

        <div className="p-5 card relative overflow-hidden">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            AI False Positive Rate
          </p>
          <h3 className="text-2xl font-black text-rose-500 mt-2 font-mono">
            {executiveMetrics?.false_positive_rate || 0.0}%
          </h3>
          <p className="text-[10px] text-slate-500 mt-1">Rejected actions percentage</p>
        </div>
      </div>

      {/* Lower Section: Incident Selector & Report View */}
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
            {incidents.map((inc) => (
              <div
                key={inc.id}
                onClick={() => onSelectExecutiveIncident(inc)}
                className={`p-4 card cursor-pointer transition-all border ${
                  selectedExecutiveIncident?.id === inc.id
                    ? 'border-[#00ff88] bg-emerald-500/5'
                    : 'border-white/5'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[10px] font-mono text-slate-400 font-semibold">#{inc.id}</span>
                  <span
                    className={`badge text-[9px] ${
                      inc.severity === 'CRITICAL'
                        ? 'badge-critical'
                        : inc.severity === 'WARNING'
                        ? 'badge-warning'
                        : 'badge-info'
                    }`}
                  >
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
                Select an incident from the index to inspect its business-level impact score, regulatory
                exposure compliance status, and AI executive summary.
              </p>
            </div>
          ) : (
            <div className="space-y-5 animate-fade-in card p-6">
              {/* Report Header */}
              <div className="flex justify-between items-start border-b border-white/5 pb-4">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="text-base font-bold text-slate-100">
                      {selectedExecutiveIncident.title}
                    </h3>
                    {executiveReport?.business_impact?.risk_score && (
                      <span
                        className={`badge text-[9px] ${
                          executiveReport.business_impact.risk_score === 'CRITICAL'
                            ? 'badge-critical'
                            : executiveReport.business_impact.risk_score === 'HIGH'
                            ? 'badge-warning'
                            : 'badge-info'
                        }`}
                      >
                        RISK: {executiveReport.business_impact.risk_score}
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-500 font-mono mt-1">
                    Correlation: {selectedExecutiveIncident.correlation_id}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-500 font-bold block uppercase">
                    Resolution status
                  </span>
                  <span className="text-xs font-bold text-[#00ff88] mt-1 block">
                    {selectedExecutiveIncident.status}
                  </span>
                </div>
              </div>

              {/* Loading State */}
              {executiveReportLoading ? (
                <div className="py-12 flex flex-col items-center justify-center gap-3">
                  <Loader2 className="w-8 h-8 text-[#00ff88] animate-spin" />
                  <span className="text-xs text-slate-400 font-mono">
                    Synthesizing executive board summary...
                  </span>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Executive Summary Card */}
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl space-y-4">
                    <div>
                      <h4 className="text-xs font-bold text-[#00ff88] uppercase tracking-wider mb-2">
                        AI Non-Technical Narrative
                      </h4>
                      <p className="text-xs text-slate-300 leading-relaxed font-sans">
                        {executiveReport?.summary}
                      </p>
                    </div>

                    {executiveReport?.simplified_explanation && (
                      <div className="pt-3 border-t border-white/5">
                        <h4 className="text-xs font-bold text-[#00d4ff] uppercase tracking-wider mb-2">
                          AI Decision Rationale
                        </h4>
                        <p className="text-xs text-slate-300 leading-relaxed font-sans italic">
                          "{executiveReport.simplified_explanation}"
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Impact Metrics Grid */}
                  <div>
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                      Valuation & Operational Impacts
                    </h4>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center">
                        <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">
                          Affected Customers
                        </span>
                        <span className="text-lg font-black text-slate-100 font-mono mt-1.5 block">
                          {executiveReport?.business_impact?.affected_users || 0}
                        </span>
                      </div>
                      <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center">
                        <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">
                          Financial Downtime Cost
                        </span>
                        <span className="text-lg font-black text-[#ff3366] font-mono mt-1.5 block">
                          ${executiveReport?.business_impact?.revenue_lost_usd?.toLocaleString() || '0.00'}
                        </span>
                      </div>
                      <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center">
                        <span className="text-[9px] text-slate-500 font-bold block uppercase tracking-wider">
                          Downtime Duration
                        </span>
                        <span className="text-lg font-black text-[#00d4ff] font-mono mt-1.5 block">
                          {executiveReport?.estimated_recovery_time_mins || 0} mins
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Compliance Assessment */}
                  <div className="border-t border-white/5 pt-4">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                      Regulatory Audit & Compliance checklist
                    </h4>
                    <div className="p-4 bg-white/5 border border-white/5 rounded-xl space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold">Regulatory Framework status</span>
                        <span
                          className={`badge ${
                            executiveReport?.compliance?.compliance_status === 'MET'
                              ? 'badge-success'
                              : executiveReport?.compliance?.compliance_status === 'PENDING'
                              ? 'badge-warning'
                              : 'badge-critical'
                          }`}
                        >
                          {executiveReport?.compliance?.compliance_status || 'PENDING'}
                        </span>
                      </div>

                      <div className="flex justify-between items-start">
                        <span className="text-xs font-semibold">Applicable Regs</span>
                        <div className="flex gap-2">
                          {executiveReport?.compliance?.regulations_applicable?.map((reg: string) => (
                            <span
                              key={reg}
                              className="bg-white/10 px-2 py-0.5 rounded text-[9px] font-bold text-slate-300"
                            >
                              {reg}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Compliance Checklist Score */}
                      <div className="space-y-1 mt-2 border-t border-white/5 pt-3">
                        <div className="flex justify-between text-xs font-semibold">
                          <span>Checklist Score</span>
                          <span className="text-[#00ff88]">
                            {executiveReport?.compliance?.compliance_score_percent || 0}%
                          </span>
                        </div>
                        <div className="w-full bg-white/5 h-2 rounded-full overflow-hidden border border-white/5">
                          <div
                            className="bg-gradient-to-r from-emerald-500 to-[#00ff88] h-full transition-all duration-500"
                            style={{
                              width: `${executiveReport?.compliance?.compliance_score_percent || 0}%`,
                            }}
                          ></div>
                        </div>
                      </div>

                      {/* Checklist Items */}
                      {executiveReport?.compliance?.checklist?.length > 0 && (
                        <div className="border-t border-white/5 pt-3 mt-3 space-y-2">
                          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">
                            Checklist Items
                          </span>
                          <div className="space-y-2">
                            {executiveReport.compliance.checklist.map((item: any) => (
                              <div
                                key={item.id}
                                className="flex items-center justify-between p-2.5 bg-white/5 border border-white/5 rounded-lg text-xs"
                              >
                                <span className="text-slate-300 font-medium">{item.task}</span>
                                <span
                                  className={`px-2 py-0.5 rounded-full text-[9px] font-black tracking-widest ${
                                    item.status
                                      ? 'bg-emerald-950/20 text-[#00ff88] border border-emerald-500/20'
                                      : 'bg-rose-950/20 text-rose-400 border border-rose-500/20'
                                  }`}
                                >
                                  {item.status ? 'PASSED' : 'PENDING'}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {executiveReport?.compliance?.required_notifications?.length > 0 && (
                        <div className="border-t border-white/5 pt-3 mt-2">
                          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-2">
                            Required Compliance Reports
                          </span>
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
  );
};
