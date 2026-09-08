import { useEffect, useState } from 'react';
import { useFactLoomStore } from '../../store/factsStore';
import { fetchDocuments, type DocumentInfo } from '../../lib/api';
import { BboxHighlight } from './BboxHighlight';
import { CaretLeft, CaretRight, MagnifyingGlassPlus, MagnifyingGlassMinus, CheckCircle } from '@phosphor-icons/react';

interface PageMetadata {
  page_number: number;
  width: number;
  height: number;
  text_blocks: any[];
}

export const EvidenceViewer: React.FC = () => {
  const { evidenceTarget } = useFactLoomStore();
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [pageMeta, setPageMeta] = useState<PageMetadata | null>(null);
  const [zoomScale, setZoomScale] = useState<number>(1.0);

  // Load documents list
  useEffect(() => {
    async function loadDocs() {
      try {
        const docs = await fetchDocuments();
        setDocuments(docs);
        if (evidenceTarget?.documentId) {
          // Find matching document by ID or filename
          const match = docs.find(
            (d) => d.id === evidenceTarget.documentId || d.filename === evidenceTarget.documentFilename
          );
          if (match) {
            setSelectedDocId(match.id);
          } else if (docs.length > 0) {
            setSelectedDocId(docs[0].id);
          }
          if (evidenceTarget.pageNumber) {
            setPageNumber(evidenceTarget.pageNumber);
          }
        } else if (docs.length > 0) {
          setSelectedDocId(docs[0].id);
        }
      } catch (err) {
        console.error('Failed to load documents:', err);
      }
    }
    loadDocs();
  }, [evidenceTarget]);

  // Load page metadata
  useEffect(() => {
    if (!selectedDocId) return;

    async function loadPage() {
      try {
        const res = await fetch(`/api/documents/${selectedDocId}/pages/${pageNumber}`);
        if (res.ok) {
          const data = await res.json();
          setPageMeta(data);
        }
      } catch (err) {
        console.error('Failed to load page meta:', err);
      }
    }
    loadPage();
  }, [selectedDocId, pageNumber]);

  const activeDoc = documents.find((d) => d.id === selectedDocId);

  // If evidenceTarget specifies a bbox and matches current page, render highlight
  const showBbox =
    evidenceTarget?.bbox &&
    (!evidenceTarget.pageNumber || evidenceTarget.pageNumber === pageNumber);

  return (
    <div className="py-8 px-6 max-w-7xl mx-auto space-y-6">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--loom-card-border)] pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="font-mono-tabular text-xs uppercase tracking-widest text-[var(--loom-verified)] bg-[var(--loom-verified)]/10 px-2 py-0.5 rounded border border-[var(--loom-verified)]/20">
              Evidence Viewer
            </span>
            <span className="text-[var(--loom-thread)] text-xs">•</span>
            <span className="font-body text-xs text-[var(--loom-thread)]">
              Physical Bounding Box Grounding Overlay
            </span>
          </div>
          <h1 className="font-display text-2xl md:text-3xl font-black text-[var(--loom-paper)]">
            Primary Document Inspector
          </h1>
        </div>

        {/* Document Selector & Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedDocId}
            onChange={(e) => {
              setSelectedDocId(e.target.value);
              setPageNumber(1);
            }}
            className="bg-[var(--loom-surface)] border border-[var(--loom-card-border)] text-xs text-[var(--loom-paper)] px-3 py-2 rounded focus:outline-none focus:border-[var(--loom-verified)] max-w-xs font-mono-tabular truncate"
          >
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename} ({d.page_count}p)
              </option>
            ))}
          </select>

          {/* Page Navigation */}
          <div className="flex items-center gap-1 bg-[var(--loom-surface)] border border-[var(--loom-card-border)] rounded px-2 py-1">
            <button
              onClick={() => setPageNumber((p) => Math.max(1, p - 1))}
              disabled={pageNumber <= 1}
              className="p-1 text-[var(--loom-thread)] hover:text-[var(--loom-paper)] disabled:opacity-30"
              title="Previous Page"
            >
              <CaretLeft size={16} />
            </button>
            <span className="font-mono-tabular text-xs text-[var(--loom-paper)] px-2">
              p. {pageNumber} / {activeDoc?.page_count || 1}
            </span>
            <button
              onClick={() => setPageNumber((p) => Math.min(activeDoc?.page_count || 100, p + 1))}
              disabled={Boolean(activeDoc && pageNumber >= activeDoc.page_count)}
              className="p-1 text-[var(--loom-thread)] hover:text-[var(--loom-paper)] disabled:opacity-30"
              title="Next Page"
            >
              <CaretRight size={16} />
            </button>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center gap-1 bg-[var(--loom-surface)] border border-[var(--loom-card-border)] rounded px-2 py-1">
            <button
              onClick={() => setZoomScale((s) => Math.max(0.6, s - 0.1))}
              className="p-1 text-[var(--loom-thread)] hover:text-[var(--loom-paper)]"
              title="Zoom Out"
            >
              <MagnifyingGlassMinus size={16} />
            </button>
            <span className="font-mono-tabular text-xs text-[var(--loom-paper)] px-1">
              {Math.round(zoomScale * 100)}%
            </span>
            <button
              onClick={() => setZoomScale((s) => Math.min(1.8, s + 0.1))}
              className="p-1 text-[var(--loom-thread)] hover:text-[var(--loom-paper)]"
              title="Zoom In"
            >
              <MagnifyingGlassPlus size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Evidence Inspection Canvas */}
      <div className="grid lg:grid-cols-4 gap-6 items-start">
        {/* Document Page Canvas Wrapper */}
        <div className="lg:col-span-3 bg-[var(--loom-card)]/50 border border-[var(--loom-card-border)] rounded-lg p-4 overflow-auto max-h-[85vh] flex justify-center items-start shadow-2xl">
          {selectedDocId ? (
            <div
              style={{ transform: `scale(${zoomScale})`, transformOrigin: 'top center' }}
              className="relative transition-transform duration-150 inline-block bg-white shadow-2xl rounded-sm"
            >
              {/* Rendered PDF Page Image */}
              <img
                src={`/api/documents/${selectedDocId}/pages/${pageNumber}/image`}
                alt={`Page ${pageNumber}`}
                className="max-w-none block select-none"
                style={{ width: pageMeta?.width ? `${pageMeta.width * 1.5}px` : '780px' }}
                loading="eager"
              />

              {/* Bounding Box Grounding Highlight Layer */}
              {showBbox && pageMeta && (
                <BboxHighlight
                  bbox={evidenceTarget.bbox!}
                  pageWidth={pageMeta.width}
                  pageHeight={pageMeta.height}
                  quoteSpan={evidenceTarget.quoteSpan}
                  value={evidenceTarget.value}
                  unit={evidenceTarget.unit}
                />
              )}
            </div>
          ) : (
            <div className="py-24 text-center font-mono-tabular text-sm text-[var(--loom-thread)]">
              Select a document to inspect pages
            </div>
          )}
        </div>

        {/* Evidence Metadata & Grounded Quote Sidebar */}
        <div className="space-y-4">
          <div className="guilloche-card rounded-lg p-5 border border-[var(--loom-card-border)] space-y-3">
            <div className="flex items-center gap-1.5 text-xs text-[var(--loom-verified)] font-mono-tabular font-semibold uppercase">
              <CheckCircle size={16} weight="fill" />
              <span>Grounded Citation Audit</span>
            </div>

            {evidenceTarget?.quoteSpan ? (
              <div className="space-y-3">
                <div className="text-xs font-body text-[var(--loom-paper)]">
                  <div className="font-mono-tabular text-[10px] text-[var(--loom-thread)] uppercase mb-1">
                    Verbatim Source Quote:
                  </div>
                  <blockquote className="bg-[var(--loom-ink)] p-3 rounded border-l-2 border-[var(--loom-verified)] italic text-[11px] leading-relaxed text-[var(--loom-paper)]/90">
                    "{evidenceTarget.quoteSpan}"
                  </blockquote>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono-tabular">
                  <div className="bg-[var(--loom-ink)] p-2 rounded border border-[var(--loom-card-border)]">
                    <span className="text-[10px] text-[var(--loom-thread)] block">VALUE:</span>
                    <span className="font-bold text-[var(--loom-verified)]">
                      {evidenceTarget.value || '—'} {evidenceTarget.unit || ''}
                    </span>
                  </div>
                  <div className="bg-[var(--loom-ink)] p-2 rounded border border-[var(--loom-card-border)]">
                    <span className="text-[10px] text-[var(--loom-thread)] block">PAGE:</span>
                    <span className="font-bold text-[var(--loom-paper)]">p. {pageNumber}</span>
                  </div>
                </div>

                {evidenceTarget.bbox && (
                  <div className="bg-[var(--loom-ink)] p-2 rounded border border-[var(--loom-card-border)] font-mono-tabular text-[10px]">
                    <span className="text-[var(--loom-thread)] block mb-0.5">PDF BBOX (PTS):</span>
                    <span className="text-[var(--loom-paper)]/80">
                      [{evidenceTarget.bbox.map((n) => Math.round(n)).join(', ')}]
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <p className="font-body text-xs text-[var(--loom-thread)] leading-relaxed">
                Click any citation badge in the Ask panel or fact card in the Explorer to inspect the exact quote and bounding box on this page.
              </p>
            )}
          </div>

          {/* Document Properties */}
          <div className="bg-[var(--loom-card)] p-4 rounded-lg border border-[var(--loom-card-border)] text-xs font-mono-tabular space-y-2">
            <div className="text-[10px] uppercase tracking-wider text-[var(--loom-thread)] font-bold">
              Document Specs
            </div>
            <div className="truncate text-[var(--loom-paper)]" title={activeDoc?.filename}>
              {activeDoc?.filename || '—'}
            </div>
            <div className="text-[11px] text-[var(--loom-thread)]">
              Dimensions: {pageMeta?.width || 595} × {pageMeta?.height || 842} pt
            </div>
            <div className="text-[11px] text-[var(--loom-thread)]">
              Total Pages: {activeDoc?.page_count || '—'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
