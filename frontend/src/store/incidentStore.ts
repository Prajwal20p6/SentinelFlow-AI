import { create } from 'zustand';
import { Incident, IncidentDetail, ClusterTopology, PodInfo, AuditEntry, PromptTemplate } from '../types';

export type GlobalStatus = 'SECURE' | 'THREAT_DETECTED' | 'DISRUPTED';

interface IncidentState {
  incidents: Incident[];
  selectedIncident: IncidentDetail | null;
  topology: ClusterTopology | null;
  selectedPod: PodInfo | null;
  auditEntries: AuditEntry[];
  prompts: PromptTemplate[];
  globalStatus: GlobalStatus;
  serverHealth: any;
  activeIncidentCount: number;
  circuitBreakers: Record<string, any>;

  setIncidents: (incidents: Incident[] | ((prev: Incident[]) => Incident[])) => void;
  setSelectedIncident: (selectedIncident: IncidentDetail | null | ((prev: IncidentDetail | null) => IncidentDetail | null)) => void;
  setTopology: (topology: ClusterTopology | null) => void;
  setSelectedPod: (selectedPod: PodInfo | null) => void;
  setAuditEntries: (auditEntries: AuditEntry[]) => void;
  setPrompts: (prompts: PromptTemplate[]) => void;
  setGlobalStatus: (globalStatus: GlobalStatus) => void;
  setServerHealth: (serverHealth: any) => void;
  setActiveIncidentCount: (activeIncidentCount: number) => void;
  setCircuitBreakers: (circuitBreakers: Record<string, any>) => void;
}

export const useIncidentStore = create<IncidentState>((set) => ({
  incidents: [],
  selectedIncident: null,
  topology: null,
  selectedPod: null,
  auditEntries: [],
  prompts: [],
  globalStatus: 'SECURE',
  serverHealth: null,
  activeIncidentCount: 0,
  circuitBreakers: {},

  setIncidents: (updater) =>
    set((state) => ({
      incidents: typeof updater === 'function' ? updater(state.incidents) : updater,
    })),
  setSelectedIncident: (updater) =>
    set((state) => ({
      selectedIncident: typeof updater === 'function' ? updater(state.selectedIncident) : updater,
    })),
  setTopology: (topology) => set({ topology }),
  setSelectedPod: (selectedPod) => set({ selectedPod }),
  setAuditEntries: (auditEntries) => set({ auditEntries }),
  setPrompts: (prompts) => set({ prompts }),
  setGlobalStatus: (globalStatus) => set({ globalStatus }),
  setServerHealth: (serverHealth) => set({ serverHealth }),
  setActiveIncidentCount: (activeIncidentCount) => set({ activeIncidentCount }),
  setCircuitBreakers: (circuitBreakers) => set({ circuitBreakers }),
}));
