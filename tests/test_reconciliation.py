"""
Unit and integration tests for FactLoom Reconciliation Engine (Phase 4).
Tests:
- Unit parsing, negative handling, scales (crore, million, lakh, billion, bps, percent)
- Tier 1 Deterministic Reconciler & rounding tolerance
- Discrete count escalation (preventing false rounding on exact headcounts)
- Footnote segment-sum tolerance
- Tier 2 Adjudicator schema validation & abstention
- Tier 3 Deterministic Verifier backstop (catching hallucinated math)
- Deterministic-first call ordering
"""

import pytest
from unittest.mock import MagicMock
from backend.reconcile.units import (
    parse_numeric_value,
    normalize_to_base,
    compute_relative_delta,
    extract_scale_and_currency,
)
from backend.reconcile.deterministic import DeterministicReconciler
from backend.reconcile.verifier import DeterministicVerifier
from backend.reconcile.adjudicator import (
    ReconciliationAdjudicator,
    ReconciliationDecision,
    RelationshipType,
    ReconciliationDimension,
)
from backend.reconcile.service import ReconciliationService


# ---------------------------------------------------------
# 1. Units & Numeric Parsing Tests
# ---------------------------------------------------------

def test_parse_numeric_value_handles_formats():
    assert parse_numeric_value("1,266.41") == 1266.41
    assert parse_numeric_value("(1,008)") == -1008.0
    assert parse_numeric_value("(1,007.79)") == -1007.79
    assert parse_numeric_value("-45.5") == -45.5
    assert parse_numeric_value("12.68%") == 12.68
    assert parse_numeric_value(">33,200") == 33200.0
    assert parse_numeric_value("~500") == 500.0
    assert parse_numeric_value("Invalid") is None


def test_normalize_to_base_scales():
    # 1 Crore = 10 Million
    base_cr, cur1 = normalize_to_base(127.0, "₹ Cr")
    base_m, cur2 = normalize_to_base(1270.0, "million rupees")
    assert cur1 == "INR"
    assert cur2 == "INR"
    assert base_cr == 1_270_000_000.0
    assert base_m == 1_270_000_000.0

    # 1 Lakh = 100,000
    base_lakh, _ = normalize_to_base(5.0, "Lakh INR")
    assert base_lakh == 500_000.0

    # 1 Billion = 1,000 Million
    base_b, _ = normalize_to_base(2.5, "billion USD")
    base_bm, _ = normalize_to_base(2500.0, "million USD")
    assert base_b == base_bm == 2_500_000_000.0

    # Basis points (100 bps = 1% = 0.01; 50 bps = 0.5% = 0.005)
    base_bps, u_bps = normalize_to_base(50.0, "bps")
    base_pct, u_pct = normalize_to_base(0.5, "%")
    assert u_bps == "rate"
    assert u_pct == "rate"
    assert abs(base_bps - 0.005) < 1e-9
    assert abs(base_bps - base_pct) < 1e-9


def test_compute_relative_delta():
    # 1266.41M vs 1270M (127 Cr)
    delta = compute_relative_delta(1266.41, 1270.0)
    assert 0.0028 < delta < 0.0029  # ~0.283%
    assert compute_relative_delta(100.0, 100.0) == 0.0


# ---------------------------------------------------------
# 2. Deterministic Tier (Tier 1) Tests
# ---------------------------------------------------------

def test_deterministic_reconciler_resolves_case_1():
    reconciler = DeterministicReconciler(tolerance_pct=0.5)
    obs_a = {"value": "1,266.41", "unit": "million rupees"}
    obs_b = {"value": "127", "unit": "₹ Cr"}

    res = reconciler.reconcile_pair(obs_a, obs_b)
    assert res is not None
    assert res["relationship_type"] == "SAME_AS"
    assert res["dimension"] == "ROUNDING + UNIT_MISMATCH"
    assert res["verified_bool"] == 1
    assert res["tier"] == "deterministic"


def test_deterministic_reconciler_escalates_discrete_counts():
    reconciler = DeterministicReconciler(tolerance_pct=0.5)
    # 33,250 vs 33,278 delta is 0.084% (<0.5%), but counts are not currency/scale conversions.
    # Must NOT be auto-resolved as ROUNDING at Tier 1; must escalate to LLM.
    obs_a = {"value": "33,250", "unit": "active customers"}
    obs_b = {"value": "33,278", "unit": "active customers"}

    res = reconciler.reconcile_pair(obs_a, obs_b)
    assert res is None, "Discrete headcount/customer counts must not be auto-resolved as ROUNDING!"


def test_deterministic_reconciler_escalates_material_differences():
    reconciler = DeterministicReconciler(tolerance_pct=0.5)
    # 127 Cr vs 150 Cr (material difference > 0.5%)
    obs_a = {"value": "127", "unit": "₹ Cr"}
    obs_b = {"value": "150", "unit": "₹ Cr"}

    res = reconciler.reconcile_pair(obs_a, obs_b)
    assert res is None


def test_check_segment_sum_tolerance():
    reconciler = DeterministicReconciler(tolerance_pct=0.5)
    # Sum of parts = 5077 + 1517 + 776 + 328 + 444 = 8142
    parts = [
        (5077.0, "₹ Cr"),
        (1517.0, "₹ Cr"),
        (776.0, "₹ Cr"),
        (328.0, "₹ Cr"),
        (444.0, "₹ Cr"),
    ]
    # Total stated: 8,142 Cr
    assert reconciler.check_segment_sum_tolerance(8142.0, "₹ Cr", parts, tolerance_pct=0.5) is True
    # Stated 8,140 Cr (within 0.5%)
    assert reconciler.check_segment_sum_tolerance(8140.0, "₹ Cr", parts, tolerance_pct=0.5) is True
    # Stated 8,000 Cr (outside 0.5%)
    assert reconciler.check_segment_sum_tolerance(8000.0, "₹ Cr", parts, tolerance_pct=0.5) is False


# ---------------------------------------------------------
# 3. Deterministic Verifier (Tier 3) Backstop Tests
# ---------------------------------------------------------

def test_verifier_catches_bogus_llm_claim():
    verifier = DeterministicVerifier(tolerance_pct=0.5)
    obs_a = {"value": "1,266.41", "unit": "million rupees"}
    obs_b = {"value": "500", "unit": "₹ Cr"}

    bogus_claim = {
        "relationship_type": "SAME_AS",
        "dimension": "ROUNDING",
        "justification": "Hallucinated claim that 1,266M and 500Cr are the same.",
        "verified_bool": 1
    }

    v_bool, final = verifier.verify(bogus_claim, obs_a, obs_b)
    assert v_bool == 0
    assert final["relationship_type"] == "UNRESOLVED"
    assert final["verified_bool"] == 0
    assert "rejection" in final["justification"].lower()


def test_verifier_corrects_false_contradiction_on_rounded_pair():
    verifier = DeterministicVerifier(tolerance_pct=0.5)
    obs_a = {"value": "1,266.41", "unit": "million rupees"}
    obs_b = {"value": "127", "unit": "₹ Cr"}

    # Hallucinated LLM claim that they CONTRADICT each other
    bad_claim = {
        "relationship_type": "CONTRADICTS",
        "dimension": "ACCOUNTING_TREATMENT",
        "justification": "LLM mistakenly claiming 1266.41M and 127Cr contradict.",
        "verified_bool": 1
    }

    v_bool, final = verifier.verify(bad_claim, obs_a, obs_b)
    assert v_bool == 1
    assert final["relationship_type"] == "SAME_AS"
    assert "ROUNDING" in final["dimension"]


def test_verifier_validates_supersedes_dates():
    verifier = DeterministicVerifier()
    # Obs A from 2024, Obs B from 2022
    # Claim: B supersedes A (invalid direction because B is older than A)
    obs_a = {"value": "Director A", "doc_vintage_date": "2024-05-17"}
    obs_b = {"value": "Director B", "doc_vintage_date": "2022-05-11"}

    claim = {
        "relationship_type": "SUPERSEDES",
        "dimension": "REPORTING_VINTAGE",
        "justification": "Older doc supersedes newer doc",
        "verified_bool": 1
    }

    v_bool, final = verifier.verify(claim, obs_a, obs_b)
    assert v_bool == 0
    assert final["relationship_type"] == "UNRESOLVED"


def test_verifier_validates_estimate_vs_actual():
    verifier = DeterministicVerifier()
    
    # Valid case: Observation A is advance estimate, Observation B is official actual release with later date
    obs_est = {
        "value": "6.4%",
        "quote_span": "First Advance Estimate of real GDP growth is 6.4%",
        "doc_vintage_date": "2024-01-31"
    }
    obs_act = {
        "value": "6.5%",
        "quote_span": "Real GDP growth stood at 6.5% per official release",
        "doc_vintage_date": "2024-05-31"
    }
    valid_claim = {
        "relationship_type": "RECONCILED_BY",
        "dimension": "ESTIMATE_VS_ACTUAL",
        "justification": "Observation A is an advance estimate reconciled by official release in B",
        "verified_bool": 1
    }
    v_bool, final = verifier.verify(valid_claim, obs_est, obs_act)
    assert v_bool == 1
    assert final["relationship_type"] == "RECONCILED_BY"

    # Invalid case 1: Inverted temporal ordering (actual published before estimate)
    obs_act_early = dict(obs_act, doc_vintage_date="2023-01-01")
    v_bool, final = verifier.verify(valid_claim, obs_est, obs_act_early)
    assert v_bool == 0
    assert final["relationship_type"] == "UNRESOLVED"
    assert "temporal inversion" in final["justification"]

    # Invalid case 2: Neither observation cites estimate terminology
    obs_plain1 = {"value": "100", "quote_span": "Net revenue 100", "doc_vintage_date": "2024-01-01"}
    obs_plain2 = {"value": "120", "quote_span": "Net revenue 120", "doc_vintage_date": "2024-05-01"}
    v_bool, final = verifier.verify(valid_claim, obs_plain1, obs_plain2)
    assert v_bool == 0
    assert final["relationship_type"] == "UNRESOLVED"
    assert "neither observation cites projection/estimate" in final["justification"]


# ---------------------------------------------------------
# 4. Service Call-Ordering Tests
# ---------------------------------------------------------

def test_deterministic_tier_prevents_llm_calls_for_case_1():
    mock_adjudicator = MagicMock()
    service = ReconciliationService(adjudicator=mock_adjudicator)

    obs_a = {"id": "obs_1", "value": "1,266.41", "unit": "million rupees"}
    obs_b = {"id": "obs_2", "value": "127", "unit": "₹ Cr"}

    res = service.reconcile_observation_pair(obs_a, obs_b, entity_name="Delhivery", metric_name="EBITDA")

    assert res["relationship_type"] == "SAME_AS"
    assert res["dimension"] == "ROUNDING + UNIT_MISMATCH"
    assert res["tier"] == "deterministic"
    # CRITICAL: LLM was NEVER called
    mock_adjudicator.adjudicate.assert_not_called()


# ---------------------------------------------------------
# 5. Schema & Taxonomy Enum Tests
# ---------------------------------------------------------

def test_reconciliation_decision_pydantic_schema():
    valid = ReconciliationDecision(
        relationship_type=RelationshipType.SAME_AS,
        dimension=ReconciliationDimension.ROUNDING,
        justification="Values match within 0.5% tolerance.",
        confidence=0.95
    )
    assert valid.relationship_type == "SAME_AS"
    assert valid.dimension == "ROUNDING"

    # Verify invalid enum raises ValidationError
    with pytest.raises(Exception):
        ReconciliationDecision(
            relationship_type="INVALID_TYPE",
            dimension="ROUNDING",
            justification="Test"
        )

    with pytest.raises(Exception):
        ReconciliationDecision(
            relationship_type="SAME_AS",
            dimension="INVALID_DIMENSION",
            justification="Test"
        )


def test_adjudicator_safe_fallback_on_llm_error():
    mock_client = MagicMock()
    mock_client.generate_json.side_effect = Exception("Rate limit or connection drop")
    adjudicator = ReconciliationAdjudicator(groq_client=mock_client)

    obs_a = {"id": "obs_1", "value": "100"}
    obs_b = {"id": "obs_2", "value": "200"}

    res = adjudicator.adjudicate(
        entity_name="Test Entity",
        metric_name="Test Metric",
        obs_a=obs_a,
        obs_b=obs_b
    )

    # Must safely fall back to UNRESOLVED + UNKNOWN
    assert res["relationship_type"] == "UNRESOLVED"
    assert res["dimension"] == "UNKNOWN"
    assert res["tier"] == "llm_adjudicated"
    assert "abstain" in res["justification"].lower()

