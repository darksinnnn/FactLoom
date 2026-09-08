"""
FactLoom Answer Synthesizer & Ambiguity Engine
Synthesizes evidence-grounded answers citing explicit observations,
adheres to multi-fact abstention rules when un-unified candidates exist,
and embeds verified reconciliation reasoning.
Zero hardcoded starter-set tokens.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.extract.client import GroqClient
from backend.query.parser import ParsedQuery
from backend.query.retriever import RetrievalResult, RetrievedFact, RetrievedObservation, RetrievedRelationship
from backend.query.citation_validator import CitationValidator, CitationValidationResult

logger = logging.getLogger(__name__)

def _parse_bbox(bbox_json: Optional[str]) -> Optional[List[float]]:
    """Safely parse bbox JSON string to float list."""
    if not bbox_json:
        return None
    try:
        parsed = json.loads(bbox_json)
        if isinstance(parsed, list) and len(parsed) == 4:
            return [float(x) for x in parsed]
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return None

class AnswerCitation(BaseModel):
    observation_id: str
    fact_id: str
    document_id: str = ""
    document_filename: str
    page_number: int
    value: str
    unit: Optional[str] = None
    quote: str
    quote_span: Optional[str] = None  # alias for quote for frontend compatibility
    bbox: Optional[List[float]] = None

class QueryAnswerResponse(BaseModel):
    question: str
    parsed_query: ParsedQuery
    answer: str
    is_ambiguous: bool = False
    abstention_reason: Optional[str] = None
    facts: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[AnswerCitation] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    citation_validation: Optional[CitationValidationResult] = None

SYNTHESIZER_SYSTEM_PROMPT = """You are FactLoom's grounded financial and macroeconomic query responder.
You are provided with verified Facts, Observations (with literal quotes, document names, and page numbers),
and Reconciled Relationships between these observations.

RULES:
1. Strict Grounding: State ONLY facts directly supported by the provided observations. NEVER invent figures, dates, or explanations.
2. Mandatory Citations: Every single factual figure or status claim MUST be followed immediately by its observation citation tag, formatted exactly as `[cite:observation_id]`.
3. Reconciliation Transparency:
   - If observations corroborate with a `SAME_AS` relationship, explain the dimension (e.g. unit mismatch, presentation rounding).
   - If observations have an `UNRESOLVED` relationship (e.g. conflicting counts without an explanatory footnote), present both numbers clearly and EXPLICITLY state that the sources provide no footnote or explanation bridging the gap. DO NOT invent hypotheses.
   - If observations have a `SUPERSEDES` relationship (e.g. director directorship status change over time), explain which filing is later and what change occurred.
   - If observations have a `RECONCILED_BY` / `ESTIMATE_VS_ACTUAL` relationship, distinguish the advance estimate from the official reported actual.
4. Ambiguity / Multi-Fact Abstention:
   - If multiple distinct Facts exist (e.g. different periods or measures) and the user question did not specify which one, present all distinct facts labeled clearly by their period/scope. DO NOT average or collapse them into a single number.
5. Output JSON: Respond with a valid JSON object with a single key "answer" containing your cited answer text:
   {"answer": "Your complete grounded response with [cite:obs_id] tags."}
"""

class AnswerSynthesizer:
    def __init__(
        self,
        groq_client: Optional[GroqClient] = None,
        citation_validator: Optional[CitationValidator] = None
    ):
        self.client = groq_client or GroqClient()
        self.validator = citation_validator or CitationValidator()

    def answer_query(
        self,
        parsed_query: ParsedQuery,
        retrieval: RetrievalResult
    ) -> QueryAnswerResponse:
        """
        Generate grounded answer, detect ambiguity, and audit citations.
        """
        if not retrieval.facts or not retrieval.observations:
            return QueryAnswerResponse(
                question=parsed_query.raw_question,
                parsed_query=parsed_query,
                answer="No grounded facts matching this inquiry were found in the current document repository.",
                is_ambiguous=False,
                facts=[],
                citations=[],
                relationships=[]
            )

        # 1. Ambiguity & Multi-Fact Abstention Check
        # If the query resolved to multiple Facts and NO 'SAME_AS' relationship unifies them:
        is_ambiguous = False
        abstention_reason = None

        if len(retrieval.facts) > 1:
            periods = sorted(list({f.period for f in retrieval.facts if f.period and f.period.lower() != "unspecified"}))
            # If inquiry covers multiple distinct periods and user didn't specify a single period:
            if len(periods) > 1 and not parsed_query.period_mention:
                is_ambiguous = True
                abstention_reason = (
                    f"The inquiry resolves to {len(retrieval.facts)} distinct facts across periods ({', '.join(periods)}). "
                    f"Abstaining from a single merged figure per ambiguity protocol; presenting all labeled facts."
                )
            else:
                # Check if any relationship between the facts unifies them
                same_as_relationships = [r for r in retrieval.relationships if r.type == "SAME_AS"]
                if not same_as_relationships:
                    is_ambiguous = True
                    abstention_reason = (
                        f"The inquiry resolves to {len(retrieval.facts)} distinct facts with no unifying relationship. "
                        f"Abstaining from a single merged figure per ambiguity protocol; presenting all labeled facts."
                    )

        # 2. Synthesize Answer (via LLM with deterministic template fallback)
        raw_answer = self._generate_answer_text(parsed_query, retrieval, is_ambiguous, abstention_reason)

        # 3. Deterministic Citation Validation
        obs_id_set = {o.id for o in retrieval.observations}
        fact_id_set = {f.id for f in retrieval.facts}
        val_result = self.validator.validate_answer(
            raw_answer,
            valid_observation_ids=obs_id_set,
            valid_fact_ids=fact_id_set
        )

        # 4. Build Structured Citations List
        citations_list: List[AnswerCitation] = []
        cited_obs_ids = self.validator.extract_citation_tokens(raw_answer)
        obs_lookup = {o.id: o for o in retrieval.observations}

        for cid in cited_obs_ids:
            if cid in obs_lookup:
                ob = obs_lookup[cid]
                citations_list.append(AnswerCitation(
                    observation_id=ob.id,
                    fact_id=ob.fact_id,
                    document_id=ob.document_id,
                    document_filename=ob.document_filename,
                    page_number=ob.page_number,
                    value=ob.value,
                    unit=ob.unit,
                    quote=ob.quote_span,
                    quote_span=ob.quote_span,
                    bbox=_parse_bbox(ob.bbox_json)
                ))

        # Fallback if LLM omitted cite tags: attach all retrieved observations
        if not citations_list:
            for ob in retrieval.observations:
                citations_list.append(AnswerCitation(
                    observation_id=ob.id,
                    fact_id=ob.fact_id,
                    document_id=ob.document_id,
                    document_filename=ob.document_filename,
                    page_number=ob.page_number,
                    value=ob.value,
                    unit=ob.unit,
                    quote=ob.quote_span,
                    quote_span=ob.quote_span,
                    bbox=_parse_bbox(ob.bbox_json)
                ))

        # Format facts for response
        facts_payload = [f.model_dump() for f in retrieval.facts]
        relationships_payload = [r.model_dump() for r in retrieval.relationships]

        return QueryAnswerResponse(
            question=parsed_query.raw_question,
            parsed_query=parsed_query,
            answer=val_result.cleaned_answer,
            is_ambiguous=is_ambiguous,
            abstention_reason=abstention_reason,
            facts=facts_payload,
            citations=citations_list,
            relationships=relationships_payload,
            citation_validation=val_result
        )

    def _generate_answer_text(
        self,
        parsed_query: ParsedQuery,
        retrieval: RetrievalResult,
        is_ambiguous: bool,
        abstention_reason: Optional[str]
    ) -> str:
        """Call Groq to draft grounded answer with fallback to deterministic synthesis."""
        # Prepare compact context payload for prompt (strictly bounded to fit model limits)
        facts_summary = []
        for f in retrieval.facts[:6]:
            facts_summary.append(
                f"- Fact [{f.id}]: {f.entity_name} | {f.metric_name} | Period: {f.period} | Scope: {f.scope or 'Consolidated'}"
            )

        obs_summary = []
        for o in retrieval.observations[:8]:
            quote_text = o.quote_span[:90] + "..." if len(o.quote_span) > 90 else o.quote_span
            obs_summary.append(
                f"- Observation [{o.id}] (under Fact {o.fact_id}): Value: {o.value} {o.unit or ''} | "
                f"Source: {o.document_filename} (p.{o.page_number}) | Quote: \"{quote_text}\""
            )

        rel_summary = []
        for r in retrieval.relationships[:6]:
            rel_summary.append(
                f"- Relationship: [{r.observation_a_id}] <-> [{r.observation_b_id}] | "
                f"Type: {r.type} | Dimension: {r.dimension} | Justification: {r.justification[:100]}"
            )

        user_content = (
            f"User Question: {parsed_query.raw_question}\n\n"
            f"Ambiguity Status: {'AMBIGUOUS - Multiple distinct facts found. Return all labeled facts.' if is_ambiguous else 'SPECIFIC'}\n\n"
            f"RETRIEVED FACTS:\n" + "\n".join(facts_summary) + "\n\n"
            f"RETRIEVED OBSERVATIONS (Cite with [cite:observation_id]):\n" + "\n".join(obs_summary) + "\n\n"
            f"RECONCILED RELATIONSHIPS:\n" + ("\n".join(rel_summary) if rel_summary else "None") + "\n\n"
            f"Draft a concise, authoritative answer directly addressing the question. CITE EVERY FIGURE with [cite:obs_id]. "
            f"Respond with a JSON object: {{\"answer\": \"...\"}}."
        )

        messages = [
            {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        try:
            resp = self.client.chat_completion(
                messages=messages,
                model_role="answer_synthesizer",
                temperature=0.0,
                response_json=True,
                reasoning_effort="low"
            )
            ans = resp.get("answer") or resp.get("content") or resp.get("text") or ""
            if ans and len(ans.strip()) > 10:
                return ans.strip()
        except Exception as e:
            logger.warning(f"Answer synthesizer LLM call failed: {e}. Using deterministic fallback synthesis.")

        # Deterministic Fallback Synthesis
        return self._deterministic_fallback_synthesis(parsed_query, retrieval, is_ambiguous, abstention_reason)

    def _deterministic_fallback_synthesis(
        self,
        parsed_query: ParsedQuery,
        retrieval: RetrievalResult,
        is_ambiguous: bool,
        abstention_reason: Optional[str]
    ) -> str:
        """Deterministic fallback synthesis guaranteeing grounded output and citations."""
        lines = []

        if is_ambiguous:
            lines.append(f"The question is ambiguous across multiple distinct periods or metrics. Abstaining from a single merged figure:")
            for f in retrieval.facts:
                f_obs = [o for o in retrieval.observations if o.fact_id == f.id]
                obs_str = ", ".join([f"{o.value} {o.unit or ''} [cite:{o.id}] (p.{o.page_number} of {o.document_filename})" for o in f_obs])
                lines.append(f"- **{f.period}** ({f.entity_name} {f.metric_name}): {obs_str}")
            return "\n".join(lines)

        # Single Fact or unified facts
        fact = retrieval.facts[0]
        obs = retrieval.observations

        # Check relationships
        rels = retrieval.relationships
        if rels:
            r = rels[0]
            if r.type == "SAME_AS":
                lines.append(
                    f"For {fact.period}, {fact.entity_name} reported {fact.metric_name} across multiple documents that corroborate via {r.dimension}: "
                    + " vs ".join([f"{o.value} {o.unit or ''} [cite:{o.id}]" for o in obs])
                    + f". {r.justification}"
                )
            elif r.type == "UNRESOLVED":
                lines.append(
                    f"For {fact.period}, {fact.entity_name} reported conflicting values for {fact.metric_name}: "
                    + " vs ".join([f"\"{o.quote_span}\" ({o.value} {o.unit or ''}) [cite:{o.id}]" for o in obs])
                    + f". This discrepancy is **UNRESOLVED**: the documents provide no footnote or explanatory context reconciling the figures."
                )
            elif r.type == "SUPERSEDES":
                lines.append(
                    f"Regarding {fact.entity_name} {fact.metric_name}: "
                    + f"The earlier filing recorded {obs[0].value} [cite:{obs[0].id}], but the subsequent filing records {obs[1].value} [cite:{obs[1].id}], "
                    + f"which supersedes the earlier status ({r.justification})."
                )
            elif r.type == "RECONCILED_BY":
                lines.append(
                    f"For {fact.period}, {fact.entity_name} {fact.metric_name} is reconciled by {r.dimension}: "
                    + f"{obs[0].value} {obs[0].unit or ''} [cite:{obs[0].id}] is updated by {obs[1].value} {obs[1].unit or ''} [cite:{obs[1].id}]. "
                    + f"{r.justification}"
                )
            else:
                lines.append(
                    f"{fact.entity_name} {fact.metric_name} ({fact.period}): "
                    + ", ".join([f"{o.value} {o.unit or ''} [cite:{o.id}]" for o in obs])
                )
        else:
            lines.append(
                f"{fact.entity_name} reported {fact.metric_name} for {fact.period} as: "
                + ", ".join([f"{o.value} {o.unit or ''} [cite:{o.id}] in {o.document_filename} (p.{o.page_number})" for o in obs])
            )

        return "\n".join(lines)
