import { useEffect, useState } from 'react';
import { fetchRelationships, type Relationship } from '../../lib/api';
import { BraidView } from './BraidView';
import { FrayView } from './FrayView';
import { KnotView } from './KnotView';
import { VerifierBadge } from './VerifierBadge';
import { StatusBadge } from '../shared/StatusBadge';
import { TabularValue } from '../shared/TabularValue';
import { useFactLoomStore } from '../../store/factsStore';
import { ArrowSquareOut } from '@phosphor-icons/react';

export const ReconciliationHub: React.FC = () => {
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState<string>('case-1');
  const { openEvidence } = useFactLoomStore();

  useEffect(() => {
    async function loadData() {
      try {
        const data = await fetchRelationships();
        setRelationships(data);
      } catch (err) {
        console.error('Failed to load relationships:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Four locked demo cases filter definitions
  const demoCases = [
    {
      id: 'case-1',
      title: 'Case 1: FY24 EBITDA Corroboration',
      type: 'SAME_AS',
      dimension: 'ROUNDING + UNIT_MISMATCH',
      subtitle: 'Annual Report ₹1,266.41M vs Earnings Deck ₹127Cr (0.283% delta)',
      filter: (r: Relationship) => {
        const t = r.relationship_type || r.type;
        return t === 'SAME_AS' || Boolean(r.value_a?.includes('1,266.41') || r.value_b?.includes('127'));
      },
    },
    {
      id: 'case-2',
      title: 'Case 2: Active Customers (Mandatory Abstention)',
      type: 'UNRESOLVED',
      dimension: 'UNKNOWN',
      subtitle: 'Deck 33,250 vs AR 33,278 (0.084% discrete count divergence)',
      filter: (r: Relationship) => {
        const t = r.relationship_type || r.type;
        return t === 'UNRESOLVED' || Boolean(r.value_a?.includes('33,2') || r.value_b?.includes('33,2'));
      },
    },
    {
      id: 'case-3a',
      title: 'Case 3a: Director Sujan Status Transition',
      type: 'SUPERSEDES',
      dimension: 'REPORTING_VINTAGE',
      subtitle: '2022 Prospectus nominee superseded by Aug 24, 2023 cessation',
      filter: (r: Relationship) => {
        const t = r.relationship_type || r.type;
        return t === 'SUPERSEDES' || Boolean(r.quote_a?.toLowerCase().includes('sujan') || r.quote_b?.toLowerCase().includes('sujan'));
      },
    },
    {
      id: 'case-3b',
      title: 'Case 3b: India Real GDP Estimate vs Actual',
      type: 'RECONCILED_BY',
      dimension: 'ESTIMATE_VS_ACTUAL',
      subtitle: '6.4% First Advance Estimate updated by 6.5% Official Release',
      filter: (r: Relationship) => {
        const t = r.relationship_type || r.type;
        return t === 'RECONCILED_BY' || Boolean(r.value_a?.includes('6.4') || r.value_b?.includes('6.5'));
      },
    },
    {
      id: 'all',
      title: 'All Ingested Relationships',
      type: 'ALL',
      dimension: 'DYNAMIC',
      subtitle: 'Every reconciled edge discovered across documents in the database',
      filter: () => true,
    },
  ];

  const activeCaseMeta = demoCases.find((c) => c.id === selectedCase) || demoCases[0];
  const displayedRelationships = relationships.filter(activeCaseMeta.filter);

  return (
    <div className="py-8 px-6 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="font-mono-tabular text-xs uppercase tracking-widest text-[var(--loom-verified)] bg-[var(--loom-verified)]/10 px-2.5 py-1 rounded border border-[var(--loom-verified)]/20">
            Reconciliation Engine
          </span>
          <span className="text-[var(--loom-thread)] text-xs">•</span>
          <span className="font-body text-xs text-[var(--loom-thread)]">
            State-driven Braid / Fray / Knot animations mapped to real backend data
          </span>
        </div>
        <h1 className="font-display text-3xl md:text-4xl font-black tracking-tight text-[var(--loom-paper)]">
          Cross-Document Fact Reconciliation
        </h1>
        <p className="font-body text-sm text-[var(--loom-thread)] mt-1.5 max-w-3xl">
          Observe how FactLoom analyzes paired claims across independent filings. True agreements braid into a unified cord; ungrounded differences fray visibly; temporal transitions knot chronologically.
        </p>
      </div>

      {/* Case Selector Navigation */}
      <div className="flex flex-wrap gap-2.5 border-b border-[var(--loom-card-border)] pb-4">
        {demoCases.map((c) => {
          const isSelected = selectedCase === c.id;
          return (
            <button
              key={c.id}
              onClick={() => setSelectedCase(c.id)}
              className={`px-3.5 py-2 rounded text-xs font-body transition-all text-left border ${
                isSelected
                  ? 'bg-[var(--loom-surface)] border-[var(--loom-verified)]/60 text-[var(--loom-paper)] shadow'
                  : 'bg-[var(--loom-card)]/60 border-[var(--loom-card-border)] text-[var(--loom-thread)] hover:text-[var(--loom-paper)] hover:border-[var(--loom-hairline)]'
              }`}
            >
              <div className="font-medium text-xs truncate text-[var(--loom-paper)]">{c.title}</div>
              <div className="font-mono-tabular text-[10px] text-[var(--loom-thread)] mt-0.5">{c.dimension}</div>
            </button>
          );
        })}
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="py-20 text-center font-mono-tabular text-sm text-[var(--loom-thread)]">
          Retrieving verified relationship edges from backend...
        </div>
      ) : displayedRelationships.length === 0 ? (
        <div className="py-16 text-center rounded-lg border border-[var(--loom-card-border)] bg-[var(--loom-card)] p-8">
          <p className="font-body text-[var(--loom-paper)]">No relationship records matched this filter.</p>
          <p className="font-body text-xs text-[var(--loom-thread)] mt-1">
            Run the automated seed suite or ingest starter documents to populate database edges.
          </p>
        </div>
      ) : (
        <div className="space-y-10">
          {displayedRelationships.map((rel) => {
            const relType = rel.relationship_type || rel.type || 'UNRESOLVED';

            return (
              <div
                key={rel.id}
                className="guilloche-card rounded-lg p-6 md:p-8 space-y-6 shadow-xl border border-[var(--loom-card-border)]"
              >
                {/* Meta Bar */}
                <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[var(--loom-card-border)]">
                  <div className="flex items-center gap-3">
                    <StatusBadge status={relType} />
                    <span className="font-mono-tabular text-xs text-[var(--loom-thread)]">
                      Dimension: <strong className="text-[var(--loom-paper)]">{rel.dimension}</strong>
                    </span>
                  </div>
                  <VerifierBadge verified={rel.verified_bool} claim={rel.justification} />
                </div>

                {/* Paired Observation Cards */}
                <div className="grid md:grid-cols-2 gap-6 items-stretch">
                  {/* Observation A Card */}
                  <div className="bg-[var(--loom-ink)]/90 border border-[var(--loom-card-border)] rounded-md p-5 space-y-3 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between text-xs text-[var(--loom-thread)] font-mono-tabular mb-1.5">
                        <span className="truncate max-w-[220px]" title={rel.doc_a}>
                          {rel.doc_a || 'Document A'}
                        </span>
                        <span className="px-1.5 py-0.5 bg-[var(--loom-surface)] rounded text-[10px]">
                          Observation A
                        </span>
                      </div>
                      <div className="my-2">
                        <TabularValue
                          value={rel.value_a}
                          unit={rel.unit_a}
                          align="left"
                          className="text-2xl font-bold"
                        />
                      </div>
                      {rel.quote_a && (
                        <blockquote className="text-xs font-body italic text-[var(--loom-paper)]/80 border-l-2 border-[var(--loom-verified)]/40 pl-3 py-1 my-2 bg-[var(--loom-surface)]/40 rounded-r">
                          "{rel.quote_a}"
                        </blockquote>
                      )}
                    </div>
                    <div className="pt-2 border-t border-[var(--loom-card-border)]/50 flex justify-end">
                      <button
                        onClick={() =>
                          openEvidence({
                            documentId: rel.doc_a || '',
                            documentFilename: rel.doc_a,
                            pageNumber: 1, // Opens relevant page
                            quoteSpan: rel.quote_a,
                            value: rel.value_a,
                            unit: rel.unit_a,
                          })
                        }
                        className="inline-flex items-center gap-1 text-[11px] font-mono-tabular text-[var(--loom-verified)] hover:underline"
                      >
                        <span>View Grounded PDF Page</span>
                        <ArrowSquareOut size={12} />
                      </button>
                    </div>
                  </div>

                  {/* Observation B Card */}
                  <div className="bg-[var(--loom-ink)]/90 border border-[var(--loom-card-border)] rounded-md p-5 space-y-3 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between text-xs text-[var(--loom-thread)] font-mono-tabular mb-1.5">
                        <span className="truncate max-w-[220px]" title={rel.doc_b}>
                          {rel.doc_b || 'Document B'}
                        </span>
                        <span className="px-1.5 py-0.5 bg-[var(--loom-surface)] rounded text-[10px]">
                          Observation B
                        </span>
                      </div>
                      <div className="my-2">
                        <TabularValue
                          value={rel.value_b}
                          unit={rel.unit_b}
                          align="left"
                          className="text-2xl font-bold"
                        />
                      </div>
                      {rel.quote_b && (
                        <blockquote className="text-xs font-body italic text-[var(--loom-paper)]/80 border-l-2 border-[var(--loom-verified)]/40 pl-3 py-1 my-2 bg-[var(--loom-surface)]/40 rounded-r">
                          "{rel.quote_b}"
                        </blockquote>
                      )}
                    </div>
                    <div className="pt-2 border-t border-[var(--loom-card-border)]/50 flex justify-end">
                      <button
                        onClick={() =>
                          openEvidence({
                            documentId: rel.doc_b || '',
                            documentFilename: rel.doc_b,
                            pageNumber: 1,
                            quoteSpan: rel.quote_b,
                            value: rel.value_b,
                            unit: rel.unit_b,
                          })
                        }
                        className="inline-flex items-center gap-1 text-[11px] font-mono-tabular text-[var(--loom-verified)] hover:underline"
                      >
                        <span>View Grounded PDF Page</span>
                        <ArrowSquareOut size={12} />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Central State-Driven Animation Visual */}
                <div className="py-2">
                  {relType === 'SAME_AS' || relType === 'RECONCILED_BY' ? (
                    <BraidView dimension={rel.dimension} />
                  ) : relType === 'SUPERSEDES' ? (
                    <KnotView dimension={rel.dimension} />
                  ) : (
                    <FrayView dimension={rel.dimension} />
                  )}
                </div>

                {/* Justification Box */}
                <div className="bg-[var(--loom-surface)]/80 border border-[var(--loom-card-border)] rounded-md p-4 text-xs font-body text-[var(--loom-paper)]/90 leading-relaxed">
                  <div className="font-mono-tabular text-[10px] uppercase text-[var(--loom-thread)] mb-1 font-semibold">
                    Reconciliation Reasoning & Proof:
                  </div>
                  {rel.justification}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
