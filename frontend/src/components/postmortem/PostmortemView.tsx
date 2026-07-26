'use client';

import React from 'react';
import { FileText } from 'lucide-react';
import { usePostmortemStore } from '../../store/postmortemStore';
import { api } from '../../lib/api';


interface PostmortemViewProps {
  onGeneratePostmortem: () => void;
}

export const PostmortemView: React.FC<PostmortemViewProps> = ({
  onGeneratePostmortem,
}) => {
  const {
    postmortemData,
    postmortemLoading,
    postmortemGenerating,
  } = usePostmortemStore();

  return (
    <div className="space-y-6 animate-fade-in font-mono text-xs">
      <div className="flex justify-between items-center bg-white/5 p-4 rounded-xl border border-white/5">
        <div>
          <h4 className="text-sm font-bold text-slate-200">Incident Postmortem Report</h4>
          <p className="text-[10px] text-slate-500 mt-1">
            Comprehensive analysis: Detection → Analysis → Safety Check → AI Decision → Execution → Resolution → Postmortem
          </p>
        </div>
        <div className="flex gap-2">
          {postmortemData?.incident_details?.id && (
            <button
              onClick={async () => {
                try {
                  const blob = await api.exportPostmortemPdf(postmortemData.incident_details.id);
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `postmortem_incident_${postmortemData.incident_details.id}.pdf`;
                  document.body.appendChild(a);
                  a.click();
                  a.remove();
                } catch (err) {
                  console.error(err);
                }
              }}
              className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 text-slate-900 font-bold rounded-lg text-[10px] uppercase tracking-wider hover:from-emerald-500 hover:to-teal-500 transition-all flex items-center gap-1.5"
            >
              <FileText className="w-3.5 h-3.5" /> Export PDF
            </button>
          )}
          <button
            onClick={onGeneratePostmortem}
            disabled={postmortemGenerating}
            className="px-4 py-2 bg-[#00ff88]/10 text-[#00ff88] border border-[#00ff88]/20 font-bold rounded-lg text-[10px] uppercase tracking-wider hover:bg-[#00ff88]/20 transition-all disabled:opacity-50"
          >
            {postmortemGenerating ? 'Generating...' : postmortemData ? 'Regenerate Report' : 'Generate Report'}
          </button>
        </div>
      </div>


      {postmortemLoading ? (
        <div className="text-center py-12 text-slate-500">
          <div className="animate-spin w-6 h-6 border-2 border-[#00ff88] border-t-transparent rounded-full mx-auto mb-3" />
          Loading postmortem...
        </div>
      ) : postmortemData ? (
        <>
          {/* Executive Summary */}
          <div className="p-4 bg-black/30 rounded-xl border border-white/5">
            <h5 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">
              Executive Summary
            </h5>
            <pre className="text-[11px] text-slate-300 whitespace-pre-wrap leading-relaxed">
              {postmortemData.executive_summary}
            </pre>
          </div>

          {/* Incident Details */}
          {postmortemData.incident_details && (
            <div className="p-4 bg-black/30 rounded-xl border border-white/5">
              <h5 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">
                Incident Details
              </h5>
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 text-[10px]">
                <div>
                  <span className="text-slate-500">ID:</span>{' '}
                  <span className="text-slate-200 font-bold">#{postmortemData.incident_details.id}</span>
                </div>
                <div>
                  <span className="text-slate-500">Title:</span>{' '}
                  <span className="text-slate-200 font-bold">{postmortemData.incident_details.title}</span>
                </div>
                <div>
                  <span className="text-slate-500">Correlation ID:</span>{' '}
                  <span className="text-slate-400 font-bold">{postmortemData.incident_details.correlation_id}</span>
                </div>
                <div>
                  <span className="text-slate-500">Metric Type:</span>{' '}
                  <span className="text-[#00d4ff] font-bold">{postmortemData.incident_details.metric_type}</span>
                </div>
                <div>
                  <span className="text-slate-500">Detection Method:</span>{' '}
                  <span className="text-slate-300 font-bold">
                    {postmortemData.incident_details.source || 'K8s Telemetry Monitor'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Status:</span>{' '}
                  <span
                    className={`font-bold ${
                      postmortemData.incident_details.status === 'EXECUTED' ? 'text-emerald-400' : 'text-amber-400'
                    }`}
                  >
                    {postmortemData.incident_details.status}
                  </span>
                </div>
              </div>
              {postmortemData.incident_details.description && (
                <p className="mt-2 text-[10px] text-slate-400 leading-relaxed">
                  {postmortemData.incident_details.description}
                </p>
              )}
            </div>
          )}

          {/* Impact Assessment */}
          {postmortemData.impact && (
            <div className="p-4 bg-black/30 rounded-xl border border-white/5">
              <h5 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">
                Impact Assessment
              </h5>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-[10px]">
                <div>
                  <span className="text-slate-500">Severity:</span>{' '}
                  <span
                    className={`font-bold ${
                      postmortemData.impact.severity_description === 'Critical'
                        ? 'text-rose-400'
                        : postmortemData.impact.severity_description === 'High'
                        ? 'text-amber-400'
                        : 'text-emerald-400'
                    }`}
                  >
                    {postmortemData.impact.severity_description || postmortemData.severity}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Affected Users:</span>{' '}
                  <span className="text-slate-200 font-bold">
                    {postmortemData.impact.estimated_affected_users || 0}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Blast Radius:</span>{' '}
                  <span className="text-slate-300 font-bold">{postmortemData.impact.blast_radius || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-500">Est. Cost:</span>{' '}
                  <span className="text-amber-400 font-bold">
                    ${postmortemData.impact.downtime_cost_estimate_usd?.toFixed(2) || '0.00'}
                  </span>
                </div>
              </div>
              {postmortemData.impact.cascading_risk && (
                <p className="mt-2 text-[10px] text-slate-400">
                  Cascading Risk: {postmortemData.impact.cascading_risk}
                </p>
              )}
            </div>
          )}

          {/* Actions Performed */}
          {postmortemData.actions_taken?.length > 0 && (
            <div className="p-4 bg-black/30 rounded-xl border border-white/5">
              <h5 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">
                Actions Performed
              </h5>
              <div className="space-y-2">
                {postmortemData.actions_taken.map((action: any, i: number) => (
                  <div key={i} className="p-2 bg-white/5 rounded border border-white/5 text-[10px]">
                    <div className="flex justify-between items-center mb-1">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                          action.stage?.includes('EXECUT')
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : action.stage?.includes('VALIDATE') || action.stage?.includes('SAFETY')
                            ? 'bg-[#00d4ff]/10 text-[#00d4ff]'
                            : 'bg-white/5 text-slate-400'
                        }`}
                      >
                        {action.stage}
                      </span>
                      <span className="text-slate-500">
                        {action.timestamp ? new Date(action.timestamp).toLocaleTimeString() : ''}
                      </span>
                    </div>
                    <p className="text-slate-300">{action.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detailed Timeline */}
          {postmortemData.timeline?.length > 0 && (
            <div className="p-4 bg-black/30 rounded-xl border border-white/5">
              <h5 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">
                Detailed Timeline
              </h5>
              <div className="space-y-2">
                {postmortemData.timeline.map((evt: any, i: number) => (
                  <div key={i} className="flex gap-3 text-[10px]">
                    <span className="text-slate-500 w-20 shrink-0">
                      {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : ''}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] font-bold shrink-0 ${
                        evt.event_type === 'action'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : evt.event_type === 'decision'
                          ? 'bg-[#00d4ff]/10 text-[#00d4ff]'
                          : evt.event_type === 'detection'
                          ? 'bg-amber-500/10 text-amber-400'
                          : 'bg-white/5 text-slate-400'
                      }`}
                    >
                      {evt.event_type || 'event'}
                    </span>
                    <div>
                      <span className="text-slate-300 font-bold">{evt.title}</span>
                      {evt.description && <p className="text-slate-500 mt-0.5">{evt.description}</p>}
                      {evt.actor && <span className="text-slate-600 ml-2">by {evt.actor}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Lifecycle Flow */}
          {postmortemData.lifecycle_flow && (
            <div className="p-4 bg-black/30 rounded-xl border border-white/5">
              <h5 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">
                Lifecycle Flow
              </h5>
              <div className="flex flex-wrap gap-2">
                {postmortemData.lifecycle_flow.map((stage: any, idx: number) => (
                  <div
                    key={idx}
                    className={`px-3 py-2 rounded-lg border text-[10px] ${
                      stage.status === 'completed'
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                        : stage.status === 'in_progress'
                        ? 'bg-amber-500/10 border-amber-500/20 text-amber-400 animate-pulse'
                        : 'bg-white/5 border-white/10 text-slate-500'
                    }`}
                  >
                    <span className="font-bold block">{stage.name}</span>
                    {stage.timestamp && (
                      <span className="text-[9px] opacity-70">
                        {new Date(stage.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timing & Severity */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              {
                label: 'Detection',
                value: postmortemData.timing?.detection_time
                  ? new Date(postmortemData.timing.detection_time).toLocaleString()
                  : 'N/A',
              },
              {
                label: 'Resolution',
                value: postmortemData.timing?.resolution_time
                  ? new Date(postmortemData.timing.resolution_time).toLocaleString()
                  : 'Pending',
              },
              {
                label: 'Duration',
                value: postmortemData.timing?.duration_formatted || 'N/A',
              },
              {
                label: 'Severity',
                value: postmortemData.severity || 'N/A',
                color:
                  postmortemData.severity === 'CRITICAL'
                    ? 'text-rose-400'
                    : postmortemData.severity === 'WARNING'
                    ? 'text-amber-400'
                    : 'text-emerald-400',
              },
            ].map((item, idx) => (
              <div key={idx} className="p-3 bg-white/5 rounded-lg border border-white/5">
                <span className="text-[9px] text-slate-500 uppercase tracking-widest block mb-1">
                  {item.label}
                </span>
                <span className={`text-xs font-bold ${item.color || 'text-slate-200'}`}>{item.value}</span>
              </div>
            ))}
          </div>

          {/* Root Cause */}
          {postmortemData.root_cause && (
            <div className="p-4 bg-black/30 rounded-xl border border-white/5">
              <h5 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">
                Root Cause Analysis
              </h5>
              <p className="text-[11px] text-slate-300 leading-relaxed mb-2">
                {postmortemData.root_cause.primary_cause}
              </p>
              {postmortemData.root_cause.evidence?.length > 0 && (
                <div className="mt-2">
                  <span className="text-[9px] text-slate-500 uppercase font-bold">Evidence:</span>
                  <ul className="mt-1 space-y-1">
                    {postmortemData.root_cause.evidence.map((e: string, i: number) => (
                      <li key={i} className="text-[10px] text-slate-400">
                        • {e}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12 text-slate-500">
          <FileText className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-xs">No postmortem report available for this incident.</p>
          <p className="text-[10px] mt-1 text-slate-600">Click "Generate Report" to create one.</p>
        </div>
      )}
    </div>
  );
};
