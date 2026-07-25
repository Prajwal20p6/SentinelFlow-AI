import { create } from 'zustand';

interface PostmortemState {
  postmortemData: any;
  postmortemLoading: boolean;
  postmortemGenerating: boolean;
  postmortemPdfDownloading: boolean;
  postmortemPdfError: string | null;
  simulationData: any;
  simulationLoading: boolean;
  remediationOptions: any[];
  decisionGraph: any;
  runbooks: any[];
  runbookFeedbackMsg: string;

  setPostmortemData: (data: any) => void;
  setPostmortemLoading: (loading: boolean) => void;
  setPostmortemGenerating: (generating: boolean) => void;
  setPostmortemPdfDownloading: (downloading: boolean) => void;
  setPostmortemPdfError: (error: string | null) => void;
  setSimulationData: (data: any) => void;
  setSimulationLoading: (loading: boolean) => void;
  setRemediationOptions: (options: any[]) => void;
  setDecisionGraph: (graph: any) => void;
  setRunbooks: (runbooks: any[]) => void;
  setRunbookFeedbackMsg: (msg: string) => void;
}

export const usePostmortemStore = create<PostmortemState>((set) => ({
  postmortemData: null,
  postmortemLoading: false,
  postmortemGenerating: false,
  postmortemPdfDownloading: false,
  postmortemPdfError: null,
  simulationData: null,
  simulationLoading: false,
  remediationOptions: [],
  decisionGraph: null,
  runbooks: [],
  runbookFeedbackMsg: '',

  setPostmortemData: (postmortemData) => set({ postmortemData }),
  setPostmortemLoading: (postmortemLoading) => set({ postmortemLoading }),
  setPostmortemGenerating: (postmortemGenerating) => set({ postmortemGenerating }),
  setPostmortemPdfDownloading: (postmortemPdfDownloading) => set({ postmortemPdfDownloading }),
  setPostmortemPdfError: (postmortemPdfError) => set({ postmortemPdfError }),
  setSimulationData: (simulationData) => set({ simulationData }),
  setSimulationLoading: (simulationLoading) => set({ simulationLoading }),
  setRemediationOptions: (remediationOptions) => set({ remediationOptions }),
  setDecisionGraph: (decisionGraph) => set({ decisionGraph }),
  setRunbooks: (runbooks) => set({ runbooks }),
  setRunbookFeedbackMsg: (runbookFeedbackMsg) => set({ runbookFeedbackMsg }),
}));
