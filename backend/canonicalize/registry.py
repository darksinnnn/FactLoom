"""
FactLoom Registry Engine
Manages Entity and Metric registries with 3-tier resolution:
1. High similarity (>= upper_threshold) -> Deterministic auto-alias
2. Low similarity (< lower_threshold) -> Deterministic auto-new
3. Middle band (lower <= sim < upper) -> LLM adjudication call with audit logging

STRICT GUARDRAIL: Zero dataset-specific strings in logic or prompts.
"""

import os
import re
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from backend.store.db import get_connection, init_db
from backend.canonicalize.embedder import EmbeddingEngine
from backend.canonicalize.prompts.canonicalize_prompt import (
    CANONICALIZE_SYSTEM_PROMPT,
    build_adjudication_prompt
)
from backend.extract.client import GroqClient

logger = logging.getLogger(__name__)

# Standard accounting/scoping modifiers that distinguish fundamentally different metrics
DISTINGUISHING_MODIFIERS = {
    "adjusted", "core", "headline", "gross", "net", "underlying", 
    "normalized", "diluted", "basic", "operating", "non-operating"
}

class RegistryEngine:
    def __init__(
        self,
        db_path: Optional[str] = None,
        groq_client: Optional[GroqClient] = None,
        embedder: Optional[EmbeddingEngine] = None,
        upper_threshold: float = 0.88,
        lower_threshold: float = 0.65
    ):
        self.db_path = db_path
        init_db(self.db_path)
        self.client = groq_client or GroqClient()
        self.embedder = embedder or EmbeddingEngine.get_instance()
        self.upper_threshold = upper_threshold
        self.lower_threshold = lower_threshold

        self._entities_cache: List[Dict[str, Any]] = []
        self._metrics_cache: List[Dict[str, Any]] = []
        self._decision_cache: Dict[str, Tuple[str, str]] = {}
        self._load_caches()


    def _load_caches(self) -> None:
        """Load existing entities and metrics into in-memory vector cache."""
        conn = get_connection(self.db_path)
        try:
            ent_rows = conn.execute("SELECT id, canonical_name, entity_type_guess, embedding FROM entities").fetchall()
            self._entities_cache = []
            for r in ent_rows:
                emb = self.embedder.deserialize_vector(r["embedding"]) if r["embedding"] else None
                self._entities_cache.append({
                    "id": r["id"],
                    "canonical_name": r["canonical_name"],
                    "entity_type_guess": r["entity_type_guess"],
                    "embedding": emb
                })

            met_rows = conn.execute("SELECT id, canonical_name, unit_family, embedding FROM metrics").fetchall()
            self._metrics_cache = []
            for r in met_rows:
                emb = self.embedder.deserialize_vector(r["embedding"]) if r["embedding"] else None
                self._metrics_cache.append({
                    "id": r["id"],
                    "canonical_name": r["canonical_name"],
                    "unit_family": r["unit_family"],
                    "embedding": emb
                })
        finally:
            conn.close()

    @staticmethod
    def clean_metric_mention(mention: str) -> str:
        """
        Defense-in-depth metric normalization:
        1. Strip bracketed unit and currency annotations (e.g., '(₹Cr)', '(in million)').
        2. Strip leaked period/date patterns (e.g., 'FY24', 'FY23', 'Q4 FY24', 'March 31, 2024').
        3. Normalize extra whitespace and punctuation.
        """
        s = mention.strip()
        # Strip bracketed unit or currency annotations
        s = re.sub(r'\s*\([^)]*(?:cr|inr|usd|mn|million|\$|%|₹|rs)[^)]*\)$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s*\([^)]*\)$', '', s)
        # Strip trailing leaked period patterns
        s = re.sub(r'\b(?:FY|FY\s*)\d{2,4}\b', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\bQ[1-4]\s*(?:FY)?\s*\d{2,4}\b', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\bQ[1-4]\b', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\b(?:March|December|September|June)\s*\d{1,2},?\s*\d{4}\b', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\b20\d{2}[-–]\d{2,4}\b', '', s)
        s = re.sub(r'\b20\d{2}\b', '', s)
        # Clean extra whitespace and trailing punctuation
        s = re.sub(r'[\s.,;:\-]+$', '', s).strip()
        s = re.sub(r'\s{2,}', ' ', s).strip()
        return s if s else mention.strip()

    @staticmethod
    def clean_entity_mention(mention: str) -> str:
        """
        Normalize entity mentions:
        Strip common legal suffixes (Limited, Ltd, Inc, Corp, etc.) for matching.
        """
        s = mention.strip()
        s = re.sub(r'\b(?:Private\s+Limited|Pvt\.?\s*Ltd\.?|Limited|Ltd\.?|Incorporated|Inc\.?|Corporation|Corp\.?)\b\.?', '', s, flags=re.IGNORECASE)
        s = re.sub(r'[\s.,;:\-]+$', '', s).strip()
        s = re.sub(r'\s{2,}', ' ', s).strip()
        return s if s else mention.strip()

    @staticmethod
    def has_modifier_mismatch(mention_a: str, mention_b: str) -> bool:
        """
        Check if one mention has a qualifying modifier (e.g., 'Adjusted')
        while the other does not.
        """
        tokens_a = set(re.findall(r'\b\w+\b', mention_a.lower()))
        tokens_b = set(re.findall(r'\b\w+\b', mention_b.lower()))

        mods_a = tokens_a.intersection(DISTINGUISHING_MODIFIERS)
        mods_b = tokens_b.intersection(DISTINGUISHING_MODIFIERS)

        return mods_a != mods_b

    def _record_decision(
        self,
        mention_text: str,
        resolved_id: str,
        target_type: str,
        decision_type: str,
        similarity_score: float,
        llm_reasoning: Optional[str] = None,
        model_used: str = "deterministic"
    ) -> None:
        """Persist resolution audit record to registry_decisions table."""
        conn = get_connection(self.db_path)
        try:
            with conn:
                decision_id = f"dec_{uuid.uuid4().hex[:10]}"
                created_at = datetime.utcnow().isoformat() + "Z"
                conn.execute("""
                    INSERT INTO registry_decisions (
                        id, mention_text, resolved_entity_or_metric_id,
                        target_type, decision_type, similarity_score,
                        llm_reasoning, model_used, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    decision_id, mention_text, resolved_id,
                    target_type, decision_type, similarity_score,
                    llm_reasoning, model_used, created_at
                ))
        finally:
            conn.close()

    def resolve_entity(
        self,
        mention_text: str,
        context: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Resolve an entity mention to (entity_id, canonical_name).
        Follows 3-tier architecture:
        - Similarity >= upper_threshold -> auto-alias
        - Similarity < lower_threshold -> auto-new
        - Middle band -> LLM adjudication
        """
        cleaned = mention_text.strip()
        if not cleaned:
            cleaned = "Unknown Entity"

        cache_key = f"entity:{cleaned.lower()}"
        if cache_key in self._decision_cache:
            return self._decision_cache[cache_key]

        cleaned_base = self.clean_entity_mention(cleaned)

        # Exact case-insensitive match or base entity match
        for ent in self._entities_cache:
            if ent["canonical_name"].lower() == cleaned.lower() or (
                cleaned_base and self.clean_entity_mention(ent["canonical_name"]).lower() == cleaned_base.lower()
            ):
                self._record_decision(
                    mention_text=mention_text,
                    resolved_id=ent["id"],
                    target_type="entity",
                    decision_type="auto_alias",
                    similarity_score=1.0,
                    llm_reasoning=f"Exact or normalized base match with canonical entity '{ent['canonical_name']}'"
                )
                res = (ent["id"], ent["canonical_name"])
                self._decision_cache[cache_key] = res
                return res

        emb = self.embedder.embed_text(cleaned)

        if not self._entities_cache:
            # Initial entry
            return self._create_new_entity(cleaned, emb, mention_text, "Initial entity in registry", 1.0)

        # Nearest neighbor search
        ranked: List[Tuple[float, Dict[str, Any]]] = []
        for ent in self._entities_cache:
            if ent["embedding"] is not None:
                sim = self.embedder.cosine_similarity(emb, ent["embedding"])
                ranked.append((sim, ent))

        ranked.sort(key=lambda x: x[0], reverse=True)
        top_sim, top_ent = ranked[0]

        # Tier 1: High similarity -> Auto-alias
        if top_sim >= self.upper_threshold:
            self._record_decision(
                mention_text=mention_text,
                resolved_id=top_ent["id"],
                target_type="entity",
                decision_type="auto_alias",
                similarity_score=top_sim,
                llm_reasoning=f"Deterministic auto-alias: high cosine similarity ({top_sim:.4f} >= {self.upper_threshold}) with '{top_ent['canonical_name']}'"
            )
            return top_ent["id"], top_ent["canonical_name"]

        # Tier 2: Low similarity -> Auto-new
        if top_sim < self.lower_threshold:
            reason = f"Deterministic auto-new: low cosine similarity ({top_sim:.4f} < {self.lower_threshold}) with nearest '{top_ent['canonical_name']}'"
            return self._create_new_entity(cleaned, emb, mention_text, reason, top_sim)

        # Tier 3: Middle band -> LLM Adjudication
        candidates = [
            {"id": e["id"], "canonical_name": e["canonical_name"], "similarity": s}
            for s, e in ranked[:3]
        ]
        decision = self._adjudicate_with_llm("entity", cleaned, candidates, claim_context=context)
        model_used = decision.get("_model_used", "deterministic")

        if decision.get("decision") == "alias_of" and decision.get("matched_id"):
            matched_id = decision["matched_id"]
            matched_ent = next((e for e in self._entities_cache if e["id"] == matched_id), top_ent)
            self._record_decision(
                mention_text=mention_text,
                resolved_id=matched_ent["id"],
                target_type="entity",
                decision_type="llm_adjudicated",
                similarity_score=top_sim,
                llm_reasoning=decision.get("reason", "LLM determined alias of existing entity"),
                model_used=model_used
            )
            return matched_ent["id"], matched_ent["canonical_name"]
        else:
            canonical_name = decision.get("canonical_name") or cleaned
            reason = decision.get("reason", "LLM determined distinct new entity entry")
            return self._create_new_entity(canonical_name, emb, mention_text, reason, top_sim, is_llm=True, model_used=model_used)

    def resolve_metric(
        self,
        mention_text: str,
        unit: Optional[str] = None,
        context: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Resolve a metric mention to (metric_id, canonical_name).
        Applies mention pre-cleaning (bracketed unit stripping) and modifier divergence guards.
        """
        raw_mention = mention_text.strip()
        cleaned = self.clean_metric_mention(raw_mention)
        if not cleaned:
            cleaned = raw_mention or "Unknown Metric"

        cache_key = f"metric:{raw_mention.lower()}"
        if cache_key in self._decision_cache:
            return self._decision_cache[cache_key]


        # Exact case-insensitive match
        for met in self._metrics_cache:
            if met["canonical_name"].lower() == cleaned.lower():
                self._record_decision(
                    mention_text=raw_mention,
                    resolved_id=met["id"],
                    target_type="metric",
                    decision_type="auto_alias",
                    similarity_score=1.0,
                    llm_reasoning=f"Exact string match with canonical metric '{met['canonical_name']}' after normalization"
                )
                res = (met["id"], met["canonical_name"])
                self._decision_cache[cache_key] = res
                return res

        emb = self.embedder.embed_text(cleaned)

        if not self._metrics_cache:
            return self._create_new_metric(cleaned, emb, raw_mention, "Initial metric in registry", 1.0, unit)

        # Nearest neighbor search
        ranked: List[Tuple[float, Dict[str, Any]]] = []
        for met in self._metrics_cache:
            if met["embedding"] is not None:
                sim = self.embedder.cosine_similarity(emb, met["embedding"])
                ranked.append((sim, met))

        ranked.sort(key=lambda x: x[0], reverse=True)
        top_sim, top_met = ranked[0]

        # Modifier mismatch guard: if one has 'Adjusted' and other doesn't, cannot auto-alias
        has_mod_mismatch = self.has_modifier_mismatch(cleaned, top_met["canonical_name"])

        # Tier 1: High similarity without modifier conflict -> Auto-alias
        if top_sim >= self.upper_threshold and not has_mod_mismatch:
            self._record_decision(
                mention_text=raw_mention,
                resolved_id=top_met["id"],
                target_type="metric",
                decision_type="auto_alias",
                similarity_score=top_sim,
                llm_reasoning=f"Deterministic auto-alias: high cosine similarity ({top_sim:.4f} >= {self.upper_threshold}) with '{top_met['canonical_name']}'"
            )
            return top_met["id"], top_met["canonical_name"]

        # Tier 2: Low similarity -> Auto-new
        if top_sim < self.lower_threshold and not has_mod_mismatch:
            reason = f"Deterministic auto-new: low cosine similarity ({top_sim:.4f} < {self.lower_threshold}) with nearest '{top_met['canonical_name']}'"
            return self._create_new_metric(cleaned, emb, raw_mention, reason, top_sim, unit)

        # Tier 3: Middle band (or high similarity blocked by modifier mismatch) -> LLM Adjudication
        candidates = [
            {"id": m["id"], "canonical_name": m["canonical_name"], "similarity": s}
            for s, m in ranked[:3]
        ]
        decision = self._adjudicate_with_llm("metric", cleaned, candidates, unit=unit, claim_context=context)
        model_used = decision.get("_model_used", "deterministic")

        if decision.get("decision") == "alias_of" and decision.get("matched_id"):
            matched_id = decision["matched_id"]
            matched_met = next((m for m in self._metrics_cache if m["id"] == matched_id), top_met)
            self._record_decision(
                mention_text=raw_mention,
                resolved_id=matched_met["id"],
                target_type="metric",
                decision_type="llm_adjudicated",
                similarity_score=top_sim,
                llm_reasoning=decision.get("reason", "LLM determined alias of existing metric"),
                model_used=model_used
            )
            return matched_met["id"], matched_met["canonical_name"]
        else:
            canonical_name = decision.get("canonical_name") or cleaned
            reason = decision.get("reason", "LLM determined distinct metric formula or qualifier")
            return self._create_new_metric(canonical_name, emb, raw_mention, reason, top_sim, unit, is_llm=True, model_used=model_used)

    def _adjudicate_with_llm(
        self,
        target_type: str,
        mention_text: str,
        candidates: List[Dict[str, Any]],
        unit: Optional[str] = None,
        claim_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Invoke Groq LLM to adjudicate middle-band candidate matching."""
        user_prompt = build_adjudication_prompt(
            target_type=target_type,
            mention_text=mention_text,
            candidates=candidates,
            unit=unit,
            claim_context=claim_context
        )
        messages = [
            {"role": "system", "content": CANONICALIZE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        try:
            # Use canonicalizer_fast (gpt-oss-20b) for canonicalization adjudication per architecture.md §4
            resp = self.client.chat_completion(
                messages=messages,
                model_role="canonicalizer_fast",
                temperature=0.0,
                response_json=True,
                reasoning_effort="low"
            )
            if isinstance(resp, dict) and "decision" in resp:
                return resp
        except Exception as e:
            logger.warning(f"Adjudicator primary model call failed: {e}. Trying canonicalizer_fast...")
            try:
                resp = self.client.chat_completion(
                    messages=messages,
                    model_role="canonicalizer_fast",
                    temperature=0.0,
                    response_json=True,
                    reasoning_effort="low"
                )
                if isinstance(resp, dict) and "decision" in resp:
                    return resp
            except Exception as e2:
                logger.error(f"Adjudicator fallback call failed: {e2}. Defaulting to new_entry.")

        # Safe fallback if LLM unreachable: preserve distinctness
        return {
            "decision": "new_entry",
            "matched_id": None,
            "canonical_name": mention_text,
            "reason": "Fallback: preserved distinctness as new canonical entry"
        }

    def _create_new_entity(
        self,
        canonical_name: str,
        embedding: Any,
        mention_text: str,
        reason: str,
        similarity: float,
        is_llm: bool = False,
        model_used: str = "deterministic"
    ) -> Tuple[str, str]:
        """Insert new canonical entity and log decision."""
        entity_id = f"ent_{uuid.uuid4().hex[:8]}"
        created_at = datetime.utcnow().isoformat() + "Z"
        emb_blob = self.embedder.serialize_vector(embedding)

        conn = get_connection(self.db_path)
        try:
            with conn:
                conn.execute("""
                    INSERT INTO entities (id, canonical_name, entity_type_guess, embedding, created_from_mention, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (entity_id, canonical_name, "organization", emb_blob, mention_text, created_at))
        finally:
            conn.close()

        self._entities_cache.append({
            "id": entity_id,
            "canonical_name": canonical_name,
            "entity_type_guess": "organization",
            "embedding": embedding
        })

        dec_type = "llm_adjudicated" if is_llm else "auto_new"
        self._record_decision(mention_text, entity_id, "entity", dec_type, similarity, reason, model_used=model_used)
        self._decision_cache[f"entity:{mention_text.strip().lower()}"] = (entity_id, canonical_name)
        return entity_id, canonical_name

    def _create_new_metric(
        self,
        canonical_name: str,
        embedding: Any,
        mention_text: str,
        reason: str,
        similarity: float,
        unit: Optional[str] = None,
        is_llm: bool = False,
        model_used: str = "deterministic"
    ) -> Tuple[str, str]:
        """Insert new canonical metric and log decision."""
        metric_id = f"met_{uuid.uuid4().hex[:8]}"
        created_at = datetime.utcnow().isoformat() + "Z"
        emb_blob = self.embedder.serialize_vector(embedding)
        unit_family = "currency" if unit and any(c in unit.lower() for c in ["inr", "rs", "usd", "$", "₹", "cr", "mn", "million"]) else "other"

        conn = get_connection(self.db_path)
        try:
            with conn:
                conn.execute("""
                    INSERT INTO metrics (id, canonical_name, unit_family, embedding, created_from_mention, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (metric_id, canonical_name, unit_family, emb_blob, mention_text, created_at))
        finally:
            conn.close()

        self._metrics_cache.append({
            "id": metric_id,
            "canonical_name": canonical_name,
            "unit_family": unit_family,
            "embedding": embedding
        })

        dec_type = "llm_adjudicated" if is_llm else "auto_new"
        self._record_decision(mention_text, metric_id, "metric", dec_type, similarity, reason, model_used=model_used)
        self._decision_cache[f"metric:{mention_text.strip().lower()}"] = (metric_id, canonical_name)
        return metric_id, canonical_name

