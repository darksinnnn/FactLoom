import { useState } from 'react';
import { askQuestion, type AskResponse } from '../../lib/api';
import { AmbiguousResultSet } from './AmbiguousResultSet';
import { useFactLoomStore } from '../../store/factsStore';
import { PaperPlaneTilt, Sparkle, ArrowSquareOut, CheckCircle } from '@phosphor-icons/react';

export const AskPanel: React.FC = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { openEvidence } = useFactLoomStore();

  const demoQueries = [
    {
      label: 'Case 1: FY24 EBITDA',
      q: "What was Delhivery's FY24 EBITDA?",
      desc: 'Corroboration across Annual Report & Deck',
    },
    {
      label: 'Case 2: Active Customers',
      q: 'How many active customers did Delhivery have in FY24?',
      desc: 'Discrete count contradiction (Abstention)',
    },
    {
      label: 'Case 3a: Director Sujan',
      q: 'Is Sujan Hajra a director of Delhivery?',
      desc: 'Temporal supersedes (resignation)',
    },
    {
      label: 'Case 3b: India Real GDP FY25',
      q: "What was India's Real GDP growth in FY25?",
      desc: 'Reconciled by Estimate vs Actual release',
    },
    {
      label: 'Ambiguous Query: India GDP',
      q: "What is India's GDP growth?",
      desc: 'Temporal ambiguity: returns multiple periods uncollapsed',
    },
  ];

  async function handleAsk(questionText: string) {
    if (!questionText.trim()) return;
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const res = await askQuestion(questionText);
      setResponse(res);
    } catch (err: any) {
      setError(err.message || 'An error occurred during query execution.');
    } finally {
      setLoading(false);
    }
  }

  // Render clickable citations inside answer text
  function renderFormattedAnswer(answerText: string, citations: any[]) {
    // Splits text by citation tokens [cite:obs_id]
    const parts = answerText.split(/(\[cite:[^\]]+\])/g);

    return parts.map((part, i) => {
      const match = part.match(/\[cite:([^\]]+)\]/);
      if (match) {
        const obsId = match[1];
        const citation = citations?.find((c) => c.observation_id === obsId);

        return (
          <button
            key={i}
            onClick={() => {
              if (citation) {
                openEvidence({
                  documentId: citation.document_id || '',
                  documentFilename: citation.document_filename,
                  pageNumber: citation.page_number || 1,
                  bbox: citation.bbox,
                  quoteSpan: citation.quote_span,
                  value: citation.value,
                  unit: citation.unit,
                });
              }
            }}
            className="inline-flex items-center gap-1 mx-1 px-1.5 py-0.5 rounded text-[11px] font-mono-tabular bg-[var(--loom-verified)]/15 border border-[var(--loom-verified)]/40 text-[var(--loom-verified)] hover:bg-[var(--loom-verified)]/30 transition-colors"
            title={`Click to inspect evidence on page ${citation?.page_number || 1}`}
          >
            <span>cite:{obsId.slice(0, 6)}...</span>
            <ArrowSquareOut size={11} />
          </button>
        );
      }
      return <span key={i}>{part}</span>;
    });
  }

  return (
    <div className="py-8 px-6 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <span className="font-mono-tabular text-xs uppercase tracking-widest text-[var(--loom-verified)] bg-[var(--loom-verified)]/10 px-2 py-0.5 rounded border border-[var(--loom-verified)]/20">
            Query Engine
          </span>
          <span className="text-[var(--loom-thread)] text-xs">•</span>
          <span className="font-body text-xs text-[var(--loom-thread)]">
            Grounded Citations with Zero Hallucination Guarantee
          </span>
        </div>
        <h1 className="font-display text-3xl font-black text-[var(--loom-paper)]">
          Audit & Ask
        </h1>
        <p className="font-body text-xs text-[var(--loom-thread)] mt-1">
          Ask questions against the reconciled fact graph. Every single claim is grounded by clickable citation tokens tied to physical bounding boxes.
        </p>
      </div>

      {/* Preset Demo Questions */}
      <div className="space-y-2">
        <span className="text-[10px] font-mono-tabular uppercase tracking-wider text-[var(--loom-thread)]">
          Scripted Demo Questions:
        </span>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
          {demoQueries.map((dq, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(dq.q);
                handleAsk(dq.q);
              }}
              className="p-3 text-left rounded bg-[var(--loom-card)]/70 border border-[var(--loom-card-border)] hover:border-[var(--loom-hairline)] hover:bg-[var(--loom-surface)] transition-all group"
            >
              <div className="flex items-center justify-between text-[11px] font-medium text-[var(--loom-verified)]">
                <span>{dq.label}</span>
                <Sparkle size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div className="font-body text-xs text-[var(--loom-paper)] mt-1 truncate">
                "{dq.q}"
              </div>
              <div className="text-[10px] font-mono-tabular text-[var(--loom-thread)] mt-0.5">
                {dq.desc}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Query Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleAsk(query);
        }}
        className="relative"
      >
        <div className="relative flex items-center">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question across filings (e.g. What was Delhivery's FY24 EBITDA?)"
            className="w-full bg-[var(--loom-card)] border border-[var(--loom-card-border)] rounded-lg py-3.5 pl-4 pr-12 text-sm text-[var(--loom-paper)] placeholder:text-[var(--loom-thread)]/60 focus:outline-none focus:border-[var(--loom-verified)] shadow-lg font-body"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-2 p-2 rounded bg-[var(--loom-verified)] text-[var(--loom-ink)] disabled:opacity-30 hover:bg-[var(--loom-verified)]/90 transition-all shadow"
          >
            <PaperPlaneTilt size={16} weight="bold" />
          </button>
        </div>
      </form>

      {/* Loading state */}
      {loading && (
        <div className="guilloche-card rounded-lg p-8 text-center space-y-3 border border-[var(--loom-card-border)]">
          <div className="font-mono-tabular text-xs text-[var(--loom-verified)] animate-pulse">
            Retrieving facts, traversing reconciliation graph, and validating citation tokens...
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-4 rounded bg-[var(--loom-contradiction)]/10 border border-[var(--loom-contradiction)]/30 text-xs text-[var(--loom-contradiction)] font-mono-tabular">
          Error: {error}
        </div>
      )}

      {/* Answer Response Container */}
      {response && !loading && (
        <div className="space-y-6">
          {/* Ambiguity Handling */}
          {response.is_ambiguous ? (
            <AmbiguousResultSet
              facts={response.facts_retrieved}
              observations={response.observations_cited}
              question={response.question}
            />
          ) : null}

          {/* Synthesized Answer Box */}
          <div className="guilloche-card rounded-lg p-6 border border-[var(--loom-card-border)] space-y-4 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--loom-card-border)]">
              <div className="flex items-center gap-2">
                <CheckCircle size={16} className="text-[var(--loom-verified)]" weight="fill" />
                <span className="font-mono-tabular text-xs font-semibold text-[var(--loom-verified)] uppercase tracking-wider">
                  Grounded Synthesis
                </span>
              </div>
              <span className="font-mono-tabular text-[10px] text-[var(--loom-thread)]">
                {response.citations?.length || 0} Grounded Citation Tokens
              </span>
            </div>

            <div className="font-body text-sm text-[var(--loom-paper)] leading-relaxed space-y-3">
              <p>{renderFormattedAnswer(response.answer, response.citations)}</p>
            </div>

            {/* Cited Observations Strip */}
            {response.citations && response.citations.length > 0 && (
              <div className="pt-4 border-t border-[var(--loom-card-border)]/50 space-y-2">
                <span className="font-mono-tabular text-[10px] uppercase text-[var(--loom-thread)] block">
                  Click Citation To Inspect Source Document Bbox:
                </span>
                <div className="flex flex-wrap gap-2">
                  {response.citations.map((c, i) => (
                    <button
                      key={i}
                      onClick={() =>
                        openEvidence({
                          documentId: c.document_id || '',
                          documentFilename: c.document_filename,
                          pageNumber: c.page_number || 1,
                          bbox: c.bbox,
                          quoteSpan: c.quote_span,
                          value: c.value,
                          unit: c.unit,
                        })
                      }
                      className="text-left p-2 rounded bg-[var(--loom-ink)] border border-[var(--loom-card-border)] hover:border-[var(--loom-verified)] text-[11px] transition-all"
                    >
                      <div className="flex items-center gap-1.5 font-mono-tabular text-[10px] text-[var(--loom-verified)]">
                        <span>{c.token}</span>
                        <span>• p. {c.page_number}</span>
                      </div>
                      <div className="text-[10px] text-[var(--loom-paper)] font-bold truncate max-w-[200px]">
                        {c.value} {c.unit || ''}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
