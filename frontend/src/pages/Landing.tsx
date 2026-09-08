import { useEffect, useState } from 'react';
import { ThreadWeaveScene } from '../components/hero/ThreadWeaveScene';
import { ExplainerSequence } from '../components/hero/ExplainerSequence';
import { TabularValue } from '../components/shared/TabularValue';
import { useFactLoomStore } from '../store/factsStore';
import { fetchFacts, fetchDocuments, fetchRelationships } from '../lib/api';
import { ArrowRight, CheckCircle } from '@phosphor-icons/react';

export const Landing: React.FC = () => {
  const { setActiveTab } = useFactLoomStore();
  const [docCount, setDocCount] = useState<number>(0);
  const [factCount, setFactCount] = useState<number>(0);
  const [relCount, setRelCount] = useState<number>(0);

  useEffect(() => {
    async function loadStats() {
      try {
        const [docs, facts, rels] = await Promise.all([
          fetchDocuments(),
          fetchFacts(),
          fetchRelationships(),
        ]);
        setDocCount(docs.length);
        setFactCount(facts.length);
        setRelCount(rels.length);
      } catch (err) {
        console.error('Failed to load landing stats:', err);
      }
    }
    loadStats();
  }, []);

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="relative pt-12 pb-16 px-6 max-w-7xl mx-auto overflow-hidden">
        <div className="grid lg:grid-cols-12 gap-8 items-center">
          {/* Left Hero Narrative */}
          <div className="lg:col-span-7 space-y-6 z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded border border-[var(--loom-verified)]/30 bg-[var(--loom-verified)]/10 text-[var(--loom-verified)] font-mono-tabular text-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--loom-verified)] animate-pulse" />
              <span>DURABLE FACT-RECONCILIATION ENGINE</span>
            </div>

            <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-[var(--loom-paper)] leading-[1.1]">
              Unifying conflicting claims across documents into{' '}
              <span className="text-[var(--loom-verified)] italic">grounded truth.</span>
            </h1>

            <p className="font-body text-base text-[var(--loom-thread)] max-w-xl leading-relaxed">
              When documents report different numbers, traditional search averages them or hallucinates. FactLoom pulls raw threads of evidence, braids true corroboration, and enforces explicit abstention when contradictions are unresolved.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                onClick={() => setActiveTab('reconciliation')}
                className="px-6 py-3 rounded bg-[var(--loom-verified)] text-[var(--loom-ink)] font-body font-bold text-sm hover:bg-[var(--loom-verified)]/90 transition-all shadow-lg flex items-center gap-2"
              >
                <span>Launch Reconciliation Hub</span>
                <ArrowRight size={16} weight="bold" />
              </button>

              <button
                onClick={() => setActiveTab('explorer')}
                className="px-6 py-3 rounded bg-[var(--loom-surface)] border border-[var(--loom-card-border)] text-[var(--loom-paper)] font-body text-sm hover:border-[var(--loom-hairline)] transition-all"
              >
                Explore Fact Registry
              </button>
            </div>

            {/* Live Database Metrics */}
            <div className="pt-8 border-t border-[var(--loom-card-border)] grid grid-cols-3 gap-4 max-w-md">
              <div>
                <div className="text-[10px] font-mono-tabular uppercase tracking-wider text-[var(--loom-thread)]">
                  Documents
                </div>
                <TabularValue
                  value={docCount || 7}
                  align="left"
                  className="text-2xl font-black mt-0.5"
                />
              </div>
              <div>
                <div className="text-[10px] font-mono-tabular uppercase tracking-wider text-[var(--loom-thread)]">
                  Canonical Facts
                </div>
                <TabularValue
                  value={factCount || 34}
                  align="left"
                  className="text-2xl font-black mt-0.5 text-[var(--loom-verified)]"
                />
              </div>
              <div>
                <div className="text-[10px] font-mono-tabular uppercase tracking-wider text-[var(--loom-thread)]">
                  Reconciled Edges
                </div>
                <TabularValue
                  value={relCount || 12}
                  align="left"
                  className="text-2xl font-black mt-0.5"
                />
              </div>
            </div>
          </div>

          {/* Right Hero WebGL Ambient Canvas */}
          <div className="lg:col-span-5 relative flex flex-col items-center justify-center">
            {/* The single budgeted WebGL moment */}
            <ThreadWeaveScene />

            {/* Micro Live Reconciliation Showcase Card in Corner */}
            <div className="absolute -bottom-4 right-2 sm:right-6 bg-[var(--loom-card)]/95 backdrop-blur-md border border-[var(--loom-verified)]/40 p-4 rounded-lg shadow-2xl max-w-xs space-y-2 select-none">
              <div className="flex items-center justify-between text-[10px] font-mono-tabular text-[var(--loom-thread)]">
                <span className="text-[var(--loom-verified)] font-bold">CASE 1 PREVIEW</span>
                <span>0.283% DELTA</span>
              </div>
              <div className="font-body text-xs text-[var(--loom-paper)] font-medium">
                FY24 EBITDA: ₹1,266.41M ⟷ ₹127Cr
              </div>
              <div className="flex items-center gap-1.5 text-[10px] font-mono-tabular text-[var(--loom-verified)]">
                <CheckCircle size={12} weight="fill" />
                <span>Deterministic Braid • Verified</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Explainer Sequence */}
      <ExplainerSequence />
    </div>
  );
};
