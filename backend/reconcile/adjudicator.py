"""
FactLoom LLM Reconciliation Adjudicator (Tier 2)
Orchestrates Agent 3 with Groq model routing (gpt-oss-120b / qwen3.8-27b),
strict enum validation, and fail-safe abstention defaults.
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

from backend.extract.client import GroqClient
from backend.reconcile.prompts.reconcile_prompt import (
    RECONCILE_SYSTEM_PROMPT,
    build_reconciliation_prompt
)

logger = logging.getLogger(__name__)

class RelationshipType(str, Enum):
    SAME_AS = "SAME_AS"
    CONTRADICTS = "CONTRADICTS"
    SUPERSEDES = "SUPERSEDES"
    RECONCILED_BY = "RECONCILED_BY"
    UNRESOLVED = "UNRESOLVED"

class ReconciliationDimension(str, Enum):
    UNIT_MISMATCH = "UNIT_MISMATCH"
    ROUNDING = "ROUNDING"
    PERIOD_MISMATCH = "PERIOD_MISMATCH"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    DEFINITION_MISMATCH = "DEFINITION_MISMATCH"
    ESTIMATE_VS_ACTUAL = "ESTIMATE_VS_ACTUAL"
    REPORTING_VINTAGE = "REPORTING_VINTAGE"
    RESTATEMENT = "RESTATEMENT"
    DERIVED_VALUE = "DERIVED_VALUE"
    TRUE_CONTRADICTION = "TRUE_CONTRADICTION"
    UNKNOWN = "UNKNOWN"

class ReconciliationDecision(BaseModel):
    relationship_type: RelationshipType
    dimension: ReconciliationDimension
    justification: str = Field(description="Evidence-grounded explanation citing both observations")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)

class ReconciliationAdjudicator:
    def __init__(self, groq_client: Optional[GroqClient] = None):
        self.client = groq_client or GroqClient()

    def adjudicate(
        self,
        entity_name: str,
        metric_name: str,
        obs_a: Dict[str, Any],
        obs_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adjudicate relationship between two candidate observations using LLM.
        Strictly validates output against the locked taxonomy enum.
        """
        user_prompt = build_reconciliation_prompt(
            entity_name=entity_name,
            metric_name=metric_name,
            obs_a=obs_a,
            obs_b=obs_b
        )

        messages = [
            {"role": "system", "content": RECONCILE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        try:
            resp = self.client.chat_completion(
                messages=messages,
                model_role="reconciliation_adjudicator",
                temperature=0.0,
                response_json=True,
                reasoning_effort="low"
            )

            model_used = resp.get("_model_used", "openai/gpt-oss-120b")
            validated = ReconciliationDecision.model_validate(resp)

            return {
                "relationship_type": validated.relationship_type.value,
                "dimension": validated.dimension.value,
                "justification": validated.justification,
                "confidence": validated.confidence,
                "model_used": model_used,
                "tier": "llm_adjudicated"
            }

        except Exception as e:
            logger.warning(f"Reconciliation adjudication call failed or returned invalid schema: {e}. Defaulting to UNRESOLVED.")
            return {
                "relationship_type": "UNRESOLVED",
                "dimension": "UNKNOWN",
                "justification": f"Adjudication error ({type(e).__name__}): abstained to UNRESOLVED without guessing.",
                "confidence": 0.5,
                "model_used": "fallback",
                "tier": "llm_adjudicated"
            }
