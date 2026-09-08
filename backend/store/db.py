"""
FactLoom SQLite Database & Storage Engine
Relational core as specified in architecture.md §3.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.environ.get("FACTLOOM_DB_PATH", "factloom.db")

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables according to architecture.md §3 schema."""
    conn = get_connection(db_path)
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            doc_type_guess TEXT,
            uploaded_at TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            file_path TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pages (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            page_number INTEGER NOT NULL,
            width REAL,
            height REAL,
            text_blocks TEXT NOT NULL,       -- JSON array of text blocks with bboxes
            table_blocks TEXT,              -- JSON array of structured tables
            bbox_data TEXT,                 -- Full bounding box metadata
            full_text TEXT NOT NULL,
            is_scanned INTEGER DEFAULT 0,
            has_text_layer INTEGER DEFAULT 1,
            UNIQUE(document_id, page_number)
        );

        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            canonical_name TEXT UNIQUE NOT NULL,
            entity_type_guess TEXT,         -- organization / person / place / other
            embedding BLOB,                 -- serialized float vector or JSON
            created_from_mention TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS metrics (
            id TEXT PRIMARY KEY,
            canonical_name TEXT UNIQUE NOT NULL,
            unit_family TEXT,               -- currency / percentage / count / ratio / etc.
            embedding BLOB,
            created_from_mention TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS facts (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL REFERENCES entities(id),
            metric_id TEXT NOT NULL REFERENCES metrics(id),
            scope TEXT,                     -- consolidated / standalone / segment / national
            period TEXT,                    -- FY24, Q4 FY24, 2024-25, etc.
            measurement_type TEXT,          -- flow / stock / rate / ratio / nominal / real
            definition TEXT,                -- context or line-item formula
            embedding BLOB,
            created_at TEXT NOT NULL,
            UNIQUE(entity_id, metric_id, scope, period, measurement_type, definition)
        );

        CREATE TABLE IF NOT EXISTS observations (
            id TEXT PRIMARY KEY,
            fact_id TEXT NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
            document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            page_id TEXT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
            page_number INTEGER NOT NULL,
            value TEXT NOT NULL,            -- string representation to preserve decimal precision
            unit TEXT,
            quote_span TEXT NOT NULL,       -- verbatim substring for grounding
            bbox TEXT,                      -- JSON: [x0, y0, x1, y1]
            confidence REAL NOT NULL,
            doc_vintage_date TEXT,
            extracted_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS relationships (
            id TEXT PRIMARY KEY,
            observation_a_id TEXT NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
            observation_b_id TEXT NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
            type TEXT NOT NULL,             -- SAME_AS / CONTRADICTS / SUPERSEDES / RECONCILED_BY / UNRESOLVED
            dimension TEXT NOT NULL,        -- UNIT_MISMATCH / ROUNDING / PERIOD_MISMATCH / SCOPE_MISMATCH / DEFINITION_MISMATCH / ESTIMATE_VS_ACTUAL / REPORTING_VINTAGE / RESTATEMENT / DERIVED_VALUE / TRUE_CONTRADICTION / UNKNOWN
            justification TEXT NOT NULL,
            verified_bool INTEGER NOT NULL, -- 1 = verified by deterministic check, 0 = unverified/failed
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS registry_decisions (
            id TEXT PRIMARY KEY,
            mention_text TEXT NOT NULL,
            resolved_entity_or_metric_id TEXT NOT NULL,
            target_type TEXT NOT NULL,      -- entity / metric
            decision_type TEXT NOT NULL,    -- auto_alias / auto_new / llm_adjudicated
            similarity_score REAL,
            llm_reasoning TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS eval_runs (
            id TEXT PRIMARY KEY,
            run_at TEXT NOT NULL,
            question TEXT NOT NULL,
            expected TEXT NOT NULL,
            actual TEXT NOT NULL,
            category TEXT NOT NULL,
            pass_bool INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_pages_doc_num ON pages(document_id, page_number);
        CREATE INDEX IF NOT EXISTS idx_observations_fact ON observations(fact_id);
        CREATE INDEX IF NOT EXISTS idx_observations_doc ON observations(document_id);
        CREATE INDEX IF NOT EXISTS idx_relationships_pair ON relationships(observation_a_id, observation_b_id);
        CREATE INDEX IF NOT EXISTS idx_registry_decisions_mention ON registry_decisions(mention_text);
        """)
    conn.close()

if __name__ == "__main__":
    init_db()
    print("FactLoom database schema initialized successfully.")
