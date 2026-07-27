'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { IncidentList } from '../../../components/incidents/IncidentList';
import { IncidentDetailView } from '../../../components/incidents/IncidentDetailView';
import { useIncidentStore } from '../../../store/incidentStore';
import { usePostmortemStore } from '../../../store/postmortemStore';
import { useLiveStore } from '../../../store/liveStore';
import { useMastraStore } from '../../../store/mastraStore';
import { api } from '../../../lib/api';

export default function IncidentsPage() {
  const router = useRouter();
  const {
    incidents,
    setIncidents,
    selectedIncident,
    setSelectedIncident,
  } = useIncidentStore();

  const {
    postmortemData,
    setPostmortemData,
    setPostmortemLoading,
    setPostmortemGenerating,
  } = usePostmortemStore();

  const {
    activeAgents,
    workflowProgress,
    replayIndex,
    setReplayIndex,
    isPlayingReplay,
    setIsPlayingReplay,
  } = useLiveStore();

  const { setMastraSelectedId } = useMastraStore();

  const [inspectorTab, setInspectorTab] = useState<'timeline' | 'simulation' | 'options' | 'runbooks' | 'graph' | 'replay' | 'attack' | 'postmortem'>('timeline');

  useEffect(() => {
    api.getIncidents()
      .then((res) => setIncidents(res.incidents))
      .catch(console.error);
  }, [setIncidents]);

  const handleSelectIncident = async (incident: any) => {
    setSelectedIncident(incident);
    try {
      const detail = await api.getIncidentDetail(incident.id);
      setSelectedIncident(detail);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchPostmortem = async (id: number) => {
    setPostmortemLoading(true);
    try {
      const res = await api.getPostmortem(id);
      if (res && res.postmortem) {
        setPostmortemData(res.postmortem);
      } else {
        setPostmortemGenerating(true);
        const genRes = await api.generatePostmortem(id);
        setPostmortemData(genRes.postmortem);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setPostmortemLoading(false);
      setPostmortemGenerating(false);
    }
  };

  const explainabilityReport = (() => {
    if (!selectedIncident?.explainability_json) return null;
    try {
      return JSON.parse(selectedIncident.explainability_json);
    } catch (e) {
      return null;
    }
  })();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
      <div className="lg:col-span-1 space-y-4">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-base font-bold text-slate-200">System Incidents</h3>
          <span className="text-xs bg-white/5 px-2.5 py-1 rounded text-slate-500">
            Total: {incidents.length}
          </span>
        </div>

        <IncidentList
          incidents={incidents}
          selectedIncident={selectedIncident}
          onSelectIncident={handleSelectIncident}
        />
      </div>

      <div className="lg:col-span-2">
        {selectedIncident ? (
          <IncidentDetailView
            selectedIncident={selectedIncident}
            incidents={incidents}
            inspectorTab={inspectorTab}
            setInspectorTab={setInspectorTab}
            explainabilityReport={explainabilityReport}
            activeAgent={activeAgents[selectedIncident.id]}
            wp={workflowProgress[selectedIncident.id]}
            replayIndex={replayIndex}
            setReplayIndex={setReplayIndex}
            isPlayingReplay={isPlayingReplay}
            setIsPlayingReplay={setIsPlayingReplay}
            fetchPostmortem={fetchPostmortem}
            onViewInMastra={(id) => {
              setMastraSelectedId(id);
              router.push('/mastra');
            }}
            onSelectIncident={handleSelectIncident}
          />
        ) : (
          <div className="h-96 card flex items-center justify-center text-slate-500 font-mono text-xs">
            Select an incident from the list to view real-time remediation details.
          </div>
        )}
      </div>
    </div>
  );
}
