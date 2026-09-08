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
        height="100"
        viewBox="0 0 500 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible select-none"
      >
        {/* Soft amber ambient warning glow centered on the unresolved gap */}
        <radialGradient id="frayGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--loom-unresolved)" stopOpacity="0.14" />
          <stop offset="60%" stopColor="var(--loom-unresolved)" stopOpacity="0.04" />
          <stop offset="100%" stopColor="var(--loom-unresolved)" stopOpacity="0" />
        </radialGradient>
        <ellipse cx="250" cy="50" rx="90" ry="45" fill="url(#frayGlow)" />

        {/* ============================================================ */}
        {/* THREAD A (Left Cord - Evidence from Document A)               */}
        {/* ============================================================ */}
        {/* Main braided trunk entering from left */}
        <motion.path
          d="M 15 35 C 75 35, 135 34, 195 35"
          stroke="var(--loom-unresolved)"
          strokeWidth="3.2"
          strokeLinecap="round"
          initial={isReducedMotion ? undefined : { pathLength: 0.1 }}
          animate={isReducedMotion ? undefined : { pathLength: 1 }}
          transition={{ duration: 0.9, ease: 'easeOut' }}
        />
        {/* Second ply of main trunk */}
        <path
          d="M 15 37 C 75 37, 135 36, 192 37"
          stroke="var(--loom-unresolved)"
          strokeWidth="1.6"
          strokeOpacity="0.7"
          strokeLinecap="round"
        />

        {/* FRAY 1: Top upward-curling fiber strand */}
        <motion.path
          d="M 195 34 C 215 26, 230 14, 246 10"
          stroke="var(--loom-unresolved)"
          strokeWidth="1.8"
          strokeLinecap="round"
          animate={isReducedMotion ? undefined : { y: [-1, 1.5, -1] }}
          transition={{ duration: 3.2, repeat: Infinity, ease: 'easeInOut' }}
        />
        {/* Micro-wisp 1b splitting off strand 1 */}
        <path
          d="M 218 25 C 228 20, 238 18, 244 19"
          stroke="var(--loom-unresolved)"
          strokeWidth="0.9"
          strokeOpacity="0.6"
          strokeDasharray="2 3"
        />

        {/* FRAY 2: Center horizontal reaching strand (tapers off before reaching center) */}
        <path
          d="M 195 35 C 212 35, 226 33, 238 30"
          stroke="var(--loom-unresolved)"
          strokeWidth="1.4"
          strokeLinecap="round"
        />

        {/* FRAY 3: Downward-curling fiber strand */}
        <motion.path
          d="M 195 36 C 216 38, 232 46, 244 54"
          stroke="var(--loom-unresolved)"
          strokeWidth="1.8"
          strokeLinecap="round"
          animate={isReducedMotion ? undefined : { y: [1, -1.5, 1] }}
          transition={{ duration: 3.8, repeat: Infinity, ease: 'easeInOut', delay: 0.3 }}
        />
        {/* Micro-wisp 3b splitting off strand 3 */}
        <path
          d="M 215 39 C 226 43, 235 48, 241 45"
          stroke="var(--loom-unresolved)"
          strokeWidth="0.9"
          strokeOpacity="0.5"
          strokeDasharray="3 3"
        />

        {/* Loose floating fiber fragment near gap */}
        <path
          d="M 234 22 C 238 20, 242 21, 245 20"
          stroke="var(--loom-unresolved)"
          strokeWidth="0.75"
          strokeOpacity="0.4"
        />

        {/* ============================================================ */}
        {/* THREAD B (Right Cord - Evidence from Document B)              */}
        {/* ============================================================ */}
        {/* Main braided trunk entering from right */}
        <motion.path
          d="M 485 55 C 425 55, 365 56, 305 55"
          stroke="var(--loom-contradiction)"
          strokeWidth="3.2"
          strokeLinecap="round"
          initial={isReducedMotion ? undefined : { pathLength: 0.1 }}
          animate={isReducedMotion ? undefined : { pathLength: 1 }}
          transition={{ duration: 0.9, ease: 'easeOut', delay: 0.1 }}
        />
        {/* Second ply of main trunk */}
        <path
          d="M 485 53 C 425 53, 365 54, 308 53"
          stroke="var(--loom-contradiction)"
          strokeWidth="1.6"
          strokeOpacity="0.7"
          strokeLinecap="round"
        />

        {/* FRAY B1: Upward-curling fiber strand */}
        <motion.path
          d="M 305 54 C 285 44, 270 34, 254 28"
          stroke="var(--loom-contradiction)"
          strokeWidth="1.8"
          strokeLinecap="round"
          animate={isReducedMotion ? undefined : { y: [-1, 1.2, -1] }}
          transition={{ duration: 3.4, repeat: Infinity, ease: 'easeInOut', delay: 0.2 }}
        />
        {/* Micro-wisp B1b splitting off strand B1 */}
        <path
          d="M 284 46 C 274 41, 265 42, 258 40"
          stroke="var(--loom-contradiction)"
          strokeWidth="0.9"
          strokeOpacity="0.6"
          strokeDasharray="2 3"
        />

        {/* FRAY B2: Center horizontal reaching strand (tapers off before reaching center) */}
        <path
          d="M 305 55 C 288 56, 274 58, 262 61"
          stroke="var(--loom-contradiction)"
          strokeWidth="1.4"
          strokeLinecap="round"
        />

        {/* FRAY B3: Downward-curling fiber strand */}
        <motion.path
          d="M 305 56 C 284 66, 268 76, 252 82"
          stroke="var(--loom-contradiction)"
          strokeWidth="1.8"
          strokeLinecap="round"
          animate={isReducedMotion ? undefined : { y: [1.2, -1, 1.2] }}
          transition={{ duration: 4.0, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
        />
        {/* Micro-wisp B3b splitting off strand B3 */}
        <path
          d="M 282 67 C 272 73, 263 72, 257 74"
          stroke="var(--loom-contradiction)"
          strokeWidth="0.9"
          strokeOpacity="0.5"
          strokeDasharray="3 3"
        />

        {/* Loose floating fiber fragment near gap */}
        <path
          d="M 264 68 C 260 70, 256 69, 253 71"
          stroke="var(--loom-contradiction)"
          strokeWidth="0.75"
          strokeOpacity="0.4"
        />

        {/* Unbridgeable Chasm indicator lines */}
        <line
          x1="247"
          y1="8"
          x2="247"
          y2="92"
          stroke="var(--loom-card-border)"
          strokeWidth="1"
          strokeDasharray="2 4"
          strokeOpacity="0.4"
        />
        <line
          x1="253"
          y1="8"
          x2="253"
          y2="92"
          stroke="var(--loom-card-border)"
          strokeWidth="1"
          strokeDasharray="2 4"
          strokeOpacity="0.4"
        />
      </svg>

      {/* Discrete Abstention Badge anchored precisely in the central gap */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[var(--loom-card)]/95 backdrop-blur-md px-3.5 py-1.5 rounded border border-[var(--loom-unresolved)]/60 shadow-lg flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-[var(--loom-unresolved)] animate-pulse" />
        <span className="font-mono-tabular text-[10px] uppercase tracking-wider text-[var(--loom-unresolved)] font-bold">
          FRAYED FIBERS • UNRESOLVED ABSTENTION {dimension ? `[${dimension}]` : ''}
        </span>
      </div>
    </div>
  );
};

