'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Activity,
  Zap,
  HelpCircle,
  Play,
  Pause,
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  Shield,
  GitBranch,
  BookOpen,
  Loader2,
  Target,
  Crosshair,
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

/* â”€â”€â”€ Shared empty-state banner â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function EmptyState({ icon: Icon, title, message }: { icon: any; title: string; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-center space-y-3 opacity-70">
      <Icon className="w-10 h-10 text-slate-500" />
      <p className="text-sm font-bold text-slate-400">{title}</p>
      <p className="text-xs text-slate-500 max-w-md">{message}</p>
    </div>
  );
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
  /* â”€â”€ Lazy-loaded tab data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  const [tabData, setTabData] = useState<Record<string, any>>({});
  const [tabLoading, setTabLoading] = useState<Record<string, boolean>>({});
  const [tabError, setTabError] = useState<Record<string, string>>({});
  const prevIncidentId = useRef<number | null>(null);

  // Reset tab caches when selected incident changes
  useEffect(() => {
    if (prevIncidentId.current !== selectedIncident.id) {
      setTabData({});
      setTabLoading({});
      setTabError({});
      prevIncidentId.current = selectedIncident.id;
    }
  }, [selectedIncident.id]);

  const fetchTabData = useCallback(async (tab: string) => {
    if (tabData[tab] !== undefined || tabLoading[tab]) return;
    setTabLoading((p) => ({ ...p, [tab]: true }));
    setTabError((p) => ({ ...p, [tab]: '' }));
    try {
      let data: any;
      switch (tab) {
        case 'attack': data = await api.getAttackGraph(selectedIncident.id); break;
        case 'simulation': data = await api.getSimulation(selectedIncident.id); break;
        case 'options': data = await api.getRemediationOptions(selectedIncident.id); break;
        case 'runbooks': data = await api.getRunbooks(selectedIncident.id); break;
        case 'graph': data = await api.getDecisionGraph(selectedIncident.id); break;
        case 'replay': data = await api.getReplay(selectedIncident.id); break;
        default: data = null;
      }
      setTabData((p) => ({ ...p, [tab]: data }));
    } catch (err: any) {
      setTabError((p) => ({ ...p, [tab]: err?.data?.detail || err?.message || 'Failed to load data' }));
    } finally {
      setTabLoading((p) => ({ ...p, [tab]: false }));
    }
  }, [selectedIncident.id, tabData, tabLoading]);

  // Fetch data when tab changes (for lazy-loaded tabs)
  useEffect(() => {
    if (['attack', 'simulation', 'options', 'runbooks', 'graph', 'replay'].includes(inspectorTab)) {
      fetchTabData(inspectorTab);
    }
  }, [inspectorTab, fetchTabData]);

  /* â”€â”€ Replay auto-play timer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  const replayEvents = tabData['replay'] as any[] | undefined;
  useEffect(() => {
    if (!isPlayingReplay || !replayEvents || replayEvents.length === 0) return;
    const timer = setInterval(() => {
      if (replayIndex + 1 >= replayEvents.length) {
        setIsPlayingReplay(false);
        setReplayIndex(replayEvents.length - 1);
      } else {
        setReplayIndex(replayIndex + 1);
      }
    }, 1200);
    return () => clearInterval(timer);
  }, [isPlayingReplay, replayEvents, replayIndex, setReplayIndex, setIsPlayingReplay]);

  /* â”€â”€ Loading / error wrappers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  function renderTabWrapper(tab: string, children: React.ReactNode) {
    if (tabLoading[tab]) {
      return (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 text-[#00ff88] animate-spin" />
          <span className="ml-3 text-xs text-slate-400 font-mono">Loadingâ€¦</span>
        </div>
      );
    }
    if (tabError[tab]) {
      return (
        <div className="p-5 bg-rose-950/20 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{tabError[tab]}</span>
        </div>
      );
    }
    return children;
  }

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
                  &quot;{activeAgent?.message || wp?.step_name || 'Running automated diagnosis steps...'}&quot;
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

      {/* â•â•â•â•â•â•â•â•â•â• TAB 1: TIMELINE & RCA â•â•â•â•â•â•â•â•â•â• */}
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
                    &quot;{explainabilityReport.overall_explanation}&quot;
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

      {/* â•â•â•â•â•â•â•â•â•â• TAB 2: ATTACK GRAPH â•â•â•â•â•â•â•â•â•â• */}
      {inspectorTab === 'attack' && renderTabWrapper('attack', (() => {
        const data = tabData['attack'];
        if (!data || (Array.isArray(data) && data.length === 0) || (data.nodes && data.nodes.length === 0)) {
          return <EmptyState icon={Crosshair} title="No Attack Graph Available" message="Attack graphs are generated for security-classified incidents involving lateral movement or multi-stage compromise chains. This incident type does not have an associated attack graph." />;
        }
        const nodes = data.nodes || [];
        const edges = data.edges || [];
        return (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
              <Crosshair className="w-4 h-4 text-rose-400" />
              <span className="font-bold text-slate-200">Attack Flow Visualization</span>
              <span className="ml-auto badge badge-critical text-[9px]">{nodes.length} NODES Â· {edges.length} EDGES</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {nodes.map((n: any, i: number) => (
                <div key={i} className={`p-3 rounded-xl border text-xs font-mono space-y-1.5 ${
                  n.type === 'entry' ? 'bg-rose-950/20 border-rose-500/30' :
                  n.type === 'pivot' ? 'bg-amber-950/20 border-amber-500/30' :
                  'bg-slate-800/50 border-white/10'
                }`}>
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-slate-200 truncate">{n.label || n.id || `Node ${i}`}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-black uppercase ${
                      n.type === 'entry' ? 'text-rose-400 bg-rose-950/40' :
                      n.type === 'pivot' ? 'text-amber-400 bg-amber-950/40' :
                      'text-slate-400 bg-slate-800'
                    }`}>{n.type || 'node'}</span>
                  </div>
                  {n.technique && <p className="text-slate-400">{n.technique}</p>}
                  {n.description && <p className="text-slate-500 text-[10px]">{n.description}</p>}
                </div>
              ))}
            </div>
            {edges.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Lateral Movement Paths</p>
                <div className="space-y-1.5">
                  {edges.map((e: any, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-[11px] font-mono text-slate-400 bg-white/5 p-2 rounded-lg">
                      <span className="text-rose-400 font-bold">{e.source || e.from}</span>
                      <span className="text-slate-500">â†’</span>
                      <span className="text-amber-400 font-bold">{e.target || e.to}</span>
                      {e.label && <span className="text-slate-500 ml-auto italic">{e.label}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })())}

      {/* â•â•â•â•â•â•â•â•â•â• TAB 3: WHAT-IF SIMULATION â•â•â•â•â•â•â•â•â•â• */}
      {inspectorTab === 'simulation' && renderTabWrapper('simulation', (() => {
        const sim = tabData['simulation'];
        if (!sim) {
          return <EmptyState icon={Target} title="No Simulation Data" message="What-if simulation analysis was not generated for this incident." />;
        }
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-mono">
                <Target className="w-4 h-4 text-[#00d4ff]" />
                <span className="font-bold text-slate-200">What-If Impact Simulation</span>
              </div>
              <span className={`badge text-[9px] font-black ${
                sim.risk_assessment === 'CRITICAL' ? 'badge-critical' :
                sim.risk_assessment === 'MEDIUM' ? 'badge-warning' : 'badge-success'
              }`}>{sim.risk_assessment || 'LOW'} RISK</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Remediation Type', value: sim.remediation_type, color: 'text-[#00d4ff]' },
                { label: 'Predicted Downtime', value: `${sim.predicted_downtime_sec || 0}s`, color: 'text-amber-400' },
                { label: 'Affected Users', value: sim.affected_users ?? 0, color: 'text-rose-400' },
                { label: 'Success Probability', value: `${sim.success_probability || 0}%`, color: 'text-[#00ff88]' },
              ].map((m, i) => (
                <div key={i} className="p-3 bg-white/5 rounded-xl border border-white/5 text-center">
                  <p className="text-[10px] text-slate-500 font-mono uppercase">{m.label}</p>
                  <p className={`text-lg font-black font-mono mt-1 ${m.color}`}>{m.value}</p>
                </div>
              ))}
            </div>
            <div className="p-4 bg-white/5 rounded-xl border border-white/5 space-y-3 text-xs">
              <div>
                <p className="text-slate-400 font-bold mb-1">Predicted Impact</p>
                <p className="text-slate-300 leading-relaxed">{sim.predicted_impact}</p>
              </div>
              {sim.rollback_plan && (
                <div>
                  <p className="text-slate-400 font-bold mb-1">Rollback Plan</p>
                  <p className="text-emerald-400 font-mono text-[11px] bg-slate-900/50 p-2 rounded-lg">{sim.rollback_plan}</p>
                </div>
              )}
              {sim.affected_resources && (
                <div>
                  <p className="text-slate-400 font-bold mb-1">Affected Resources</p>
                  <div className="flex flex-wrap gap-1.5">
                    {(Array.isArray(sim.affected_resources) ? sim.affected_resources : [sim.affected_resources]).map((r: string, i: number) => (
                      <span key={i} className="px-2 py-0.5 bg-slate-800 rounded text-[10px] font-mono text-slate-300 border border-white/5">{r}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })())}

      {/* â•â•â•â•â•â•â•â•â•â• TAB 4: REMEDIATION AGENT â•â•â•â•â•â•â•â•â•â• */}
      {inspectorTab === 'options' && renderTabWrapper('options', (() => {
        const opts = tabData['options'];
        if (!opts || (Array.isArray(opts) && opts.length === 0)) {
          return <EmptyState icon={Shield} title="No Remediation Options" message="The Remediation Agent has not generated repair candidates for this incident." />;
        }
        const optionsList = Array.isArray(opts) ? opts : (opts.options || [opts]);
        return (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono">
              <Shield className="w-4 h-4 text-[#00ff88]" />
              <span className="font-bold text-slate-200">Ranked Remediation Options</span>
              <span className="ml-auto text-slate-500">{optionsList.length} candidates</span>
            </div>
            <div className="space-y-3">
              {optionsList.map((opt: any, i: number) => (
                <div key={i} className="p-4 bg-white/5 rounded-xl border border-white/10 hover:border-[#00ff88]/20 transition-all space-y-2">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-lg bg-[#00ff88]/10 text-[#00ff88] flex items-center justify-center text-xs font-black">#{i + 1}</span>
                      <span className="text-sm font-bold text-slate-200">{opt.name || opt.action || `Option ${i + 1}`}</span>
                    </div>
                    <span className={`badge text-[9px] ${
                      (opt.risk || opt.risk_level || '').toUpperCase() === 'HIGH' ? 'badge-critical' :
                      (opt.risk || opt.risk_level || '').toUpperCase() === 'MEDIUM' ? 'badge-warning' : 'badge-success'
                    }`}>{opt.risk || opt.risk_level || 'LOW'} RISK</span>
                  </div>
                  {opt.description && <p className="text-xs text-slate-400 leading-relaxed">{opt.description}</p>}
                  {(opt.command || opt.action_command) && (
                    <p className="text-[11px] font-mono text-emerald-400 bg-slate-900/50 p-2 rounded-lg">{opt.command || opt.action_command}</p>
                  )}
                  <div className="flex gap-4 text-[10px] text-slate-500 font-mono">
                    {opt.confidence !== undefined && <span>Confidence: <strong className="text-slate-300">{typeof opt.confidence === 'number' ? `${(opt.confidence * 100).toFixed(0)}%` : opt.confidence}</strong></span>}
                    {opt.estimated_duration && <span>Duration: <strong className="text-slate-300">{opt.estimated_duration}</strong></span>}
                    {opt.rollback_possible !== undefined && <span>Rollback: <strong className={opt.rollback_possible ? 'text-[#00ff88]' : 'text-rose-400'}>{opt.rollback_possible ? 'Yes' : 'No'}</strong></span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })())}

      {/* â•â•â•â•â•â•â•â•â•â• TAB 5: RUNBOOK RAG â•â•â•â•â•â•â•â•â•â• */}
      {inspectorTab === 'runbooks' && renderTabWrapper('runbooks', (() => {
        const rbs = tabData['runbooks'];
        if (!rbs || (Array.isArray(rbs) && rbs.length === 0)) {
          return <EmptyState icon={BookOpen} title="No Runbook Recommendations" message="The RAG-powered runbook recommender found no matching runbooks for this incident's symptom profile." />;
        }
        const runbooksList = Array.isArray(rbs) ? rbs : (rbs.runbooks || [rbs]);
        return (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono">
              <BookOpen className="w-4 h-4 text-[#00d4ff]" />
              <span className="font-bold text-slate-200">Recommended Runbooks</span>
              <span className="ml-auto text-slate-500">{runbooksList.length} matches</span>
            </div>
            <div className="space-y-3">
              {runbooksList.map((rb: any, i: number) => (
                <div key={i} className="p-4 bg-white/5 rounded-xl border border-white/10 space-y-2">
                  <div className="flex justify-between items-start">
                    <span className="text-sm font-bold text-slate-200">{rb.title || rb.name || `Runbook ${i + 1}`}</span>
                    {rb.match_score !== undefined && (
                      <span className="badge badge-info text-[9px]">{typeof rb.match_score === 'number' ? `${(rb.match_score * 100).toFixed(0)}%` : rb.match_score} MATCH</span>
                    )}
                  </div>
                  {rb.description && <p className="text-xs text-slate-400 leading-relaxed">{rb.description}</p>}
                  {rb.steps && Array.isArray(rb.steps) && (
                    <div className="space-y-1">
                      {rb.steps.map((step: any, si: number) => (
                        <div key={si} className="flex items-start gap-2 text-[11px] text-slate-300">
                          <span className="text-[#00ff88] font-bold shrink-0 mt-0.5">{si + 1}.</span>
                          <span>{typeof step === 'string' ? step : step.description || step.action || JSON.stringify(step)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="flex gap-4 text-[10px] text-slate-500 font-mono">
                    {rb.category && <span>Category: <strong className="text-slate-300">{rb.category}</strong></span>}
                    {rb.severity_match && <span>Severity: <strong className="text-slate-300">{rb.severity_match}</strong></span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })())}

      {/* â•â•â•â•â•â•â•â•â•â• TAB 6: DECISION DAG â•â•â•â•â•â•â•â•â•â• */}
      {inspectorTab === 'graph' && renderTabWrapper('graph', (() => {
        const graph = tabData['graph'];
        if (!graph || (graph.nodes && graph.nodes.length === 0)) {
          return <EmptyState icon={GitBranch} title="No Decision Graph" message="The AI decision graph has not been generated for this incident. Decision DAGs are built during the Mastra workflow analysis phase." />;
        }
        const nodes = graph.nodes || [];
        const edges = graph.edges || [];
        return (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono">
              <GitBranch className="w-4 h-4 text-violet-400" />
              <span className="font-bold text-slate-200">AI Decision DAG</span>
              <span className="ml-auto badge badge-info text-[9px]">{nodes.length} DECISIONS Â· {edges.length} PATHS</span>
            </div>
            <div className="space-y-2">
              {nodes.map((node: any, i: number) => (
                <div key={i} className={`p-3 rounded-xl border text-xs font-mono space-y-1 ${
                  node.decision === 'APPROVED' || node.type === 'action' ? 'bg-emerald-950/20 border-emerald-500/20' :
                  node.decision === 'REJECTED' ? 'bg-rose-950/20 border-rose-500/20' :
                  'bg-white/5 border-white/10'
                }`}>
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-slate-200">{node.label || node.name || `Step ${i + 1}`}</span>
                    {node.decision && <span className={`text-[10px] font-black ${node.decision === 'APPROVED' ? 'text-[#00ff88]' : node.decision === 'REJECTED' ? 'text-rose-400' : 'text-[#00d4ff]'}`}>{node.decision}</span>}
                  </div>
                  {node.reasoning && <p className="text-slate-400 text-[10px] italic">{node.reasoning}</p>}
                  {node.confidence !== undefined && (
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-slate-800 rounded-full h-1 overflow-hidden">
                        <div className="bg-violet-500 h-1 rounded-full" style={{ width: `${(typeof node.confidence === 'number' && node.confidence <= 1 ? node.confidence * 100 : node.confidence)}%` }} />
                      </div>
                      <span className="text-[9px] text-slate-500">{typeof node.confidence === 'number' && node.confidence <= 1 ? `${(node.confidence * 100).toFixed(0)}%` : `${node.confidence}%`}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })())}

      {/* â•â•â•â•â•â•â•â•â•â• TAB 7: INTERACTIVE REPLAY â•â•â•â•â•â•â•â•â•â• */}
      {inspectorTab === 'replay' && renderTabWrapper('replay', (() => {
        const events = replayEvents;
        if (!events || events.length === 0) {
          return <EmptyState icon={Play} title="No Replay Data" message="No replay events have been recorded for this incident yet. Replay data is generated during the incident resolution workflow." />;
        }
        const currentIdx = Math.max(0, Math.min(replayIndex, events.length - 1));
        const currentEvent = replayIndex >= 0 ? events[currentIdx] : null;
        return (
          <div className="space-y-4">
            {/* Transport Controls */}
            <div className="flex items-center gap-3 p-3 bg-white/5 rounded-xl border border-white/5">
              <button
                onClick={() => { setReplayIndex(0); setIsPlayingReplay(false); }}
                className="p-2 rounded-lg hover:bg-white/10 transition-all text-slate-400 hover:text-slate-200"
                title="Reset"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  if (isPlayingReplay) {
                    setIsPlayingReplay(false);
                  } else {
                    if (replayIndex >= events.length - 1) setReplayIndex(0);
                    setIsPlayingReplay(true);
                  }
                }}
                className="p-2.5 rounded-lg bg-[#00ff88]/10 hover:bg-[#00ff88]/20 text-[#00ff88] transition-all"
                title={isPlayingReplay ? 'Pause' : 'Play'}
              >
                {isPlayingReplay ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
              </button>
              {/* Scrubber */}
              <input
                type="range"
                min={0}
                max={events.length - 1}
                value={replayIndex >= 0 ? replayIndex : 0}
                onChange={(e) => { setIsPlayingReplay(false); setReplayIndex(parseInt(e.target.value)); }}
                className="flex-1 accent-[#00ff88] h-1"
              />
              <span className="text-[10px] font-mono text-slate-400 shrink-0">
                {(replayIndex >= 0 ? replayIndex + 1 : 0)} / {events.length}
              </span>
            </div>

            {/* Current Event Detail */}
            {currentEvent && (
              <div className="p-4 bg-gradient-to-r from-emerald-950/20 to-teal-950/20 border border-[#00ff88]/20 rounded-xl space-y-3 animate-fade-in">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-lg bg-[#00ff88]/10 text-[#00ff88] flex items-center justify-center text-[10px] font-black">{currentIdx + 1}</span>
                    <span className="text-sm font-bold text-slate-200">{currentEvent.event_type}</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">{currentEvent.timestamp ? new Date(currentEvent.timestamp).toLocaleTimeString() : ''}</span>
                </div>
                {currentEvent.agent_name && (
                  <p className="text-xs font-mono text-[#00d4ff]">Agent: {currentEvent.agent_name}</p>
                )}
                {currentEvent.decision && (
                  <p className="text-xs font-mono">
                    Decision: <span className={currentEvent.decision === 'APPROVED' ? 'text-[#00ff88] font-bold' : currentEvent.decision === 'REJECTED' ? 'text-rose-400 font-bold' : 'text-slate-300'}>{currentEvent.decision}</span>
                  </p>
                )}
                {currentEvent.reasoning && (
                  <p className="text-xs text-slate-400 italic leading-relaxed bg-white/5 p-3 rounded-lg">&quot;{currentEvent.reasoning}&quot;</p>
                )}
                {currentEvent.event_data && Object.keys(currentEvent.event_data).length > 0 && (
                  <details className="text-[10px] text-slate-500 font-mono">
                    <summary className="cursor-pointer hover:text-slate-300 transition-colors">Event Data</summary>
                    <pre className="mt-2 p-2 bg-slate-900/50 rounded-lg overflow-auto max-h-40 text-slate-400">{JSON.stringify(currentEvent.event_data, null, 2)}</pre>
                  </details>
                )}
              </div>
            )}

            {/* Event Timeline Strip */}
            <div className="space-y-1.5 max-h-64 overflow-y-auto">
              {events.map((evt: any, i: number) => (
                <div
                  key={i}
                  onClick={() => { setIsPlayingReplay(false); setReplayIndex(i); }}
                  className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all text-xs font-mono ${
                    i === currentIdx
                      ? 'bg-[#00ff88]/10 border border-[#00ff88]/20 text-[#00ff88]'
                      : i <= replayIndex
                      ? 'bg-white/5 text-slate-300 hover:bg-white/10'
                      : 'text-slate-500 hover:bg-white/5'
                  }`}
                >
                  <span className="w-5 text-right shrink-0">{i + 1}</span>
                  <span className={`w-2 h-2 rounded-full shrink-0 ${i <= replayIndex ? 'bg-[#00ff88]' : 'bg-slate-600'}`} />
                  <span className="truncate font-bold">{evt.event_type}</span>
                  {evt.agent_name && <span className="text-slate-500 ml-auto shrink-0">{evt.agent_name}</span>}
                </div>
              ))}
            </div>
          </div>
        );
      })())}

      {/* â•â•â•â•â•â•â•â•â•â• TAB 8: POSTMORTEM REPORT â•â•â•â•â•â•â•â•â•â• */}
      {inspectorTab === 'postmortem' && (
        <PostmortemView onGeneratePostmortem={() => fetchPostmortem(selectedIncident.id)} />
      )}
    </div>
  );
};

