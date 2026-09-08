"""
Unit and integration tests for FactLoom Query & Answer Engine (Phase 5).
Tests:
- Query parser extraction and period normalization
- Citation validator token extraction, resolution audit, and hallucination backstop
- Ambiguity detection and multi-fact abstention logic
- REST endpoint POST /ask
"""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.query.parser import QueryParser, ParsedQuery
from backend.query.retriever import KnowledgeRetriever, RetrievalResult, RetrievedFact, RetrievedObservation, RetrievedRelationship
from backend.query.citation_validator import CitationValidator
from backend.query.synthesizer import AnswerSynthesizer, QueryAnswerResponse
from backend.query.service import QueryService
from backend.query.seed_cases import seed_demo_cases

@pytest.fixture(scope="module", autouse=True)
def setup_test_cases():
    seed_demo_cases()

def test_query_parser_heuristic_fallback():
    parser = QueryParser()
    # Test heuristic fallback parsing directly
    res = parser._heuristic_fallback_parse("What was Delhivery's FY24 EBITDA?")
    assert res["entity_mention"] == "Delhivery"
    assert "EBITDA" in res["metric_mention"]
    assert res["period_mention"] == "FY24"

    # Ambiguous question with no period
    res_ambig = parser._heuristic_fallback_parse("What is India's GDP growth?")
    assert res_ambig["entity_mention"] == "India"
    assert "GDP growth" in res_ambig["metric_mention"]
    assert res_ambig["period_mention"] is None

    # Director inquiry
    res_dir = parser._heuristic_fallback_parse("Is Suvir Sujan currently a director at Delhivery?")
    assert res_dir["entity_mention"] == "Suvir Sujan"
    assert "director" in res_dir["metric_mention"].lower()

def test_citation_validator_extract_tokens():
    validator = CitationValidator()
    text = "Figure 1 [cite:obs_abc123] corroborates with figure 2 [cite:obs_def456] and [obs_ghi789]."
    tokens = validator.extract_citation_tokens(text)
    assert "obs_abc123" in tokens
    assert "obs_def456" in tokens
    assert "obs_ghi789" in tokens
    assert len(tokens) == 3

def test_citation_validator_catches_hallucinated_ids():
    validator = CitationValidator()
    text = "Here is verified observation [cite:obs_nonexistent_fake_999]."
    result = validator.validate_answer(text)
    assert result.is_valid is False
    assert result.resolution_rate_pct == 0.0
    assert "obs_nonexistent_fake_999" not in result.cleaned_answer

def test_ambiguity_abstention_triggers_on_multi_facts():
    # Setup mock retrieval with 2 distinct facts not unified by SAME_AS
    retrieval = RetrievalResult(
        facts=[
            RetrievedFact(
                id="fact_1", entity_name="India", metric_name="Real GDP Growth",
                period="FY24", measurement_type="actual", observation_count=1
            ),
            RetrievedFact(
                id="fact_2", entity_name="India", metric_name="Real GDP Growth",
                period="FY25", measurement_type="estimate", observation_count=1
            )
        ],
        observations=[
            RetrievedObservation(
                id="obs_1", fact_id="fact_1", document_id="doc_1", document_filename="rbi.pdf",
                page_number=24, value="8.2%", quote_span="8.2%"
            ),
            RetrievedObservation(
                id="obs_2", fact_id="fact_2", document_id="doc_2", document_filename="econ.pdf",
                page_number=1, value="6.4%", quote_span="6.4%"
            )
        ],
        relationships=[]
    )

    mock_client = MagicMock()
    # Force fallback synthesis to inspect deterministic ambiguity abstention
    mock_client.chat_completion.side_effect = Exception("LLM fallback")
    synthesizer = AnswerSynthesizer(groq_client=mock_client)

    parsed = ParsedQuery(
        raw_question="What is India's GDP growth?",
        canonical_entity="India",
        canonical_metric="Real GDP Growth",
        period_mention=None
    )

    resp = synthesizer.answer_query(parsed, retrieval)
    assert resp.is_ambiguous is True
    assert "Abstaining from a single merged figure" in (resp.abstention_reason or "")
    assert len(resp.facts) == 2

def test_post_ask_api_endpoint():
    client = TestClient(app)
    response = client.post("/ask", json={"question": "What was Delhivery's FY24 EBITDA?"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["citations"]) >= 2
    assert ("1,266" in data["answer"] or "127" in data["answer"])

def test_post_ask_empty_question_rejected():
    client = TestClient(app)
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 400
