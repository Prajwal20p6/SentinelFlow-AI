import { create } from 'zustand';
import { ObservabilitySummary } from '../types';

interface AgentActivityItem {
  agent_name: string;
  status: string;
  progress: number;
  message: string;
  details: any;
  timestamp: string;
}

interface WorkflowProgressItem {
  current_step: number;
  total_steps: number;
  step_name: string;
  step_status: string;
  estimated_completion?: string;
  timestamp: string;
}

interface LiveState {
  activeAgents: Record<number, AgentActivityItem>;
  agentActivitiesLog: Record<number, AgentActivityItem[]>;
  workflowProgress: Record<number, WorkflowProgressItem>;
  obsSummary: ObservabilitySummary | null;
  obsTraces: any[];
  notifications: any[];
  liveMetrics: any;
  metricsHistory: any[];
  metricsAnnotations: any[];
  metricsLoading: boolean;
  selectedMetricService: string | null;
  replayEvents: any[];
  isPlayingReplay: boolean;
  replayIndex: number;
  replaySpeed: 1 | 5 | 10;
  replayIntervalId: any;

  setActiveAgents: (updater: (prev: Record<number, AgentActivityItem>) => Record<number, AgentActivityItem>) => void;
  setAgentActivitiesLog: (updater: (prev: Record<number, AgentActivityItem[]>) => Record<number, AgentActivityItem[]>) => void;
  setWorkflowProgress: (updater: (prev: Record<number, WorkflowProgressItem>) => Record<number, WorkflowProgressItem>) => void;
  setObsSummary: (summary: ObservabilitySummary | null) => void;
  setObsTraces: (traces: any[]) => void;
  setNotifications: (notifications: any[]) => void;
  setLiveMetrics: (metrics: any) => void;
  setMetricsHistory: (history: any[]) => void;
  setMetricsAnnotations: (annotations: any[]) => void;
  setMetricsLoading: (loading: boolean) => void;
  setSelectedMetricService: (service: string | null) => void;
  setReplayEvents: (events: any[]) => void;
  setIsPlayingReplay: (playing: boolean) => void;
  setReplayIndex: (index: number | ((prev: number) => number)) => void;
  setReplaySpeed: (speed: 1 | 5 | 10) => void;
  setReplayIntervalId: (id: any) => void;
}

export const useLiveStore = create<LiveState>((set) => ({
  activeAgents: {},
  agentActivitiesLog: {},
  workflowProgress: {},
  obsSummary: null,
  obsTraces: [],
  notifications: [],
  liveMetrics: null,
  metricsHistory: [],
  metricsAnnotations: [],
  metricsLoading: false,
  selectedMetricService: null,
  replayEvents: [],
  isPlayingReplay: false,
  replayIndex: -1,
  replaySpeed: 1,
  replayIntervalId: null,

  setActiveAgents: (updater) =>
    set((state) => ({ activeAgents: updater(state.activeAgents) })),
  setAgentActivitiesLog: (updater) =>
    set((state) => ({ agentActivitiesLog: updater(state.agentActivitiesLog) })),
  setWorkflowProgress: (updater) =>
    set((state) => ({ workflowProgress: updater(state.workflowProgress) })),
  setObsSummary: (obsSummary) => set({ obsSummary }),
  setObsTraces: (obsTraces) => set({ obsTraces }),
  setNotifications: (notifications) => set({ notifications }),
  setLiveMetrics: (liveMetrics) => set({ liveMetrics }),
  setMetricsHistory: (metricsHistory) => set({ metricsHistory }),
  setMetricsAnnotations: (metricsAnnotations) => set({ metricsAnnotations }),
  setMetricsLoading: (metricsLoading) => set({ metricsLoading }),
  setSelectedMetricService: (selectedMetricService) => set({ selectedMetricService }),
  setReplayEvents: (replayEvents) => set({ replayEvents }),
  setIsPlayingReplay: (isPlayingReplay) => set({ isPlayingReplay }),
  setReplayIndex: (updater) =>
    set((state) => ({
      replayIndex: typeof updater === 'function' ? updater(state.replayIndex) : updater,
    })),
  setReplaySpeed: (replaySpeed) => set({ replaySpeed }),
  setReplayIntervalId: (replayIntervalId) => set({ replayIntervalId }),
}));
