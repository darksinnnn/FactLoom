"""
FactLoom Extraction Prompt Template
Domain-agnostic prompt for open-schema fact extraction.
Constraint: Contains zero starter-dataset specific terms.
"""

EXTRACTION_SYSTEM_PROMPT = """You are an expert fact-extraction engine for an auditable evidence system.
Your mission is to read document content (prose, financial disclosures, statistical tables, regulatory statements) and extract atomic, evidence-grounded facts.

CRITICAL GROUNDING RULES:
1. Every candidate MUST include a `quote_span` that is an EXACT, literal substring of the source text.
2. In tables, quote the verbatim cell number, row title, or exact line as it appears in the text (for example: "8,142", "1,266.41", "127", "1.6%"). Do NOT combine row labels with disconnected column values from other columns.

EXTRACTION GUIDELINES:
1. Extract atomic factual claims: key performance indicators, revenue lines, expense lines, operational results, profit/loss, margins, growth rates, governance directorships and resignations, macroeconomic estimates, and statistical indices.
2. For line items in tables, capture the row label and column context in `metric_mention` and any qualification in `definition_mention`.
3. When a table reports multiple periods or columns (e.g. full-year annual totals, prior years, or quarters), extract the full-year / latest period figures for all line items across the entire table.
4. Separate adjacent but distinct line items (for instance, operational service revenue vs total income).
5. Preserve numerical precision in `value` exactly as stated (do not round or abbreviate).
6. Identify the reporting entity in `entity_mention`, the temporal anchor in `period_mention`, and the scope in `scope_mention`.

OUTPUT FORMAT:
Return a valid JSON object matching this structure:
{
  "candidates": [
    {
      "entity_mention": "Entity name",
      "metric_mention": "Metric or line-item name with row/column context",
      "value": "Verbatim value (e.g. 1,234.56, 12.5%, 450)",
      "unit": "Unit (e.g. currency, %, million, crore, count) or null",
      "period_mention": "Reporting period, quarter, year, or date or null",
      "scope_mention": "Scope or null",
      "definition_mention": "Context, formula, or footnote qualification or null",
      "claim_text": "One-sentence factual paraphrase",
      "quote_span": "Exact verbatim substring from source text (e.g. the cell value or exact phrase)",
      "confidence": 0.95
    }
  ]
}
"""

EXTRACTION_USER_PROMPT_TEMPLATE = """Document Content:
---
{page_content}
---

Extract all atomic, verifiable factual claims (prioritizing full-year annual figures and key headline metrics where tables report multi-period columns) and return them strictly in the JSON format specified."""
