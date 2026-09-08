import React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';

interface KnotViewProps {
  dimension?: string;
  className?: string;
}

export const KnotView: React.FC<KnotViewProps> = ({ dimension = 'REPORTING_VINTAGE', className = '' }) => {
  const isReducedMotion = useReducedMotion();

  return (
    <div className={`relative flex flex-col items-center justify-center my-4 ${className}`}>
      <svg
        width="100%"
        height="85"
        viewBox="0 0 500 85"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible select-none"
      >
        {/* Thread from T1 (Left) entering into loop */}
        <motion.path
          d="M 20 42 L 180 42 C 210 42, 230 15, 250 15 C 270 15, 280 42, 260 65 C 240 80, 220 55, 250 42 L 480 42"
          stroke="var(--loom-verified)"
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={isReducedMotion ? undefined : { pathLength: 0.2 }}
          animate={isReducedMotion ? undefined : { pathLength: 1 }}
          transition={{ duration: 1.2, ease: 'easeInOut' }}
        />

        {/* The Overhand Knot Loop Stitches */}
        <circle cx="250" cy="42" r="16" stroke="var(--loom-paper)" strokeWidth="2" strokeDasharray="3 3" />
        <line x1="240" y1="36" x2="260" y2="48" stroke="var(--loom-ink)" strokeWidth="3" />

        {/* Directional transition arrows on thread */}
        <path d="M 120 38 L 126 42 L 120 46" fill="var(--loom-verified)" />
        <path d="M 380 38 L 386 42 L 380 46" fill="var(--loom-verified)" />
      </svg>

      {/* Knot Label */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[var(--loom-card)]/90 backdrop-blur-md px-3 py-1 rounded border border-[var(--loom-verified)]/40 shadow-md">
        <span className="font-mono-tabular text-[10px] uppercase tracking-widest text-[var(--loom-verified)] font-bold">
          TEMPORAL KNOT • SUPERSEDES ({dimension})
        </span>
      </div>
    </div>
  );
};
