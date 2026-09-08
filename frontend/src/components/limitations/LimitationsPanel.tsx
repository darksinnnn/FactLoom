import { Info } from '@phosphor-icons/react';

export const LimitationsPanel: React.FC = () => {
  const boundaries = [
    {
      id: 'discrete-counts',
      title: '1. Discrete Count Safeguard vs Continuous Financial Tolerances',
      category: 'RECONCILIATION ENGINE',
      description:
        'In Case 2 (Active Customers: 33,250 in Earnings Deck vs 33,278 in Annual Report), the numerical delta is only 0.084% — well within the 0.5% continuous rounding tolerance that correctly corroborates Case 1. Without an explicit Discrete Count Safeguard, a naive reconciler would collapse these discrete headcount figures into SAME_AS. FactLoom explicitly flags integer counts as zero-tolerance quantities, enforcing mandatory abstention (UNRESOLVED) rather than manufacturing a false corroboration.',
      boundary:
        'Metric names containing count/headcount/customers/centers/pincodes are guarded against continuous percentage tolerances.',
    },
    {
      id: 'scope-splitter',
      title: '2. Structural Table Breakdowns vs Stripped-Header Boundary Case',
      category: 'CANONICAL REGISTRY',
      description:
        'In multi-segment tables (e.g., Apple 10-Q net sales by region), segment rows like "Americas", "Europe", or "Greater China" can be mistakenly extracted as top-level metrics. FactLoom employs a primary structural parser detecting "[Metric] by [Dimension]" table headers to demote row headers to scope on the parent metric, backed by a narrow gazetteer safety net.',
      boundary:
        'If a non-geographic breakdown table (e.g. customer age cohorts) has its table header completely stripped or omitted by an upstream PDF stream parser, the row qualifiers can register as standalone metrics unless caught by structural rules.',
    },
    {
      id: 'modifier-attachment',
      title: '3. Accounting Qualifier Attachment Heuristic (Basic/Diluted)',
      category: 'CANONICAL REGISTRY',
      description:
        'In financial statements, line items such as "Basic" and "Diluted" often appear as isolated single-word row headers without repeating the head noun ("shares" or "earnings per share"). FactLoom applies a domain-vocabulary modifier heuristic attaching known financial qualifiers (basic, diluted, current, non-current, class a/b) to adjacent head nouns (shares, assets, liabilities, debt).',
      boundary:
        'This is a targeted financial heuristic rather than a universal grammatical dependency parser. Rare non-standard qualifiers outside the curated set will not automatically link to split parent nouns.',
    },
    {
      id: 'segment-sum',
      title: '4. Segment-Sum Footnote & Subtotal Tolerances (Case 4)',
      category: 'DETERMINISTIC RECONCILER',
      description:
        'Segment reporting tables frequently display discrepancies between the sum of reported individual business lines and the printed Total row due to unallocated corporate overhead, inter-segment eliminations, or rounding footings. FactLoom implements deterministic subtotal tolerance checks (0.5% – 1.0%) to prevent these mathematical accounting conventions from triggering false contradiction alarms or expensive LLM escalations.',
      boundary:
        'Differences exceeding the 1.0% subtotal threshold are escalated to LLM semantic review or marked UNRESOLVED.',
    },
  ];

  return (
    <div className="py-10 px-6 max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="border-b border-[var(--loom-card-border)] pb-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="font-mono-tabular text-xs uppercase tracking-widest text-[var(--loom-thread)] bg-[var(--loom-surface)] px-2 py-0.5 rounded border border-[var(--loom-card-border)]">
            System Boundaries
          </span>
          <span className="text-[var(--loom-thread)] text-xs">•</span>
          <span className="font-body text-xs text-[var(--loom-thread)]">
            Candid Operational Disclosures
          </span>
        </div>
        <h1 className="font-display text-3xl font-black text-[var(--loom-paper)]">
          Known Limitations & Edge Case Behavior
        </h1>
        <p className="font-body text-sm text-[var(--loom-thread)] mt-2 leading-relaxed">
          FactLoom is engineered around transparent verification rather than opaque certainty. This page outlines the explicit heuristic boundaries, edge cases, and safeguards discovered during development and evaluation.
        </p>
      </div>

      {/* Disclosed Limitations List */}
      <div className="space-y-6">
        {boundaries.map((item) => (
          <div
            key={item.id}
            className="bg-[var(--loom-card)] border border-[var(--loom-card-border)] rounded-lg p-6 space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono-tabular text-[10px] uppercase tracking-wider text-[var(--loom-verified)] bg-[var(--loom-verified)]/10 px-2 py-0.5 rounded">
                {item.category}
              </span>
            </div>

            <h3 className="font-display text-xl font-bold text-[var(--loom-paper)]">
              {item.title}
            </h3>

            <p className="font-body text-xs text-[var(--loom-paper)]/85 leading-relaxed">
              {item.description}
            </p>

            <div className="bg-[var(--loom-ink)] p-3 rounded border border-[var(--loom-card-border)] text-xs font-mono-tabular text-[var(--loom-thread)] flex items-start gap-2">
              <Info size={16} className="text-[var(--loom-thread)] shrink-0 mt-0.5" />
              <div>
                <strong className="text-[var(--loom-paper)]">Boundary Condition: </strong>
                {item.boundary}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
