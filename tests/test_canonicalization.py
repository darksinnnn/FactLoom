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

