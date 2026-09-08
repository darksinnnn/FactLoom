"""
FactLoom Canonicalization Prompts
Domain-agnostic prompts for middle-band entity and metric registry adjudication.
STRICT GUARDRAIL: Zero dataset-specific strings.
"""

from typing import List, Dict, Any, Optional

CANONICALIZE_SYSTEM_PROMPT = """You are FactLoom's Registry Adjudicator.
Your job is to determine whether an extracted mention in a document refers to the exact same underlying concept as an existing canonical registry entry, or whether it represents a distinct concept that must be given its own canonical entry.

RULES:
1. SEMANTIC DISTINCTIONS:
   - Specific qualifying modifiers (such as "Adjusted", "Core", "Headline", "Gross", "Net", "Underlying", "Normalized", "Diluted", "Basic", "Operating", "Non-operating") denote distinct formulas, scopes, or definitions. They MUST be kept distinct as a separate concept (choose "new_entry"), NOT merged into the base unqualified concept.
   - Distinct entity subsidiaries, legal entities, or distinct corporate tiers (e.g., Parent vs Subsidiary vs Segment) are distinct entities.

2. EQUIVALENCES AND ALIASES:
   - Different linguistic phrasing, syntactic variations, full expansions of standard acronyms/initialisms, or superficial unit suffixes (e.g. currency symbols or unit indicators appended in parentheses) that denote the exact same underlying metric are aliases (choose "alias_of").
   - Case differences, punctuation differences, and common abbreviations for identical entities are aliases (choose "alias_of").

3. OUTPUT FORMAT:
   Return valid JSON only matching this exact schema:
   {
     "decision": "alias_of" | "new_entry",
     "matched_id": "<id of the candidate entry if alias_of, or null>",
     "canonical_name": "<clean canonical name if new_entry, or null>",
     "reason": "<one concise sentence explaining the decision>"
   }
"""

def build_adjudication_prompt(
    target_type: str,
    mention_text: str,
    candidates: List[Dict[str, Any]],
    unit: Optional[str] = None,
    claim_context: Optional[str] = None
) -> str:
    """
    Build the user prompt for registry candidate adjudication.
    """
    prompt = f"TARGET TYPE: {target_type.upper()}\n"
    prompt += f"NEW MENTION: \"{mention_text}\"\n"
    if unit:
        prompt += f"UNIT: \"{unit}\"\n"
    if claim_context:
        prompt += f"CLAIM CONTEXT: \"{claim_context}\"\n"
    
    prompt += "\nCANDIDATE REGISTRY ENTRIES:\n"
    for idx, c in enumerate(candidates, 1):
        prompt += f"{idx}. ID: {c['id']} | Name: \"{c['canonical_name']}\" | Similarity: {c.get('similarity', 0.0):.4f}\n"
    
    prompt += "\nEvaluate if the new mention is an 'alias_of' one of these candidates, or a 'new_entry'. Output JSON only."
    return prompt
