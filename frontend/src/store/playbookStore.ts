import { create } from 'zustand';

interface PlaybookState {
  playbookExecutions: any[];
  selectedExecution: any | null;
  playbookName: string;
  playbookTargetIncident: number | null;
  playbookLoading: boolean;
  playbookMsg: string;

  setPlaybookExecutions: (executions: any[] | ((prev: any[]) => any[])) => void;
  setSelectedExecution: (execution: any | null) => void;
  setPlaybookName: (name: string) => void;
  setPlaybookTargetIncident: (incidentId: number | null) => void;
  setPlaybookLoading: (loading: boolean) => void;
  setPlaybookMsg: (msg: string) => void;
}

export const usePlaybookStore = create<PlaybookState>((set) => ({
  playbookExecutions: [],
  selectedExecution: null,
  playbookName: 'Standard Kubernetes Recovery Playbook',
  playbookTargetIncident: null,
  playbookLoading: false,
  playbookMsg: '',

  setPlaybookExecutions: (updater) =>
    set((state) => ({
      playbookExecutions: typeof updater === 'function' ? updater(state.playbookExecutions) : updater,
    })),
  setSelectedExecution: (selectedExecution) => set({ selectedExecution }),
  setPlaybookName: (playbookName) => set({ playbookName }),
  setPlaybookTargetIncident: (playbookTargetIncident) => set({ playbookTargetIncident }),
  setPlaybookLoading: (playbookLoading) => set({ playbookLoading }),
  setPlaybookMsg: (playbookMsg) => set({ playbookMsg }),
}));
