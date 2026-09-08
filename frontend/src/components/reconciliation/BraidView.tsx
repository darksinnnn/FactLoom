import React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';

interface BraidViewProps {
  dimension: string;
  className?: string;
}

export const BraidView: React.FC<BraidViewProps> = ({ dimension, className = '' }) => {
  const isReducedMotion = useReducedMotion();

  return (
    <div className={`relative flex flex-col items-center justify-center my-4 ${className}`}>
      <svg
        width="100%"
        height="80"
        viewBox="0 0 500 80"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible select-none"
      >
        {/* Background glow for the braid unification */}
        <radialGradient id="braidGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#34D399" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#34D399" stopOpacity="0" />
        </radialGradient>
        <circle cx="250" cy="40" r="36" fill="url(#braidGlow)" />

        {/* Thread A (from Observation A on Left, entering at y=20) */}
        <motion.path
          d="M 20 20 C 120 20, 180 60, 250 40 C 320 20, 380 40, 480 40"
          stroke="var(--loom-verified)"
          strokeWidth="3.5"
          strokeLinecap="round"
          initial={isReducedMotion ? undefined : { pathLength: 0.2, opacity: 0.7 }}
          animate={isReducedMotion ? undefined : { pathLength: 1, opacity: 1 }}
          transition={{ duration: 1.2, ease: 'easeInOut' }}
        />

        {/* Thread B (from Observation B on Right/Left entering at y=60) */}
        <motion.path
          d="M 20 60 C 120 60, 180 20, 250 40 C 320 60, 380 40, 480 40"
          stroke="var(--loom-paper)"
          strokeWidth="3.5"
          strokeLinecap="round"
          initial={isReducedMotion ? undefined : { pathLength: 0.2, opacity: 0.7 }}
          animate={isReducedMotion ? undefined : { pathLength: 1, opacity: 1 }}
          transition={{ duration: 1.2, ease: 'easeInOut', delay: 0.1 }}
        />

        {/* Braided Cord Center Wrap Lines (Hairline Security Print Weave) */}
        <line x1="240" y1="32" x2="246" y2="48" stroke="var(--loom-ink)" strokeWidth="2.5" />
        <line x1="250" y1="32" x2="256" y2="48" stroke="var(--loom-ink)" strokeWidth="2.5" />
        <line x1="260" y1="32" x2="266" y2="48" stroke="var(--loom-ink)" strokeWidth="2.5" />

        {/* Consolidated Output Cord (Continuing unified to the right) */}
        <line
          x1="265"
          y1="40"
          x2="480"
          y2="40"
          stroke="var(--loom-verified)"
          strokeWidth="4.5"
          strokeLinecap="round"
        />
      </svg>

      {/* Dimension Label Badge Centered on Braid */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[var(--loom-card)]/90 backdrop-blur-md px-3 py-1 rounded border border-[var(--loom-verified)]/40 shadow-md">
        <span className="font-mono-tabular text-[10px] uppercase tracking-widest text-[var(--loom-verified)] font-bold">
          BRAIDED • {dimension || 'CORROBORATED'}
        </span>
      </div>
    </div>
  );
};
