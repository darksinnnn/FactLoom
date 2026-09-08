import type { FactSummary, Observation } from '../../lib/api';
import { TabularValue } from '../shared/TabularValue';
import { Warning, ArrowSquareOut } from '@phosphor-icons/react';
import { useFactLoomStore } from '../../store/factsStore';

interface AmbiguousResultSetProps {
  facts: FactSummary[];
  observations: Observation[];
  question: string;
}

export const AmbiguousResultSet: React.FC<AmbiguousResultSetProps> = ({
  facts,
  observations,
  question,
}) => {
  const { openEvidence } = useFactLoomStore();

  return (
    <div className="space-y-4 my-6">
      {/* Explicit Abstention Banner */}
      <div className="bg-[var(--loom-unresolved)]/10 border border-[var(--loom-unresolved)]/30 rounded-lg p-4 flex items-start gap-3">
        <Warning size={20} className="text-[var(--loom-unresolved)] shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-body font-bold text-xs uppercase tracking-wider text-[var(--loom-unresolved)]">
            Temporal Ambiguity Detected — Multi-Fact Abstention Triggered
          </h4>
          <p className="font-body text-xs text-[var(--loom-paper)]/90 leading-relaxed">
            The question <strong className="italic">"{question}"</strong> lacks an explicit period or vintage qualifier. Rather than hallucinating a single averaged figure or guessing a timeframe, FactLoom preserves truth by presenting all {facts.length} distinct matching canonical facts side-by-side.
          </p>
        </div>
      </div>

      {/* Side-by-Side Un-merged Fact Cards */}
      <div className="grid md:grid-cols-2 gap-4">
        {facts.map((fact) => {
          const matchingObs = observations.filter((o) => o.fact_id === fact.id);

          return (
            <div
              key={fact.id}
              className="bg-[var(--loom-card)] border border-[var(--loom-card-border)] rounded-lg p-5 space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono-tabular text-xs uppercase tracking-wider text-[var(--loom-verified)] bg-[var(--loom-verified)]/10 px-2 py-0.5 rounded">
                  {fact.period || 'Consolidated'}
                </span>
                <span className="font-mono-tabular text-[10px] text-[var(--loom-thread)]">
                  {matchingObs.length} Observation{matchingObs.length > 1 ? 's' : ''}
                </span>
              </div>

              <h3 className="font-display text-lg font-bold text-[var(--loom-paper)]">
                {fact.entity} — {fact.metric}
              </h3>

              <div className="space-y-2 pt-2 border-t border-[var(--loom-card-border)]/60">
                {matchingObs.map((obs) => {
                  let parsedBbox: number[] | null = null;
                  try {
                    if (obs.bbox) parsedBbox = JSON.parse(obs.bbox);
                  } catch (_) {}

                  return (
                    <div
                      key={obs.id}
                      className="bg-[var(--loom-ink)] p-3 rounded border border-[var(--loom-card-border)]/50 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono-tabular text-[10px] text-[var(--loom-thread)] truncate max-w-[180px]">
                          {obs.document_filename || 'Source Doc'} (p. {obs.page_number})
                        </span>
                        <TabularValue
                          value={obs.value}
                          unit={obs.unit}
                          align="right"
                          className="font-bold text-sm"
                        />
                      </div>
                      {obs.quote_span && (
                        <p className="font-body text-[11px] italic text-[var(--loom-paper)]/80">
                          "{obs.quote_span}"
                        </p>
                      )}
                      <div className="pt-1 flex justify-end">
                        <button
                          onClick={() =>
                            openEvidence({
                              documentId: obs.document_id,
                              documentFilename: obs.document_filename,
                              pageNumber: obs.page_number,
                              bbox: parsedBbox,
                              quoteSpan: obs.quote_span,
                              value: obs.value,
                              unit: obs.unit,
                            })
                          }
                          className="text-[10px] font-mono-tabular text-[var(--loom-verified)] hover:underline inline-flex items-center gap-1"
                        >
                          <span>Inspect Bbox</span>
                          <ArrowSquareOut size={10} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
