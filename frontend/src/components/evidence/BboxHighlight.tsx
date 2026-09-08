import React from 'react';
import { motion } from 'framer-motion';

interface BboxHighlightProps {
  bbox: number[]; // [x0, y0, x1, y1] in PDF user points
  pageWidth: number;
  pageHeight: number;
  quoteSpan?: string | null;
  value?: string | null;
  unit?: string | null;
}

export const BboxHighlight: React.FC<BboxHighlightProps> = ({
  bbox,
  pageWidth,
  pageHeight,
  quoteSpan,
  value,
  unit,
}) => {
  if (!bbox || bbox.length < 4 || pageWidth <= 0 || pageHeight <= 0) return null;

  const [x0, y0, x1, y1] = bbox;

  // Percentage positioning matching the natural PDF coordinate space
  const leftPct = (x0 / pageWidth) * 100;
  const topPct = (y0 / pageHeight) * 100;
  const widthPct = ((x1 - x0) / pageWidth) * 100;
  const heightPct = ((y1 - y0) / pageHeight) * 100;

  return (
    <motion.div
      initial={{ scale: 1.15, opacity: 0.3 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.8, ease: 'easeOut' }}
      style={{
        left: `${leftPct}%`,
        top: `${topPct}%`,
        width: `${widthPct}%`,
        height: `${heightPct}%`,
      }}
      className="absolute pointer-events-auto cursor-pointer group z-20"
    >
      {/* Hairline security-print highlight outline (not flat yellow marker) */}
      <div className="w-full h-full border-2 border-[var(--loom-verified)] bg-[var(--loom-verified)]/15 rounded-sm shadow-[0_0_12px_rgba(52,211,153,0.35)] relative">
        {/* Subtle corner indicator dots */}
        <div className="absolute -top-1 -left-1 w-2 h-2 bg-[var(--loom-verified)] rounded-full" />
        <div className="absolute -top-1 -right-1 w-2 h-2 bg-[var(--loom-verified)] rounded-full" />
        <div className="absolute -bottom-1 -left-1 w-2 h-2 bg-[var(--loom-verified)] rounded-full" />
        <div className="absolute -bottom-1 -right-1 w-2 h-2 bg-[var(--loom-verified)] rounded-full" />
      </div>

      {/* Floating Grounding Provenance Tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-30 min-w-[240px] max-w-sm bg-[var(--loom-card)]/95 backdrop-blur-md border border-[var(--loom-verified)]/40 p-3 rounded-md shadow-2xl text-xs">
        <div className="font-mono-tabular text-[10px] text-[var(--loom-verified)] uppercase tracking-wider font-bold mb-1 flex items-center justify-between">
          <span>Grounded Evidence Quote</span>
          {value && (
            <span className="text-[var(--loom-paper)]">
              {value} {unit || ''}
            </span>
          )}
        </div>
        {quoteSpan && (
          <p className="font-body text-[var(--loom-paper)] text-[11px] leading-relaxed italic">
            "{quoteSpan}"
          </p>
        )}
        <div className="font-mono-tabular text-[9px] text-[var(--loom-thread)] mt-1 pt-1 border-t border-[var(--loom-card-border)]">
          Coords: [{bbox.map((n) => Math.round(n)).join(', ')}]
        </div>
      </div>
    </motion.div>
  );
};
