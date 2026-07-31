'use client';

import React, { useState } from 'react';
import {
  Zap,
  RefreshCw,
  AlertTriangle,
  Database,
  Loader2,
  Activity,
  Cpu,
  ListChecks,
  Terminal,
  Clock,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { useMastraStore } from '../../store/mastraStore';
import { api } from '../../lib/api';
import { useWebSocket } from '../../hooks/useWebSocket';
import { QdrantRetrievalPanel } from '../qdrant/QdrantRetrievalPanel';
import { EnkryptValidationPanel } from '../enkrypt/EnkryptValidationPanel';

interface MastraExecutionCenterProps {
  onTriggerDemo: (type: string) => Promise<void>;
}

export const MastraExecutionCenter: React.FC<MastraExecutionCenterProps> = ({
  onTriggerDemo,
}) => {
  const {
    mastraEvents,
    setMastraEvents,
    mastraExecution,
    setMastraExecution,
    mastraSelectedId,
    setMastraSelectedId,
    mastraLoading,
    setMastraLoading,
    setRagEvents,
    setEnkryptEvents,
  } = useMastraStore();

  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  // Subscribe to real-time WebSocket events
  useWebSocket('MastraExecution', (evtData: any) => {
    if (evtData) {
      setMastraEvents((prev: any[]) => [...prev.slice(-49), evtData]);
      if (evtData.incident_id === mastraSelectedId || !mastraSelectedId) {
        setMastraExecution((prev: any) => {
          if (!prev) return prev;
          const updatedPipeline = (prev.pipeline || []).map((step: any) => {
            if (step.step_key === evtData.step_name || step.step_number === evtData.step_number) {
              return {
                ...step,
                status: evtData.step_status,
                duration_seconds: evtData.duration_seconds || step.duration_seconds,
                input_excerpt: evtData.input_excerpt || step.input_excerpt,
                output_excerpt: evtData.output_excerpt || step.output_excerpt,
                is_simulated: evtData.is_simulated || step.is_simulated,
                simulation_reason: evtData.simulation_reason || step.simulation_reason,
                token_usage: evtData.token_usage || step.token_usage,
                confidence: evtData.confidence || step.confidence,
              };
            }
            return step;
          });
          return {
            ...prev,
            pipeline: updatedPipeline,
            agent: evtData.agent_name
              ? { name: evtData.agent_name, sub_type: evtData.agent_sub_type, domain: evtData.agent_domain }
              : prev.agent,
            ai_provider: evtData.ai_provider || prev.ai_provider,
            confidence: evtData.confidence || prev.confidence,
            safety: {
              status: evtData.safety_status || prev.safety?.status,
              risk_score: evtData.risk_score || prev.safety?.risk_score,
            },
          };
        });
      }
    }
  });

  useWebSocket('RAGRetrieval', (evtData: any) => {
    if (evtData) {
      setRagEvents((prev: any[]) => [...prev.slice(-19), evtData]);
    }
  });

  useWebSocket('EnkryptValidation', (evtData: any) => {
    if (evtData) {
      setEnkryptEvents((prev: any[]) => [...prev.slice(-29), evtData]);
    }
  });

  const handleRefresh = async () => {
    setMastraLoading(true);
    try {
      const res = await api.getActiveExecution();
      setMastraExecution(res);
      setMastraSelectedId(res.incident?.id || null);
    } catch (e) {
      console.error(e);
    }
    setMastraLoading(false);
  };

  const mastraOptions = (() => {
    if (!mastraExecution?.incident?.remediation_options_json) return null;
    try {
      return JSON.parse(mastraExecution.incident.remediation_options_json);
    } catch {
      return null;
    }
  })();

  // Compute overall workflow duration
  const totalWorkflowSeconds = (mastraExecution?.pipeline || []).reduce(
    (acc: number, s: any) => acc + (s.duration_seconds || 0),
    0
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white flex items-center gap-3">
          <Zap className="w-5 h-5 text-[#00ff88]" />
          Mastra Live AI Orchestration Execution Center
        </h2>
        <div className="flex gap-2">
          <button
            onClick={handleRefresh}
            className="px-3 py-1.5 bg-[#00ff88]/10 text-[#00ff88] border border-[#00ff88]/30 rounded-lg text-xs font-mono hover:bg-[#00ff88]/20 transition-all flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3 h-3 ${mastraLoading ? 'animate-spin' : ''}`} />
            Refresh Execution
          </button>
        </div>
      </div>

      {/* Quick Demo Triggers */}
      <div className="card p-4">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">
          Trigger Incident Scenario to Observe Live AI Orchestration
        </h4>
        <div className="flex flex-wrap gap-2">
          {[
            'CPU_SPIKE',
            'MEMORY_EXHAUSTION',
            'UNAUTHORIZED_ACCESS',
            'DISK_FULL',
            'HIGH_LATENCY',
            'ERROR_RATE_SPIKE',
            'DDOS_ATTACK',
            'NETWORK_OUTAGE',
          ].map((type) => (
            <button
              key={type}
              onClick={() => onTriggerDemo(type)}
              className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-[10px] font-mono text-slate-300 hover:bg-[#00ff88]/10 hover:text-[#00ff88] hover:border-[#00ff88]/30 transition-all"
            >
              {type.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {mastraExecution ? (
        <>
          {/* Simulated Fallback Warning Banner */}
          {(mastraExecution?.is_simulated ||
            mastraExecution?.incident?.is_simulated ||
            mastraExecution?.rca?.is_simulated ||
            mastraExecution?.result?.is_simulated ||
            mastraExecution?.threats?.is_simulated ||
            mastraExecution?.remediation?.is_simulated) && (
            <div className="p-4 bg-amber-500/15 border border-amber-500/40 rounded-xl flex items-center justify-between gap-4 text-amber-300">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 animate-pulse" />
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-amber-200">
                    ⚠ Simulated Fallback Active — Provider/Quota Limitation
                  </h4>
                  <p className="text-xs text-amber-300/80 font-mono mt-0.5">
                    Reason:{' '}
                    {mastraExecution?.simulation_reason ||
                      mastraExecution?.incident?.simulation_reason ||
                      mastraExecution?.rca?.simulation_reason ||
                      mastraExecution?.result?.simulation_reason ||
                      'Live LLM provider threw an exception or returned simulated fallback data.'}
                  </p>
                </div>
              </div>
              <span className="px-2.5 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded-md text-[10px] font-mono uppercase font-bold shrink-0">
                SIMULATED DATA
              </span>
            </div>
          )}

          {/* Incident Info Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="card p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Incident</p>
              <p className="text-sm font-bold text-white mt-1">
                {mastraExecution.incident?.metric_type?.replace(/_/g, ' ') || 'None'}
              </p>
              <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                #{mastraExecution.incident?.id}
              </p>
            </div>
            <div className="card p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Severity</p>
              <p
                className={`text-sm font-bold mt-1 ${
                  mastraExecution.incident?.severity === 'CRITICAL'
                    ? 'text-rose-400'
                    : mastraExecution.incident?.severity === 'HIGH'
                    ? 'text-orange-400'
                    : mastraExecution.incident?.severity === 'MEDIUM'
                    ? 'text-yellow-400'
                    : 'text-[#00ff88]'
                }`}
              >
                {mastraExecution.incident?.severity || 'N/A'}
              </p>
            </div>
            <div className="card p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Status</p>
              <p
                className={`text-sm font-bold mt-1 ${
                  mastraExecution.incident?.status === 'EXECUTING'
                    ? 'text-[#00d4ff]'
                    : mastraExecution.incident?.status === 'PENDING_APPROVAL'
                    ? 'text-yellow-400'
                    : mastraExecution.incident?.status === 'EXECUTED'
                    ? 'text-[#00ff88]'
                    : 'text-slate-300'
                }`}
              >
                {mastraExecution.incident?.status || 'N/A'}
              </p>
            </div>
            <div className="card p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Workflow</p>
              <p className="text-sm font-bold text-[#00d4ff] mt-1">
                {mastraExecution.workflow?.name || 'IncidentResponseWorkflow'}
              </p>
              <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                Total Duration: {totalWorkflowSeconds.toFixed(1)}s
              </p>
            </div>
            <div className="card p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Active Agent</p>
              <p className="text-sm font-bold text-[#00ff88] mt-1">
                {mastraExecution.agent?.name || 'Pending'}
              </p>
              <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                {mastraExecution.agent?.sub_type || ''} / {mastraExecution.agent?.domain || ''}
              </p>
            </div>
          </div>

          {/* AI + Safety Info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="card p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">AI Provider</p>
              <p className="text-sm font-bold text-[#00d4ff] mt-1 capitalize">
                {mastraExecution.ai_provider || 'simulation'}
              </p>
            </div>
            <div className="card p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Confidence</p>
              <div className="flex items-center gap-2 mt-1.5">
                <div className="flex-1 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-[#00ff88] h-1.5 rounded-full transition-all duration-500"
                    style={{ width: `${(mastraExecution.confidence || 0) * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-slate-300">
                  {Math.round((mastraExecution.confidence || 0) * 100)}%
                </span>
              </div>
            </div>
            <div className="card p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Safety Status</p>
              <p
                className={`text-sm font-bold mt-1 ${
                  mastraExecution.safety?.status === 'BLOCKED'
                    ? 'text-rose-400'
                    : mastraExecution.safety?.status === 'ALLOWED'
                    ? 'text-[#00ff88]'
                    : 'text-slate-400'
                }`}
              >
                {mastraExecution.safety?.status || 'Pending'}
              </p>
            </div>
            <div className="card p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Risk Score</p>
              <div className="flex items-center gap-2 mt-1.5">
                <div className="flex-1 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-500 ${
                      (mastraExecution.safety?.risk_score || 0) > 0.7
                        ? 'bg-rose-400'
                        : (mastraExecution.safety?.risk_score || 0) > 0.4
                        ? 'bg-yellow-400'
                        : 'bg-[#00ff88]'
                    }`}
                    style={{ width: `${(mastraExecution.safety?.risk_score || 0) * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-slate-300">
                  {Math.round((mastraExecution.safety?.risk_score || 0) * 100)}%
                </span>
              </div>
            </div>
          </div>

          {/* AI Orchestration Components Grid: Qdrant & Enkrypt AI */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <QdrantRetrievalPanel />
            <EnkryptValidationPanel />
          </div>

          {/* Remediation Options & Agent Purpose Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Agent Purpose Card */}
            <div className="card p-5 space-y-3">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                <Cpu className="w-4 h-4 text-[#00ff88]" /> Active Agent Purpose
              </h4>
              {mastraExecution.agent?.name ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs border-b border-white/5 pb-2">
                    <span className="text-slate-300 font-bold">{mastraExecution.agent.name}</span>
                    <span className="text-[#00ff88] font-mono text-[10px]">
                      {mastraExecution.agent.sub_type} domain
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-mono">
                    {mastraExecution.agent.name === 'RootCauseAnalysisAgent'
                      ? 'Synthesize metrics, logs, deployments, past incidents, and dependencies to diagnose root cause.'
                      : mastraExecution.agent.name === 'ThreatIntelAgent'
                      ? 'Parse active incident logs, extract IOCs, query VirusTotal/AbuseIPDB.'
                      : mastraExecution.agent.name === 'RemediationAgent'
                      ? 'Intelligent agent ranking recovery plans based on success, risk, and user impact.'
                      : 'Collaborates to resolve the failure scenario via multi-agent reasoning loops.'}
                  </p>
                </div>
              ) : (
                <p className="text-xs text-slate-500 font-mono">Waiting for active agent assignment...</p>
              )}
            </div>

            {/* Remediation Options */}
            <div className="card p-5 space-y-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                <ListChecks className="w-4 h-4 text-[#00ff88]" /> Remediation Decision & Options
              </h4>
              <div className="space-y-3">
                <div>
                  <span className="text-[10px] text-slate-500 font-mono uppercase block mb-1">
                    Recommended Command
                  </span>
                  <div className="p-2.5 bg-black/40 border border-white/5 rounded-lg text-xs font-mono text-[#00ff88] break-all">
                    {mastraExecution.incident?.suggested_action || 'Formulating plan...'}
                  </div>
                </div>
                {mastraOptions && mastraOptions.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-[10px] text-slate-500 font-mono uppercase block">
                      Ranked Alternatives Evaluated:
                    </span>
                    <div className="space-y-2 font-mono">
                      {mastraOptions.map((opt: any, idx: number) => (
                        <div
                          key={idx}
                          className="p-2.5 bg-white/5 border border-white/5 rounded-lg text-[10px] space-y-1"
                        >
                          <div className="flex justify-between items-center">
                            <span className="text-slate-200 font-bold">{opt.name}</span>
                            <span
                              className={`font-mono font-bold ${
                                idx === 0 ? 'text-[#00ff88]' : 'text-slate-500'
                              }`}
                            >
                              Score:{' '}
                              {opt.composite_score ||
                                opt.success_probability - opt.risk_score - opt.user_impact}
                            </span>
                          </div>
                          <p className="text-slate-400">{opt.reasoning || opt.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Part 1 — Mastra Workflow Visualization Pipeline */}
          <div className="card p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-widest flex items-center gap-2">
                <Activity className="w-4 h-4 text-[#00d4ff]" /> Mastra Workflow Step Pipeline & Live Input/Output Traces
              </h4>
              <span className="text-[10px] font-mono text-slate-500">
                Click any step to inspect real-time agent input, output, and provider metadata
              </span>
            </div>

            <div className="space-y-3">
              {(mastraExecution.pipeline || []).map((step: any, idx: number) => {
                const isExpanded = expandedStep === step.step_key;
                const isCompleted = step.status === 'completed';
                const isRunning = step.status === 'running' || step.status === 'in_progress';
                const isFailed = step.status === 'failed';

                const statusColor = isCompleted
                  ? 'bg-[#00ff88]/5 border-[#00ff88]/20'
                  : isRunning
                  ? 'bg-[#00d4ff]/10 border-[#00d4ff]/40 shadow-[0_0_15px_rgba(0,212,255,0.15)]'
                  : isFailed
                  ? 'bg-rose-500/10 border-rose-500/30'
                  : 'bg-white/[0.02] border-white/5';

                const badgeBg = isCompleted
                  ? 'bg-[#00ff88]/20 text-[#00ff88]'
                  : isRunning
                  ? 'bg-[#00d4ff]/20 text-[#00d4ff] animate-pulse'
                  : isFailed
                  ? 'bg-rose-500/20 text-rose-400'
                  : 'bg-slate-800 text-slate-500';

                return (
                  <div
                    key={step.step_key}
                    className={`rounded-xl border transition-all ${statusColor}`}
                  >
                    {/* Main Step Bar */}
                    <div
                      onClick={() => setExpandedStep(isExpanded ? null : step.step_key)}
                      className="p-3 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-all rounded-xl"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${badgeBg}`}>
                          {isCompleted ? '✓' : isRunning ? '⚡' : isFailed ? '✕' : step.step_number}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-200">{step.label}</span>
                            <span className="text-[9px] font-mono text-slate-500 uppercase">
                              [{step.step_key}]
                            </span>
                            {step.is_simulated && (
                              <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[9px] font-mono rounded">
                                SIMULATED
                              </span>
                            )}
                          </div>
                          {step.error_message && (
                            <p className="text-[10px] text-rose-400 font-mono mt-0.5 truncate">
                              {step.error_message}
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        {step.confidence !== undefined && step.confidence > 0 && (
                          <span className="text-[10px] font-mono text-[#00ff88] bg-[#00ff88]/10 px-2 py-0.5 rounded">
                            {Math.round(step.confidence * 100)}% conf
                          </span>
                        )}

                        <span
                          className={`text-[10px] font-mono font-bold ${
                            isCompleted
                              ? 'text-[#00ff88]'
                              : isRunning
                              ? 'text-[#00d4ff]'
                              : isFailed
                              ? 'text-rose-400'
                              : 'text-slate-600'
                          }`}
                        >
                          {isRunning
                            ? 'RUNNING...'
                            : isCompleted
                            ? `${(step.duration_seconds || 0).toFixed(1)}s`
                            : isFailed
                            ? 'FAILED'
                            : 'QUEUED'}
                        </span>

                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        )}
                      </div>
                    </div>

                    {/* Expandable Step Input / Output Detail Drawer */}
                    {isExpanded && (
                      <div className="p-4 border-t border-white/5 bg-black/50 space-y-3 text-xs font-mono rounded-b-xl">
                        {/* Token Usage Section */}
                        <div className="p-2.5 bg-black/60 border border-white/5 rounded-lg flex items-center justify-between text-[10px]">
                          <span className="text-slate-400 uppercase font-bold">LLM Token Usage:</span>
                          {step.token_usage ? (
                            <span className="text-[#00ff88] font-bold">
                              Prompt: {step.token_usage.prompt_tokens} | Completion: {step.token_usage.completion_tokens} | Total: {step.token_usage.total_tokens}
                            </span>
                          ) : (
                            <span className="text-slate-500 italic">
                              Not available for this provider (simulation mode / usage metadata omitted)
                            </span>
                          )}
                        </div>

                        {/* Input Excerpt */}
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 uppercase font-bold flex items-center gap-1">
                            <ArrowRight className="w-3 h-3 text-[#00d4ff]" /> Agent Input Payload:
                          </span>
                          <pre className="p-3 bg-black/80 rounded-lg text-[10px] text-slate-300 whitespace-pre-wrap max-h-36 overflow-y-auto leading-relaxed border border-white/5">
                            {step.input_excerpt || `{\n  "incident_id": ${mastraExecution.incident?.id},\n  "step": "${step.step_key}",\n  "scenario": "${mastraExecution.incident?.metric_type}"\n}`}
                          </pre>
                        </div>

                        {/* Output Excerpt */}
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 uppercase font-bold flex items-center gap-1">
                            <ArrowRight className="w-3 h-3 text-[#00ff88]" /> Agent Response Output:
                          </span>
                          <pre className="p-3 bg-black/80 rounded-lg text-[10px] text-slate-300 whitespace-pre-wrap max-h-36 overflow-y-auto leading-relaxed border border-white/5">
                            {step.output_excerpt || `{\n  "status": "${step.status}",\n  "duration_seconds": ${step.duration_seconds || 0},\n  "action": "${mastraExecution.incident?.suggested_action || 'Analyzed'}"\n}`}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Live Event Stream */}
          <div className="card p-5">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
              <Terminal className="w-4 h-4 text-[#00d4ff]" /> Live Event Stream
            </h4>
            <div className="bg-black/50 border border-white/5 rounded-xl p-4 font-mono text-[10px] max-h-64 overflow-y-auto space-y-1">
              {mastraEvents
                .filter((e) => !mastraSelectedId || e.incident_id === mastraSelectedId)
                .map((evt: any, i: number) => (
                  <p
                    key={i}
                    className={`${
                      evt.step_status === 'completed'
                        ? 'text-[#00ff88]'
                        : evt.step_status === 'in_progress' || evt.step_status === 'running'
                        ? 'text-[#00d4ff]'
                        : evt.step_status === 'failed'
                        ? 'text-rose-400'
                        : 'text-slate-400'
                    }`}
                  >
                    <span className="text-slate-600">{new Date(evt.timestamp).toLocaleTimeString()}</span>{' '}
                    <span className="text-slate-300 font-bold">{evt.step_name}</span>{' '}
                    <span className="text-slate-500">[{evt.step_status}]</span>
                    {evt.duration_seconds > 0 && (
                      <span className="text-slate-500"> {evt.duration_seconds.toFixed(1)}s</span>
                    )}
                    {evt.message && <span className="text-slate-400"> — {evt.message}</span>}
                  </p>
                ))}
              {mastraEvents.filter((e) => !mastraSelectedId || e.incident_id === mastraSelectedId).length === 0 && (
                <p className="text-slate-600">
                  Waiting for execution events... Trigger an incident above to start.
                </p>
              )}
            </div>
          </div>

          {/* Timeline Events */}
          {mastraExecution.timeline_events && mastraExecution.timeline_events.length > 0 && (
            <div className="card p-5">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-[#00d4ff]" /> Timeline
              </h4>
              <div className="space-y-2">
                {mastraExecution.timeline_events.map((te: any, i: number) => (
                  <div key={i} className="flex items-start gap-3 text-xs">
                    <div className="w-2 h-2 rounded-full bg-[#00ff88] mt-1.5 flex-shrink-0" />
                    <div>
                      <span className="text-slate-300 font-bold">{te.title}</span>
                      {te.actor && <span className="text-slate-500 ml-2">by {te.actor}</span>}
                      {te.timestamp && (
                        <span className="text-slate-600 ml-2 font-mono">
                          {new Date(te.timestamp).toLocaleTimeString()}
                        </span>
                      )}
                      {te.description && <p className="text-slate-500 mt-0.5">{te.description}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="card p-16 flex flex-col items-center justify-center text-center">
          <Zap className="w-16 h-16 text-slate-700 mb-4" />
          <h4 className="text-sm font-bold text-slate-400">No Active Execution</h4>
          <p className="text-xs text-slate-600 mt-2">
            Click "Refresh Execution" to check for active incidents, or trigger a demo scenario above
          </p>
        </div>
      )}
    </div>
  );
};
