import React from 'react';

interface TabularValueProps {
  value: string | number | null | undefined;
  unit?: string | null;
  className?: string;
  align?: 'left' | 'right' | 'center';
  highlight?: boolean;
}

export const TabularValue: React.FC<TabularValueProps> = ({
  value,
  unit,
  className = '',
  align = 'right',
  highlight = false,
}) => {
  if (value === null || value === undefined || value === '') {
    return <span className="font-mono-tabular text-[var(--loom-thread)] text-sm">—</span>;
  }

  const alignmentClass = align === 'right' ? 'text-right justify-end' : align === 'center' ? 'text-center justify-center' : 'text-left justify-start';

  return (
    <span
      className={`font-mono-tabular inline-flex items-baseline gap-1 tracking-tight ${alignmentClass} ${
        highlight ? 'text-[var(--loom-verified)] font-medium' : 'text-[var(--loom-paper)]'
      } ${className}`}
    >
      <span>{String(value)}</span>
      {unit && (
        <span className="text-xs font-normal text-[var(--loom-thread)] uppercase">
          {unit}
        </span>
      )}
    </span>
  );
};
