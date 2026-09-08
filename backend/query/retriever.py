"""
FactLoom Knowledge Graph Retriever
Retrieves canonical facts, underlying observations with bounding boxes and source citations,
and reconciled relationship edges matching parsed query criteria.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.store.db import get_connection
from backend.query.parser import ParsedQuery

logger = logging.getLogger(__name__)

class RetrievedObservation(BaseModel):
    id: str
    fact_id: str
    document_id: str
    document_filename: str
    page_number: int
    value: str
    unit: Optional[str] = None
    quote_span: str
    bbox_json: Optional[str] = None
    doc_vintage_date: Optional[str] = None
    table_name: Optional[str] = None
    confidence: float = 1.0

class RetrievedFact(BaseModel):
    id: str
    entity_name: str
    metric_name: str
    scope: Optional[str] = None
    period: str
    measurement_type: str
    definition: Optional[str] = None
    observation_count: int = 0
    observations: List[RetrievedObservation] = Field(default_factory=list)

class RetrievedRelationship(BaseModel):
    id: str
    observation_a_id: str
    observation_b_id: str
    type: str
    dimension: str
    justification: str
    verified_bool: int = 1

class RetrievalResult(BaseModel):
    facts: List[RetrievedFact] = Field(default_factory=list)
    observations: List[RetrievedObservation] = Field(default_factory=list)
    relationships: List[RetrievedRelationship] = Field(default_factory=list)
    total_facts: int = 0
    total_observations: int = 0

class KnowledgeRetriever:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def retrieve(self, parsed: ParsedQuery) -> RetrievalResult:
        """
        Query database for facts, observations, and relationships matching parsed query.
        """
        conn = get_connection(self.db_path)
        try:
            # 1. Build dynamic Fact matching query
            query_parts = ["""
                SELECT f.id as fact_id, f.scope, f.period, f.measurement_type, f.definition,
                       e.canonical_name as entity_name, m.canonical_name as metric_name
                FROM facts f
                JOIN entities e ON f.entity_id = e.id
                JOIN metrics m ON f.metric_id = m.id
                WHERE 1=1
            """]
            params: List[Any] = []

            # Match Entity (canonical or raw)
            # Match Entity (canonical or mention)
            if parsed.canonical_entity:
                query_parts.append("AND (LOWER(e.canonical_name) = LOWER(?) OR LOWER(e.created_from_mention) = LOWER(?))")
                params.extend([parsed.canonical_entity, parsed.canonical_entity])
            elif parsed.entity_mention:
                query_parts.append("AND (LOWER(e.canonical_name) LIKE LOWER(?) OR LOWER(e.created_from_mention) LIKE LOWER(?))")
                params.extend([f"%{parsed.entity_mention}%", f"%{parsed.entity_mention}%"])

            # Match Metric (canonical or mention)
            if parsed.canonical_metric:
                query_parts.append("AND (LOWER(m.canonical_name) = LOWER(?) OR LOWER(m.created_from_mention) = LOWER(?))")
                params.extend([parsed.canonical_metric, parsed.canonical_metric])
            elif parsed.metric_mention:
                query_parts.append("AND (LOWER(m.canonical_name) LIKE LOWER(?) OR LOWER(m.created_from_mention) LIKE LOWER(?))")
                params.extend([f"%{parsed.metric_mention}%", f"%{parsed.metric_mention}%"])

            # Filter by Period if explicitly specified in query
            if parsed.period_mention:
                # E.g. "FY24", "2024", "2023-24"
                query_parts.append("AND (LOWER(f.period) LIKE LOWER(?) OR LOWER(?) LIKE '%' || LOWER(f.period) || '%')")
                params.extend([f"%{parsed.period_mention}%", parsed.period_mention])

            # Filter by Scope if specified
            if parsed.scope_mention:
                query_parts.append("AND (LOWER(f.scope) LIKE LOWER(?))")
                params.append(f"%{parsed.scope_mention}%")

            fact_rows = conn.execute(" ".join(query_parts), params).fetchall()

            # If no facts found with strict match, relax metric/entity filters to partial matching
            if not fact_rows and (parsed.metric_mention or parsed.entity_mention):
                relaxed_query = """
                    SELECT f.id as fact_id, f.scope, f.period, f.measurement_type, f.definition,
                           e.canonical_name as entity_name, m.canonical_name as metric_name
                    FROM facts f
                    JOIN entities e ON f.entity_id = e.id
                    JOIN metrics m ON f.metric_id = m.id
                    WHERE (LOWER(m.canonical_name) LIKE LOWER(?) OR LOWER(e.canonical_name) LIKE LOWER(?))
                """
                m_token = parsed.canonical_metric or parsed.metric_mention or ""
                e_token = parsed.canonical_entity or parsed.entity_mention or ""
                fact_rows = conn.execute(relaxed_query, (f"%{m_token}%", f"%{e_token}%")).fetchall()

            if not fact_rows:
                return RetrievalResult()

            fact_ids = [r["fact_id"] for r in fact_rows]
            placeholders = ",".join(["?"] * len(fact_ids))

            # 2. Retrieve all Observations for these Facts
            obs_query = f"""
                SELECT o.id, o.fact_id, o.document_id, o.page_number, o.value, o.unit,
                       o.quote_span, o.bbox as bbox_json, o.doc_vintage_date, o.confidence,
                       d.filename as document_filename
                FROM observations o
                JOIN documents d ON o.document_id = d.id
                WHERE o.fact_id IN ({placeholders})
                ORDER BY o.page_number ASC
            """
            obs_rows = conn.execute(obs_query, fact_ids).fetchall()

            obs_by_fact: Dict[str, List[RetrievedObservation]] = {}
            all_obs_list: List[RetrievedObservation] = []
            obs_id_set = set()

            for ob in obs_rows:
                obs_obj = RetrievedObservation(
                    id=ob["id"],
                    fact_id=ob["fact_id"],
                    document_id=ob["document_id"],
                    document_filename=ob["document_filename"],
                    page_number=ob["page_number"],
                    value=ob["value"],
                    unit=ob["unit"],
                    quote_span=ob["quote_span"],
                    bbox_json=ob["bbox_json"],
                    doc_vintage_date=ob["doc_vintage_date"],
                    table_name=None,
                    confidence=ob["confidence"] if ob["confidence"] is not None else 1.0
                )
                all_obs_list.append(obs_obj)
                obs_id_set.add(obs_obj.id)
                obs_by_fact.setdefault(ob["fact_id"], []).append(obs_obj)

            # 3. Retrieve Relationships between these Observations
            all_relationships: List[RetrievedRelationship] = []
            if obs_id_set:
                obs_placeholders = ",".join(["?"] * len(obs_id_set))
                rel_query = f"""
                    SELECT id, observation_a_id, observation_b_id, type, dimension,
                           justification, verified_bool
                    FROM relationships
                    WHERE observation_a_id IN ({obs_placeholders})
                       OR observation_b_id IN ({obs_placeholders})
                """
                rel_rows = conn.execute(rel_query, list(obs_id_set) + list(obs_id_set)).fetchall()
                for r in rel_rows:
                    all_relationships.append(RetrievedRelationship(
                        id=r["id"],
                        observation_a_id=r["observation_a_id"],
                        observation_b_id=r["observation_b_id"],
                        type=r["type"],
                        dimension=r["dimension"],
                        justification=r["justification"],
                        verified_bool=r["verified_bool"] if r["verified_bool"] is not None else 1
                    ))

            # Assemble Facts
            facts_list: List[RetrievedFact] = []
            for fr in fact_rows:
                fid = fr["fact_id"]
                obs_for_fact = obs_by_fact.get(fid, [])
                facts_list.append(RetrievedFact(
                    id=fid,
                    entity_name=fr["entity_name"],
                    metric_name=fr["metric_name"],
                    scope=fr["scope"],
                    period=fr["period"],
                    measurement_type=fr["measurement_type"],
                    definition=fr["definition"],
                    observation_count=len(obs_for_fact),
                    observations=obs_for_fact
                ))

            return RetrievalResult(
                facts=facts_list,
                observations=all_obs_list,
                relationships=all_relationships,
                total_facts=len(facts_list),
                total_observations=len(all_obs_list)
            )

        finally:
            conn.close()
