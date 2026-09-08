"""
FactLoom Query Parser & Canonicalizer
Extracts entity, metric, period, and scope mentions from natural language questions
and resolves them against the dynamic RegistryEngine.
Zero hardcoded starter-set tokens.
"""

import re
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.extract.client import GroqClient
from backend.canonicalize.registry import RegistryEngine

logger = logging.getLogger(__name__)

QUERY_PARSER_SYSTEM_PROMPT = """You are a precise financial and macroeconomic query parser.
Given a user's natural language question about financial statements, macroeconomic indicators, corporate governance, or operating metrics:
Extract the following structured fields:
- entity_mention: The primary corporate, governmental, or individual entity being asked about (e.g., company name, sovereign country, individual person). If not mentioned, null.
- metric_mention: The core metric, indicator, role, or concept being asked about (e.g., "Revenue", "Operating Margin", "Directorship", "Annual Growth", "Customer Headcount").
- period_mention: The explicit time period or fiscal period mentioned in the question (e.g., "FY24", "Q4 FY24", "2024-25", "2023"). If NO time period is explicitly mentioned in the question, return null.
- scope_mention: Any specific geographical, segmental, or divisional slice mentioned. If none, null.

Respond ONLY with a valid JSON object matching this schema:
{
  "entity_mention": string or null,
  "metric_mention": string,
  "period_mention": string or null,
  "scope_mention": string or null
}
"""

class ParsedQuery(BaseModel):
    entity_mention: Optional[str] = None
    metric_mention: Optional[str] = None
    period_mention: Optional[str] = None
    scope_mention: Optional[str] = None
    canonical_entity: Optional[str] = None
    canonical_metric: Optional[str] = None
    raw_question: str = ""

class QueryParser:
    def __init__(
        self,
        registry_engine: Optional[RegistryEngine] = None,
        groq_client: Optional[GroqClient] = None
    ):
        self.registry = registry_engine or RegistryEngine()
        self.client = groq_client or GroqClient()

    def parse_question(self, question: str) -> ParsedQuery:
        """
        Parse natural language question into canonicalized search criteria.
        """
        q = question.strip()
        parsed_dict = self._llm_parse(q)
        if not parsed_dict:
            parsed_dict = self._heuristic_fallback_parse(q)

        entity_m = parsed_dict.get("entity_mention")
        metric_m = parsed_dict.get("metric_mention")
        period_m = parsed_dict.get("period_mention")
        scope_m = parsed_dict.get("scope_mention")

        canonical_entity = None
        canonical_metric = None

        if entity_m:
            res_e = self.registry.resolve_entity(entity_m)
            canonical_entity = res_e[1] if isinstance(res_e, (tuple, list)) else str(res_e)
        if metric_m:
            res_m = self.registry.resolve_metric(metric_m)
            canonical_metric = res_m[1] if isinstance(res_m, (tuple, list)) else str(res_m)

        return ParsedQuery(
            entity_mention=entity_m,
            metric_mention=metric_m,
            period_mention=period_m,
            scope_mention=scope_m,
            canonical_entity=canonical_entity,
            canonical_metric=canonical_metric,
            raw_question=q
        )

    def _llm_parse(self, question: str) -> Optional[Dict[str, Any]]:
        """Call Groq to extract structured query components."""
        messages = [
            {"role": "system", "content": QUERY_PARSER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}"}
        ]
        try:
            resp = self.client.chat_completion(
                messages=messages,
                model_role="query_parser",
                temperature=0.0,
                response_json=True
            )
            if isinstance(resp, dict) and (resp.get("metric_mention") or resp.get("entity_mention")):
                return resp
        except Exception as e:
            logger.warning(f"Query parser LLM extraction failed: {e}. Using heuristic fallback.")
        return None

    def _heuristic_fallback_parse(self, question: str) -> Dict[str, Any]:
        """
        Deterministic regex fallback for question parsing.
        Zero hardcoded domain tokens.
        """
        entity = None
        metric = None
        period = None
        scope = None

        q = question.strip()

        # 1. Detect fiscal years / dates
        m_fy = re.search(r'\b(FY\s*\d{2,4}|Q[1-4]\s*FY\s*\d{2,4}|\d{4}-\d{2,4}|\d{4})\b', q, re.IGNORECASE)
        if m_fy:
            period = m_fy.group(1).strip()

        # 2. Possessive entity extraction: "What was [Entity]'s [Metric]?"
        cleaned_prefix = re.sub(r'^(?:what\s+(?:was|is|are)|how\s+many|tell\s+me\s+about)\s+', '', q, flags=re.IGNORECASE).strip()
        m_poss = re.search(r"\b([A-Z][a-zA-Z\s]+?)'s\s+(.+?)(?:\s*\?|$)", cleaned_prefix)
        if m_poss:
            entity = m_poss.group(1).strip()
            cand_metric = m_poss.group(2).strip()
            if period:
                cand_metric = re.sub(r'\b' + re.escape(period) + r'\b', '', cand_metric, flags=re.IGNORECASE).strip()
            metric = cand_metric

        # 3. "Is [Entity] currently a [Role] at [Company]?"
        if not entity:
            m_is = re.search(r"Is\s+([A-Z][a-zA-Z\s]+?)\s+(?:currently\s+)?a\s+([A-Za-z\s]+?)(?:\s+at|\s+in|\s*\?|$)", q, re.IGNORECASE)
            if m_is:
                entity = m_is.group(1).strip()
                metric = m_is.group(2).strip()

        # 4. "How many [Metric] does [Entity] have in [Period]?"
        if not entity:
            m_how_many = re.search(r"how\s+many\s+([A-Za-z\s]+?)\s+does\s+([A-Z][a-zA-Z\s]+?)\s+(?:have|report)", q, re.IGNORECASE)
            if m_how_many:
                metric = m_how_many.group(1).strip()
                entity = m_how_many.group(2).strip()

        # 5. "What was [Entity] [Metric]...?"
        if not metric:
            m_what = re.search(r"what\s+(?:was|is)\s+([A-Za-z\s]+?)(?:\s*\?|$)", q, re.IGNORECASE)
            if m_what:
                metric = m_what.group(1).strip()

        return {
            "entity_mention": entity,
            "metric_mention": metric or q,
            "period_mention": period,
            "scope_mention": scope
        }
