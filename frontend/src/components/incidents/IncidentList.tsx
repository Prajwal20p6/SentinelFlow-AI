'use client';

import React from 'react';
import { Incident } from '../../types';

interface IncidentListProps {
  incidents: Incident[];
  selectedIncident: Incident | null;
  onSelectIncident: (inc: Incident) => void;
}

export const IncidentList: React.FC<IncidentListProps> = ({
  incidents,
  selectedIncident,
  onSelectIncident,
}) => {
  return (
    <div className="lg:col-span-1 space-y-4">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-base font-bold text-slate-200">System Incidents</h3>
        <span className="text-xs bg-white/5 px-2.5 py-1 rounded text-slate-500">
          Total: {incidents.length}
        </span>
      </div>

      <div className="space-y-3 overflow-y-auto max-h-[calc(100vh-180px)] pr-2">
        {incidents
          .slice()
          .sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0))
          .map((inc) => {
            const slaInfo = (() => {
              if (!inc.sla_breach_at) return null;
              const diffMs = new Date(inc.sla_breach_at).getTime() - new Date().getTime();
              if (diffMs <= 0) return { text: 'SLA BREACHED', color: 'text-rose-500 font-bold' };
              const diffMins = Math.floor(diffMs / 60000);
              if (diffMins < 60)
                return { text: `${diffMins}m remaining`, color: 'text-amber-400 animate-pulse font-bold' };
              const diffHours = Math.floor(diffMins / 60);
              return { text: `${diffHours}h remaining`, color: 'text-slate-400 font-mono' };
            })();

            const isRoot = incidents.some((i) => i.parent_incident_id === inc.id);
            const cascadingCount = incidents.filter((i) => i.parent_incident_id === inc.id).length;
            const isCascading = !!inc.parent_incident_id;

            return (
              <div
                key={inc.id}
                onClick={() => onSelectIncident(inc)}
                className={`p-4 card cursor-pointer transition-all border ${
                  selectedIncident?.id === inc.id
                    ? 'border-[#00ff88] bg-emerald-500/5'
                    : 'border-white/5'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs font-bold text-slate-500 font-mono">#{inc.id}</span>
                    {isRoot && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-emerald-950/20 text-[#00ff88] border border-emerald-500/30">
                        ROOT ({cascadingCount} CASC)
                      </span>
                    )}
                    {isCascading && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-rose-950/20 text-rose-400 border border-rose-500/30">
                        CASCADING (#{inc.parent_incident_id})
                      </span>
                    )}
                    {inc.sla_target && (
                      <span
                        className={`px-1.5 py-0.5 rounded text-[9px] font-black tracking-widest ${
                          inc.sla_target === 'P0'
                            ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                            : inc.sla_target === 'P1'
                            ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                            : inc.sla_target === 'P2'
                            ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                            : 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
                        }`}
                      >
                        {inc.sla_target} (Score: {inc.priority_score})
                      </span>
                    )}
                  </div>
                  <span
                    className={`badge ${
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
                <h4 className="text-sm font-bold text-slate-200 line-clamp-1">{inc.title}</h4>
                <div className="flex items-center justify-between mt-1">
                  <p className="text-xs text-slate-500 font-mono">{inc.metric_type}</p>
                  {(inc.alert_count ?? 1) > 1 && (
                    <span className="px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 font-mono text-[9px] font-bold">
                      {inc.alert_count} alerts grouped
                    </span>
                  )}
                </div>

                <div className="flex justify-between items-center mt-3 pt-3 border-t border-white/5 text-[10px]">
                  <span className="text-slate-400 font-bold uppercase tracking-wider">{inc.status}</span>
                  {slaInfo ? (
                    <span className={slaInfo.color}>{slaInfo.text}</span>
                  ) : (
                    <span className="text-slate-500">
                      {new Date(inc.created_at).toLocaleTimeString()}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        {incidents.length === 0 && (
          <div className="text-center py-8 text-slate-500 font-mono text-xs">
            No incident telemetry records loaded.
          </div>
        )}
      </div>
    </div>
  );
};
