"""
FactLoom Extraction Data Schema
Open-schema fact candidate models per architecture.md §2.2 and agents.md Agent 1.
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field

class FactCandidate(BaseModel):
    """An open-schema atomic fact candidate extracted from document content."""
    entity_mention: Optional[str] = Field(
        default="Unknown",
        description="The entity or organization this fact pertains to (e.g. company, agency, country, person)."
    )
    metric_mention: str = Field(
        ...,
        description="The metric or property being reported (e.g. revenue, profit, headcount, interest rate)."
    )
    value: str = Field(
        ...,
        description="The verbatim numerical or qualitative value reported."
    )
    unit: Optional[str] = Field(
        None,
        description="The unit of measurement (e.g. %, currency, count, ratio, days) if stated."
    )
    period_mention: Optional[str] = Field(
        None,
        description="The time period or reporting date (e.g. annual period, quarter, year, specific date) if stated."
    )
    scope_mention: Optional[str] = Field(
        None,
        description="The operational or accounting scope (e.g. consolidated, standalone, segment, national) if stated."
    )
    definition_mention: Optional[str] = Field(
        None,
        description="Any line-item definition, calculation formula, or contextual qualification provided in the text/table."
    )
    claim_text: str = Field(
        ...,
        description="A concise one-sentence factual statement summarizing this observation."
    )
    quote_span: str = Field(
        ...,
        description="A short, exact verbatim substring from the source text that proves this claim."
    )
    confidence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0."
    )

class ExtractionResponse(BaseModel):
    """Container for batch fact candidates returned by the extraction agent."""
    candidates: List[FactCandidate] = Field(
        default_factory=list,
        description="List of extracted fact candidates."
    )
