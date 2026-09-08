"""
Unit tests for FactLoom Canonicalization & Registry Engine.
Tests normalization, defense-in-depth period stripping, modifier guards, and threshold safety.
"""

import pytest
from backend.canonicalize.registry import RegistryEngine
from backend.canonicalize.embedder import EmbeddingEngine

def test_clean_metric_mention_strips_leaked_periods_and_units():
    test_cases = {
        "Employee benefit expense excl. share based payments FY24": "Employee benefit expense excl. share based payments",
        "Other income FY23": "Other income",
        "Revenue from customers (A+B) FY23": "Revenue from customers (A+B)",
        "Total freight, handling and servicing cost FY23": "Total freight, handling and servicing cost",
        "EBITDA (₹Cr)": "EBITDA",
        "Revenue (in INR Million)": "Revenue",
        "Operating Profit March 31, 2024": "Operating Profit",
        "Net Sales Q4 FY24": "Net Sales",
        "Net Profit 2023-24": "Net Profit"
    }
    for raw, expected in test_cases.items():
        assert RegistryEngine.clean_metric_mention(raw) == expected

def test_clean_entity_mention_normalizes_legal_suffixes():
    test_cases = {
        "Delhivery Limited": "Delhivery",
        "Delhivery Ltd.": "Delhivery",
        "Acme Global Technologies Inc.": "Acme Global Technologies",
        "Globex Corporation": "Globex"
    }
    for raw, expected in test_cases.items():
        assert RegistryEngine.clean_entity_mention(raw) == expected

def test_has_modifier_mismatch_detects_accounting_qualifiers():
    assert RegistryEngine.has_modifier_mismatch("Adjusted EBITDA", "EBITDA") is True
    assert RegistryEngine.has_modifier_mismatch("Core Operating Profit", "Operating Profit") is True
    assert RegistryEngine.has_modifier_mismatch("Gross Revenue", "Net Revenue") is True
    assert RegistryEngine.has_modifier_mismatch("EBITDA", "EBITDA") is False

def test_empirical_threshold_guards():
    e = EmbeddingEngine.get_instance()
    
    # Negative control: completely distinct concepts must score well below lower threshold (0.65)
    v_rev = e.embed_text("Revenue from services")
    v_inc = e.embed_text("Total income")
    sim_neg = e.cosine_similarity(v_rev, v_inc)
    assert sim_neg < 0.65, f"Expected < 0.65, got {sim_neg:.4f}"

    # Semantic divergence risk: PTL freight revenue vs tonnage must score below upper threshold (0.88)
    v_pr = e.embed_text("PTL freight revenue")
    v_pt = e.embed_text("PTL freight tonnage")
    sim_risk = e.cosine_similarity(v_pr, v_pt)
    assert sim_risk < 0.88, f"Expected < 0.88 to avoid false merge, got {sim_risk:.4f}"

def test_case_insensitivity_and_whitespace_variants(tmp_path):
    db_file = str(tmp_path / "test_reg.db")
    engine = RegistryEngine(db_path=db_file)

    # Metric case & whitespace insensitivity
    id1, name1 = engine.resolve_metric("EBITDA")
    id2, name2 = engine.resolve_metric("ebitda")
    id3, name3 = engine.resolve_metric("   EBITDA \n\t  ")
    assert id1 == id2 == id3
    assert name1 == "EBITDA"

    # Entity case & whitespace insensitivity
    ent1, ename1 = engine.resolve_entity("Apple Inc.")
    ent2, ename2 = engine.resolve_entity("apple inc.")
    ent3, ename3 = engine.resolve_entity("   APPLE INC. \n ")
    ent4, ename4 = engine.resolve_entity("apple")
    assert ent1 == ent2 == ent3 == ent4

def test_multi_word_partial_match_does_not_false_alias(tmp_path):
    """Verify that multi-word accounting concepts sharing keywords are NOT falsely merged."""
    e = EmbeddingEngine.get_instance()

    pairs_to_check = [
        ("Operating Cash Flow", "Operating Expense"),
        ("Total Current Assets", "Total Current Liabilities"),
        ("Net Interest Income", "Net Interest Margin")
    ]

    for term_a, term_b in pairs_to_check:
        va = e.embed_text(term_a)
        vb = e.embed_text(term_b)
        sim = e.cosine_similarity(va, vb)
        # Upper threshold is 0.88; these sharing words must stay strictly below 0.88
        assert sim < 0.88, f"False merge risk! '{term_a}' and '{term_b}' cosine sim is {sim:.4f} >= 0.88"

    # Also test end-to-end through RegistryEngine
    db_file = str(tmp_path / "test_multiword.db")
    engine = RegistryEngine(db_path=db_file)
    id_cf, _ = engine.resolve_metric("Operating Cash Flow")
    id_exp, _ = engine.resolve_metric("Operating Expense")
    assert id_cf != id_exp, "Operating Cash Flow and Operating Expense must not be merged!"

def test_registry_decisions_logs_model_used(tmp_path):
    db_file = str(tmp_path / "test_decisions.db")
    engine = RegistryEngine(db_path=db_file)

    engine.resolve_entity("Delhivery Limited")
    engine.resolve_entity("Delhivery")  # Auto-alias
    engine.resolve_metric("EBITDA")
    engine.resolve_metric("EBITDA (₹Cr)")  # Auto-alias

    conn = engine.get_connection() if hasattr(engine, "get_connection") else None
    import sqlite3
    c = sqlite3.connect(db_file)
    rows = c.execute("SELECT mention_text, target_type, decision_type, model_used FROM registry_decisions").fetchall()
    c.close()

    assert len(rows) >= 4
    for r in rows:
        assert r[3] is not None and len(r[3]) > 0
        assert r[3] in ["deterministic", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]

def test_separate_metric_and_scope_disentangles_geographic_segments():
    from backend.canonicalize.fact_service import separate_metric_and_scope

    # Segment table: (1) Net sales by reportable segment
    m, s = separate_metric_and_scope(
        metric_mention="Americas",
        scope_mention=None,
        definition_mention="(1) Net sales by reportable segment",
        claim_text="Net sales in the Americas segment are $162,560."
    )
    assert m == "Net sales"
    assert s == "Americas"

    m2, s2 = separate_metric_and_scope(
        metric_mention="Europe",
        scope_mention=None,
        definition_mention="(1) Net sales by reportable segment",
        claim_text="Net sales in Europe are 94,294."
    )
    assert m2 == "Net sales"
    assert s2 == "Europe"

    # Standalone EPS modifier contextualization
    m3, s3 = separate_metric_and_scope(
        metric_mention="Diluted",
        scope_mention=None,
        definition_mention="Shares used in computing earnings per share",
        claim_text="Diluted shares total 15,812,547."
    )
    assert m3 == "Diluted shares"

def test_dynamic_failover_to_qwen_on_429(tmp_path, monkeypatch):
    """
    Simulates a 429 rate limit with retry-after on primary model (gpt-oss-120b),
    verifying automatic dynamic failover to qwen3.8-27b and model provenance logging.
    """
    import json
    import httpx
    from backend.extract.client import GroqClient

    call_models = []

    class MockResponse:
        def __init__(self, status_code, json_data, headers=None):
            self.status_code = status_code
            self._json = json_data
            self.headers = headers or {}
            self.text = json.dumps(json_data)

        def json(self):
            return self._json

    def mock_post(url, headers=None, json=None):
        requested_model = json.get("model")
        call_models.append(requested_model)
        if "120b" in requested_model:
            # Return 429 rate limit with retry-after
            return MockResponse(
                429,
                {"error": {"message": "Rate limit exceeded. Please try again in 6.0s"}},
                {"retry-after": "6.0"}
            )
        else:
            # Fallback model succeeds
            return MockResponse(
                200,
                {
                    "model": requested_model,
                    "choices": [{
                        "message": {
                            "content": '{"decision": "new_entry", "matched_id": null, "canonical_name": "Operating Metric X", "reason": "Distinct operational metric"}'
                        }
                    }]
                }
            )

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, headers=None, json=None: mock_post(url, headers, json))

    client = GroqClient(api_key="mock_key")
    res = client.chat_completion(
        messages=[{"role": "user", "content": "Adjudicate metric"}],
        model_role="canonicalizer_fast",
        response_json=True
    )

    assert "qwen/qwen3.8-27b" in call_models, f"Expected qwen/qwen3.8-27b in calls, got {call_models}"
    assert res.get("_model_used") == "qwen/qwen3.8-27b"

    # End-to-end through RegistryEngine to verify model_used persistence in registry_decisions
    db_file = str(tmp_path / "test_failover_db.db")
    engine = RegistryEngine(db_path=db_file, groq_client=client)

    # Force middle-band adjudication
    # Pre-populate an initial metric to compare against
    engine.resolve_metric("Standard Revenue")
    # A candidate that lands in the middle band (sim ~0.7-0.8)
    engine.resolve_metric("Operating Inflow", context="Context")

    import sqlite3
    c = sqlite3.connect(db_file)
    qwen_rows = c.execute("SELECT mention_text, decision_type, model_used FROM registry_decisions WHERE model_used = 'qwen/qwen3.8-27b'").fetchall()
    c.close()

    assert len(qwen_rows) > 0, "Expected registry_decisions to contain a row with model_used = 'qwen/qwen3.8-27b'"
    assert qwen_rows[0][2] == "qwen/qwen3.8-27b"


