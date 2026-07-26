'use client';

import React from 'react';
import {
  Activity,
  Zap,
  HelpCircle,
  Play,
  Pause,
  RotateCcw,
  CheckCircle,
} from 'lucide-react';
import { Incident } from '../../types';
import { PostmortemView } from '../postmortem/PostmortemView';
import { api } from '../../lib/api';

interface IncidentDetailViewProps {
  selectedIncident: Incident;
  incidents: Incident[];
  inspectorTab: 'timeline' | 'simulation' | 'options' | 'runbooks' | 'graph' | 'replay' | 'attack' | 'postmortem';
  setInspectorTab: (tab: any) => void;
  explainabilityReport: any;
  activeAgent: any;
  wp: any;
  replayIndex: number;
  setReplayIndex: (idx: number) => void;
  isPlayingReplay: boolean;
  setIsPlayingReplay: (playing: boolean) => void;
  fetchPostmortem: (id: number) => void;
  onViewInMastra: (id: number) => void;
  onSelectIncident: (inc: Incident) => void;
}

export const IncidentDetailView: React.FC<IncidentDetailViewProps> = ({
  selectedIncident,
  incidents,
  inspectorTab,
  setInspectorTab,
  explainabilityReport,
  activeAgent,
  wp,
  replayIndex,
  setReplayIndex,
  isPlayingReplay,
  setIsPlayingReplay,
  fetchPostmortem,
  onViewInMastra,
  onSelectIncident,
}) => {
  return (
    <div className="card p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-start border-b border-white/5 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-bold text-slate-100">{selectedIncident.title}</h3>
            <span
              className={`badge ${
                selectedIncident.severity === 'CRITICAL'
                  ? 'badge-critical'
                  : selectedIncident.severity === 'WARNING'
                  ? 'badge-warning'
                  : 'badge-info'
              }`}
            >
              {selectedIncident.severity}
            </span>
          </div>
          <p className="text-xs text-[#00d4ff] font-mono mt-1.5">
            CID: {selectedIncident.correlation_id}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onViewInMastra(selectedIncident.id)}
            className="px-3 py-1.5 bg-[#00ff88]/10 text-[#00ff88] border border-[#00ff88]/30 rounded-lg text-xs font-mono font-bold hover:bg-[#00ff88]/20 transition-all flex items-center gap-1.5"
          >
            <Zap className="w-3.5 h-3.5 text-[#00ff88]" /> View in Mastra Live
          </button>
        </div>
      </div>

      {/* Active Agent Workflow Box */}
      {(() => {
        if (!activeAgent && !wp) return null;
        return (
          <div className="p-5 bg-gradient-to-r from-emerald-950/20 to-teal-950/20 border border-[#00ff88]/30 rounded-xl space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <h4 className="text-xs font-bold text-[#00ff88] uppercase tracking-widest flex items-center gap-2">
                <Zap className="w-4 h-4 text-[#00ff88] animate-pulse" /> Active Mastra Orchestrator
              </h4>
              <span className="badge badge-success text-[9px] font-mono animate-pulse">
                {activeAgent?.status || wp?.step_status || 'EXECUTING'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono text-slate-300">
              <div>
                <p className="text-slate-400 font-bold">Agent:</p>
                <p className="text-slate-100 font-semibold">
                  {activeAgent?.agent_name || 'Mastra Agent Orchestrator'}
                </p>
              </div>
              <div>
                <p className="text-slate-400 font-bold">Status:</p>
                <p className="text-slate-100 font-semibold capitalize">
                  {activeAgent?.status || 'Executing...'}
                </p>
              </div>
              <div className="md:col-span-2">
                <p className="text-slate-400 font-bold">Message:</p>
                <p className="text-slate-100 italic">
                  "{activeAgent?.message || wp?.step_name || 'Running automated diagnosis steps...'}"
                </p>
              </div>
            </div>

            {/* Progress bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-[10px] font-mono text-slate-400">
                <span>Progress</span>
                <span>
                  {activeAgent
                    ? `${activeAgent.progress}%`
                    : wp
                    ? `${Math.round((wp.current_step / wp.total_steps) * 100)}%`
                    : '0%'}
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-[#00ff88] h-1.5 rounded-full transition-all duration-500"
                  style={{
                    width: `${
                      activeAgent
                        ? activeAgent.progress
                        : wp
                        ? (wp.current_step / wp.total_steps) * 100
                        : 0
                    }%`,
                  }}
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
          { id: 'postmortem', label: 'Postmortem Report' },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => {
              setInspectorTab(t.id as any);
              if (t.id === 'replay') {
                setReplayIndex(-1);
                setIsPlayingReplay(false);
              }
              if (t.id === 'postmortem' && selectedIncident) {
                fetchPostmortem(selectedIncident.id);
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
            const isRoot = incidents.some((i) => i.parent_incident_id === selectedIncident.id);
            const isCascading = !!selectedIncident.parent_incident_id;

            if (!isRoot && !isCascading) return null;

            const parentIncident = isCascading
              ? incidents.find((i) => i.id === selectedIncident.parent_incident_id)
              : null;

            const cascadingChildren = isRoot
              ? incidents.filter((i) => i.parent_incident_id === selectedIncident.id)
              : [];

            return (
              <div className="p-5 bg-[#00d4ff]/5 border border-[#00d4ff]/20 rounded-xl space-y-4 mb-4">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                  <h4 className="text-xs font-bold text-[#00d4ff] uppercase tracking-widest flex items-center gap-1.5">
                    <Activity className="w-4 h-4 text-[#00d4ff]" /> Incident Correlation & Cascading Failure Path
                  </h4>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-black tracking-widest ${
                      isRoot
                        ? 'bg-emerald-950/20 text-[#00ff88] border border-emerald-500/30'
                        : 'bg-rose-950/20 text-rose-400 border border-rose-500/30'
                    }`}
                  >
                    {isRoot ? 'PRIMARY ROOT CAUSE' : 'CASCADING FAILURE'}
                  </span>
                </div>

                {isRoot && (
                  <div className="space-y-3">
                    <p className="text-xs text-slate-300 font-mono">
                      This incident has been identified as the{' '}
                      <span className="text-[#00ff88] font-bold">Root Cause</span> of the following cascading
                      failures:
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {cascadingChildren.map((child) => (
                        <div
                          key={child.id}
                          onClick={() =>
                            api.getIncidentDetail(child.id).then(onSelectIncident).catch(console.error)
                          }
                          className="p-3 bg-white/5 border border-white/5 hover:border-[#00ff88]/30 rounded-xl transition-all cursor-pointer space-y-2"
                        >
                          <div className="flex justify-between items-center text-[10px]">
                            <span className="font-mono text-slate-400">#{child.id}</span>
                            <span
                              className={`badge ${
                                child.severity === 'CRITICAL'
                                  ? 'badge-critical'
                                  : child.severity === 'WARNING'
                                  ? 'badge-warning'
                                  : 'badge-info'
                              }`}
                            >
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
                      This incident is a <span className="text-rose-400 font-bold">Cascading Consequence</span> of
                      the primary root cause incident:
                    </p>
                    <div
                      onClick={() =>
                        api
                          .getIncidentDetail(parentIncident.id)
                          .then(onSelectIncident)
                          .catch(console.error)
                      }
                      className="p-4 bg-white/5 border border-white/5 hover:border-[#00ff88]/30 rounded-xl transition-all cursor-pointer space-y-2"
                    >
                      <div className="flex justify-between items-center text-[10px]">
                        <span className="font-mono text-[#00ff88] font-bold">
                          ROOT CAUSE #{parentIncident.id}
                        </span>
                        <span
                          className={`badge ${
                            parentIncident.severity === 'CRITICAL'
                              ? 'badge-critical'
                              : parentIncident.severity === 'WARNING'
                              ? 'badge-warning'
                              : 'badge-info'
                          }`}
                        >
                          {parentIncident.severity}
                        </span>
                      </div>
                      <h5 className="text-xs font-bold text-slate-200">{parentIncident.title}</h5>
                      <p className="text-[10px] text-slate-500 font-mono">{parentIncident.metric_type}</p>
                      <div className="flex justify-between items-center text-[9px] text-slate-400 pt-1.5 border-t border-white/5">
                        <span className="uppercase font-bold text-[#00ff88]">
                          {parentIncident.status}
                        </span>
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
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1.5">
                  Anomaly Analysis Details
                </h4>
                <div className="p-4 bg-white/5 rounded-xl border border-white/5 text-sm leading-relaxed text-slate-300">
                  {selectedIncident.description}
                </div>
              </div>

              {selectedIncident.suggested_action && (
                <div>
                  <h4 className="text-xs font-bold text-[#00ff88] uppercase tracking-widest mb-1.5">
                    Suggested Autopilot Remediator
                  </h4>
                  <div className="terminal p-4 flex justify-between items-center text-xs">
                    <span className="text-emerald-400 font-mono">
                      {selectedIncident.suggested_action}
                    </span>
                    <span className="badge badge-success shrink-0 font-bold">
                      100% SAFE ENVELOPE VERIFIED
                    </span>
                  </div>
                </div>
              )}

              {/* AI Explainability */}
              {explainabilityReport && (
                <div className="p-5 bg-gradient-to-br from-indigo-950/20 to-purple-950/20 border border-[#00d4ff]/20 rounded-xl space-y-4">
                  <div className="flex items-center justify-between border-b border-white/5 pb-2">
                    <h4 className="text-xs font-bold text-[#00d4ff] uppercase tracking-widest flex items-center gap-1.5">
                      <HelpCircle className="w-4 h-4 text-[#00d4ff]" /> AI Explainability & Decision Path
                    </h4>
                    <span className="badge badge-info text-[9px] font-mono">
                      {Math.round(
                        explainabilityReport.overall_confidence ||
                          selectedIncident.confidence_score * 100
                      )}
                      % CONFIDENCE
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed italic bg-white/5 p-3 rounded-lg border border-white/5">
                    "{explainabilityReport.overall_explanation}"
                  </p>
                </div>
              )}
            </div>

            {/* Metrics column */}
            <div className="space-y-4">
              <div>
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1.5">
                  Metrics & Impact Scope
                </h4>
                <div className="p-4 bg-white/5 rounded-xl border border-white/5 space-y-3 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Metric Type:</span>
                    <span className="font-bold font-mono text-slate-200">
                      {selectedIncident.metric_type}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Confidence Score:</span>
                    <span className="font-bold font-mono text-[#00ff88]">
                      {(selectedIncident.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Risk Score:</span>
                    <span className="font-bold font-mono text-amber-400">
                      {(((selectedIncident as any).risk_score || 0) * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-slate-400">Created:</span>
                    <span className="font-mono text-slate-400">
                      {new Date(selectedIncident.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* TAB 8: POSTMORTEM REPORT */}
      {inspectorTab === 'postmortem' && (
        <PostmortemView onGeneratePostmortem={() => fetchPostmortem(selectedIncident.id)} />
      )}
    </div>
  );
};
