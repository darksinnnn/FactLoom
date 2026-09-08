"""
FactLoom Ingestion Service
Handles parsing PDFs and persisting document/page models to SQLite.
"""

import os
import uuid
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from backend.store.db import get_connection
from backend.ingest.parser import PDFParser, ParsedPage

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self, parser: Optional[PDFParser] = None):
        self.parser = parser or PDFParser()

    def ingest_document(
        self,
        pdf_path: str,
        doc_type_guess: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Parse a PDF and persist document + page records."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"File not found: {pdf_path}")

        filename = os.path.basename(pdf_path)
        parsed_pages = self.parser.parse(pdf_path)
        page_count = len(parsed_pages)
        doc_id = str(uuid.uuid4())
        uploaded_at = datetime.utcnow().isoformat()

        conn = get_connection(db_path)
        with conn:
            conn.execute(
                """
                INSERT INTO documents (id, filename, doc_type_guess, uploaded_at, page_count, file_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (doc_id, filename, doc_type_guess or "pdf", uploaded_at, page_count, os.path.abspath(pdf_path))
            )

            for p in parsed_pages:
                page_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO pages (
                        id, document_id, page_number, width, height,
                        text_blocks, table_blocks, bbox_data, full_text,
                        is_scanned, has_text_layer
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        page_id,
                        doc_id,
                        p.page_number,
                        p.width,
                        p.height,
                        json.dumps(p.text_blocks),
                        json.dumps(p.table_blocks),
                        json.dumps({"blocks": p.text_blocks, "tables": p.table_blocks}),
                        p.full_text,
                        1 if p.is_scanned else 0,
                        1 if p.has_text_layer else 0
                    )
                )

        conn.close()
        logger.info(f"Successfully ingested {filename} (ID: {doc_id}) with {page_count} pages.")
        return {
            "document_id": doc_id,
            "filename": filename,
            "page_count": page_count,
            "uploaded_at": uploaded_at
        }

    def get_document_stats(self, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all ingested documents and their page parsing statistics."""
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.id, d.filename, d.page_count, d.uploaded_at,
                   COUNT(p.id) as stored_pages,
                   SUM(CASE WHEN length(trim(p.full_text)) > 0 THEN 1 ELSE 0 END) as pages_with_text,
                   SUM(CASE WHEN p.is_scanned = 1 THEN 1 ELSE 0 END) as scanned_pages
            FROM documents d
            LEFT JOIN pages p ON d.id = p.document_id
            GROUP BY d.id
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
