import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { fetchFactDetail, type FactDetail } from '../../lib/api';
import { TabularValue } from '../shared/TabularValue';
import { StatusBadge } from '../shared/StatusBadge';
import { useFactLoomStore } from '../../store/factsStore';
import { X, ArrowSquareOut, FileText } from '@phosphor-icons/react';

interface FactDetailPanelProps {
  factId: string;
  onClose: () => void;
}

export const FactDetailPanel: React.FC<FactDetailPanelProps> = ({ factId, onClose }) => {
  const [detail, setDetail] = useState<FactDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const { openEvidence } = useFactLoomStore();

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchFactDetail(factId);
        setDetail(data);
      } catch (err) {
        console.error('Failed to load fact details:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [factId]);

  if (loading) {
    return (
      <div className="bg-[var(--loom-card)] border border-[var(--loom-card-border)] rounded-lg p-6 text-center font-mono-tabular text-xs text-[var(--loom-thread)]">
        Loading canonical fact identity & observations...
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="bg-[var(--loom-card)] border border-[var(--loom-card-border)] rounded-lg p-6 text-center text-xs text-[var(--loom-thread)]">
        Fact record not found.
      </div>
    );
  }

  const { fact, observations, relationships } = detail;

  return (
    <motion.div
      layoutId={`fact-card-${factId}`}
      className="guilloche-card rounded-lg p-6 border border-[var(--loom-card-border)] space-y-6 shadow-2xl relative"
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 p-1.5 rounded text-[var(--loom-thread)] hover:text-[var(--loom-paper)] hover:bg-[var(--loom-surface)]"
      >
        <X size={18} />
      </button>

      {/* Header: Canonical Identity */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="font-mono-tabular text-[10px] uppercase tracking-widest text-[var(--loom-verified)] bg-[var(--loom-verified)]/10 px-2 py-0.5 rounded border border-[var(--loom-verified)]/20">
            Canonical Fact Identity
          </span>
          <span className="font-mono-tabular text-xs text-[var(--loom-thread)]">
            ID: {fact.id.slice(0, 8)}...
          </span>
        </div>
        <h2 className="font-display text-2xl font-bold text-[var(--loom-paper)]">
          {fact.entity} — {fact.metric}
        </h2>
        <div className="flex flex-wrap items-center gap-2 mt-2 font-mono-tabular text-xs text-[var(--loom-thread)]">
          <span className="bg-[var(--loom-surface)] px-2 py-0.5 rounded">
            Period: <strong className="text-[var(--loom-paper)]">{fact.period || 'Consolidated'}</strong>
          </span>
          <span className="bg-[var(--loom-surface)] px-2 py-0.5 rounded">
            Scope: <strong className="text-[var(--loom-paper)]">{fact.scope || 'Consolidated'}</strong>
          </span>
          {fact.measurement_type && (
            <span className="bg-[var(--loom-surface)] px-2 py-0.5 rounded">
              Type: {fact.measurement_type}
            </span>
          )}
        </div>
      </div>

      {/* Observations List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-[var(--loom-card-border)]">
          <h3 className="font-body text-xs font-semibold uppercase tracking-wider text-[var(--loom-thread)]">
            Attached Grounded Observations ({observations.length})
          </h3>
          <span className="font-mono-tabular text-[10px] text-[var(--loom-thread)]">
            Disparate surface forms clustered by Registry
          </span>
        </div>

        <div className="grid gap-3">
          {observations.map((obs) => {
            let parsedBbox: number[] | null = null;
            try {
              if (obs.bbox) parsedBbox = JSON.parse(obs.bbox);
            } catch (_) {}

            return (
              <div
                key={obs.id}
                className="bg-[var(--loom-ink)] border border-[var(--loom-card-border)] rounded-md p-4 space-y-2 hover:border-[var(--loom-hairline)] transition-all"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-mono-tabular text-xs text-[var(--loom-thread)]">
                    <FileText size={14} className="text-[var(--loom-verified)]" />
                    <span className="truncate max-w-[200px]" title={obs.document_filename}>
                      {obs.document_filename || 'Source PDF'}
                    </span>
                    <span>• p. {obs.page_number}</span>
                  </div>
                  <TabularValue
                    value={obs.value}
                    unit={obs.unit}
                    align="right"
                    className="text-lg font-bold"
                  />
                </div>

                {obs.quote_span && (
                  <blockquote className="text-xs font-body italic text-[var(--loom-paper)]/80 border-l-2 border-[var(--loom-thread)]/40 pl-3 py-1 my-1 bg-[var(--loom-surface)]/40 rounded-r">
                    "{obs.quote_span}"
                  </blockquote>
                )}

                <div className="flex items-center justify-between pt-1 border-t border-[var(--loom-card-border)]/40 text-[10px] font-mono-tabular">
                  <span className="text-[var(--loom-thread)]">
                    Vintage: {obs.doc_vintage_date || 'Undated'}
                  </span>
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
                    className="inline-flex items-center gap-1 text-[var(--loom-verified)] hover:underline"
                  >
                    <span>View Evidence & Bbox</span>
                    <ArrowSquareOut size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Relationships */}
      {relationships.length > 0 && (
        <div className="space-y-3 pt-2">
          <h3 className="font-body text-xs font-semibold uppercase tracking-wider text-[var(--loom-thread)]">
            Reconciliation Edges ({relationships.length})
          </h3>
          <div className="space-y-2">
            {relationships.map((r) => (
              <div
                key={r.id}
                className="bg-[var(--loom-surface)] border border-[var(--loom-card-border)] rounded p-3 text-xs flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <StatusBadge status={r.relationship_type || r.type || 'neutral'} size="sm" />
                  <span className="font-mono-tabular text-[11px] text-[var(--loom-paper)]">
                    Dimension: {r.dimension}
                  </span>
                </div>
                <span className="font-mono-tabular text-[10px] text-[var(--loom-verified)]">
                  {r.verified_bool ? '✓ Verified' : 'Unverified'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
};
