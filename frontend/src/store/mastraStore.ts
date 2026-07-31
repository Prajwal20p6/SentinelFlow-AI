import { create } from 'zustand';

interface MastraState {
  mastraEvents: any[];
  mastraExecution: any | null;
  mastraSelectedId: number | null;
  mastraLoading: boolean;
  ragEvents: any[];
  enkryptEvents: any[];
  activeStorageTier: string;
  enkryptAvailable: boolean;

  setMastraEvents: (events: any[] | ((prev: any[]) => any[])) => void;
  setMastraExecution: (execution: any | ((prev: any) => any)) => void;
  setMastraSelectedId: (id: number | null) => void;
  setMastraLoading: (loading: boolean) => void;
  setRagEvents: (events: any[] | ((prev: any[]) => any[])) => void;
  setEnkryptEvents: (events: any[] | ((prev: any[]) => any[])) => void;
  setActiveStorageTier: (tier: string) => void;
  setEnkryptAvailable: (available: boolean) => void;
}

export const useMastraStore = create<MastraState>((set) => ({
  mastraEvents: [],
  mastraExecution: null,
  mastraSelectedId: null,
  mastraLoading: false,
  ragEvents: [],
  enkryptEvents: [],
  activeStorageTier: 'InMemory fallback',
  enkryptAvailable: false,

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
  setRagEvents: (updater) =>
    set((state) => ({
      ragEvents: typeof updater === 'function' ? updater(state.ragEvents) : updater,
    })),
  setEnkryptEvents: (updater) =>
    set((state) => ({
      enkryptEvents: typeof updater === 'function' ? updater(state.enkryptEvents) : updater,
    })),
  setActiveStorageTier: (activeStorageTier) => set({ activeStorageTier }),
  setEnkryptAvailable: (enkryptAvailable) => set({ enkryptAvailable }),
}));
