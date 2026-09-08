"""
FactLoom Deterministic Reconciliation Tier (Tier 1)
Enforces the core rule: deterministic checks run BEFORE any LLM adjudication.
Resolves unit conversion, date alignment, and presentation rounding tolerance.
"""

from typing import Dict, Any, Optional, List, Tuple
from backend.reconcile.units import (
    parse_numerical_value,
    extract_scale_and_currency,
    normalize_to_base,
    compute_relative_delta
)

class DeterministicReconciler:
    def __init__(self, tolerance_pct: float = 0.5):
        """
        tolerance_pct: Relative percentage tolerance (default 0.5% = 0.005)
        for presentation rounding in financial disclosures.
        """
        self.tolerance_pct = tolerance_pct

    def reconcile_pair(
        self,
        obs_a: Dict[str, Any],
        obs_b: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to deterministically reconcile two observations.
        Returns a relationship dictionary if resolved, or None if escalation to Tier 2 (LLM) is needed.
        """
        val_a_raw = obs_a.get("value")
        val_b_raw = obs_b.get("value")

        num_a = parse_numerical_value(val_a_raw)
        num_b = parse_numerical_value(val_b_raw)

        if num_a is None or num_b is None:
            return None

        unit_a = obs_a.get("unit")
        unit_b = obs_b.get("unit")

        scale_a, curr_a = extract_scale_and_currency(unit_a)
        scale_b, curr_b = extract_scale_and_currency(unit_b)

        # Incompatible currency families cannot be deterministically auto-merged without exchange rates
        if curr_a != curr_b and curr_a not in ["count", "unitless"] and curr_b not in ["count", "unitless"]:
            return None

        base_a, _ = normalize_to_base(num_a, unit_a)
        base_b, _ = normalize_to_base(num_b, unit_b)

        delta = compute_relative_delta(base_a, base_b)
        tolerance = self.tolerance_pct / 100.0

        # Percentage points presentation rounding check (e.g. 1.56% vs 1.6%)
        is_rate = (curr_a == "rate" or curr_b == "rate" or "%" in str(unit_a or "") or "%" in str(unit_b or ""))
        abs_diff = abs(num_a - num_b)

        # Exact match
        if delta == 0.0 or (is_rate and abs_diff == 0.0):
            return {
                "relationship_type": "SAME_AS",
                "dimension": "ROUNDING",
                "justification": f"Deterministic verification: values are identical ({val_a_raw} {unit_a or ''}).",
                "verified_bool": 1,
                "tier": "deterministic"
            }

        # Presentation rounding applies strictly to currency figures, scaled representations (e.g. million vs crore),
        # or rate figures. Discrete integer counts (e.g. 33,250 vs 33,278 customers) with discrepancies
        # cannot be assumed as presentation rounding and MUST escalate to LLM adjudication (Case 2).
        has_scale_mismatch = (scale_a != scale_b)
        is_currency = (curr_a in ["INR", "USD", "EUR", "GBP"] or curr_b in ["INR", "USD", "EUR", "GBP"])

        if not (has_scale_mismatch or is_currency or is_rate):
            return None

        is_match = False
        if delta <= tolerance:
            is_match = True
        elif is_rate and abs_diff <= 0.05:
            # e.g. 1.56% vs 1.6% (abs diff 0.04 percentage points)
            is_match = True

        if is_match:
            # Determine applicable dimension
            if has_scale_mismatch and delta > 0:
                dimension = "ROUNDING + UNIT_MISMATCH"
            elif has_scale_mismatch:
                dimension = "UNIT_MISMATCH"
            else:
                dimension = "ROUNDING"

            justification = (
                f"Deterministic verification: {val_a_raw} {unit_a or ''} "
                f"({base_a:,.2f}) aligns with {val_b_raw} {unit_b or ''} "
                f"({base_b:,.2f}) within {delta*100:.3f}% tolerance."
            )

            return {
                "relationship_type": "SAME_AS",
                "dimension": dimension,
                "justification": justification,
                "verified_bool": 1,
                "tier": "deterministic"
            }

        return None


    def check_segment_sum_tolerance(
        self,
        total_val: float,
        total_unit: Optional[str],
        parts: List[Tuple[float, Optional[str]]],
        tolerance_pct: Optional[float] = None
    ) -> bool:
        """
        Verify if sum of individual parts equals stated total within rounding tolerance
        to defuse Case 4a segment-sum footnote contradictions.
        """
        base_total, _ = normalize_to_base(total_val, total_unit)
        base_sum = sum(normalize_to_base(val, u)[0] for val, u in parts)
        delta = compute_relative_delta(base_sum, base_total)
        tol = (tolerance_pct if tolerance_pct is not None else self.tolerance_pct) / 100.0
        return delta <= tol
