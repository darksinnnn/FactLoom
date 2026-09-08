import React from 'react';
import { CheckCircle, WarningCircle } from '@phosphor-icons/react';

interface VerifierBadgeProps {
  verified: boolean | number;
  claim?: string;
  className?: string;
}

export const VerifierBadge: React.FC<VerifierBadgeProps> = ({ verified, claim, className = '' }) => {
  const isVerified = Boolean(verified);

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono-tabular border ${
        isVerified
          ? 'bg-[var(--loom-verified)]/10 border-[var(--loom-verified)]/30 text-[var(--loom-verified)]'
          : 'bg-[var(--loom-unresolved)]/10 border-[var(--loom-unresolved)]/30 text-[var(--loom-unresolved)]'
      } ${className}`}
      title={claim || (isVerified ? 'Deterministically verified by Tier 3 verifier' : 'Unverified or abstained')}
    >
      {isVerified ? (
        <>
          <CheckCircle size={14} weight="fill" />
          <span className="font-semibold uppercase tracking-wider text-[10px]">Tier-3 Verified</span>
        </>
      ) : (
        <>
          <WarningCircle size={14} weight="fill" />
          <span className="font-semibold uppercase tracking-wider text-[10px]">Unverified / Abstention</span>
        </>
      )}
    </div>
  );
};
