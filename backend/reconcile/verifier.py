"""
FactLoom Deterministic Verifier (Tier 3)
Independent deterministic backstop that re-checks arithmetic, unit math,
and temporal ordering before persisting any relationship.
Downgrades invalid LLM claims to UNRESOLVED with verified_bool = 0.
"""

from typing import Dict, Any, Tuple
from backend.reconcile.units import (
    parse_numerical_value,
    normalize_to_base,
    compute_relative_delta
)

class DeterministicVerifier:
    def __init__(self, tolerance_pct: float = 0.5):
        self.tolerance_pct = tolerance_pct

    def verify(
        self,
        rel_decision: Dict[str, Any],
        obs_a: Dict[str, Any],
        obs_b: Dict[str, Any]
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Verify relationship claims deterministically.
        Returns (verified_bool: 1|0, final_relationship_dict).
        """
        decision = dict(rel_decision)
        rel_type = decision.get("relationship_type", "UNRESOLVED")
        dimension = decision.get("dimension", "UNKNOWN")
        justification = decision.get("justification", "")

        val_a = obs_a.get("value")
        val_b = obs_b.get("value")
        num_a = parse_numerical_value(val_a)
        num_b = parse_numerical_value(val_b)

        # Rule 1: Verify arithmetic for SAME_AS, UNIT_MISMATCH, or ROUNDING
        if rel_type == "SAME_AS" or dimension in ["UNIT_MISMATCH", "ROUNDING"]:
            if num_a is None or num_b is None:
                # Textual or non-numeric claim; if SAME_AS on different text, require verifier pass
                if str(val_a or "").strip().lower() == str(val_b or "").strip().lower():
                    decision["verified_bool"] = 1
                    return 1, decision
                else:
                    decision["relationship_type"] = "UNRESOLVED"
                    decision["dimension"] = "UNKNOWN"
                    decision["justification"] = f"[Verifier rejection: non-numeric values differ ({val_a} vs {val_b})]. Original: {justification}"
                    decision["verified_bool"] = 0
                    return 0, decision

            unit_a = obs_a.get("unit")
            unit_b = obs_b.get("unit")
            base_a, curr_a = normalize_to_base(num_a, unit_a)
            base_b, curr_b = normalize_to_base(num_b, unit_b)

            delta = compute_relative_delta(base_a, base_b)
            tolerance = self.tolerance_pct / 100.0

            is_rate = ("%" in str(unit_a or "") or "%" in str(unit_b or "") or curr_a == "rate" or curr_b == "rate")
            abs_diff = abs(num_a - num_b)

            arithmetic_valid = False
            if delta <= tolerance:
                arithmetic_valid = True
            elif is_rate and abs_diff <= 0.05:
                arithmetic_valid = True

            if not arithmetic_valid:
                # Downgrade invalid LLM claim
                decision["relationship_type"] = "UNRESOLVED"
                decision["dimension"] = "UNKNOWN"
                decision["justification"] = (
                    f"[Verifier rejection: arithmetic delta {delta*100:.2f}% exceeds {self.tolerance_pct}% tolerance band "
                    f"({val_a} vs {val_b})]. Original claim: {justification}"
                )
                decision["verified_bool"] = 0
                return 0, decision

            decision["verified_bool"] = 1
            return 1, decision

        # Rule 2: Verify temporal direction for SUPERSEDES
        if rel_type == "SUPERSEDES":
            vintage_a = obs_a.get("doc_vintage_date")
            vintage_b = obs_b.get("doc_vintage_date")

            # If Observation B claims to supersede Observation A, B cannot be from an older filing vintage
            # unless B contains explicit temporal language citing an effective date after A
            quote_b = (obs_b.get("quote_span") or "").lower()
            quote_a = (obs_a.get("quote_span") or "").lower()

            has_cessation_or_effect = any(k in quote_b for k in ["ceased", "effect from", "resigned", "appointed", "effective", "with effect"])

            if vintage_a and vintage_b and vintage_b < vintage_a and not has_cessation_or_effect:
                decision["relationship_type"] = "UNRESOLVED"
                decision["dimension"] = "UNKNOWN"
                decision["justification"] = (
                    f"[Verifier rejection: temporal inversion. Document B ({vintage_b}) is older than Document A ({vintage_a})]. "
                    f"Original claim: {justification}"
                )
                decision["verified_bool"] = 0
                return 0, decision

            decision["verified_bool"] = 1
            return 1, decision

        # Rule 3: False CONTRADICTS check
        if rel_type == "CONTRADICTS" and num_a is not None and num_b is not None:
            unit_a = obs_a.get("unit")
            unit_b = obs_b.get("unit")
            base_a, _ = normalize_to_base(num_a, unit_a)
            base_b, _ = normalize_to_base(num_b, unit_b)
            delta = compute_relative_delta(base_a, base_b)
            if delta <= (self.tolerance_pct / 100.0):
                # LLM hallucinated a contradiction on values that actually match within tolerance!
                decision["relationship_type"] = "SAME_AS"
                decision["dimension"] = "ROUNDING"
                decision["justification"] = f"[Verifier correction: values align within {delta*100:.3f}% rounding tolerance]. Original: {justification}"
                decision["verified_bool"] = 1
                return 1, decision

        # Rule 4: Verify ESTIMATE_VS_ACTUAL claims
        if dimension == "ESTIMATE_VS_ACTUAL" or (rel_type == "RECONCILED_BY" and "estimate" in justification.lower()):
            quote_a = (obs_a.get("quote_span") or "").lower()
            quote_b = (obs_b.get("quote_span") or "").lower()
            val_a_str = str(obs_a.get("value") or "").lower()
            val_b_str = str(obs_b.get("value") or "").lower()

            ESTIMATE_TERMS = {"estimate", "advance", "projected", "forecast", "provisional", "target", "budgeted", "budget", "estimated"}
            ACTUAL_TERMS = {"actual", "official release", "stood at", "final", "reported", "realized", "result", "revised"}

            a_has_est = any(t in quote_a or t in val_a_str for t in ESTIMATE_TERMS)
            b_has_est = any(t in quote_b or t in val_b_str for t in ESTIMATE_TERMS)
            a_has_act = any(t in quote_a or t in val_a_str for t in ACTUAL_TERMS)
            b_has_act = any(t in quote_b or t in val_b_str for t in ACTUAL_TERMS)

            has_valid_asymmetry = (a_has_est and b_has_act) or (b_has_est and a_has_act) or (a_has_est != b_has_est)

            # Check temporal ordering: the actual figure must not predate the estimate vintage
            vintage_a = obs_a.get("doc_vintage_date")
            vintage_b = obs_b.get("doc_vintage_date")
            temporal_valid = True
            if vintage_a and vintage_b:
                if a_has_est and b_has_act and vintage_b < vintage_a:
                    temporal_valid = False
                elif b_has_est and a_has_act and vintage_a < vintage_b:
                    temporal_valid = False

            if not has_valid_asymmetry or not temporal_valid:
                decision["relationship_type"] = "UNRESOLVED"
                decision["dimension"] = "UNKNOWN"
                fail_reason = "temporal inversion" if not temporal_valid else "neither observation cites projection/estimate terminology"
                decision["justification"] = (
                    f"[Verifier rejection: invalid ESTIMATE_VS_ACTUAL claim ({fail_reason})]. "
                    f"Original claim: {justification}"
                )
                decision["verified_bool"] = 0
                return 0, decision

            decision["verified_bool"] = 1
            return 1, decision

        # Rule 5: Abstentions and other verified relationships
        decision["verified_bool"] = 1
        return 1, decision
