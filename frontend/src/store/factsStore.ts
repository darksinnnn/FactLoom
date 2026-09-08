import { create } from 'zustand';

export type NavTab = 'command' | 'reconciliation' | 'explorer' | 'evidence' | 'ask' | 'limitations' | 'upload';

export interface EvidenceTarget {
  documentId: string;
  documentFilename?: string;
  pageNumber: number;
  bbox?: number[] | null;
  quoteSpan?: string | null;
  observationId?: string;
  value?: string;
  unit?: string | null;
}

interface FactLoomState {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;

  // Selected Fact in Explorer
  selectedFactId: string | null;
  setSelectedFactId: (id: string | null) => void;

  // Active Evidence target for the Evidence Viewer
  evidenceTarget: EvidenceTarget | null;
  evidenceTargetVersion: number;
  openEvidence: (target: EvidenceTarget) => void;

  // Selected Reconciliation Demo Case
  selectedCaseId: string | null;
  setSelectedCaseId: (caseId: string | null) => void;
}

export const useFactLoomStore = create<FactLoomState>((set) => ({
  activeTab: 'command',
  setActiveTab: (tab) => set({ activeTab: tab }),

  selectedFactId: null,
  setSelectedFactId: (id) => set({ selectedFactId: id }),

  evidenceTarget: null,
  evidenceTargetVersion: 0,
  openEvidence: (target) => set((state) => ({
    evidenceTarget: target,
    evidenceTargetVersion: state.evidenceTargetVersion + 1,
    activeTab: 'evidence',
  })),

  selectedCaseId: null,
  setSelectedCaseId: (caseId) => set({ selectedCaseId: caseId }),
}));
