import { useState, useRef } from 'react';
import { uploadDocumentFile } from '../../lib/api';
import { UploadSimple, CheckCircle, Warning } from '@phosphor-icons/react';

export const UploadZone: React.FC = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ document_id: string; pages_parsed: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(selectedFile: File) {
    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Only digitally authored or scanned PDF documents are supported.');
      return;
    }
    setFile(selectedFile);
    setError(null);
    setResult(null);
    setUploading(true);

    try {
      const res = await uploadDocumentFile(selectedFile);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to parse and ingest PDF document.');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="py-10 px-6 max-w-3xl mx-auto space-y-6">
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <span className="font-mono-tabular text-xs uppercase tracking-widest text-[var(--loom-verified)] bg-[var(--loom-verified)]/10 px-2 py-0.5 rounded border border-[var(--loom-verified)]/20">
            Document Ingestion
          </span>
          <span className="text-[var(--loom-thread)] text-xs">•</span>
          <span className="font-body text-xs text-[var(--loom-thread)]">
            Open-Schema PDF Stream Parser
          </span>
        </div>
        <h1 className="font-display text-3xl font-black text-[var(--loom-paper)]">
          Ingest & Extract Facts
        </h1>
        <p className="font-body text-xs text-[var(--loom-thread)] mt-1">
          Upload any digital financial report, earnings presentation, or statistical bulletin. The parser extracts layout blocks and physical bboxes directly into the ingestion store.
        </p>
      </div>

      {/* Drag Drop Area */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
          }
        }}
        onClick={() => inputRef.current?.click()}
        className={`guilloche-card rounded-xl p-12 text-center cursor-pointer transition-all border-2 border-dashed ${
          isDragging
            ? 'border-[var(--loom-verified)] bg-[var(--loom-surface)] shadow-2xl scale-[1.01]'
            : 'border-[var(--loom-card-border)] hover:border-[var(--loom-hairline)]'
        }`}
      >
        <input
          type="file"
          ref={inputRef}
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFile(e.target.files[0]);
            }
          }}
        />

        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-14 h-14 rounded-full bg-[var(--loom-surface)] border border-[var(--loom-card-border)] flex items-center justify-center text-[var(--loom-verified)]">
            <UploadSimple size={28} />
          </div>
          <div className="space-y-1">
            <p className="font-body font-semibold text-sm text-[var(--loom-paper)]">
              Click to browse or drag and drop PDF file here
            </p>
            <p className="font-mono-tabular text-xs text-[var(--loom-thread)]">
              PDF with native text layer or scanned documents
            </p>
          </div>
        </div>
      </div>

      {/* Upload Progress / Status */}
      {uploading && (
        <div className="bg-[var(--loom-card)] p-4 rounded-lg border border-[var(--loom-card-border)] flex items-center gap-3">
          <div className="w-4 h-4 rounded-full border-2 border-[var(--loom-verified)] border-t-transparent animate-spin" />
          <span className="font-mono-tabular text-xs text-[var(--loom-paper)]">
            Parsing pages and generating bounding boxes for {file?.name}...
          </span>
        </div>
      )}

      {/* Success Result */}
      {result && (
        <div className="bg-[var(--loom-verified)]/10 border border-[var(--loom-verified)]/30 rounded-lg p-5 flex items-start gap-3">
          <CheckCircle size={22} className="text-[var(--loom-verified)] shrink-0" weight="fill" />
          <div className="space-y-1">
            <h4 className="font-body font-bold text-xs uppercase tracking-wider text-[var(--loom-verified)]">
              Ingestion Succeeded
            </h4>
            <p className="font-mono-tabular text-xs text-[var(--loom-paper)]">
              Parsed {result.pages_parsed} pages with block-level bounding boxes.
            </p>
            <p className="font-mono-tabular text-[11px] text-[var(--loom-thread)]">
              Doc ID: {result.document_id}
            </p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="bg-[var(--loom-contradiction)]/10 border border-[var(--loom-contradiction)]/30 rounded-lg p-4 flex items-center gap-3 text-xs text-[var(--loom-contradiction)] font-mono-tabular">
          <Warning size={18} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};
