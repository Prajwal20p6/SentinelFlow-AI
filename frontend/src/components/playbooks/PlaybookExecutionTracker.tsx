'use client';

import React from 'react';
import {
  Play,
  RefreshCw,
  Loader2,
  CheckCircle,
  XCircle,
  ChevronRight,
  Terminal,
  ListChecks,
} from 'lucide-react';
import { usePlaybookStore } from '../../store/playbookStore';
import { useIncidentStore } from '../../store/incidentStore';

interface PlaybookExecutionTrackerProps {
  onStartExecution: () => void;
  onCancelExecution: (executionId: string) => void;
  onRefresh: () => void;
}

export const PlaybookExecutionTracker: React.FC<PlaybookExecutionTrackerProps> = ({
  onStartExecution,
  onCancelExecution,
  onRefresh,
}) => {
  const {
    playbookExecutions,
    selectedExecution, setSelectedExecution,
    playbookLoading,
    playbookName, setPlaybookName,
    playbookTargetIncident, setPlaybookTargetIncident,
    playbookMsg,
  } = usePlaybookStore();

  const { incidents } = useIncidentStore();

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Playbook Execution Tracker</h2>
          <p className="text-xs text-slate-500 mt-1">
            Step-by-step playbook execution with live progress bars, status logs, and ETA
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="p-2 bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg transition-all"
        >
          <RefreshCw className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel */}
        <div className="space-y-4">
          <div className="card p-5 space-y-4">
            <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest flex items-center gap-2">
              <Play className="w-4 h-4 text-[#00ff88]" /> Start Playbook
            </h4>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block mb-1.5">
                  Playbook Name
                </label>
                <input
                  type="text"
                  value={playbookName}
                  onChange={(e) => setPlaybookName(e.target.value)}
                  className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm text-slate-300 font-mono focus:outline-none focus:border-[#00ff88]/30"
                  placeholder="Playbook name..."
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block mb-1.5">
                  Target Incident
                </label>
                <select
                  value={playbookTargetIncident ?? ''}
                  onChange={(e) =>
                    setPlaybookTargetIncident(e.target.value ? Number(e.target.value) : null)
                  }
                  className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-[#00ff88]/30"
                >
                  <option value="">Select incident...</option>
                  {incidents.slice(0, 10).map((inc: any) => (
                    <option key={inc.id} value={inc.id}>
                      #{inc.id} — {inc.metric_type} ({inc.severity})
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={onStartExecution}
                disabled={playbookLoading || !playbookTargetIncident}
                className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-slate-900 font-bold text-xs rounded-xl uppercase tracking-wider transition-all flex items-center justify-center gap-2"
              >
                {playbookLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Start Execution
              </button>
              {playbookMsg && (
                <p
                  className={`text-[10px] font-mono p-2 rounded-lg ${
                    playbookMsg.startsWith('Error')
                      ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      : 'bg-emerald-500/10 text-[#00ff88] border border-emerald-500/20'
                  }`}
                >
                  {playbookMsg}
                </p>
              )}
            </div>
          </div>

          <div className="card p-5">
            <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-4">
              Execution History
            </h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {playbookExecutions.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-6">
                  No executions yet. Start a playbook above.
                </p>
              ) : (
                playbookExecutions
                  .filter((exec: any) => exec && typeof exec === 'object' && 'execution_id' in exec)
                  .map((exec: any) => (
                    <button
                      key={exec.execution_id}
                      onClick={() => setSelectedExecution(exec)}
                      className={`w-full text-left p-3 rounded-xl border transition-all ${
                        selectedExecution?.execution_id === exec.execution_id
                          ? 'border-[#00ff88]/30 bg-emerald-500/5'
                          : 'border-white/5 bg-white/2 hover:bg-white/5'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-mono text-slate-500">
                          {exec.execution_id.slice(0, 12)}...
                        </span>
                        <span
                          className={`badge ${
                            exec.status === 'COMPLETE'
                              ? 'badge-success'
                              : exec.status === 'RUNNING'
                              ? 'badge-info'
                              : exec.status === 'FAILED'
                              ? 'badge-critical'
                              : 'badge-warning'
                          }`}
                        >
                          {exec.status}
                        </span>
                      </div>
                      <p className="text-xs font-semibold text-slate-300 truncate">{exec.playbook_name}</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">Incident #{exec.incident_id}</p>
                      <div className="w-full bg-white/5 h-1 rounded-full mt-2 overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            exec.status === 'COMPLETE'
                              ? 'bg-[#00ff88]'
                              : exec.status === 'FAILED'
                              ? 'bg-rose-500'
                              : 'bg-[#00d4ff]'
                          }`}
                          style={{ width: `${exec.progress_pct}%` }}
                        ></div>
                      </div>
                      <span className="text-[9px] text-slate-600 font-mono">
                        {exec.progress_pct}% complete
                      </span>
                    </button>
                  ))
              )}
            </div>
          </div>
        </div>

        {/* Right Panel */}
        <div className="lg:col-span-2">
          {selectedExecution ? (
            <div className="space-y-4">
              <div className="card p-5">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-100">{selectedExecution.playbook_name}</h3>
                    <p className="text-xs text-slate-500 font-mono mt-1">{selectedExecution.execution_id}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`badge ${
                        selectedExecution.status === 'COMPLETE'
                          ? 'badge-success'
                          : selectedExecution.status === 'RUNNING'
                          ? 'badge-info'
                          : selectedExecution.status === 'FAILED'
                          ? 'badge-critical'
                          : 'badge-warning'
                      }`}
                    >
                      {selectedExecution.status}
                    </span>
                    {selectedExecution.status === 'RUNNING' && (
                      <button
                        onClick={() => onCancelExecution(selectedExecution.execution_id)}
                        className="px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 rounded-lg text-xs font-bold transition-all"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>

                <div className="mb-3">
                  <div className="flex justify-between text-[10px] text-slate-500 mb-1.5">
                    <span>Overall Progress</span>
                    <span className="font-mono">{selectedExecution.progress_pct}%</span>
                  </div>
                  <div className="w-full bg-white/5 h-3 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${
                        selectedExecution.status === 'COMPLETE'
                          ? 'bg-gradient-to-r from-emerald-500 to-[#00ff88]'
                          : selectedExecution.status === 'FAILED'
                          ? 'bg-gradient-to-r from-rose-600 to-rose-400'
                          : 'bg-gradient-to-r from-[#00d4ff] to-[#0080ff] animate-pulse'
                      }`}
                      style={{ width: `${selectedExecution.progress_pct}%` }}
                    ></div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 text-center font-mono text-xs">
                  <div className="p-2 bg-white/5 rounded-lg">
                    <span className="text-slate-500 block text-[9px] uppercase">Steps</span>
                    <span className="text-slate-200 font-bold">
                      {selectedExecution.current_step}/{selectedExecution.total_steps}
                    </span>
                  </div>
                  <div className="p-2 bg-white/5 rounded-lg">
                    <span className="text-slate-500 block text-[9px] uppercase">Incident</span>
                    <span className="text-[#00d4ff] font-bold">#{selectedExecution.incident_id}</span>
                  </div>
                  <div className="p-2 bg-white/5 rounded-lg">
                    <span className="text-slate-500 block text-[9px] uppercase">ETA</span>
                    <span className="text-amber-400 font-bold text-[10px]">
                      {selectedExecution.estimated_completion
                        ? new Date(selectedExecution.estimated_completion).toLocaleTimeString()
                        : '--'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Step Progress */}
              <div className="card p-5">
                <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-4">
                  Step Progress
                </h4>
                <div className="space-y-2">
                  {(selectedExecution.steps || [])
                    .filter((step: any) => step && typeof step === 'object' && 'name' in step)
                    .map((step: any, i: number) => (
                      <div
                        key={i}
                        className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                          step.status === 'COMPLETE'
                            ? 'bg-emerald-500/5 border-emerald-500/20'
                            : step.status === 'RUNNING'
                            ? 'bg-[#00d4ff]/5 border-[#00d4ff]/20'
                            : step.status === 'FAILED'
                            ? 'bg-rose-500/5 border-rose-500/20'
                            : step.status === 'SKIPPED'
                            ? 'bg-white/2 border-white/5 opacity-40'
                            : 'bg-white/2 border-white/5'
                        }`}
                      >
                        <div className="flex-shrink-0">
                          {step.status === 'COMPLETE' ? (
                            <CheckCircle className="w-5 h-5 text-[#00ff88]" />
                          ) : step.status === 'RUNNING' ? (
                            <Loader2 className="w-5 h-5 text-[#00d4ff] animate-spin" />
                          ) : step.status === 'FAILED' ? (
                            <XCircle className="w-5 h-5 text-rose-400" />
                          ) : step.status === 'SKIPPED' ? (
                            <ChevronRight className="w-5 h-5 text-slate-600" />
                          ) : (
                            <div className="w-5 h-5 rounded-full border-2 border-slate-600 flex items-center justify-center">
                              <span className="text-[8px] text-slate-600 font-bold">{i + 1}</span>
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p
                            className={`text-xs font-semibold ${
                              step.status === 'COMPLETE'
                                ? 'text-slate-200'
                                : step.status === 'RUNNING'
                                ? 'text-[#00d4ff]'
                                : step.status === 'FAILED'
                                ? 'text-rose-400'
                                : 'text-slate-500'
                            }`}
                          >
                            {step.name}
                          </p>
                          {step.started_at && (
                            <p className="text-[9px] text-slate-600 font-mono mt-0.5">
                              {step.status === 'COMPLETE'
                                ? `Completed at ${new Date(step.completed_at).toLocaleTimeString()}`
                                : step.status === 'RUNNING'
                                ? `Started at ${new Date(step.started_at).toLocaleTimeString()}`
                                : ''}
                            </p>
                          )}
                        </div>
                        <span
                          className={`badge text-[9px] flex-shrink-0 ${
                            step.status === 'COMPLETE'
                              ? 'badge-success'
                              : step.status === 'RUNNING'
                              ? 'badge-info'
                              : step.status === 'FAILED'
                              ? 'badge-critical'
                              : step.status === 'SKIPPED'
                              ? 'badge-warning'
                              : 'bg-slate-800 text-slate-500 border border-slate-700'
                          }`}
                        >
                          {step.status}
                        </span>
                      </div>
                    ))}
                </div>
              </div>

              {/* Execution Log */}
              <div className="card p-5">
                <h4 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-[#00d4ff]" /> Execution Log
                </h4>
                <div className="bg-black/50 border border-white/5 rounded-xl p-4 font-mono text-[10px] max-h-48 overflow-y-auto space-y-1">
                  {(selectedExecution.log || []).map((line: string, i: number) => (
                    <p
                      key={i}
                      className={`${
                        line.includes('FAILED') || line.includes('Error')
                          ? 'text-rose-400'
                          : line.includes('COMPLETE') || line.includes('successfully')
                          ? 'text-[#00ff88]'
                          : 'text-slate-400'
                      }`}
                    >
                      {line}
                    </p>
                  ))}
                  {(!selectedExecution.log || selectedExecution.log.length === 0) && (
                    <p className="text-slate-600">No log entries yet.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="card p-16 flex flex-col items-center justify-center text-center">
              <ListChecks className="w-16 h-16 text-slate-700 mb-4" />
              <h4 className="text-sm font-bold text-slate-400">
                Select an execution from the list or start a new playbook
              </h4>
              <p className="text-xs text-slate-600 mt-2">
                All step progress, logs, and ETA will appear here in real-time
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
