"""
FactLoom Fact Service & Observation Pipeline
Assembles durable Fact identities from resolved Entity and Metric IDs.
Binds Observations to Facts with strict provenance.
STRICT GUARDRAIL: Zero dataset-specific strings.
"""

import os
import re
import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from backend.store.db import get_connection
from backend.canonicalize.registry import RegistryEngine

GENERIC_ENTITY_NAMES = {
    "unnamed entity", "unknown entity", "the company", "company",
    "entity", "the entity", "entity name", "firm", "the firm"
}

def is_generic_entity(entity_str: Optional[str]) -> bool:
    """Check if entity mention is a generic placeholder rather than a concrete named entity."""
    if not entity_str:
        return True
    s = entity_str.strip().lower()
    if s in GENERIC_ENTITY_NAMES:
        return True
    generic_keywords = [
        "not named", "not specified", "not mentioned", "unnamed", 
        "unknown", "reporting entity", "unspecified entity", "the firm"
    ]
    return any(k in s for k in generic_keywords)

def normalize_period(period_str: Optional[str]) -> str:
    """
    Standardize common fiscal and calendar period strings.
    E.g., 'FY 2023-24' -> 'FY24', 'March 31, 2024' -> 'FY24'.
    """
    if not period_str:
        return "Unspecified"
    p = period_str.strip()
    
    # Q4 FY24 / Q4 FY 2024 / Q4 2024
    m_quarter = re.search(r'\b(Q[1-4])\s*(?:FY|FY\s*)?(\d{2,4})', p, re.IGNORECASE)
    if m_quarter:
        q = m_quarter.group(1).upper()
        yr = m_quarter.group(2)
        yr_short = yr[-2:] if len(yr) == 4 else yr
        return f"{q} FY{yr_short}"

    # Fiscal year-end date mapping: 'March 31, 2024' or '31 March 2024' -> 'FY24'
    m_mar = re.search(r'(?:March\s*31|31(?:st)?\s*March)[,\s]+(20\d{2})', p, re.IGNORECASE)
    if m_mar:
        yr = m_mar.group(1)[-2:]
        return f"FY{yr}"

    # FY 2023-24 / FY 23-24 / FY24
    m_fy_range = re.search(r'\bFY\s*(?:20)?(\d{2})[-–](?:20)?(\d{2})\b', p, re.IGNORECASE)
    if m_fy_range:
        return f"FY{m_fy_range.group(2)}"

    m_fy = re.search(r'\bFY\s*(?:20)?(\d{2})\b', p, re.IGNORECASE)
    if m_fy:
        return f"FY{m_fy.group(1)}"

    # Year range: 2024-25
    m_yr_range = re.search(r'\b(?:20)?(\d{2})[-–](?:20)?(\d{2})\b', p)
    if m_yr_range:
        return f"20{m_yr_range.group(1)}-{m_yr_range.group(2)}"

    return p

def normalize_scope(scope_str: Optional[str]) -> str:
    """Standardize scope mention to Consolidated, Standalone, Segment, or National."""
    if not scope_str:
        return "Consolidated"
    s = scope_str.strip().lower()
    if "standalone" in s:
        return "Standalone"
    if "segment" in s:
        return "Segment"
    if "national" in s or "country" in s:
        return "National"
    # If the scope string contains date or period markers, it was misplaced by LLM
    if re.search(r'\b(?:fy|q[1-4]|20\d{2})\b', s):
        return "Consolidated"
    if "consolidated" in s:
        return "Consolidated"
    return scope_str.strip().title()

def normalize_definition(definition_str: Optional[str], metric: str, period: str) -> str:
    """
    Clean definition mention. Redundant restatements of metric or period are normalized to empty.
    """
    if not definition_str:
        return ""
    d = definition_str.strip()
    d_clean = re.sub(r'[^\w\s]', '', d).lower().strip()
    m_clean = re.sub(r'[^\w\s]', '', metric).lower().strip()
    p_clean = re.sub(r'[^\w\s]', '', period).lower().strip()
    
    redundant_echoes = {
        m_clean, p_clean,
        f"{p_clean} {m_clean}",
        f"{m_clean} {p_clean}"
    }
    if d_clean in redundant_echoes or not d_clean:
        return ""
    return d

class FactService:
    def __init__(self, db_path: Optional[str] = None, registry_engine: Optional[RegistryEngine] = None):
        self.db_path = db_path
        self.registry = registry_engine or RegistryEngine(db_path=db_path)
        self._doc_primary_entities: Dict[str, str] = {}

    def ingest_observations(
        self,
        extracted_candidates: List[Dict[str, Any]],
        document_id: str,
        page_number: int,
        page_id: Optional[str] = None,
        doc_vintage_date: Optional[str] = None,
        default_entity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Takes extracted fact candidates, resolves mentions into canonical entities & metrics,
        finds or creates canonical Facts, and stores grounded Observations.
        """
        conn = get_connection(self.db_path)
        ingested_observations: List[Dict[str, Any]] = []

        try:
            # Track default entity for document
            if default_entity:
                self._doc_primary_entities[document_id] = default_entity

            # Resolve actual page_id if not provided
            if not page_id:
                row = conn.execute(
                    "SELECT id FROM pages WHERE document_id = ? AND page_number = ?",
                    (document_id, page_number)
                ).fetchone()
                if row:
                    page_id = row["id"]
                else:
                    page_id = f"page_{document_id}_{page_number}"

            for cand in extracted_candidates:
                raw_entity = (cand.get("entity_mention") or "").strip()
                if is_generic_entity(raw_entity):
                    entity_mention = self._doc_primary_entities.get(document_id) or default_entity or "Unknown Entity"
                else:
                    entity_mention = raw_entity
                    # Cache first specific entity seen for this document
                    if document_id not in self._doc_primary_entities and not is_generic_entity(raw_entity):
                        self._doc_primary_entities[document_id] = entity_mention

                metric_mention = cand.get("metric_mention") or "Unknown Metric"
                unit = cand.get("unit")
                claim_text = cand.get("claim_text")

                # Step 1: Resolve Entity and Metric via Registry
                entity_id, canonical_entity = self.registry.resolve_entity(
                    entity_mention, context=claim_text
                )
                metric_id, canonical_metric = self.registry.resolve_metric(
                    metric_mention, unit=unit, context=claim_text
                )

                # Remember resolved canonical entity for document
                if not is_generic_entity(canonical_entity):
                    self._doc_primary_entities[document_id] = canonical_entity

                # Step 2: Normalize dimensions
                period = normalize_period(cand.get("period_mention"))
                scope = normalize_scope(cand.get("scope_mention"))
                measurement_type = cand.get("measurement_type") or "flow"
                definition = normalize_definition(cand.get("definition_mention"), canonical_metric, period)

                # Step 3: Find or Create Fact Identity
                fact_row = conn.execute("""
                    SELECT id FROM facts
                    WHERE entity_id = ? AND metric_id = ? AND scope = ?
                      AND period = ? AND measurement_type = ? AND definition = ?
                """, (entity_id, metric_id, scope, period, measurement_type, definition)).fetchone()

                now_ts = datetime.utcnow().isoformat() + "Z"

                if fact_row:
                    fact_id = fact_row["id"]
                else:
                    fact_id = f"fact_{uuid.uuid4().hex[:10]}"
                    with conn:
                        conn.execute("""
                            INSERT INTO facts (
                                id, entity_id, metric_id, scope, period,
                                measurement_type, definition, embedding, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)
                        """, (
                            fact_id, entity_id, metric_id, scope, period,
                            measurement_type, definition, now_ts
                        ))

                # Step 4: Create Observation
                obs_id = f"obs_{uuid.uuid4().hex[:10]}"
                bbox_json = json.dumps(cand.get("bbox", []))
                val_str = str(cand.get("value", "")).strip()
                quote_span = cand.get("quote_span", "")
                confidence = float(cand.get("confidence", 0.9))

                with conn:
                    conn.execute("""
                        INSERT INTO observations (
                            id, fact_id, document_id, page_id, page_number,
                            value, unit, quote_span, bbox, confidence,
                            doc_vintage_date, extracted_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        obs_id, fact_id, document_id, page_id, page_number,
                        val_str, unit, quote_span, bbox_json, confidence,
                        doc_vintage_date, now_ts
                    ))

                ingested_observations.append({
                    "observation_id": obs_id,
                    "fact_id": fact_id,
                    "canonical_entity": canonical_entity,
                    "canonical_metric": canonical_metric,
                    "period": period,
                    "scope": scope,
                    "value": val_str,
                    "unit": unit,
                    "quote_span": quote_span
                })

        finally:
            conn.close()

        return ingested_observations
