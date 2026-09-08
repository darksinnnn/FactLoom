import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Cpu, CheckCircle, GitFork } from '@phosphor-icons/react';

interface Stage {
  id: string;
  title: string;
  subtitle: string;
  badge: string;
  codeSnippet: string;
  description: string;
  icon: React.ReactNode;
}

export const ExplainerSequence: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);

  const stages: Stage[] = [
    {
      id: 'ingest',
      title: '1. Ingestion & Grounding',
      subtitle: 'Extracting physical user-unit bboxes directly from PDF layers',
      badge: 'PARSER',
      icon: <FileText size={20} className="text-[var(--loom-paper)]" />,
      description:
        'Every candidate fact is strictly bounded by a verbatim quote span and bounding box coordinates [x0, y0, x1, y1] on the original document page. Hallucinated quotes fail automated grounding verification.',
      codeSnippet: `Observation(
  doc="02-delhivery-ar-fy24.pdf",
  page=36,
  value="1,266.41",
  unit="₹M",
  bbox=[142.1, 410.8, 198.3, 424.2]
)`,
    },
    {
      id: 'canonicalize',
      title: '2. Registry Canonicalization',
      subtitle: 'Clustering disparate surface mentions into immutable Fact identities',
      badge: 'REGISTRY',
      icon: <Cpu size={20} className="text-[var(--loom-unresolved)]" />,
      description:
        'Embedding similarity and LLM adjudication resolve variations ("EBITDA", "EBITDA (₹Cr)", "Earnings before interest...") into a single canonical metric, preventing false registry proliferation.',
      codeSnippet: `FactIdentity(
  entity="Delhivery Limited",
  metric="EBITDA",
  period="FY24",
  scope="Consolidated"
)`,
    },
    {
      id: 'reconcile',
      title: '3. Deterministic-First Reconciliation',
      subtitle: 'Unit scaling, tolerance checking, and semantic adjudications',
      badge: 'RECONCILER',
      icon: <GitFork size={20} className="text-[var(--loom-verified)]" />,
      description:
        'Continuous numbers are normalized to base scale (₹1,266.41M vs ₹127Cr -> 0.283% delta <= 0.5% tolerance) resolving deterministically without expensive LLM calls. Discrete counts (33,250 vs 33,278) trigger mandatory abstention.',
      codeSnippet: `Relationship(
  type="SAME_AS",
  dimensions=["ROUNDING", "UNIT_MISMATCH"],
  verified=True,
  delta_pct=0.283
)`,
    },
    {
      id: 'audit',
      title: '4. The Verifier Backstop',
      subtitle: 'Deterministic audit of arithmetic, dates, and estimate revisions',
      badge: 'VERIFIER',
      icon: <CheckCircle size={20} className="text-[var(--loom-verified)]" />,
      description:
        'Every LLM claim is deterministically re-audited. For SUPERSEDES, date ordering (T2 >= T1) is verified. For ESTIMATE_VS_ACTUAL, semantic asymmetry and temporal succession are proven before verified=True is stamped.',
      codeSnippet: `VerifierResult(
  claim="₹127Cr matches ₹1,266.41M",
  recomputed_delta=0.002835,
  status="VERIFIED_CORRECT"
)`,
    },
  ];

  return (
    <section className="py-16 px-6 max-w-7xl mx-auto border-t border-[var(--loom-card-border)]">
      <div className="mb-10 text-center max-w-2xl mx-auto">
        <span className="font-mono-tabular text-xs uppercase tracking-widest text-[var(--loom-verified)] bg-[var(--loom-verified)]/10 px-2.5 py-1 rounded border border-[var(--loom-verified)]/20">
          Architecture Workflow
        </span>
        <h2 className="font-display text-3xl md:text-4xl font-black tracking-tight text-[var(--loom-paper)] mt-4">
          From Raw Ingestion to Verified Knot
        </h2>
        <p className="font-body text-sm text-[var(--loom-thread)] mt-2">
          FactLoom pulls threads of evidence out of digital documents, braiding agreement and isolating unresolved contradictions.
        </p>
      </div>

      {/* Step Selector Tabs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {stages.map((stage, idx) => {
          const isActive = activeStep === idx;
          return (
            <button
              key={stage.id}
              onClick={() => setActiveStep(idx)}
              className={`p-4 text-left rounded border transition-all text-sm ${
                isActive
                  ? 'bg-[var(--loom-surface)] border-[var(--loom-verified)]/60 shadow-lg'
                  : 'bg-[var(--loom-card)]/50 border-[var(--loom-card-border)] hover:border-[var(--loom-hairline)]'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono-tabular text-[10px] uppercase text-[var(--loom-thread)]">
                  Step 0{idx + 1}
                </span>
                {stage.icon}
              </div>
              <h3 className="font-body font-medium text-[var(--loom-paper)] truncate">{stage.title}</h3>
            </button>
          );
        })}
      </div>

      {/* Stage Detail Visualizer */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeStep}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.25 }}
          className="guilloche-card rounded-lg p-6 md:p-8 grid md:grid-cols-2 gap-8 items-center"
        >
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="font-mono-tabular text-xs text-[var(--loom-verified)] font-medium">
                {stages[activeStep].badge}
              </span>
              <span className="text-[var(--loom-thread)] text-xs">•</span>
              <span className="font-body text-xs text-[var(--loom-thread)]">
                {stages[activeStep].subtitle}
              </span>
            </div>
            <h3 className="font-display text-2xl font-bold text-[var(--loom-paper)] mb-4">
              {stages[activeStep].title}
            </h3>
            <p className="font-body text-sm text-[var(--loom-paper)]/80 leading-relaxed">
              {stages[activeStep].description}
            </p>
          </div>

          <div className="bg-[var(--loom-ink)] border border-[var(--loom-card-border)] rounded-md p-5 font-mono-tabular text-xs overflow-x-auto text-[var(--loom-paper)]/90">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-[var(--loom-card-border)] text-[var(--loom-thread)] text-[11px]">
              <span>Grounded Evidence Schema</span>
              <span>JSON / Python</span>
            </div>
            <pre className="text-[var(--loom-verified)] leading-relaxed">
              {stages[activeStep].codeSnippet}
            </pre>
          </div>
        </motion.div>
      </AnimatePresence>
    </section>
  );
};
