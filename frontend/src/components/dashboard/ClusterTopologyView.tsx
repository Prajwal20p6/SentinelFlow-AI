'use client';

import React, { useRef, useEffect } from 'react';
import { Server, Terminal, Play, Loader2 } from 'lucide-react';
import { ClusterTopology, PodInfo } from '../../types';

interface ClusterTopologyViewProps {
  topology: ClusterTopology | null;
  selectedPod: PodInfo | null;
  selectPodForInspection: (pod: PodInfo) => void;
  commandInput: string;
  setCommandInput: (input: string) => void;
  commandLoading: boolean;
  submitGuardedCommand: () => void;
  commandResult: any;
  podLogStream: string[];
}

export const ClusterTopologyView: React.FC<ClusterTopologyViewProps> = ({
  topology,
  selectedPod,
  selectPodForInspection,
  commandInput,
  setCommandInput,
  commandLoading,
  submitGuardedCommand,
  commandResult,
  podLogStream,
}) => {
  const logTerminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logTerminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [podLogStream]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
      {/* Node / Pod Visualizer Map */}
      <div className="lg:col-span-2 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold text-slate-200">Pod Cluster Monitor</h2>
            <p className="text-xs text-slate-500 mt-1">Select visual node blocks to inspect container live metrics, logs, and scale states</p>
          </div>
        </div>

        <div className="p-6 bg-[#111827] border border-white/5 rounded-2xl space-y-6 relative">
          {/* Grid of Nodes and Pods */}
          {topology ? (
            <div className="space-y-8">
              {topology.nodes.map(node => (
                <div key={node.name} className="p-4 bg-[#1a1f2e] border border-white/5 rounded-xl space-y-3">
                  <div className="flex justify-between items-center text-xs border-b border-white/5 pb-2">
                    <div className="flex items-center gap-2">
                      <Server className="w-4 h-4 text-[#00ff88]" />
                      <span className="font-bold text-slate-300">{node.name}</span>
                      <span className="text-[10px] text-slate-500">({node.role})</span>
                    </div>
                    <div className="flex gap-4 text-[10px] text-slate-400 font-mono">
                      <span>CPU: {node.cpu_usage}%</span>
                      <span>MEM: {node.memory_usage}%</span>
                    </div>
                  </div>

                  {/* Pod elements mapped to current node */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                    {topology.pods
                      .filter(p => p.node === node.name)
                      .map(pod => (
                        <div
                          key={pod.name}
                          onClick={() => selectPodForInspection(pod)}
                          className={`p-3 bg-[#111827] border cursor-pointer rounded-lg hover:border-emerald-500 transition-all flex flex-col justify-between ${selectedPod?.name === pod.name ? 'border-[#00ff88] bg-emerald-500/5' : 'border-white/5'}`}
                        >
                          <div className="flex justify-between items-start gap-2 mb-2">
                            <span className="text-xs font-bold truncate text-slate-300" title={pod.name}>
                              {pod.service}
                            </span>
                            <div className="relative flex h-2 w-2 shrink-0">
                              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${pod.status === 'Running' ? 'bg-[#00ff88]' : 'bg-[#ff3366]'}`}></span>
                              <span className={`relative inline-flex rounded-full h-2 w-2 ${pod.status === 'Running' ? 'bg-[#00ff88]' : 'bg-[#ff3366]'}`}></span>
                            </div>
                          </div>

                          <div className="space-y-1 text-[9px] font-mono text-slate-500">
                            <div className="flex justify-between">
                              <span>CPU</span>
                              <span className="text-slate-400">{pod.cpu_usage}%</span>
                            </div>
                            <div className="flex justify-between">
                              <span>MEM</span>
                              <span className="text-slate-400">{pod.memory_usage}%</span>
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-500 font-mono text-xs">
              Syncing cluster statusExporter maps...
            </div>
          )}
        </div>

        {/* Guarded Console Terminal Panel */}
        <div className="card p-5">
          <h4 className="text-xs font-bold text-slate-200 uppercase tracking-widest mb-3 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-[#00ff88]" /> Guarded Infrastructure Terminal
          </h4>
          
          <div className="flex gap-3 mb-4">
            <input
              type="text"
              value={commandInput}
              onChange={e => setCommandInput(e.target.value)}
              placeholder="kubectl rollout restart deployment/payment-gateway"
              className="flex-1 px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-lg focus:outline-none focus:border-emerald-500 text-xs font-mono text-slate-300"
            />
            <button
              onClick={submitGuardedCommand}
              disabled={commandLoading}
              className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-xs rounded-lg transition-all flex items-center gap-2"
            >
              {commandLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              EXECUTE
            </button>
          </div>

          {/* Terminal Execution Result */}
          {commandResult && (
            <div className="terminal p-4 space-y-3 text-xs leading-relaxed animate-fade-in">
              <div className="flex justify-between items-center border-b border-white/5 pb-2">
                <span className="font-bold text-slate-400">Enkrypt AI Safety Envelope Scan Report</span>
                <span className={`badge ${commandResult.status === 'ALLOWED' ? 'badge-success' : 'badge-critical'}`}>
                  {commandResult.status}
                </span>
              </div>
              <div className="space-y-1.5">
                <p className="text-slate-500">Command evaluated: <span className="text-slate-200 font-mono">{commandResult.command}</span></p>
                <p className="text-slate-500">Safety assessment risk score: <span className="font-mono font-bold text-[#00ff88]">{Math.round(commandResult.risk_score * 100)}%</span></p>
                <p className="text-slate-400 italic">Assessment: {commandResult.risk_assessment}</p>
              </div>
              {commandResult.execution_output && (
                <div className="pt-2 border-t border-white/5">
                  <p className="text-slate-500 mb-1">Standard output logs:</p>
                  <pre className="text-[#00ff88] font-mono whitespace-pre-wrap">{commandResult.execution_output}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Side Spec Inspector / Log Streamer */}
      <div className="lg:col-span-1 space-y-6">
        {selectedPod ? (
          <div className="card p-5 space-y-5 animate-fade-in">
            <div>
              <h3 className="text-base font-bold text-slate-200 truncate" title={selectedPod.name}>
                {selectedPod.service}
              </h3>
              <p className="text-[10px] text-slate-500 font-mono mt-1">Namespace: {selectedPod.namespace}</p>
            </div>

            {/* Stats Specs */}
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="p-3 bg-white/5 border border-white/5 rounded-xl">
                <span className="text-slate-500 block mb-1">Status</span>
                <span className="font-bold text-emerald-400 uppercase tracking-wider">{selectedPod.status}</span>
              </div>
              <div className="p-3 bg-white/5 border border-white/5 rounded-xl">
                <span className="text-slate-500 block mb-1">Node host</span>
                <span className="font-semibold text-slate-300">{selectedPod.node}</span>
              </div>
              <div className="p-3 bg-white/5 border border-white/5 rounded-xl">
                <span className="text-slate-500 block mb-1">CPU cores</span>
                <span className="font-mono font-bold text-slate-300">{selectedPod.cpu_usage}%</span>
              </div>
              <div className="p-3 bg-white/5 border border-white/5 rounded-xl">
                <span className="text-slate-500 block mb-1">Memory usage</span>
                <span className="font-mono font-bold text-slate-300">{selectedPod.memory_usage}%</span>
              </div>
            </div>

            {/* Streaming container logs console */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex justify-between items-center">
                <span>Live Container Feed</span>
                <span className="text-[9px] text-[#00ff88] animate-pulse">STREAMING</span>
              </h4>

              <div className="terminal p-4 h-64 overflow-y-auto font-mono text-[10px] text-slate-300 space-y-1.5">
                {podLogStream.map((log, i) => (
                  <div key={i} className="whitespace-pre-wrap leading-relaxed">
                    {log}
                  </div>
                ))}
                <div ref={logTerminalEndRef}></div>
              </div>
            </div>

            {/* Troubleshooting Shortcuts */}
            <div className="pt-4 border-t border-white/5 space-y-2">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1.5">Manual Remedies</h4>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    setCommandInput(`kubectl scale deployment/${selectedPod.service} --replicas=3 -n ${selectedPod.namespace}`);
                    submitGuardedCommand();
                  }}
                  className="py-2 bg-white/5 hover:bg-white/10 text-slate-300 font-semibold text-[10px] rounded border border-white/10 transition-all uppercase"
                >
                  Scale Out (x3)
                </button>
                <button
                  onClick={() => {
                    setCommandInput(`kubectl rollout restart deployment/${selectedPod.service} -n ${selectedPod.namespace}`);
                    submitGuardedCommand();
                  }}
                  className="py-2 bg-white/5 hover:bg-white/10 text-slate-300 font-semibold text-[10px] rounded border border-white/10 transition-all uppercase"
                >
                  Rolling Restart
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="card p-12 text-center flex flex-col justify-center items-center">
            <Server className="w-10 h-10 text-slate-600 mb-3 animate-pulse-glow" />
            <h4 className="text-xs font-bold text-slate-400">Select a cluster node pod to stream live output and deploy remedies</h4>
          </div>
        )}
      </div>
    </div>
  );
};
