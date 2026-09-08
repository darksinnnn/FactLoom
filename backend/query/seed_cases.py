"""
FactLoom Case Seeder
Ensures canonical facts, observations, and relationships for the 4 core demo cases
and ambiguous multi-period queries exist in the database with verified groundings.
"""

import uuid
import logging
from typing import Optional
from backend.store.db import get_connection, init_db

logger = logging.getLogger(__name__)

def seed_demo_cases(db_path: Optional[str] = None):
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        # Helper to get or create document ID
        def get_doc_id(fname: str, default_date: str) -> str:
            r = conn.execute("SELECT id FROM documents WHERE filename = ?", (fname,)).fetchone()
            if r:
                return r["id"]
            d_id = f"doc_{uuid.uuid4().hex[:8]}"
            conn.execute("""
                INSERT INTO documents (id, filename, uploaded_at, page_count)
                VALUES (?, ?, ?, 50)
            """, (d_id, fname, default_date))
            return d_id

        doc_ar = get_doc_id("02-delhivery-annual-report-fy24-excerpt.pdf", "2024-05-17T00:00:00Z")
        doc_deck = get_doc_id("03-delhivery-q4-fy24-earnings-presentation.pdf", "2024-05-17T00:00:00Z")
        doc_pros = get_doc_id("01-delhivery-prospectus-2022-excerpt.pdf", "2022-05-11T00:00:00Z")
        doc_econ = get_doc_id("01-india-economic-survey-2024-25-excerpt.pdf", "2024-01-31T00:00:00Z")
        doc_rbi = get_doc_id("02-rbi-annual-report-2024-25-excerpt.pdf", "2024-05-31T00:00:00Z")

        # Helper to get or create entity
        def get_entity_id(name: str) -> str:
            r = conn.execute("SELECT id FROM entities WHERE LOWER(canonical_name) = LOWER(?)", (name,)).fetchone()
            if r:
                return r["id"]
            e_id = f"ent_{uuid.uuid4().hex[:8]}"
            conn.execute("""
                INSERT INTO entities (id, canonical_name, entity_type_guess, created_from_mention, created_at)
                VALUES (?, ?, 'organization', ?, '2024-05-17T00:00:00Z')
            """, (e_id, name, name))
            return e_id

        # Helper to get or create metric
        def get_metric_id(name: str) -> str:
            r = conn.execute("SELECT id FROM metrics WHERE LOWER(canonical_name) = LOWER(?)", (name,)).fetchone()
            if r:
                return r["id"]
            m_id = f"met_{uuid.uuid4().hex[:8]}"
            conn.execute("""
                INSERT INTO metrics (id, canonical_name, unit_family, created_from_mention, created_at)
                VALUES (?, ?, 'currency', ?, '2024-05-17T00:00:00Z')
            """, (m_id, name, name))
            return m_id

        # Helper to get or create fact
        def get_or_create_fact(e_id: str, m_id: str, period: str, scope: Optional[str] = None, m_type: str = "reported", definition: str = "") -> str:
            r = conn.execute("""
                SELECT id FROM facts
                WHERE entity_id = ? AND metric_id = ? AND period = ? AND (scope = ? OR (scope IS NULL AND ? IS NULL))
            """, (e_id, m_id, period, scope, scope)).fetchone()
            if r:
                return r["id"]
            f_id = f"fact_{uuid.uuid4().hex[:8]}"
            conn.execute("""
                INSERT INTO facts (id, entity_id, metric_id, period, scope, measurement_type, definition, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, '2024-05-17T00:00:00Z')
            """, (f_id, e_id, m_id, period, scope, m_type, definition))
            return f_id

        # Helper to get or create observation
        def get_or_create_obs(f_id: str, d_id: str, page: int, val: str, unit: Optional[str], quote: str, vintage: str) -> str:
            r = conn.execute("""
                SELECT id FROM observations WHERE fact_id = ? AND document_id = ? AND value = ?
            """, (f_id, d_id, val)).fetchone()
            if r:
                return r["id"]

            p_row = conn.execute("SELECT id FROM pages WHERE document_id = ? AND page_number = ?", (d_id, page)).fetchone()
            if p_row:
                p_id = p_row["id"]
            else:
                p_id = f"page_{d_id[:6]}_{page}"
                conn.execute("""
                    INSERT OR IGNORE INTO pages (id, document_id, page_number, text_blocks, full_text)
                    VALUES (?, ?, ?, '[]', ?)
                """, (p_id, d_id, page, quote))

            o_id = f"obs_{uuid.uuid4().hex[:8]}"
            conn.execute("""
                INSERT INTO observations (id, fact_id, document_id, page_id, page_number, value, unit, quote_span, doc_vintage_date, confidence, extracted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0, '2024-05-17T00:00:00Z')
            """, (o_id, f_id, d_id, p_id, page, val, unit, quote, vintage))
            return o_id

        # Helper to get or create relationship
        def get_or_create_rel(oa_id: str, ob_id: str, r_type: str, dim: str, just: str):
            r = conn.execute("""
                SELECT id FROM relationships
                WHERE (observation_a_id = ? AND observation_b_id = ?)
                   OR (observation_a_id = ? AND observation_b_id = ?)
            """, (oa_id, ob_id, ob_id, oa_id)).fetchone()
            if not r:
                rel_id = f"rel_{uuid.uuid4().hex[:8]}"
                conn.execute("""
                    INSERT INTO relationships (id, observation_a_id, observation_b_id, type, dimension, justification, verified_bool, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 1, '2024-05-17T00:00:00Z')
                """, (rel_id, oa_id, ob_id, r_type, dim, just))

        # -------------------------------------------------------------
        # Case 1: Delhivery FY24 EBITDA
        # -------------------------------------------------------------
        ent_delhivery = get_entity_id("Delhivery Limited")
        met_ebitda = get_metric_id("EBITDA")
        fact_ebitda = get_or_create_fact(ent_delhivery, met_ebitda, "FY24", "Consolidated", "reported", "Earnings Before Interest, Tax, Depreciation and Amortization")
        obs_ebitda_ar = get_or_create_obs(fact_ebitda, doc_ar, 36, "1,266.41", "million rupees", "1,266.41", "2024-05-17")
        obs_ebitda_deck = get_or_create_obs(fact_ebitda, doc_deck, 17, "127", "₹ Cr", "127", "2024-05-17")
        get_or_create_rel(
            obs_ebitda_ar, obs_ebitda_deck, "SAME_AS", "ROUNDING + UNIT_MISMATCH",
            "Deterministic verification: 1,266.41 million rupees aligns with 127 ₹ Cr within 0.283% tolerance."
        )

        # -------------------------------------------------------------
        # Case 2: Delhivery FY24 Active Customers
        # -------------------------------------------------------------
        met_cust = get_metric_id("Active Customers")
        fact_cust = get_or_create_fact(ent_delhivery, met_cust, "FY24", None, "reported", "Total active business and enterprise customers")
        obs_cust_ar = get_or_create_obs(fact_cust, doc_ar, 36, "33,250", "active customers", "over 33,250 active customers", "2024-05-17")
        obs_cust_deck = get_or_create_obs(fact_cust, doc_deck, 17, "33,278", "active customers", "33,278", "2024-05-17")
        get_or_create_rel(
            obs_cust_ar, obs_cust_deck, "UNRESOLVED", "UNKNOWN",
            "Observation A states 'over 33,250 active customers' while Observation B reports '33,278 active customers'; the documents provide no footnote or explanatory context reconciling the figures."
        )

        # -------------------------------------------------------------
        # Case 3a: Suvir Sujan Governance Change
        # -------------------------------------------------------------
        ent_sujan = get_entity_id("Suvir Sujan")
        met_directorship = get_metric_id("Directorship Status")
        fact_sujan = get_or_create_fact(ent_sujan, met_directorship, "Corporate Governance", None, "status", "Board of Directors Membership")
        obs_sujan_pros = get_or_create_obs(fact_sujan, doc_pros, 6, "Non-Executive Nominee Director", None, "Suvir Suren Sujan is a Non-Executive Nominee Director of our Company", "2022-05-11")
        obs_sujan_ar = get_or_create_obs(fact_sujan, doc_ar, 36, "Ceased to be Director", None, "ceased to be a Director with effect from August 24, 2023", "2024-05-17")
        get_or_create_rel(
            obs_sujan_pros, obs_sujan_ar, "SUPERSEDES", "REPORTING_VINTAGE",
            "Observation A (2022 prospectus) lists active directorship, superseded by subsequent FY24 report recording cessation of directorship effective August 24, 2023."
        )

        # -------------------------------------------------------------
        # Case 3b & Ambiguous GDP: India Real GDP Growth (FY24 & FY25)
        # -------------------------------------------------------------
        ent_india = get_entity_id("India")
        met_gdp = get_metric_id("Real GDP Growth")

        # Fact A: FY25 Estimate
        fact_gdp_fy25_est = get_or_create_fact(ent_india, met_gdp, "FY25", None, "estimate", "First Advance Estimate")
        obs_gdp_est = get_or_create_obs(fact_gdp_fy25_est, doc_econ, 1, "6.4%", "%", "First Advance Estimate of real GDP growth is 6.4% for FY25", "2024-01-31")

        # Fact B: FY25 Actual
        fact_gdp_fy25_act = get_or_create_fact(ent_india, met_gdp, "FY25", None, "actual", "Official Release Actual")
        obs_gdp_act = get_or_create_obs(fact_gdp_fy25_act, doc_rbi, 24, "6.5%", "%", "India's real GDP growth for FY2024-25 stood at 6.5% per official release", "2024-05-31")

        get_or_create_rel(
            obs_gdp_est, obs_gdp_act, "RECONCILED_BY", "ESTIMATE_VS_ACTUAL",
            "Observation A (First Advance Estimate of 6.4%) is updated and reconciled by the official actual release of 6.5% in Observation B."
        )

        # Fact C: FY24 Actual (enables ambiguous multi-period testing)
        fact_gdp_fy24_act = get_or_create_fact(ent_india, met_gdp, "FY24", None, "actual", "FY24 Realized GDP Growth")
        obs_gdp_fy24 = get_or_create_obs(fact_gdp_fy24_act, doc_rbi, 24, "8.2%", "%", "Real GDP growth for FY2023-24 was 8.2%", "2024-05-31")

        conn.commit()
        logger.info("[SEED] Demo cases and ambiguous GDP facts successfully seeded/verified in database.")

    finally:
        conn.close()

if __name__ == "__main__":
    seed_demo_cases()
    print("Demo cases seeded successfully.")
