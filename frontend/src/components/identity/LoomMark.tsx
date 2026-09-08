import React from 'react';

interface LoomMarkProps {
  size?: number;
  className?: string;
  variant?: 'full' | 'knot' | 'compact';
}

/**
 * Hand-crafted SVG monogram: Interlocking knot formed where 'F' and 'L' threads weave.
 * Uses security-print hairline geometry and dual-thread paths.
 */
export const LoomMark: React.FC<LoomMarkProps> = ({ size = 32, className = '' }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="FactLoom Monogram"
    >
      {/* Outer subtle security ring */}
      <circle
        cx="32"
        cy="32"
        r="30"
        stroke="rgba(247, 245, 240, 0.12)"
        strokeWidth="1"
        strokeDasharray="2 4"
      />

      {/* The 'F' Thread (Emerald Signal Accent) */}
      <path
        d="M20 50V18C20 15.79 21.79 14 24 14H42C44.21 14 46 15.79 46 18V22C46 24.21 44.21 26 42 26H28V32H38C40.21 32 42 33.79 42 36V37C42 39.21 40.21 41 38 41H28V50"
        stroke="var(--loom-verified)"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* The 'L' Thread (Warm Ledger Paper White, interweaving through the F) */}
      <path
        d="M16 26H22V44C22 46.21 23.79 48 26 48H48C50.21 48 52 46.21 52 44V42"
        stroke="var(--loom-paper)"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* The Interlocking Braid Knot Center - hairline security stitch */}
      <rect
        x="24.5"
        y="28.5"
        width="7"
        height="7"
        stroke="var(--loom-unresolved)"
        strokeWidth="1.2"
        strokeDasharray="1.5 1.5"
      />
    </svg>
  );
};
