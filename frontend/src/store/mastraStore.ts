import { create } from 'zustand';

interface MastraState {
  mastraEvents: any[];
  mastraExecution: any | null;
  mastraSelectedId: number | null;
  mastraLoading: boolean;

  setMastraEvents: (events: any[] | ((prev: any[]) => any[])) => void;
  setMastraExecution: (execution: any | ((prev: any) => any)) => void;
  setMastraSelectedId: (id: number | null) => void;
  setMastraLoading: (loading: boolean) => void;
}

export const useMastraStore = create<MastraState>((set) => ({
  mastraEvents: [],
  mastraExecution: null,
  mastraSelectedId: null,
  mastraLoading: false,

  setMastraEvents: (updater) =>
    set((state) => ({
      mastraEvents: typeof updater === 'function' ? updater(state.mastraEvents) : updater,
    })),
  setMastraExecution: (updater) =>
    set((state) => ({
      mastraExecution: typeof updater === 'function' ? updater(state.mastraExecution) : updater,
    })),
  setMastraSelectedId: (mastraSelectedId) => set({ mastraSelectedId }),
  setMastraLoading: (mastraLoading) => set({ mastraLoading }),
}));
