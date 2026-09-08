import { useEffect, useState } from 'react';
import { fetchFacts, type FactSummary } from '../../lib/api';
import { FactDetailPanel } from './FactDetailPanel';
import { Stack } from '@phosphor-icons/react';

export const FactList: React.FC = () => {
  const [facts, setFacts] = useState<FactSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFactId, setSelectedFactId] = useState<string | null>(null);

  // Filters
  const [entityFilter, setEntityFilter] = useState('');
  const [metricFilter, setMetricFilter] = useState('');
  const [periodFilter, setPeriodFilter] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await fetchFacts({
          entity: entityFilter || undefined,
          metric: metricFilter || undefined,
          period: periodFilter || undefined,
        });
        setFacts(data);
        if (data.length > 0 && !selectedFactId) {
          setSelectedFactId(data[0].id);
        }
      } catch (err) {
        console.error('Failed to load facts:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [entityFilter, metricFilter, periodFilter]);

  return (
    <div className="py-8 px-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <span className="font-mono-tabular text-xs uppercase tracking-widest text-[var(--loom-verified)] bg-[var(--loom-verified)]/10 px-2 py-0.5 rounded border border-[var(--loom-verified)]/20">
            Fact Explorer
          </span>
          <span className="text-[var(--loom-thread)] text-xs">•</span>
          <span className="font-body text-xs text-[var(--loom-thread)]">
            Immutable Fact Identity Master Registry
          </span>
        </div>
        <h1 className="font-display text-2xl md:text-3xl font-black text-[var(--loom-paper)]">
          Canonical Facts & Surface Observations
        </h1>
        <p className="font-body text-xs text-[var(--loom-thread)] mt-1">
          Every entity, metric, and period cluster maps to an immutable identity. Click any row to inspect attached observations and source bboxes.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-[var(--loom-card)] p-4 rounded-lg border border-[var(--loom-card-border)]">
        <div>
          <label className="block text-[10px] font-mono-tabular text-[var(--loom-thread)] uppercase mb-1">
            Filter Entity
          </label>
          <div className="relative">
            <input
              type="text"
              placeholder="e.g. Delhivery, India, Apple..."
              value={entityFilter}
              onChange={(e) => setEntityFilter(e.target.value)}
              className="w-full bg-[var(--loom-surface)] border border-[var(--loom-card-border)] rounded px-3 py-1.5 text-xs text-[var(--loom-paper)] placeholder:text-[var(--loom-thread)]/50 focus:outline-none focus:border-[var(--loom-verified)]"
            />
          </div>
        </div>

        <div>
          <label className="block text-[10px] font-mono-tabular text-[var(--loom-thread)] uppercase mb-1">
            Filter Metric
          </label>
          <input
            type="text"
            placeholder="e.g. EBITDA, Real GDP, Active Customers..."
            value={metricFilter}
            onChange={(e) => setMetricFilter(e.target.value)}
            className="w-full bg-[var(--loom-surface)] border border-[var(--loom-card-border)] rounded px-3 py-1.5 text-xs text-[var(--loom-paper)] placeholder:text-[var(--loom-thread)]/50 focus:outline-none focus:border-[var(--loom-verified)]"
          />
        </div>

        <div>
          <label className="block text-[10px] font-mono-tabular text-[var(--loom-thread)] uppercase mb-1">
            Filter Period
          </label>
          <input
            type="text"
            placeholder="e.g. FY24, FY25, Q4 FY24..."
            value={periodFilter}
            onChange={(e) => setPeriodFilter(e.target.value)}
            className="w-full bg-[var(--loom-surface)] border border-[var(--loom-card-border)] rounded px-3 py-1.5 text-xs text-[var(--loom-paper)] placeholder:text-[var(--loom-thread)]/50 focus:outline-none focus:border-[var(--loom-verified)]"
          />
        </div>
      </div>

      {/* Main Split View: Fact Master List (Left) + Detail Morph (Right) */}
      <div className="grid lg:grid-cols-12 gap-6 items-start">
        {/* Facts Table */}
        <div className="lg:col-span-6 bg-[var(--loom-card)]/50 border border-[var(--loom-card-border)] rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--loom-card-border)] bg-[var(--loom-surface)] flex items-center justify-between">
            <span className="font-mono-tabular text-xs font-semibold text-[var(--loom-paper)] uppercase tracking-wider">
              Discovered Facts ({facts.length})
            </span>
            <span className="font-mono-tabular text-[10px] text-[var(--loom-thread)]">
              Select row to inspect
            </span>
          </div>

          {loading ? (
            <div className="p-8 text-center font-mono-tabular text-xs text-[var(--loom-thread)]">
              Querying canonical facts...
            </div>
          ) : facts.length === 0 ? (
            <div className="p-8 text-center text-xs text-[var(--loom-thread)] font-body">
              No facts found matching filter criteria.
            </div>
          ) : (
            <div className="divide-y divide-[var(--loom-card-border)] max-h-[70vh] overflow-y-auto">
              {facts.map((f) => {
                const isSelected = selectedFactId === f.id;
                return (
                  <div
                    key={f.id}
                    onClick={() => setSelectedFactId(f.id)}
                    className={`p-4 cursor-pointer transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-[var(--loom-surface)] border-l-4 border-l-[var(--loom-verified)]'
                        : 'hover:bg-[var(--loom-surface)]/50'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-body font-semibold text-xs text-[var(--loom-paper)]">
                          {f.metric}
                        </span>
                        <span className="text-[10px] font-mono-tabular text-[var(--loom-thread)] bg-[var(--loom-ink)] px-1.5 py-0.2 rounded">
                          {f.period || 'Consolidated'}
                        </span>
                      </div>
                      <div className="font-body text-[11px] text-[var(--loom-thread)] truncate max-w-xs">
                        {f.entity} {f.scope ? `• Scope: ${f.scope}` : ''}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="font-mono-tabular text-[10px] px-2 py-0.5 rounded bg-[var(--loom-ink)] border border-[var(--loom-card-border)] text-[var(--loom-verified)] flex items-center gap-1">
                        <Stack size={12} />
                        <span>{f.observation_count} obs</span>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Fact Detail View (Right) */}
        <div className="lg:col-span-6 sticky top-24">
          {selectedFactId ? (
            <FactDetailPanel
              factId={selectedFactId}
              onClose={() => setSelectedFactId(null)}
            />
          ) : (
            <div className="guilloche-card rounded-lg p-12 text-center border border-[var(--loom-card-border)] font-body text-xs text-[var(--loom-thread)]">
              Select a fact from the left column to view its canonical identity and grounded observation cards.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
