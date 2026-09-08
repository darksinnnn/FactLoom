import React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';

interface FrayViewProps {
  dimension?: string;
  className?: string;
}

export const FrayView: React.FC<FrayViewProps> = ({ dimension = 'UNKNOWN', className = '' }) => {
  const isReducedMotion = useReducedMotion();

  return (
    <div className={`relative flex flex-col items-center justify-center my-4 ${className}`}>
      <svg
        width="100%"
        height="90"
        viewBox="0 0 500 90"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible select-none"
      >
        {/* Warning ambient halo */}
        <radialGradient id="frayGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#F5A623" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#F5A623" stopOpacity="0" />
        </radialGradient>
        <circle cx="250" cy="45" r="40" fill="url(#frayGlow)" />

        {/* Thread A from Left - approaches center then recoils upwards and splits */}
        <motion.path
          d="M 20 25 C 100 25, 160 30, 210 32 C 220 30, 230 18, 245 12"
          stroke="var(--loom-unresolved)"
          strokeWidth="3.5"
          strokeLinecap="round"
          initial={isReducedMotion ? undefined : { pathLength: 0.2 }}
          animate={isReducedMotion ? undefined : { pathLength: 1 }}
          transition={{ duration: 1 }}
        />
        {/* Frayed wisps of Thread A */}
        <path d="M 215 31 C 225 26, 235 24, 250 22" stroke="var(--loom-unresolved)" strokeWidth="1.5" strokeDasharray="2 2" />
        <path d="M 210 32 C 222 34, 232 30, 242 27" stroke="var(--loom-unresolved)" strokeWidth="1.2" />

        {/* Thread B from Right - approaches center then recoils downwards and splits */}
        <motion.path
          d="M 480 65 C 400 65, 340 60, 290 58 C 280 60, 270 72, 255 78"
          stroke="var(--loom-contradiction)"
          strokeWidth="3.5"
          strokeLinecap="round"
          initial={isReducedMotion ? undefined : { pathLength: 0.2 }}
          animate={isReducedMotion ? undefined : { pathLength: 1 }}
          transition={{ duration: 1, delay: 0.1 }}
        />
        {/* Frayed wisps of Thread B */}
        <path d="M 285 59 C 275 64, 265 66, 250 68" stroke="var(--loom-contradiction)" strokeWidth="1.5" strokeDasharray="2 2" />
        <path d="M 290 58 C 278 56, 268 60, 258 63" stroke="var(--loom-contradiction)" strokeWidth="1.2" />

        {/* The Visible Gap: Center space deliberately open, zero connection */}
        <line x1="245" y1="12" x2="255" y2="78" stroke="transparent" />
      </svg>

      {/* Abstention / Unresolved Badge in the Center Gap */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[var(--loom-card)]/95 backdrop-blur-md px-3 py-1 rounded border border-[var(--loom-unresolved)]/50 shadow-md flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--loom-unresolved)] animate-pulse" />
        <span className="font-mono-tabular text-[10px] uppercase tracking-widest text-[var(--loom-unresolved)] font-bold">
          FRAYED • UNRESOLVED ABSTENTION {dimension ? `(${dimension})` : ''}
        </span>
      </div>
    </div>
  );
};
