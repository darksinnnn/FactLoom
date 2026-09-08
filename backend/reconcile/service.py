"""
FactLoom Reconciliation Service
Coordinates bounded candidate matching, 2-tier resolution (deterministic -> LLM),
and Tier 3 verifier backstop before database persistence.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from backend.store.db import get_connection, init_db
from backend.reconcile.deterministic import DeterministicReconciler
from backend.reconcile.adjudicator import ReconciliationAdjudicator
from backend.reconcile.verifier import DeterministicVerifier

logger = logging.getLogger(__name__)

class ReconciliationService:
    def __init__(
        self,
        db_path: Optional[str] = None,
        tolerance_pct: float = 0.5,
        deterministic_reconciler: Optional[DeterministicReconciler] = None,
        adjudicator: Optional[ReconciliationAdjudicator] = None,
        verifier: Optional[DeterministicVerifier] = None
    ):
        self.db_path = db_path
        init_db(self.db_path)
        self.deterministic_tier = deterministic_reconciler or DeterministicReconciler(tolerance_pct=tolerance_pct)
        self.llm_tier = adjudicator or ReconciliationAdjudicator()
        self.verifier = verifier or DeterministicVerifier(tolerance_pct=tolerance_pct)

    def reconcile_observation_pair(
        self,
        obs_a: Dict[str, Any],
        obs_b: Dict[str, Any],
        entity_name: str = "Unknown Entity",
        metric_name: str = "Unknown Metric"
    ) -> Dict[str, Any]:
        """
        Execute strict 3-tier reconciliation for a candidate observation pair:
        1. Deterministic Tier (unit conversion, rounding tolerance) -> no LLM
        2. LLM Adjudication Tier (fixed taxonomy) -> only for ambiguous remainder
        3. Deterministic Verifier -> re-checks math/dates before return
        """
        # Step 1: Tier 1 - Deterministic Reconciler
        det_result = self.deterministic_tier.reconcile_pair(obs_a, obs_b)
        if det_result is not None:
            logger.info(
                f"[RECONCILE: Tier 1 Deterministic] {obs_a.get('id')} <-> {obs_b.get('id')} "
                f"resolved as {det_result['relationship_type']} ({det_result['dimension']})"
            )
            return det_result

        # Step 2: Tier 2 - LLM Adjudicator
        logger.info(
            f"[RECONCILE: Tier 2 LLM Adjudication] Escalating {obs_a.get('id')} <-> {obs_b.get('id')} to LLM..."
        )
        llm_result = self.llm_tier.adjudicate(
            entity_name=entity_name,
            metric_name=metric_name,
            obs_a=obs_a,
            obs_b=obs_b
        )

        # Step 3: Tier 3 - Deterministic Verifier Backstop
        verified_bool, final_result = self.verifier.verify(llm_result, obs_a, obs_b)
        logger.info(
            f"[RECONCILE: Tier 3 Verifier] {obs_a.get('id')} <-> {obs_b.get('id')} "
            f"classified as {final_result['relationship_type']} ({final_result['dimension']}), verified={verified_bool}"
        )
        return final_result

    def reconcile_all_candidates(self) -> List[Dict[str, Any]]:
        """
        Run bounded candidate matching across all ingested observations in the database.
        Matches observations that:
        - Share the exact same Fact identity, OR
        - Share the same Entity and have matching/near-neighbor Metrics.
        Persists all discovered relationships.
        """
        conn = get_connection(self.db_path)
        persisted_relationships: List[Dict[str, Any]] = []

        try:
            # 1. Candidate matching on shared canonical Fact identity
            facts_with_multiple_obs = conn.execute("""
                SELECT f.id as fact_id, e.canonical_name as entity_name, m.canonical_name as metric_name,
                       COUNT(o.id) as obs_count
                FROM facts f
                JOIN entities e ON f.entity_id = e.id
                JOIN metrics m ON f.metric_id = m.id
                JOIN observations o ON f.id = o.fact_id
                GROUP BY f.id
                HAVING COUNT(o.id) >= 2
            """).fetchall()

            for f in facts_with_multiple_obs:
                fact_id = f["fact_id"]
                entity_name = f["entity_name"]
                metric_name = f["metric_name"]

                obs_rows = conn.execute("""
                    SELECT o.*, d.filename as document_filename
                    FROM observations o
                    JOIN documents d ON o.document_id = d.id
                    WHERE o.fact_id = ?
                    ORDER BY o.id
                """, (fact_id,)).fetchall()

                # Reconcile distinct observation pairs under this Fact
                for i in range(len(obs_rows)):
                    for j in range(i + 1, len(obs_rows)):
                        oa = dict(obs_rows[i])
                        ob = dict(obs_rows[j])
                        rel = self._process_and_store_pair(conn, oa, ob, entity_name, metric_name)
                        if rel:
                            persisted_relationships.append(rel)

            # 2. Candidate matching across near-neighbor Facts sharing the same Entity
            # e.g. Director appointment vs resignation, or advance estimate vs actual reporting
            near_candidate_pairs = conn.execute("""
                SELECT DISTINCT
                    o1.id as o1_id, o1.value as o1_val, o1.unit as o1_unit, o1.quote_span as o1_quote,
                    o1.doc_vintage_date as o1_vintage, d1.filename as o1_doc,
                    o2.id as o2_id, o2.value as o2_val, o2.unit as o2_unit, o2.quote_span as o2_quote,
                    o2.doc_vintage_date as o2_vintage, d2.filename as o2_doc,
                    e.canonical_name as entity_name, m.canonical_name as metric_name
                FROM observations o1
                JOIN facts f1 ON o1.fact_id = f1.id
                JOIN observations o2 ON o1.id < o2.id
                JOIN facts f2 ON o2.fact_id = f2.id
                JOIN entities e ON f1.entity_id = e.id AND f2.entity_id = e.id
                JOIN metrics m ON f1.metric_id = m.id AND f2.metric_id = m.id
                JOIN documents d1 ON o1.document_id = d1.id
                JOIN documents d2 ON o2.document_id = d2.id
                WHERE f1.id != f2.id
                  AND (f1.scope IS NULL OR f2.scope IS NULL OR f1.scope = f2.scope)
                  AND (d1.id != d2.id OR o1.doc_vintage_date != o2.doc_vintage_date)
            """).fetchall()

            for cp in near_candidate_pairs:
                oa = {
                    "id": cp["o1_id"], "value": cp["o1_val"], "unit": cp["o1_unit"],
                    "quote_span": cp["o1_quote"], "doc_vintage_date": cp["o1_vintage"],
                    "document_filename": cp["o1_doc"]
                }
                ob = {
                    "id": cp["o2_id"], "value": cp["o2_val"], "unit": cp["o2_unit"],
                    "quote_span": cp["o2_quote"], "doc_vintage_date": cp["o2_vintage"],
                    "document_filename": cp["o2_doc"]
                }
                rel = self._process_and_store_pair(conn, oa, ob, cp["entity_name"], cp["metric_name"])
                if rel:
                    persisted_relationships.append(rel)

            return persisted_relationships

        finally:
            conn.close()

    def _process_and_store_pair(
        self,
        conn: Any,
        obs_a: Dict[str, Any],
        obs_b: Dict[str, Any],
        entity_name: str,
        metric_name: str
    ) -> Optional[Dict[str, Any]]:
        """Reconcile and persist pair if not already present."""
        a_id = obs_a["id"]
        b_id = obs_b["id"]

        # Check if already reconciled
        existing = conn.execute("""
            SELECT id FROM relationships
            WHERE (observation_a_id = ? AND observation_b_id = ?)
               OR (observation_a_id = ? AND observation_b_id = ?)
        """, (a_id, b_id, b_id, a_id)).fetchone()

        if existing:
            return None

        decision = self.reconcile_observation_pair(obs_a, obs_b, entity_name, metric_name)

        rel_id = f"rel_{uuid.uuid4().hex[:10]}"
        now_ts = datetime.utcnow().isoformat() + "Z"

        with conn:
            conn.execute("""
                INSERT INTO relationships (
                    id, observation_a_id, observation_b_id, type,
                    dimension, justification, verified_bool, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rel_id, a_id, b_id,
                decision["relationship_type"],
                decision["dimension"],
                decision["justification"],
                decision.get("verified_bool", 1),
                now_ts
            ))

        decision["id"] = rel_id
        decision["observation_a_id"] = a_id
        decision["observation_b_id"] = b_id
        return decision
