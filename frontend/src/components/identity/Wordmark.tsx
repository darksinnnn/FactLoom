import React from 'react';

interface WordmarkProps {
  className?: string;
  showTagline?: boolean;
}

export const Wordmark: React.FC<WordmarkProps> = ({ className = '', showTagline = false }) => {
  return (
    <div className={`flex flex-col select-none ${className}`}>
      <span className="font-display text-2xl font-black tracking-tight text-[var(--loom-paper)] lowercase leading-none">
        factloom
      </span>
      {showTagline && (
        <span className="font-body text-[10px] tracking-widest text-[var(--loom-thread)] uppercase mt-1">
          Evidence-Grounded Reconciliation
        </span>
      )}
    </div>
  );
};
