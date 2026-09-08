import React from 'react';

export type StatusType = 'verified' | 'unresolved' | 'contradiction' | 'neutral';

interface StatusBadgeProps {
  status: StatusType | string;
  label?: string;
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status = 'neutral',
  label,
  size = 'md',
  className = '',
}) => {
  let normalizedStatus: StatusType = 'neutral';
  const s = String(status || '').toLowerCase();

  if (s.includes('same_as') || s.includes('reconciled') || s.includes('verified') || s.includes('supersedes')) {
    normalizedStatus = 'verified';
  } else if (s.includes('unresolved') || s.includes('unknown') || s.includes('ambiguous')) {
    normalizedStatus = 'unresolved';
  } else if (s.includes('contradict') || s.includes('mismatch')) {
    normalizedStatus = 'contradiction';
  }

  const displayText = label || (status ? String(status).replace(/_/g, ' ').toUpperCase() : 'UNKNOWN');

  const styles: Record<StatusType, { border: string; bg: string; text: string; dot: string }> = {
    verified: {
      border: 'border-[var(--loom-verified)]/30',
      bg: 'bg-[var(--loom-verified)]/10',
      text: 'text-[var(--loom-verified)]',
      dot: 'bg-[var(--loom-verified)]',
    },
    unresolved: {
      border: 'border-[var(--loom-unresolved)]/30',
      bg: 'bg-[var(--loom-unresolved)]/10',
      text: 'text-[var(--loom-unresolved)]',
      dot: 'bg-[var(--loom-unresolved)]',
    },
    contradiction: {
      border: 'border-[var(--loom-contradiction)]/30',
      bg: 'bg-[var(--loom-contradiction)]/10',
      text: 'text-[var(--loom-contradiction)]',
      dot: 'bg-[var(--loom-contradiction)]',
    },
    neutral: {
      border: 'border-[var(--loom-thread)]/30',
      bg: 'bg-[var(--loom-thread)]/10',
      text: 'text-[var(--loom-paper)]',
      dot: 'bg-[var(--loom-thread)]',
    },
  };

  const style = styles[normalizedStatus];
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono-tabular uppercase tracking-wider rounded-sm border ${style.border} ${style.bg} ${style.text} ${sizeClasses} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      <span>{displayText}</span>
    </span>
  );
};
