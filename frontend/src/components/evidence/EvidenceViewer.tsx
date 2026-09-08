import { useEffect, useState, useRef } from 'react';
import { useFactLoomStore } from '../../store/factsStore';
import { fetchDocuments, type DocumentInfo } from '../../lib/api';
import { BboxHighlight } from './BboxHighlight';
import {
  CaretLeft,
  CaretRight,
  MagnifyingGlassPlus,
  MagnifyingGlassMinus,
  CheckCircle,
  ArrowsInSimple,
  ArrowsOutLineHorizontal,
  FileText,
  SpinnerGap
} from '@phosphor-icons/react';

interface PageMetadata {
  page_number: number;
  width: number;
  height: number;
  text_blocks: any[];
}

type ViewMode = 'fit-page' | 'fit-width' | 'manual';

export const EvidenceViewer: React.FC = () => {
  const { evidenceTarget, evidenceTargetVersion } = useFactLoomStore();
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [pageInput, setPageInput] = useState<string>('1');
  const [pageMeta, setPageMeta] = useState<PageMetadata | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('fit-page');
  const [zoomScale, setZoomScale] = useState<number>(1.0);
  const [imageLoading, setImageLoading] = useState<boolean>(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const [containerSize, setContainerSize] = useState<{ width: number; height: number }>({
    width: 800,
    height: 600,
  });

  // Observe container dimensions for dynamic responsive fitting
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const updateSize = () => {
      if (el.clientWidth > 0 && el.clientHeight > 0) {
        setContainerSize({ width: el.clientWidth, height: el.clientHeight });
      }
    };

    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Sync pageInput with pageNumber
  useEffect(() => {
    setPageInput(String(pageNumber));
  }, [pageNumber]);

  // Load documents list once on mount — NOT on evidenceTarget changes
  useEffect(() => {
    async function loadDocs() {
      try {
        const docs = await fetchDocuments();
        setDocuments(docs);
        // Set default document if no target yet
        if (!evidenceTarget?.documentId && docs.length > 0) {
          setSelectedDocId(docs[0].id);
        }
      } catch (err) {
        console.error('Failed to load documents:', err);
      }
    }
    loadDocs();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Navigate to citation target — fires every time a new citation is clicked
  // Uses evidenceTargetVersion as key so same page/doc still triggers update
  useEffect(() => {
    const currentTarget = evidenceTarget;
    if (!currentTarget) return;

    async function applyTarget(tgt: NonNullable<typeof evidenceTarget>) {
      // Always fetch fresh document list so we can resolve even newly-uploaded docs
      let docList = documents;
      if (docList.length === 0) {
        try {
          docList = await fetchDocuments();
          setDocuments(docList);
        } catch {
          /* ignore */
        }
      }

      // Match doc by id first, then by filename
      const match = docList.find(
        (d) => d.id === tgt.documentId || d.filename === tgt.documentFilename
      );

      if (match) {
        setSelectedDocId(match.id);
      } else if (tgt.documentId) {
        // documentId not yet in list (possible if docs loaded before upload finished)
        setSelectedDocId(tgt.documentId);
      }

      // Unconditionally apply page — no stale-value guard
      if (tgt.pageNumber && tgt.pageNumber >= 1) {
        setPageNumber(tgt.pageNumber);
        setPageInput(String(tgt.pageNumber));
      }
    }

    applyTarget(currentTarget);
  // evidenceTargetVersion increments on every openEvidence() call
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [evidenceTargetVersion]);

  // Load page metadata
  useEffect(() => {
    if (!selectedDocId) return;

    async function loadPage() {
      try {
        setImageLoading(true);
        const res = await fetch(`/api/documents/${selectedDocId}/pages/${pageNumber}`);
        if (res.ok) {
          const data = await res.json();
          setPageMeta(data);
        }
      } catch (err) {
        console.error('Failed to load page meta:', err);
      } finally {
        setImageLoading(false);
      }
    }
    loadPage();
  }, [selectedDocId, pageNumber]);

  const activeDoc = documents.find((d) => d.id === selectedDocId);
  const totalPages = activeDoc?.page_count || 1;

  const handleJumpToPage = (newPage: number) => {
    const clamped = Math.max(1, Math.min(totalPages, Math.floor(newPage)));
    setPageNumber(clamped);
    setPageInput(String(clamped));
  };

  const handleInputCommit = () => {
    const parsed = parseInt(pageInput.trim(), 10);
    if (!isNaN(parsed)) {
      handleJumpToPage(parsed);
    } else {
      setPageInput(String(pageNumber));
    }
  };

  // Keyboard navigation within the viewer
  const handleViewerKeyDown = (e: React.KeyboardEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
      return;
    }
    if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
      e.preventDefault();
      handleJumpToPage(pageNumber - 1);
    } else if (e.key === 'ArrowRight' || e.key === 'PageDown') {
      e.preventDefault();
      handleJumpToPage(pageNumber + 1);
    }
  };

  // Calculation of display dimensions
  const pageNativeWidth = pageMeta?.width || 612;
  const pageNativeHeight = pageMeta?.height || 792;
  const aspectRatio = pageNativeWidth / pageNativeHeight;

  const padding = 32; // Comfortable margin inside viewport
  const availW = Math.max(160, containerSize.width - padding);
  const availH = Math.max(160, containerSize.height - padding);

  let displayWidth: number;
  let displayHeight: number;

  if (viewMode === 'fit-page') {
    const scaleW = availW / pageNativeWidth;
    const scaleH = availH / pageNativeHeight;
    const fitScale = Math.min(scaleW, scaleH);
    displayWidth = Math.round(pageNativeWidth * fitScale);
    displayHeight = Math.round(pageNativeHeight * fitScale);
  } else if (viewMode === 'fit-width') {
    displayWidth = Math.round(availW);
    displayHeight = Math.round(availW / aspectRatio);
  } else {
    // Manual zoom mode
    const baseWidth = Math.min(availW, pageNativeWidth * 1.2);
    displayWidth = Math.round(baseWidth * zoomScale);
    displayHeight = Math.round(displayWidth / aspectRatio);
  }

  const effectivePercent = Math.round((displayWidth / pageNativeWidth) * 100);

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
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Document Dropdown */}
          <select
            value={selectedDocId}
            onChange={(e) => {
              setSelectedDocId(e.target.value);
              setPageNumber(1);
            }}
            className="bg-[var(--loom-surface)] border border-[var(--loom-card-border)] text-xs text-[var(--loom-paper)] px-3 py-2 rounded-md focus:outline-none focus:border-[var(--loom-verified)] max-w-xs font-mono-tabular truncate shadow-sm"
          >
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename} ({d.page_count}p)
              </option>
            ))}
          </select>

          {/* Typeable Page Navigation */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleInputCommit();
            }}
            className="flex items-center gap-1 bg-[var(--loom-surface)] border border-[var(--loom-card-border)] rounded-md px-1.5 py-1 shadow-sm focus-within:border-[var(--loom-verified)] transition-colors"
          >
            <button
              type="button"
              onClick={() => handleJumpToPage(pageNumber - 1)}
              disabled={pageNumber <= 1}
              className="p-1 rounded text-[var(--loom-thread)] hover:text-[var(--loom-paper)] hover:bg-[var(--loom-card)] disabled:opacity-25 disabled:hover:bg-transparent transition-colors cursor-pointer disabled:cursor-not-allowed"
              title="Previous Page (←)"
            >
              <CaretLeft size={16} weight="bold" />
            </button>

            <span className="font-mono-tabular text-xs text-[var(--loom-thread)] pl-1 select-none">
              p.
            </span>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              onFocus={(e) => e.target.select()}
              onBlur={handleInputCommit}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.currentTarget.blur();
                }
              }}
              className="w-12 text-center bg-[var(--loom-ink)] border border-[var(--loom-card-border)] rounded px-1 py-0.5 text-xs font-mono-tabular text-[var(--loom-paper)] font-bold focus:outline-none focus:border-[var(--loom-verified)] focus:ring-1 focus:ring-[var(--loom-verified)] transition-all"
              title="Type page number and press Enter to jump directly"
            />
            <span className="font-mono-tabular text-xs text-[var(--loom-thread)] pr-1 select-none">
              / {totalPages}
            </span>

            <button
              type="button"
              onClick={() => handleJumpToPage(pageNumber + 1)}
              disabled={pageNumber >= totalPages}
              className="p-1 rounded text-[var(--loom-thread)] hover:text-[var(--loom-paper)] hover:bg-[var(--loom-card)] disabled:opacity-25 disabled:hover:bg-transparent transition-colors cursor-pointer disabled:cursor-not-allowed"
              title="Next Page (→)"
            >
              <CaretRight size={16} weight="bold" />
            </button>
          </form>

          {/* View Modes & Zoom Controls */}
          <div className="flex items-center gap-1 bg-[var(--loom-surface)] border border-[var(--loom-card-border)] rounded-md px-1.5 py-1 shadow-sm">
            {/* Fit Page Button */}
            <button
              type="button"
              onClick={() => setViewMode('fit-page')}
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-mono-tabular transition-colors cursor-pointer ${
                viewMode === 'fit-page'
                  ? 'bg-[var(--loom-verified)]/15 text-[var(--loom-verified)] border border-[var(--loom-verified)]/40 font-semibold'
                  : 'text-[var(--loom-thread)] hover:text-[var(--loom-paper)] hover:bg-[var(--loom-card)]'
              }`}
              title="Fit Entire Page in View (Single Page)"
            >
              <ArrowsInSimple size={14} weight="bold" />
              <span className="hidden sm:inline">Fit Page</span>
            </button>

            {/* Fit Width Button */}
            <button
              type="button"
              onClick={() => setViewMode('fit-width')}
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-mono-tabular transition-colors cursor-pointer ${
                viewMode === 'fit-width'
                  ? 'bg-[var(--loom-verified)]/15 text-[var(--loom-verified)] border border-[var(--loom-verified)]/40 font-semibold'
                  : 'text-[var(--loom-thread)] hover:text-[var(--loom-paper)] hover:bg-[var(--loom-card)]'
              }`}
              title="Fit Page Width (Scrollable)"
            >
              <ArrowsOutLineHorizontal size={14} weight="bold" />
              <span className="hidden sm:inline">Fit Width</span>
            </button>

            <div className="h-4 w-px bg-[var(--loom-card-border)] mx-1" />

            {/* Zoom Out */}
            <button
              type="button"
              onClick={() => {
                const currentRatio = displayWidth / Math.min(availW, pageNativeWidth * 1.2);
                setViewMode('manual');
                setZoomScale(Math.max(0.4, Number((currentRatio - 0.15).toFixed(2))));
              }}
              className="p-1 rounded text-[var(--loom-thread)] hover:text-[var(--loom-paper)] hover:bg-[var(--loom-card)] transition-colors cursor-pointer"
              title="Zoom Out"
            >
              <MagnifyingGlassMinus size={15} />
            </button>

            <span
              className="font-mono-tabular text-xs text-[var(--loom-paper)] px-1.5 min-w-[42px] text-center select-none"
              title="Effective zoom scale"
            >
              {effectivePercent}%
            </span>

            {/* Zoom In */}
            <button
              type="button"
              onClick={() => {
                const currentRatio = displayWidth / Math.min(availW, pageNativeWidth * 1.2);
                setViewMode('manual');
                setZoomScale(Math.min(2.5, Number((currentRatio + 0.15).toFixed(2))));
              }}
              className="p-1 rounded text-[var(--loom-thread)] hover:text-[var(--loom-paper)] hover:bg-[var(--loom-card)] transition-colors cursor-pointer"
              title="Zoom In"
            >
              <MagnifyingGlassPlus size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Evidence Inspection Canvas */}
      <div className="grid lg:grid-cols-4 gap-6 items-start">
        {/* Document Page Canvas Viewport */}
        <div
          ref={containerRef}
          onKeyDown={handleViewerKeyDown}
          tabIndex={0}
          data-lenis-prevent
          className="lg:col-span-3 bg-[var(--loom-card)]/50 border border-[var(--loom-card-border)] rounded-lg overflow-auto shadow-2xl h-[calc(100vh-13.5rem)] min-h-[520px] max-h-[85vh] focus:outline-none focus:ring-1 focus:ring-[var(--loom-verified)]/40 relative scrollable-pane overscroll-contain"
          title="Document Viewer Canvas (Use arrow keys to navigate pages)"
        >
          {selectedDocId ? (
            <div className="min-w-full min-h-full flex p-4">
              <div
                style={{
                  width: `${displayWidth}px`,
                  height: `${displayHeight}px`,
                }}
                className="m-auto relative bg-white shadow-2xl rounded-sm flex-shrink-0 transition-[width,height] duration-150 ease-out border border-black/15"
              >
                {/* Rendered PDF Page Image */}
                <img
                  src={`/api/documents/${selectedDocId}/pages/${pageNumber}/image`}
                  alt={`Page ${pageNumber}`}
                  className="w-full h-full block select-none object-contain pointer-events-none"
                  loading="eager"
                  onLoad={() => setImageLoading(false)}
                />

                {/* Loading indicator overlay */}
                {imageLoading && (
                  <div className="absolute inset-0 bg-black/10 backdrop-blur-[1px] flex items-center justify-center pointer-events-none">
                    <SpinnerGap size={32} className="text-[var(--loom-verified)] animate-spin" />
                  </div>
                )}

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
            </div>
          ) : (
            <div className="h-full min-h-[350px] flex flex-col items-center justify-center gap-3 text-[var(--loom-thread)]">
              <FileText size={48} weight="duotone" className="opacity-40" />
              <span className="font-mono-tabular text-sm">Select a document to inspect pages</span>
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
            <div className="text-[11px] text-[var(--loom-thread)] pt-1 border-t border-[var(--loom-card-border)]/60 flex items-center justify-between">
              <span>View Mode:</span>
              <span className="text-[var(--loom-verified)] capitalize">
                {viewMode === 'fit-page' ? 'Fit Page' : viewMode === 'fit-width' ? 'Fit Width' : 'Manual'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
