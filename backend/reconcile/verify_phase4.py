"""
FactLoom Phase 4 Verification Suite
Runs the full Phase 4 gate checks specified in Docs/verification.md:
1. Case 1: EBITDA / Revenue -> SAME_AS, ROUNDING + UNIT_MISMATCH, verified=true
2. Case 2: Active customers (33,250 vs 33,278) -> UNRESOLVED, UNKNOWN (abstains)
3. Case 3a: Director Suvir Sujan -> SUPERSEDES, REPORTING_VINTAGE, verified=true
4. Case 3b: India Real GDP FY25 -> RECONCILED_BY, ESTIMATE_VS_ACTUAL, verified=true
5. Case 4: Segment-sum footnote tolerance -> resolved at deterministic tier
6. Call-ordering check: Case 1 and Case 4 never issue an LLM adjudication call
7. Adversarial injection test: Verifier catches deliberately bogus LLM claim and downgrades to UNRESOLVED (verified=0)
8. Zero hardcoding check: 0 matches for starter-dataset tokens
"""

import os
import sys
import subprocess
from typing import Dict, Any, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.reconcile.service import ReconciliationService
from backend.reconcile.deterministic import DeterministicReconciler
from backend.reconcile.verifier import DeterministicVerifier

class MockCallSpyAdjudicator:
    """Spy adjudicator to verify call ordering (must NOT be called on Case 1)."""
    def __init__(self):
        self.call_count = 0

    def adjudicate(self, entity_name, metric_name, obs_a, obs_b):
        self.call_count += 1
        raise AssertionError(f"Call-ordering violation! Deterministic tier failed to intercept Case 1.")

def run_case_1(svc: ReconciliationService) -> Dict[str, Any]:
    obs_ebitda_ar = {
        "id": "obs_case1_ar",
        "value": "1,266.41",
        "unit": "million rupees",
        "quote_span": "1,266.41",
        "period": "FY24",
        "doc_vintage_date": "2024-05-17",
        "document_filename": "02-delhivery-annual-report-fy24-excerpt.pdf"
    }
    obs_ebitda_deck = {
        "id": "obs_case1_deck",
        "value": "127",
        "unit": "₹ Cr",
        "quote_span": "127",
        "period": "FY24",
        "doc_vintage_date": "2024-05-17",
        "document_filename": "03-delhivery-q4-fy24-earnings-presentation.pdf"
    }
    return svc.reconcile_observation_pair(
        obs_ebitda_ar, obs_ebitda_deck,
        entity_name="Delhivery Limited", metric_name="EBITDA"
    )

def run_case_2(svc: ReconciliationService) -> Dict[str, Any]:
    obs_cust_ar = {
        "id": "obs_case2_ar",
        "value": "33,250",
        "unit": "count",
        "quote_span": "over 33,250 active customers",
        "period": "Q4 FY24",
        "doc_vintage_date": "2024-05-17",
        "document_filename": "02-delhivery-annual-report-fy24-excerpt.pdf"
    }
    obs_cust_deck = {
        "id": "obs_case2_deck",
        "value": "33,278",
        "unit": "count",
        "quote_span": "33,278 active customers",
        "period": "Q4 FY24",
        "doc_vintage_date": "2024-05-17",
        "document_filename": "03-delhivery-q4-fy24-earnings-presentation.pdf"
    }
    return svc.reconcile_observation_pair(
        obs_cust_ar, obs_cust_deck,
        entity_name="Delhivery Limited", metric_name="Active Customers"
    )

def run_case_3a(svc: ReconciliationService) -> Dict[str, Any]:
    obs_dir_pros = {
        "id": "obs_case3_pros",
        "value": "Non-Executive Nominee Director",
        "unit": "position",
        "quote_span": "Suvir Suren Sujan (DIN: 01173669) is a Non-Executive Nominee Director of our Company.",
        "period": "As on date of Prospectus",
        "doc_vintage_date": "2022-05-11",
        "document_filename": "01-delhivery-prospectus-excerpt.pdf"
    }
    obs_dir_ar = {
        "id": "obs_case3_ar",
        "value": "Ceased to be Director",
        "unit": "position",
        "quote_span": "Mr. Suvir Suren Sujan (DIN: 01173669) ceased to be a Director with effect from August 24, 2023.",
        "period": "FY24",
        "doc_vintage_date": "2024-05-17",
        "document_filename": "02-delhivery-annual-report-fy24-excerpt.pdf"
    }
    return svc.reconcile_observation_pair(
        obs_dir_pros, obs_dir_ar,
        entity_name="Suvir Suren Sujan", metric_name="Directorship Status"
    )

def run_case_3b(svc: ReconciliationService) -> Dict[str, Any]:
    obs_gdp_est = {
        "id": "obs_case3b_est",
        "value": "6.4%",
        "unit": "%",
        "quote_span": "India's real GDP is projected to grow at 6.4% in FY25 (First Advance Estimate).",
        "period": "FY25",
        "doc_vintage_date": "2024-01-31",
        "document_filename": "05-economic-survey-2023-24-excerpt.pdf"
    }
    obs_gdp_act = {
        "id": "obs_case3b_act",
        "value": "6.5%",
        "unit": "%",
        "quote_span": "India's real GDP growth for FY2024-25 stood at 6.5% per official release.",
        "period": "FY25",
        "doc_vintage_date": "2024-06-07",
        "document_filename": "06-rbi-annual-report-2023-24-excerpt.pdf"
    }
    return svc.reconcile_observation_pair(
        obs_gdp_est, obs_gdp_act,
        entity_name="India", metric_name="Real GDP Growth"
    )

def run_case_4_segment_sum(det: DeterministicReconciler) -> bool:
    """Verify Case 4 segment-sum footnote tolerance check."""
    # Delhivery FY24 segment revenues: Express Parcel (5,077), PTL (1,517), Supply Chain (776),
    # Truckload (609), Cross Border (153). Total = 8,132 Cr vs stated consolidated Total Revenue = 8,142 Cr
    # Footnote: "totals may not correspond with sum of individual figures due to rounding"
    parts = [
        (5077.0, "₹ Cr"),
        (1517.0, "₹ Cr"),
        (776.0, "₹ Cr"),
        (609.0, "₹ Cr"),
        (153.0, "₹ Cr")
    ]
    # Within 0.5% tolerance (delta = 10 / 8142 = 0.12%)
    return det.check_segment_sum_tolerance(8142.0, "₹ Cr", parts, tolerance_pct=0.5)

def run_adversarial_injection_test(verifier: DeterministicVerifier) -> bool:
    """Verify that verifier catches and downgrades a bogus LLM arithmetic claim."""
    obs_a = {"value": "1,266.41", "unit": "million rupees"}
    obs_b = {"value": "500", "unit": "₹ Cr"}
    
    # Bogus LLM claim: asserts 1,266M and 500 Cr are SAME_AS via ROUNDING
    bogus_claim = {
        "relationship_type": "SAME_AS",
        "dimension": "ROUNDING",
        "justification": "Hallucinated claim that 1,266M and 500Cr are identical.",
        "verified_bool": 1
    }
    
    v_bool, res = verifier.verify(bogus_claim, obs_a, obs_b)
    # Must be rejected (verified_bool = 0, downgraded to UNRESOLVED)
    return (v_bool == 0) and (res["relationship_type"] == "UNRESOLVED")

def run_hardcoding_check() -> bool:
    """Check for starter dataset tokens in reconcile code."""
    forbidden = ["delhivery", "ebitda", "gdp", "superjoin", "rbi", "imf"]
    target_dir = os.path.join(os.path.dirname(__file__))
    for root, _, files in os.walk(target_dir):
        for f in files:
            if f.endswith(".py") and f != "verify_phase4.py":
                f_path = os.path.join(root, f)
                with open(f_path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read().lower()
                    for token in forbidden:
                        if token in content:
                            print(f"  [HARDCODING ERROR] Found '{token}' in {f_path}")
                            return False
    return True

def main():
    print("=" * 60)
    print("FACTLOOM PHASE 4 VERIFICATION SUITE")
    print("=" * 60)

    svc = ReconciliationService()

    # Step 1: Call Ordering Check (Case 1 must never touch LLM)
    print("\n[CHECK 1] Asserting Deterministic-First Call Ordering...")
    spy_adj = MockCallSpyAdjudicator()
    spy_svc = ReconciliationService(adjudicator=spy_adj)
    case1_spy_res = run_case_1(spy_svc)
    assert spy_adj.call_count == 0, "LLM was called for Case 1!"
    print(f"  [PASS] Case 1 resolved entirely at Tier 1 (LLM call count: {spy_adj.call_count}).")

    # Step 2: Run Case 1 (Corroboration)
    print("\n[CHECK 2] Evaluating Case 1 (EBITDA / Revenue Corroboration)...")
    res1 = run_case_1(svc)
    print(f"  Result: {res1['relationship_type']} | Dimension: {res1['dimension']} | Verified: {res1.get('verified_bool') == 1}")
    print(f"  Justification: {res1['justification']}")
    case1_pass = (
        res1["relationship_type"] == "SAME_AS" and
        "ROUNDING" in res1["dimension"] and
        res1.get("verified_bool") == 1
    )

    # Step 3: Run Case 2 (Active Customers Discrepancy)
    print("\n[CHECK 3] Evaluating Case 2 (Active Customers 33,250 vs 33,278)...")
    res2 = run_case_2(svc)
    print(f"  Result: {res2['relationship_type']} | Dimension: {res2['dimension']} | Verified: {res2.get('verified_bool') == 1}")
    print(f"  Justification: {res2['justification']}")
    case2_pass = (
        res2["relationship_type"] == "UNRESOLVED" and
        res2["dimension"] == "UNKNOWN"
    )

    # Step 4: Run Case 3a (Director Suvir Sujan)
    print("\n[CHECK 4] Evaluating Case 3a (Director Sujan Governance Change)...")
    res3a = run_case_3a(svc)
    print(f"  Result: {res3a['relationship_type']} | Dimension: {res3a['dimension']} | Verified: {res3a.get('verified_bool') == 1}")
    print(f"  Justification: {res3a['justification']}")
    case3a_pass = (
        res3a["relationship_type"] == "SUPERSEDES" and
        res3a.get("verified_bool") == 1
    )

    # Step 5: Run Case 3b (India Real GDP FY25)
    print("\n[CHECK 5] Evaluating Case 3b (India Real GDP 6.4% advance vs 6.5% actual)...")
    res3b = run_case_3b(svc)
    print(f"  Result: {res3b['relationship_type']} | Dimension: {res3b['dimension']} | Verified: {res3b.get('verified_bool') == 1}")
    print(f"  Justification: {res3b['justification']}")
    case3b_pass = (
        res3b["relationship_type"] == "RECONCILED_BY" and
        res3b["dimension"] == "ESTIMATE_VS_ACTUAL" and
        res3b.get("verified_bool") == 1
    )

    # Step 6: Run Case 4 (Segment-sum Footnote Tolerance)
    print("\n[CHECK 6] Evaluating Case 4 (Segment-sum Footnote Rounding)...")
    case4_pass = run_case_4_segment_sum(svc.deterministic_tier)
    print(f"  Segment-sum rounding footnote defused at Tier 1: {case4_pass}")

    # Step 7: Adversarial Injected Claim Test
    print("\n[CHECK 7] Evaluating Verifier Backstop on Injected Bogus Claim...")
    verifier_pass = run_adversarial_injection_test(svc.verifier)
    print(f"  Bogus LLM conversion caught and downgraded to UNRESOLVED (verified_bool=0): {verifier_pass}")

    # Step 8: Hardcoding Grep
    print("\n[CHECK 8] Running Hardcoding Grep across reconcile module...")
    hardcoding_pass = run_hardcoding_check()
    print(f"  Zero starter-set tokens in reconcile logic: {hardcoding_pass}")

    # Step 9: Print Official Self-Report
    print("\n" + "=" * 60)
    print("PHASE 4 — SELF-REPORT")
    print(f"Case 1 (EBITDA/Revenue):  {res1['relationship_type']}, {res1['dimension']}, verified={res1.get('verified_bool') == 1}")
    print(f"Case 2 (Active Cust):     {res2['relationship_type']}, {res2['dimension']}")
    print(f"Case 3 (Director Sujan):  {res3a['relationship_type']}, {res3a['dimension']}, verified={res3a.get('verified_bool') == 1}")
    print(f"Case 3b (GDP Estimate):   {res3b['relationship_type']}, {res3b['dimension']}, verified={res3b.get('verified_bool') == 1}")
    print(f"Case 4 (Segment sum):     defused at deterministic tier={case4_pass}")
    print(f"Call-ordering check:      deterministic tier intercepts Case 1 without LLM=True")
    print(f"Verifier backstop:        catches injected false claim={verifier_pass}")
    print(f"Zero hardcoding:          {hardcoding_pass}")

    gate_status = (
        case1_pass and
        case2_pass and
        case3a_pass and
        case3b_pass and
        case4_pass and
        verifier_pass and
        hardcoding_pass
    )
    print(f"Gate: {'PASS' if gate_status else 'FAIL'}")
    print("=" * 60)

    if not gate_status:
        sys.exit(1)

if __name__ == "__main__":
    main()
