"""
Unit tests for FactExtractor grounding verification and schema validation.
Runs offline with simulated model responses to test deterministic verification logic.
"""

import pytest
from backend.ingest.parser import ParsedPage
from backend.extract.extractor import FactExtractor

class MockGroqClient:
    def __init__(self, mock_response):
        self.mock_response = mock_response

    def chat_completion(self, messages, model_role="extractor", temperature=0.0, response_json=True, **kwargs):
        return self.mock_response

def test_grounding_verification_accepts_literal_quote():
    page_text = "Delhivery reported FY24 EBITDA of INR 1,266.41 million compared to a loss in FY23."
    mock_response = {
        "candidates": [
            {
                "entity_mention": "Delhivery",
                "metric_mention": "EBITDA",
                "value": "1,266.41",
                "unit": "INR million",
                "period_mention": "FY24",
                "scope_mention": "Consolidated",
                "definition_mention": None,
                "claim_text": "Delhivery reported FY24 EBITDA of 1,266.41 million.",
                "quote_span": "EBITDA of INR 1,266.41 million",
                "confidence": 0.95
            }
        ]
    }
    
    page = ParsedPage(
        page_number=1,
        width=595.0,
        height=842.0,
        text_blocks=[{"text": page_text, "bbox": [50.0, 100.0, 500.0, 120.0]}],
        table_blocks=[],
        full_text=page_text,
        has_text_layer=True,
        is_scanned=False
    )

    extractor = FactExtractor(client=MockGroqClient(mock_response))
    records = extractor.extract_from_page(page)

    assert len(records) == 1
    assert records[0]["value"] == "1,266.41"
    assert records[0]["quote_span"] == "EBITDA of INR 1,266.41 million"
    assert records[0]["bbox"] == [50.0, 100.0, 500.0, 120.0]

def test_grounding_verification_rejects_hallucinated_quote():
    page_text = "Company revenue was 5,000 million."
    mock_response = {
        "candidates": [
            {
                "entity_mention": "Company",
                "metric_mention": "Profit",
                "value": "999",
                "unit": "million",
                "period_mention": None,
                "scope_mention": None,
                "definition_mention": None,
                "claim_text": "Profit was 999 million.",
                "quote_span": "Hallucinated quote not in text",
                "confidence": 0.8
            }
        ]
    }

    page = ParsedPage(
        page_number=1,
        width=595.0,
        height=842.0,
        text_blocks=[{"text": page_text, "bbox": [50.0, 100.0, 500.0, 120.0]}],
        table_blocks=[],
        full_text=page_text,
        has_text_layer=True,
        is_scanned=False
    )

    extractor = FactExtractor(client=MockGroqClient(mock_response))
    records = extractor.extract_from_page(page)

    # Must be dropped due to failed quote_span grounding!
    assert len(records) == 0
