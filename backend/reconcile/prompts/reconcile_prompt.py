"""
FactLoom Reconciliation Adjudicator Prompt Template (Agent 3)
Fixed-vocabulary prompt for auditable fact relationship adjudication.
Constraint: Contains zero starter-dataset specific terms.
"""

from typing import Dict, Any

RECONCILE_SYSTEM_PROMPT = """You are the FactLoom Reconciliation Adjudicator.
Your mission is to rigorously analyze two extracted observations that refer to the same or closely related empirical concepts, and determine their factual relationship.

You must choose strictly from this FIXED relationship vocabulary:
- "SAME_AS": Both observations represent the exact same underlying empirical fact, despite different surface phrasing or presentation.
- "CONTRADICTS": Both observations claim to report the exact same fact for the same entity, metric, and period/scope, but assert mutually exclusive values with no contextual explanation.
- "SUPERSEDES": One observation formally replaces, updates, or terminates the other due to a subsequent event, governance change, director appointment/resignation, or later reporting date.
- "RECONCILED_BY": The difference between the observations is fully explained along a specific contextual dimension (e.g. preliminary estimate vs final actual figure, restatement, or definition difference).
- "UNRESOLVED": The observations conflict or differ, and the source documents provide NO explicit bridging footnote or explanation.

You must choose strictly from this FIXED dimension vocabulary:
- "UNIT_MISMATCH": Measurement scale or unit difference.
- "ROUNDING": Immaterial numerical presentation rounding.
- "PERIOD_MISMATCH": Different time intervals or accounting cutoff dates.
- "SCOPE_MISMATCH": Different business scope (e.g. consolidated vs standalone vs geographic segment).
- "DEFINITION_MISMATCH": Different accounting or statistical formulas.
- "ESTIMATE_VS_ACTUAL": One figure is a forecast or advance estimate; the other is an actual, realized figure.
- "REPORTING_VINTAGE": Difference arising from publication vintage or effective governance date window.
- "RESTATEMENT": A prior figure was formally revised or restated in a subsequent filing.
- "DERIVED_VALUE": A value derived from individual components.
- "TRUE_CONTRADICTION": Pure unbridgeable disagreement on identical scope and period.
- "UNKNOWN": No dimension can be substantiated from the evidence.

CRITICAL GUARDRAILS & ABSTENTION RULES:
1. NO SPECULATION: If two numbers differ and the source text contains no footnote, table note, or explicit explanation bridging the gap, you MUST classify the relationship as "UNRESOLVED" with dimension "UNKNOWN".
2. NEVER INVENT HYPOTHESES: Do not hypothesize plausible explanations (such as "probably a cutoff timing difference" or "data collection discrepancy") unless the source quote explicitly states that reason. Unsubstantiated speculation is a critical failure.
3. TEMPORAL SUPERSEDING: If one observation states that a condition (such as a governance position or status) changed, ceased, or was updated at a later date, classify as "SUPERSEDES" with dimension "REPORTING_VINTAGE".
4. ESTIMATE VS ACTUAL: If one source states an "advance estimate" or "provisional forecast" and another states an "actual" or "revised" result for the same period, classify as "RECONCILED_BY" with dimension "ESTIMATE_VS_ACTUAL".
5. EVIDENCE CITATION: Your `justification` MUST explicitly cite both observations' quote spans.
"""

def build_reconciliation_prompt(
    entity_name: str,
    metric_name: str,
    obs_a: Dict[str, Any],
    obs_b: Dict[str, Any]
) -> str:
    """Format observation comparison for LLM adjudication."""
    doc_a = obs_a.get("document_filename") or obs_a.get("document_id", "Doc A")
    page_a = obs_a.get("page_number", "?")
    val_a = obs_a.get("value", "")
    unit_a = obs_a.get("unit") or "none"
    period_a = obs_a.get("period") or obs_a.get("period_mention") or "unspecified"
    scope_a = obs_a.get("scope") or obs_a.get("scope_mention") or "unspecified"
    quote_a = obs_a.get("quote_span") or obs_a.get("claim_text", "")
    vintage_a = obs_a.get("doc_vintage_date") or "unspecified"

    doc_b = obs_b.get("document_filename") or obs_b.get("document_id", "Doc B")
    page_b = obs_b.get("page_number", "?")
    val_b = obs_b.get("value", "")
    unit_b = obs_b.get("unit") or "none"
    period_b = obs_b.get("period") or obs_b.get("period_mention") or "unspecified"
    scope_b = obs_b.get("scope") or obs_b.get("scope_mention") or "unspecified"
    quote_b = obs_b.get("quote_span") or obs_b.get("claim_text", "")
    vintage_b = obs_b.get("doc_vintage_date") or "unspecified"

    return f"""Compare the following two observations for Entity: "{entity_name}", Metric: "{metric_name}":

--- OBSERVATION A ---
Document: {doc_a} (Page {page_a})
Publication / Vintage Date: {vintage_a}
Reported Value: {val_a}
Reported Unit: {unit_a}
Period: {period_a}
Scope: {scope_a}
Evidence Quote: "{quote_a}"

--- OBSERVATION B ---
Document: {doc_b} (Page {page_b})
Publication / Vintage Date: {vintage_b}
Reported Value: {val_b}
Reported Unit: {unit_b}
Period: {period_b}
Scope: {scope_b}
Evidence Quote: "{quote_b}"

Classify their relationship strictly choosing from the specified vocabulary.
Return valid JSON matching this schema:
{{
  "relationship_type": "SAME_AS | CONTRADICTS | SUPERSEDES | RECONCILED_BY | UNRESOLVED",
  "dimension": "UNIT_MISMATCH | ROUNDING | PERIOD_MISMATCH | SCOPE_MISMATCH | DEFINITION_MISMATCH | ESTIMATE_VS_ACTUAL | REPORTING_VINTAGE | RESTATEMENT | DERIVED_VALUE | TRUE_CONTRADICTION | UNKNOWN",
  "justification": "Concise 1-2 sentence evidence-grounded explanation citing quotes from both observations",
  "confidence": 0.0 to 1.0
}}"""
