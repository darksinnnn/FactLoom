import { useFactLoomStore } from './store/factsStore';
import { useLenisScroll } from './hooks/useLenisScroll';
import { Navbar } from './components/layout/Navbar';
import { Landing } from './pages/Landing';
import { ReconciliationHub } from './components/reconciliation/ReconciliationHub';
import { FactList } from './components/fact-explorer/FactList';
import { EvidenceViewer } from './components/evidence/EvidenceViewer';
import { AskPanel } from './components/ask/AskPanel';
import { LimitationsPanel } from './components/limitations/LimitationsPanel';
import { UploadZone } from './components/upload/UploadZone';
import { LoomMark } from './components/identity/LoomMark';

import { useEffect } from 'react';
import { ErrorBoundary } from './components/shared/ErrorBoundary';

export function App() {
  const { activeTab, setActiveTab } = useFactLoomStore();

  // Initialize smooth RAF scroll loop via Lenis
  useLenisScroll(true);

  // Sync activeTab with URL hash
  useEffect(() => {
    function onHashChange() {
      const hash = window.location.hash.replace('#', '') as any;
      if (['command', 'reconciliation', 'explorer', 'evidence', 'ask', 'limitations', 'upload'].includes(hash)) {
        setActiveTab(hash);
      }
    }
    if (window.location.hash) {
      onHashChange();
    }
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, [setActiveTab]);

  return (
    <div className="min-h-screen bg-[var(--loom-ink)] text-[var(--loom-paper)] flex flex-col relative selection:bg-[var(--loom-verified)]/20 selection:text-[var(--loom-verified)]">
      {/* Noise filter texture overlay */}
      <div className="noise-overlay" />

      {/* Persistent Navigation */}
      <Navbar />

      {/* Main Routed Content */}
      <main className="flex-1">
        <ErrorBoundary>
          {activeTab === 'command' && <Landing />}
          {activeTab === 'reconciliation' && <ReconciliationHub />}
          {activeTab === 'explorer' && <FactList />}
          {activeTab === 'evidence' && <EvidenceViewer />}
          {activeTab === 'ask' && <AskPanel />}
          {activeTab === 'limitations' && <LimitationsPanel />}
          {activeTab === 'upload' && <UploadZone />}
        </ErrorBoundary>
      </main>

      {/* Editorial Ledger Footer */}
      <footer className="border-t border-[var(--loom-card-border)] bg-[var(--loom-surface)]/80 py-8 px-6 mt-16">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono-tabular text-[var(--loom-thread)]">
          <div className="flex items-center gap-2">
            <LoomMark size={20} />
            <span>FactLoom • Auditable Fact Reconciliation System</span>
          </div>
          <div className="flex items-center gap-4 text-[11px]">
            <span>FastAPI Backend :8000</span>
            <span>•</span>
            <span>PyMuPDF Bbox Grounding</span>
            <span>•</span>
            <span>Deterministic Tier-3 Verifier</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
